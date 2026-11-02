"""无头对战评估：agent vs Robot 或 agent vs 快照 DQN（双 checkpoint 对战），输出胜率与押注统计。

用法：
    python -m scripts.evaluate                       # 用保留权重 dqn_model_1.pth vs Robot
    python -m scripts.evaluate --rounds 500 --seed 7
    python -m scripts.evaluate --checkpoint run/dqn_ep20_seed7.pth
    # 双 checkpoint 对战（DQN vs DQN，每轮交换座位，对手为冻结策略）：
    python -m scripts.evaluate --rounds 500 --seed 7 \
        --checkpoint run/dqn_sp_ep200_seed7.pth \
        --opponent-checkpoint run/dqn_sp_opp_ep200_seed7.pth
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from agents.dqn import DQNAgent
from scripts.env import ACTION_NAMES, CardGameEnv

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CKPT = REPO / "dqn_model_1.pth"
DEFAULT_OUT = REPO / "run"


def _action_distribution(counts: Counter[int]) -> dict[str, float]:
    total = sum(counts.values()) or 1
    return {ACTION_NAMES.get(k, str(k)): round(v / total, 4) for k, v in sorted(counts.items())}


def evaluate(
    rounds: int = 100,
    seed: int = 20261021,
    checkpoint: Path | str = DEFAULT_CKPT,
    out_dir: Path | str = DEFAULT_OUT,
    epsilon: float = 0.0,
    verbose: bool = True,
    opponent_checkpoint: Path | str | None = None,
) -> dict:
    """评估主 checkpoint。

    - ``opponent_checkpoint=None``：对手为内置 Robot（旧行为）。
    - ``opponent_checkpoint`` 非空：对手为加载自该 checkpoint 的冻结 DQN（自博弈对战模式，
      每轮交换座位以消除先手偏置；summary 增加 ``opponent_win_rate`` 与对手动作分布）。
    """
    agent = DQNAgent.from_checkpoint(checkpoint, seed=seed, epsilon=epsilon)
    opponent: DQNAgent | None = None
    if opponent_checkpoint is None:
        env = CardGameEnv(seed=seed)
    else:
        opponent = DQNAgent.from_checkpoint(
            opponent_checkpoint, seed=seed + 1, epsilon=0.0
        )
        # 对手为冻结策略（不学习）；DQN 对手下 env 自动启用每轮座位交换
        env = CardGameEnv(seed=seed, opponent=opponent, opponent_replay_every=None)

    wins = 0
    opp_wins = 0
    rewards: list[float] = []
    action_counter: Counter[int] = Counter()
    pots: list[int] = []

    for _ in range(rounds):
        state = env.reset()
        done = False
        episode_reward = 0.0
        while not done:
            legal = env.legal_actions()
            if not legal:
                break
            action = agent.act(state, legal)
            action_counter[int(action)] += 1
            result = env.step(action)
            episode_reward += result.reward
            state = result.observation
            done = result.done
        rewards.append(episode_reward)
        if episode_reward > 0:
            wins += 1
        elif episode_reward < 0:
            opp_wins += 1
        pots.append(env.room.all_bet)

    summary = {
        "rounds": rounds,
        "seed": seed,
        "checkpoint": str(checkpoint),
        "opponent_checkpoint": str(opponent_checkpoint) if opponent_checkpoint is not None else None,
        "epsilon": epsilon,
        "win_rate": wins / rounds,
        "opponent_win_rate": opp_wins / rounds,
        "avg_reward": float(np.mean(rewards)),
        "avg_pot": float(np.mean(pots)),
        "action_distribution": _action_distribution(action_counter),
        "opponent_action_distribution": _action_distribution(env.opponent_action_counts),
    }

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"eval_seed{seed}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if verbose:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="炸金花 agent vs Robot / 双 checkpoint 评估（无头）")
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--checkpoint", default=str(DEFAULT_CKPT))
    parser.add_argument(
        "--opponent-checkpoint",
        default=None,
        help="对手 DQN checkpoint（缺省为内置 Robot；给出后进入双 checkpoint 对战模式）",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--epsilon", type=float, default=0.0)
    args = parser.parse_args()
    evaluate(
        rounds=args.rounds,
        seed=args.seed,
        checkpoint=args.checkpoint,
        out_dir=args.out,
        epsilon=args.epsilon,
        opponent_checkpoint=Path(args.opponent_checkpoint) if args.opponent_checkpoint else None,
    )


if __name__ == "__main__":
    main()
