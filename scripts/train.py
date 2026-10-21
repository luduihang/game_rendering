"""参数化训练入口（无头，不依赖 pygame）。

用法：
    python -m scripts.train --episodes 20 --seed 20261021
    python -m scripts.train --episodes 200 --seed 7 --device cuda --out run/exp1

产物统一写入 ``run/``（.gitignore 已覆盖），包括模型权重与训练摘要。
同种子两次运行应产出逐位一致的权重（见 tests/test_scripts.py）。
"""

from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

from agents.dqn import DQNAgent, DQNConfig, weights_hash
from scripts.env import CardGameEnv, to_transition

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / "run"


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train(
    episodes: int = 20,
    seed: int = 20261021,
    device: str = "cpu",
    out_dir: Path | str = DEFAULT_OUT,
    config: DQNConfig | None = None,
    min_episodes_before_save: int = 1,
    verbose: bool = True,
) -> dict:
    set_global_seed(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = config or DQNConfig(device=device, epsilon_start=1.0)
    agent = DQNAgent(input_dim=4, action_dim=6, config=cfg, seed=seed)
    env = CardGameEnv(seed=seed)

    rewards: list[float] = []
    wins = 0
    started = time.perf_counter()

    for episode in range(1, episodes + 1):
        state = env.reset()
        total_reward = 0.0
        done = False
        steps = 0
        while not done:
            legal = env.legal_actions()
            if not legal:
                break
            action = agent.act(state, legal)
            result = env.step(action)
            agent.observe(to_transition(state, action, result))
            agent.replay()
            total_reward += result.reward
            state = result.observation
            done = result.done
            steps += 1

        rewards.append(total_reward)
        if total_reward > 0:
            wins += 1
        if verbose and (episode % max(1, episodes // 10) == 0 or episode == 1):
            recent = np.mean(rewards[-20:])
            print(f"episode {episode:4d}/{episodes} | reward {total_reward:8.1f} | "
                  f"avg20 {recent:8.2f} | eps {agent.epsilon:.3f} | steps {steps}")

    elapsed = time.perf_counter() - started
    summary = {
        "episodes": episodes,
        "seed": seed,
        "device": device,
        "wins": wins,
        "win_rate": wins / episodes,
        "avg_reward": float(np.mean(rewards)),
        "epsilon_final": agent.epsilon,
        "weights_hash": weights_hash(agent),
        "elapsed_sec": round(elapsed, 3),
        "config": asdict(cfg),
    }

    if episodes >= min_episodes_before_save:
        ckpt = out_dir / f"dqn_ep{episodes}_seed{seed}.pth"
        agent.save(ckpt)
        summary["checkpoint"] = str(ckpt)

    (out_dir / f"summary_seed{seed}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if verbose:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="炸金花 DQN 训练（无头）")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    train(episodes=args.episodes, seed=args.seed, device=args.device, out_dir=args.out)


if __name__ == "__main__":
    main()
