"""selfplay-v1 预设与训练 CLI 回归测试（R-c1712b23 验收配套）。

覆盖：
1. ``--preset selfplay-v1`` 的超参是已验证配方（k=50、默认隐藏层 (128,64)、
   lr=3e-2、batch_size=4、epsilon_decay=0.99、opponent_replay_every=1）；
2. preset 一条命令跑通并产出主策略与对手两个 checkpoint（默认隐藏层）；
3. CLI 不带 preset 的 self 模式调用不再 KeyError
   （回归：main() 曾无条件 ``p["opponent_epsilon"]``，非 preset 调用必崩）；
4. ``_settle_rewards`` 零和性在塑形开启（k=50）时仍成立：
   每步（含终局）agent_reward + opponent_reward == 0，且直接调用返回 ±all_bet。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.env import CardGameEnv
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


__all__ = ["TestSelfplayV1Preset", "TestTrainCliWithoutPreset", "TestSettleZeroSumWithShaping"]
