"""selfplay-v1 预设与训练 CLI 回归测试（R-c1712b23 验收配套）。

覆盖：
1. ``--preset selfplay-v1`` 的超参是已验证配方（k=50、默认隐藏层 (128,64)、
   lr=3e-2、batch_size=4、epsilon_decay=0.99、opponent_replay_every=1）；
2. preset 一条命令跑通并产出主策略与对手两个 checkpoint（默认隐藏层）；
3. CLI 不带 preset 的 self 模式调用不再 KeyError
   （回归：main() 曾无条件 ``p["opponent_epsilon"]``，非 preset 调用必崩）；
4. ``_settle_rewards`` 零和性在塑形开启（k=50）时仍成立：
   每步（含终局）agent_reward + opponent_reward == 0，且直接调用返回 ±all_bet；
5. **逐步**零和在「带塑形的押注步」也精确成立（R-2569c185 复核返工）：
   k=50 下 3 seeds × 20 局，每个环境步 ``agent_reward + opponent_reward == 0.0``
   （精确相等），且确实覆盖到非零塑形增量的押注步；
6. preset 训练产物可被 ``DQNAgent.from_checkpoint`` **默认 config**（不传 hidden）
   无异常加载，网络形状 4→128→64→6、epsilon=0.0（UI 侧标准加载路径）。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from agents.base import BaseAgent
from agents.dqn import DQNAgent
from core.rules import Action
from scripts.env import ACTION_NAMES, BET_OPTIONS, CardGameEnv
from scripts.train import SELFPLAY_V1
from tests.test_selfplay import _dqn_opponent, _play_one_episode

REPO = Path(__file__).resolve().parents[1]


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "scripts.train", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
    )


class TestSelfplayV1Preset:
    def test_preset_hyperparameters_are_verified_recipe(self):
        """防回归：preset 必须是 2.3 验证过的配方（k=50 + 默认隐藏层）。"""
        assert SELFPLAY_V1["opponent_mode"] == "self"
        assert SELFPLAY_V1["strength_shaping"] == 50.0
        assert SELFPLAY_V1["lr"] == 3e-2
        assert SELFPLAY_V1["batch_size"] == 4
        assert SELFPLAY_V1["epsilon_decay"] == 0.99
        assert SELFPLAY_V1["opponent_replay_every"] == 1
        # 隐藏层必须保持默认 (128, 64)：DQNAgent.from_checkpoint 不推断隐藏宽度，
        # 自定义宽度（如 (32,16)）会让下游 UI 加载 size mismatch。
        assert SELFPLAY_V1.get("hidden") is None

    def test_preset_cli_produces_checkpoints(self, tmp_path):
        """preset 一条命令跑通，产出主/对手 checkpoint，隐藏层为默认 (128, 64)。"""
        proc = _run_cli(
            ["--preset", "selfplay-v1", "--episodes", "4", "--seed", "7", "--out", str(tmp_path)]
        )
        assert proc.returncode == 0, proc.stderr
        assert (tmp_path / "dqn_sp_ep4_seed7.pth").exists()
        assert (tmp_path / "dqn_sp_opp_ep4_seed7.pth").exists()
        summary = json.loads((tmp_path / "summary_seed7.json").read_text(encoding="utf-8"))
        assert summary["strength_shaping"] == 50.0
        assert summary["config"]["hidden"] == [128, 64]

    def test_preset_checkpoint_loadable_with_default_config(self, tmp_path):
        """回归：preset 产物必须能被 ``DQNAgent.from_checkpoint`` 默认 config 加载。

        ``from_checkpoint`` 只自适应 input/action 维度、**不推断隐藏层宽度**
        （agents/dqn.py:124-145）：若 preset 训练用过自定义 hidden（如 (32,16)），
        产物用默认 config（hidden 缺省 = (128,64)）加载会报
        ``size mismatch for fc1.weight``，下游 UI 直接加载即崩。
        本测试真实训练 100 局（等价 ``--preset selfplay-v1 --episodes 100 --seed 7``），
        断言产物按默认 config 无异常加载、网络形状 4→128→64→6、贪心 epsilon=0.0。
        """
        proc = _run_cli(
            ["--preset", "selfplay-v1", "--episodes", "100", "--seed", "7", "--out", str(tmp_path)]
        )
        assert proc.returncode == 0, proc.stderr
        ckpt = tmp_path / "dqn_sp_ep100_seed7.pth"
        opp_ckpt = tmp_path / "dqn_sp_opp_ep100_seed7.pth"
        assert ckpt.exists() and opp_ckpt.exists()
        # 默认 config（不传 hidden）UI 标准加载：无异常
        agent = DQNAgent.from_checkpoint(ckpt)
        assert agent.model.fc1.in_features == 4
        assert agent.model.fc1.out_features == 128
        assert agent.model.fc2.out_features == 64
        assert agent.model.fc3.out_features == 6
        assert agent.epsilon == 0.0
        # 对手产物同样满足 UI 标准加载口径
        opp = DQNAgent.from_checkpoint(opp_ckpt)
        assert opp.model.fc1.in_features == 4
        assert opp.model.fc1.out_features == 128
        assert opp.model.fc2.out_features == 64
        assert opp.model.fc3.out_features == 6
        assert opp.epsilon == 0.0


class TestTrainCliWithoutPreset:
    def test_self_mode_without_preset_does_not_keyerror(self, tmp_path):
        """回归：不带 preset 的 self 模式调用曾 KeyError('opponent_epsilon')。"""
        proc = _run_cli(
            ["--episodes", "3", "--seed", "7", "--opponent-mode", "self", "--out", str(tmp_path)]
        )
        assert "KeyError" not in (proc.stderr or "")
        assert proc.returncode == 0, proc.stderr


class TestSettleZeroSumWithShaping:
    def test_settle_rewards_zero_sum_with_strength_shaping(self):
        """塑形开启（k=50）时零和口径不变：终局 ±all_bet，每步 agent+opp == 0。"""
        env = CardGameEnv(
            seed=11,
            opponent=_dqn_opponent(),
            opponent_replay_every=1,
            strength_shaping=SELFPLAY_V1["strength_shaping"],
        )
        env.reset()
        result = _play_one_episode(env)
        assert result is not None and result.done
        # 每一步零和（_play_one_episode 内每步都成立，终局步同样）
        assert result.reward + result.info["opponent_reward"] == 0.0
        if env.room.finish:
            # 自然终局：直接调用 _settle_rewards 为零和且量级 = all_bet
            agent_r, opp_r = env._settle_rewards()
            assert agent_r + opp_r == 0.0
            assert abs(agent_r) == env.room.all_bet
            # 符号与赢家一致
            assert (agent_r > 0) == (env.room.winner == env.agent_player)


class _AlwaysCallOpponent(BaseAgent):
    """确定性对手：恒取最小合法押注（被动跟注，不弃牌/不看牌）。

    供逐步零和测试使用：保证每局**确定性地**包含「agent 押注 → 对手跟注
    （agent 被动跟注）」步，以及 agent 弃牌导致的自然终局步，避免依赖随机
    DQN 的探索碰巧覆盖这些步型（测试可复现、覆盖不 flaky）。
    """

    name = "always_call"

    def act(self, observation, legal_actions: Sequence[int]) -> int:
        return int(legal_actions[0])

    def replay(self):  # env 在 opponent_replay_every 内调用对手 replay（scripts/env.py:275），接口对齐 DQNAgent
        return None


class TestStepwiseZeroSumWithShaping:
    def test_every_step_exactly_zero_sum_including_nonzero_bet_shaping(self):
        """逐步精确零和（含带非零塑形增量的押注步）。

        既有 ``TestSettleZeroSumWithShaping`` 只断言**最后一步**零和，而那一步恰是
        fold（塑形增量为 0），未覆盖 strength_shaping=50.0 下真正产生非零塑形增量
        的押注步（reviewer 只在代码层证明押注步零和，测试未锁住）。本测试用 preset
        值 k=50.0 跑 3 seeds × 20 局，对**每个环境步**精确断言
        ``agent_reward + opponent_reward == 0.0``（IEEE-754 下 fl(A+N) + fl(-A-N) 应
        精确为 0；若实测不为 0，断言会原样报出残差，不用容差掩盖）。
        同时断言测试自身确实覆盖：押注步、**非零塑形增量的押注步**、对手跟注
        （agent 被动跟注）步、fold 步、终局步，避免「碰巧没触发塑形所以恒真」的
        空转测试。
        """
        k = SELFPLAY_V1["strength_shaping"]
        assert k == 50.0, "本测试依赖 preset 值 k=50（见 test_preset_hyperparameters_are_verified_recipe）"
        bet_actions = {int(Action.BET_10), int(Action.BET_20), int(Action.BET_50), int(Action.BET_100)}
        fold_action = int(Action.FOLD)

        total_steps = 0
        bet_steps = 0
        bet_steps_nonzero_shaping = 0
        passive_follow_steps = 0
        fold_steps = 0
        done_steps = 0
        max_abs_residual = 0.0

        for seed in (7, 11, 20261021):
            env = CardGameEnv(
                seed=seed,
                opponent=_AlwaysCallOpponent(),
                opponent_replay_every=1,
                strength_shaping=k,
            )
            for _episode in range(20):
                env.reset()
                agent_turns = 0
                legal = env.legal_actions()
                while legal:
                    # agent 策略：前 6 个 agent 行动押注（最小合法押注），其后弃牌 → 自然终局
                    action = legal[0] if agent_turns < 6 else fold_action
                    # 塑形所需前置状态在 room.apply 之前抓取（与 scripts/env.py:152-156 同口径）
                    agent_strength = float(env.encoder._strength(env.room.own_hand(env.agent_player)))
                    opp_bet_before = float(env.room.players[env.opponent_seat].bet)
                    result = env.step(action)
                    agent_turns += 1

                    # 1) 逐步严格零和（含终局步、任一押注步、被动跟注步）
                    residual = float(result.reward) + float(result.info["opponent_reward"])
                    assert residual == 0.0, (
                        f"seed={seed} agent_turn={agent_turns} "
                        f"action={ACTION_NAMES.get(action, action)}: "
                        f"reward={result.reward!r} + opponent_reward={result.info['opponent_reward']!r}"
                        f" = {residual!r} != 0.0"
                    )
                    total_steps += 1
                    max_abs_residual = max(max_abs_residual, abs(residual))

                    # 2) 覆盖统计：按 scripts/env.py:166-189 同口径重算该步 agent 侧塑形增量
                    if action in bet_actions:
                        bet_steps += 1
                        increment = k * (agent_strength - 0.5) * float(BET_OPTIONS[action])
                        opp_amount = float(env.room.players[env.opponent_seat].bet) - opp_bet_before
                        if not result.done and opp_amount > 0.0:
                            increment -= k * (0.5 - agent_strength) * opp_amount
                            passive_follow_steps += 1
                        if increment != 0.0:
                            bet_steps_nonzero_shaping += 1
                    if action == fold_action:
                        fold_steps += 1
                    if result.done:
                        done_steps += 1
                    legal = env.legal_actions()

        # 覆盖断言：各类步型必须真实发生（核心：非零塑形增量的押注步 > 0）
        assert total_steps > 0
        assert bet_steps > 0, "未覆盖任何押注步"
        assert bet_steps_nonzero_shaping > 0, (
            f"共 {bet_steps} 个押注步却没有非零塑形增量的押注步，零和断言可能是恒真空转"
        )
        assert passive_follow_steps > 0, "未覆盖任何对手跟注（agent 被动跟注）步"
        assert fold_steps > 0, "未覆盖任何 fold 步"
        assert done_steps > 0, "未覆盖任何终局步"
        assert max_abs_residual == 0.0


__all__ = [
    "TestSelfplayV1Preset",
    "TestTrainCliWithoutPreset",
    "TestSettleZeroSumWithShaping",
    "TestStepwiseZeroSumWithShaping",
]
