"""参数化训练入口（无头，不依赖 pygame）。

用法：
    python -m scripts.train --episodes 20 --seed 20261021
    python -m scripts.train --episodes 200 --seed 7 --device cuda --out run/exp1
    # 自博弈（DQN vs DQN）：
    python -m scripts.train --episodes 200 --seed 7 --opponent-mode self
    python -m scripts.train --episodes 200 --seed 7 --opponent-mode snapshot \
        --opponent-ckpt run/dqn_sp_opp_ep200_seed7.pth
    # 推荐自博弈配方（100 局内打破单动作塌缩，见 docs/selfplay_train_report.md）：
    python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7

产物统一写入 ``run/``（.gitignore 已覆盖），包括模型权重与训练摘要。
同种子两次运行应产出逐位一致的权重（见 tests/test_scripts.py、tests/test_selfplay.py）。

对手模式（--opponent-mode）：
- ``robot``（缺省）：对手为内置 Robot，行为与旧实现一致，checkpoint 命名沿用 ``dqn_ep{N}_seed{S}.pth``。
- ``self``：对手为在线 DQN（自博弈）。对手按 ``--opponent-replay-every`` 降频 replay
  （epsilon 在 replay 内衰减，同频会让双方探索同步消失、策略塌缩），
  并按 ``--opponent-sync-every`` 周期用主策略快照重置对手。
  产物：主策略 ``dqn_sp_ep{N}_seed{S}.pth`` + 对手策略 ``dqn_sp_opp_ep{N}_seed{S}.pth``。
- ``snapshot``：对手从 ``--opponent-ckpt`` 加载的固定快照（不学习），产物命名同 ``self``。
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

from agents.dqn import DQNAgent, DQNConfig, weights_hash
from scripts.env import ACTION_NAMES, CardGameEnv, to_transition

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / "run"

OPPONENT_MODES = ("robot", "self", "snapshot")

#: 推荐自博弈配方（R-c1712b23 验收版）：按押注额的零和塑形 k=50 打破「全部 bet_100」塌缩，
#: 贪心策略随牌力变化（弱牌几乎不加注、强牌大注占比显著更高），100/100 自然终局、
#: 胜率不一边倒（seed=7 实测 56/44，详见 docs/selfplay_train_report.md）。
#: 注意：hidden 必须保持默认 (128, 64)——DQNAgent.from_checkpoint 不推断隐藏层宽度，
#: 自定义宽度（如 (32,16)）会导致下游 UI 加载 size mismatch。
SELFPLAY_V1 = dict(
    opponent_mode="self",
    opponent_epsilon=0.25,
    opponent_replay_every=1,
    strength_shaping=50.0,
    # hidden 缺省 None = DQNConfig 默认 (128, 64)，勿改（见上注）
    lr=3e-2,
    gamma=0.95,
    batch_size=4,
    epsilon_start=0.5,
    epsilon_decay=0.99,
)


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _action_distribution(counts: Counter[int]) -> dict[str, float]:
    total = sum(counts.values()) or 1
    return {ACTION_NAMES.get(k, str(k)): round(v / total, 4) for k, v in sorted(counts.items())}


def train(
    episodes: int = 20,
    seed: int = 20261021,
    device: str = "cpu",
    out_dir: Path | str = DEFAULT_OUT,
    config: DQNConfig | None = None,
    min_episodes_before_save: int = 1,
    verbose: bool = True,
    opponent_mode: str = "robot",
    opponent_ckpt: Path | str | None = None,
    opponent_sync_every: int | None = None,
    opponent_replay_every: int = 4,
    opponent_epsilon: float | None = None,
    strength_shaping: float = 0.0,
    hidden: tuple[int, int] | None = None,
) -> dict:
    """训练主策略。

    自博弈参数：
    - ``opponent_mode``：``"robot" | "self" | "snapshot"``。
    - ``opponent_ckpt``：snapshot 模式必填，对手策略 checkpoint。
    - ``opponent_sync_every``：self 模式下每多少局用主策略快照重置对手。
      缺省 None = 自动（``max(1, episodes // 4)``）；0 = 关闭。
    - ``opponent_replay_every``：self 模式下对手每多少步 replay 一次（降频，防探索同步塌缩）。
    - ``opponent_epsilon``：对手初始 epsilon。缺省 None = self 模式 1.0 / snapshot 模式 0.0。
    - ``strength_shaping``：押注零和塑形系数（默认 0 = 关闭）；详见 env.CardGameEnv。
    - ``hidden``：主策略与对手共用的隐藏层宽度（缺省 None = DQNConfig 默认 (128, 64)）。
    """
    if opponent_mode not in OPPONENT_MODES:
        raise ValueError(f"未知 opponent_mode: {opponent_mode!r}（可选 {OPPONENT_MODES}）")
    if opponent_mode == "snapshot" and opponent_ckpt is None:
        raise ValueError("opponent_mode='snapshot' 必须提供 opponent_ckpt")

    set_global_seed(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = config or DQNConfig(device=device, epsilon_start=1.0)
    if hidden is not None:
        cfg = DQNConfig(**{**cfg.__dict__, "hidden": tuple(hidden)})
    agent = DQNAgent(input_dim=4, action_dim=6, config=cfg, seed=seed)

    opponent: DQNAgent | None = None
    sync_every = 0
    if opponent_mode == "robot":
        env = CardGameEnv(seed=seed)
    elif opponent_mode == "self":
        epsilon = 1.0 if opponent_epsilon is None else float(opponent_epsilon)
        opp_cfg = DQNConfig(
            device=device, epsilon_start=epsilon,
            hidden=tuple(hidden) if hidden is not None else (128, 64),
        )
        opponent = DQNAgent(input_dim=4, action_dim=6, config=opp_cfg, seed=seed + 1, epsilon=epsilon)
        env = CardGameEnv(
            seed=seed, opponent=opponent,
            opponent_replay_every=opponent_replay_every, strength_shaping=strength_shaping,
        )
        sync_every = max(1, episodes // 4) if opponent_sync_every is None else int(opponent_sync_every)
    else:  # snapshot
        epsilon = 0.0 if opponent_epsilon is None else float(opponent_epsilon)
        opponent = DQNAgent.from_checkpoint(
            opponent_ckpt, seed=seed + 1, epsilon=epsilon, device=device,
            config=DQNConfig(hidden=tuple(hidden)) if hidden is not None else None,
        )
        # 快照对手为冻结策略：不 observe/replay（env 侧 opponent_replay_every=None）
        env = CardGameEnv(
            seed=seed, opponent=opponent, opponent_replay_every=None, strength_shaping=strength_shaping
        )

    rewards: list[float] = []
    episode_steps: list[int] = []
    natural_end = 0
    wins = 0
    opp_wins = 0
    agent_actions: Counter[int] = Counter()
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
            agent_actions[int(action)] += 1
            result = env.step(action)
            agent.observe(to_transition(state, action, result))
            agent.replay()
            total_reward += result.reward
            state = result.observation
            done = result.done
            steps += 1

        rewards.append(total_reward)
        episode_steps.append(steps)
        if env.room is not None and env.room.finish:
            natural_end += 1
        if strength_shaping != 0.0:
            # 塑形会干扰奖励符号，胜率以自然终局的赢家为准（MAX_STEPS 强停算平局）
            winner = env.room.winner if env.room is not None and env.room.finish else None
            if winner == env.agent_player:
                wins += 1
            elif winner == env.opponent_seat:
                opp_wins += 1
        elif total_reward > 0:
            wins += 1
        elif total_reward < 0:
            opp_wins += 1
        if verbose and (episode % max(1, episodes // 10) == 0 or episode == 1):
            recent = np.mean(rewards[-20:])
            extra = f" | opp_eps {opponent.epsilon:.3f}" if opponent is not None else ""
            print(f"episode {episode:4d}/{episodes} | reward {total_reward:8.1f} | "
                  f"avg20 {recent:8.2f} | eps {agent.epsilon:.3f}{extra} | steps {steps}")

        if (
            opponent_mode == "self"
            and sync_every > 0
            and opponent is not None
            and episode % sync_every == 0
            and episode < episodes
        ):
            # 周期性用主策略快照重置对手，防止对手漂移与探索同步塌缩
            tmp = out_dir / f"_sync_tmp_seed{seed}.pth"
            agent.save(tmp)
            opponent.load(tmp)

    elapsed = time.perf_counter() - started
    summary = {
        "episodes": episodes,
        "seed": seed,
        "device": device,
        "opponent_mode": opponent_mode,
        "strength_shaping": strength_shaping,
        "wins": wins,
        "win_rate": wins / episodes,
        "agent_win_rate": wins / episodes,
        "opponent_wins": opp_wins,
        "opponent_win_rate": opp_wins / episodes,
        "avg_reward": float(np.mean(rewards)),
        "agent_action_distribution": _action_distribution(agent_actions),
        "opponent_action_distribution": _action_distribution(env.opponent_action_counts),
        "epsilon_final": agent.epsilon,
        "total_steps": int(sum(episode_steps)),
        "avg_steps_per_episode": round(float(np.mean(episode_steps)), 3),
        "natural_end_rate": natural_end / episodes,
        "weights_hash": weights_hash(agent),
        "opponent_weights_hash": weights_hash(opponent) if opponent is not None else None,
        "elapsed_sec": round(elapsed, 3),
        "config": asdict(cfg),
    }

    if episodes >= min_episodes_before_save:
        if opponent_mode == "robot":
            ckpt = out_dir / f"dqn_ep{episodes}_seed{seed}.pth"
        else:
            ckpt = out_dir / f"dqn_sp_ep{episodes}_seed{seed}.pth"
        agent.save(ckpt)
        summary["checkpoint"] = str(ckpt)
        if opponent is not None:
            opp_ckpt = out_dir / f"dqn_sp_opp_ep{episodes}_seed{seed}.pth"
            opponent.save(opp_ckpt)
            summary["opponent_checkpoint"] = str(opp_ckpt)

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
    parser.add_argument(
        "--preset",
        default=None,
        choices=["selfplay-v1"],
        help="预设超参组合（显式参数优先）；selfplay-v1 = 推荐 100 局自博弈配方",
    )
    parser.add_argument(
        "--opponent-mode",
        default=None,
        choices=list(OPPONENT_MODES),
        help="对手模式：robot=内置Robot（旧行为）/ self=在线DQN自博弈 / snapshot=固定快照对手",
    )
    parser.add_argument("--opponent-ckpt", default=None, help="snapshot 模式的对手 checkpoint")
    parser.add_argument(
        "--opponent-sync-every",
        type=int,
        default=None,
        help="self 模式：每多少局用主策略快照重置对手（缺省自动 max(1, episodes//4)，0 关闭）",
    )
    parser.add_argument(
        "--opponent-replay-every",
        type=int,
        default=None,
        help="self 模式：对手每多少步 replay 一次（降频防探索同步塌缩；缺省 4）",
    )
    parser.add_argument(
        "--opponent-epsilon",
        type=float,
        default=None,
        help="对手初始 epsilon（缺省：self=1.0 / snapshot=0.0）",
    )
    parser.add_argument(
        "--strength-shaping",
        type=float,
        default=None,
        help="DQN 对手模式：零和「加注者得奖/跟注者付费」塑形系数 k（按加注额计；默认 0 关闭）",
    )
    parser.add_argument("--hidden", default=None, help="隐藏层宽度，如 32,16（主策略与对手共用）")
    parser.add_argument("--lr", type=float, default=None, help="学习率（缺省 DQNConfig 默认 1e-3）")
    parser.add_argument("--gamma", type=float, default=None, help="折扣因子（缺省 0.95）")
    parser.add_argument("--batch-size", type=int, default=None, help="replay 批大小（缺省 32）")
    parser.add_argument("--epsilon-start", type=float, default=None, help="初始 epsilon（缺省 1.0）")
    parser.add_argument("--epsilon-decay", type=float, default=None, help="epsilon 衰减率（缺省 0.995）")
    args = parser.parse_args()

    # 预设 + 显式参数（显式优先）
    p = dict(SELFPLAY_V1) if args.preset == "selfplay-v1" else {}
    for key in ("opponent_mode", "opponent_epsilon", "opponent_replay_every", "strength_shaping",
                "hidden", "lr", "gamma", "batch_size", "epsilon_start", "epsilon_decay"):
        cli = getattr(args, key)
        if cli is not None:
            if key == "hidden":
                cli = tuple(int(x) for x in str(cli).split(","))
            p[key] = cli
    p.setdefault("opponent_mode", "robot")
    p.setdefault("opponent_replay_every", 4)
    p.setdefault("strength_shaping", 0.0)

    config = None
    hyper = {k: p[k] for k in ("hidden", "lr", "gamma", "batch_size", "epsilon_start", "epsilon_decay")
             if k in p}
    if hyper:
        config = DQNConfig(device=args.device, **hyper)

    train(
        episodes=args.episodes,
        seed=args.seed,
        device=args.device,
        out_dir=args.out,
        config=config,
        opponent_mode=p["opponent_mode"],
        opponent_ckpt=Path(args.opponent_ckpt) if args.opponent_ckpt else None,
        opponent_sync_every=args.opponent_sync_every,
        opponent_replay_every=p["opponent_replay_every"],
        # 缺省 None：train() 按模式取缺省（self=1.0 / snapshot=0.0），非 preset 调用不再 KeyError
        opponent_epsilon=p.get("opponent_epsilon"),
        strength_shaping=p["strength_shaping"],
        hidden=p.get("hidden"),
    )


if __name__ == "__main__":
    main()
