"""DQN 智能体（可配置）。

关键设计：
- **D8**：``DQNAgent.from_checkpoint(path)`` 从 checkpoint 的
  ``fc1.weight`` / ``fc3.weight`` 推断输入输出维度，不再硬编码 ``DQN(9, 6)``
  去加载 4 维权重（原实现因此 import 即崩）。
- **D9**：``from_checkpoint`` 默认 ``epsilon=0.0``，让训练好的策略真正生效
  （原实现在主循环里用 ``DQNAgent()`` + ``epsilon=1.0``，实际是随机策略）。
- **D7-d**：任何权重加载都只发生在函数体内，import 本模块不触碰磁盘。
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
import torch.nn as nn

from agents.base import BaseAgent, Transition

REPO_ROOT = Path(__file__).resolve().parents[1]

# 状态编码：3 个盘面特征 + 1 个手牌强度概率 = 4 维（与 dqn_model_1.pth 一致）
BOARD_FEATURES = 3
CARD_FEATURES = 1
DEFAULT_STATE_DIM = BOARD_FEATURES + CARD_FEATURES
DEFAULT_ACTION_DIM = 6


@dataclass(frozen=True)
class DQNConfig:
    hidden: tuple[int, int] = (128, 64)
    lr: float = 1e-3
    gamma: float = 0.95
    batch_size: int = 32
    buffer_size: int = 5000
    epsilon_start: float = 1.0
    epsilon_min: float = 0.01
    epsilon_decay: float = 0.995
    target_sync_every: int = 1
    device: str = "cpu"


class DQN(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, hidden: tuple[int, int] = (128, 64)):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden[0])
        self.fc2 = nn.Linear(hidden[0], hidden[1])
        self.fc3 = nn.Linear(hidden[1], output_dim)

    def forward(self, x):  # noqa: D102
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)


def checkpoint_dims(path) -> tuple[int, int]:
    """从 checkpoint 推断 (input_dim, output_dim)，不依赖调用方声明。"""
    state = torch.load(str(path), map_location="cpu", weights_only=True)
    if "fc1.weight" not in state or "fc3.weight" not in state:
        raise ValueError(f"{path} 不是 DQN checkpoint（缺少 fc1/fc3 权重）")
    return int(state["fc1.weight"].shape[1]), int(state["fc3.weight"].shape[0])


class StateEncoder:
    """把对局状态编码为 DQN 输入向量。

    与 ``draw_me_vs_DQN_Plus.py::get_state`` 保持同一语义：
        盘面：轮次/10、自己已押注/1000、对手已押注/1000
        手牌：击败随机手牌的概率（core.strength 的精确值）
    """

    def __init__(self, strength_fn=None):
        if strength_fn is None:
            from core.strength import beats_probability as strength_fn
        self._strength = strength_fn

    def encode(self, snapshot: dict, player: int, hand) -> np.ndarray:
        board = np.array(
            [
                snapshot["circle"] / 10.0,
                snapshot["bets"][player] / 1000.0,
                snapshot["bets"][1 - player] / 1000.0,
            ],
            dtype=np.float32,
        )
        card = np.array([self._strength(hand)], dtype=np.float32)
        return np.concatenate([board, card])


class DQNAgent(BaseAgent):
    name = "dqn"

    def __init__(
        self,
        input_dim: int = DEFAULT_STATE_DIM,
        action_dim: int = DEFAULT_ACTION_DIM,
        config: DQNConfig | None = None,
        seed: int | None = None,
        epsilon: float | None = None,
    ):
        self.config = config or DQNConfig()
        self.device = torch.device(self.config.device)
        self.input_dim = input_dim
        self.action_dim = action_dim
        self.seed = seed
        self.rng = random.Random(seed)

        self.model = DQN(input_dim, action_dim, self.config.hidden).to(self.device)
        self.target_model = DQN(input_dim, action_dim, self.config.hidden).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.config.lr)
        self.memory: deque[Transition] = deque(maxlen=self.config.buffer_size)
        self.epsilon = self.config.epsilon_start if epsilon is None else float(epsilon)
        self.steps = 0
        self.update_target()

    # ---------- 构造 ----------
    @classmethod
    def from_checkpoint(
        cls,
        path,
        config: DQNConfig | None = None,
        seed: int | None = None,
        epsilon: float = 0.0,
        device: str | None = None,
    ) -> "DQNAgent":
        """按 checkpoint 的实际维度构建并加载权重（D8 + D9）。"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"找不到权重文件: {path}")
        input_dim, action_dim = checkpoint_dims(path)
        cfg = config or DQNConfig()
        if device is not None:
            cfg = DQNConfig(**{**cfg.__dict__, "device": device})
        agent = cls(input_dim=input_dim, action_dim=action_dim, config=cfg, seed=seed, epsilon=epsilon)
        state = torch.load(str(path), map_location=agent.device, weights_only=True)
        agent.model.load_state_dict(state)
        agent.model.eval()
        agent.update_target()
        return agent

    # ---------- 推理 ----------
    def q_values(self, state) -> np.ndarray:
        tensor = torch.as_tensor(np.asarray(state, dtype=np.float32), device=self.device).unsqueeze(0)
        with torch.no_grad():
            return self.model(tensor).cpu().numpy()[0]

    def act(self, observation, legal_actions: Sequence[int]) -> int:
        legal = list(legal_actions)
        if not legal:
            raise ValueError("legal_actions 为空，无法行动")
        if self.epsilon > 0 and self.rng.random() < self.epsilon:
            return self.rng.choice(legal)
        q = self.q_values(observation)
        masked = np.full(self.action_dim, -np.inf, dtype=np.float64)
        masked[legal] = q[legal]
        return int(np.argmax(masked))

    # ---------- 学习 ----------
    def observe(self, transition: Transition) -> None:
        self.memory.append(transition)

    def replay(self) -> float | None:
        if len(self.memory) < self.config.batch_size:
            return None
        minibatch = self.rng.sample(self.memory, self.config.batch_size)
        states = torch.as_tensor(np.array([t.state for t in minibatch], dtype=np.float32), device=self.device)
        actions = torch.as_tensor(np.array([t.action for t in minibatch], dtype=np.int64), device=self.device)
        rewards = torch.as_tensor(np.array([t.reward for t in minibatch], dtype=np.float32), device=self.device)
        next_states = torch.as_tensor(
            np.array([t.next_state for t in minibatch], dtype=np.float32), device=self.device
        )
        dones = torch.as_tensor(np.array([t.done for t in minibatch], dtype=np.float32), device=self.device)

        current_q = self.model(states).gather(1, actions.unsqueeze(1))
        with torch.no_grad():
            next_q = self.target_model(next_states).max(1)[0]
        target_q = rewards + (1 - dones) * self.config.gamma * next_q
        loss = nn.functional.mse_loss(current_q.squeeze(), target_q)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.steps += 1
        if self.epsilon > self.config.epsilon_min:
            self.epsilon = max(self.config.epsilon_min, self.epsilon * self.config.epsilon_decay)
        if self.config.target_sync_every and self.steps % self.config.target_sync_every == 0:
            self.update_target()
        return float(loss.item())

    def update_target(self) -> None:
        self.target_model.load_state_dict(self.model.state_dict())

    def reset(self) -> None:
        """每局重置（不重置已学到的权重）。"""

    # ---------- 持久化 ----------
    def save(self, path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), str(path))

    def load(self, path) -> None:
        state = torch.load(str(path), map_location=self.device, weights_only=True)
        self.model.load_state_dict(state)
        self.update_target()


def weights_hash(agent: DQNAgent) -> str:
    """权重指纹，用于可复现性验证（同种子两次训练应逐位一致）。"""
    import hashlib

    digest = hashlib.sha256()
    for name, tensor in sorted(agent.model.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().numpy().tobytes())
    return digest.hexdigest()
