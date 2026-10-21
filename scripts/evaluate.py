"""无头对战评估：agent vs Robot，输出胜率与押注统计。

用法：
    python -m scripts.evaluate                       # 用保留权重 dqn_model_1.pth
    python -m scripts.evaluate --rounds 500 --seed 7
    python -m scripts.evaluate --checkpoint run/dqn_ep20_seed7.pth
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from agents.dqn import DQNAgent
from core.rules import Action
from scripts.env import CardGameEnv

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CKPT = REPO / "dqn_model_1.pth"
DEFAULT_OUT = REPO / "run"


def evaluate(
    rounds: int = 100,
    seed: int = 20261021,
    checkpoint: Path | str = DEFAULT_CKPT,
    out_dir: Path | str = DEFAULT_OUT,
    epsilon: float = 0.0,
    verbose: bool = True,
) -> dict:
    agent = DQNAgent.from_checkpoint(checkpoint, seed=seed, epsilon=epsilon)
    env = CardGameEnv(seed=seed)

    wins = 0
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
            action_counter[action] += 1
            result = env.step(action)
            episode_reward += result.reward
            state = result.observation
            done = result.done
        rewards.append(episode_reward)
        if episode_reward > 0:
            wins += 1
        pots.append(env.room.all_bet)

    action_names = {
        int(Action.BET_10): "bet_10",
        int(Action.BET_20): "bet_20",
        int(Action.BET_50): "bet_50",
        int(Action.BET_100): "bet_100",
        int(Action.FOLD): "fold",
        int(Action.COMPARE): "compare",
    }
    total_actions = sum(action_counter.values()) or 1
    summary = {
        "rounds": rounds,
        "seed": seed,
        "checkpoint": str(checkpoint),
        "epsilon": epsilon,
        "win_rate": wins / rounds,
        "avg_reward": float(np.mean(rewards)),
        "avg_pot": float(np.mean(pots)),
        "action_distribution": {
            action_names.get(k, str(k)): round(v / total_actions, 4) for k, v in sorted(action_counter.items())
        },
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
    parser = argparse.ArgumentParser(description="炸金花 agent vs Robot 评估（无头）")
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--checkpoint", default=str(DEFAULT_CKPT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--epsilon", type=float, default=0.0)
    args = parser.parse_args()
    evaluate(rounds=args.rounds, seed=args.seed, checkpoint=args.checkpoint,
             out_dir=args.out, epsilon=args.epsilon)


if __name__ == "__main__":
    main()
