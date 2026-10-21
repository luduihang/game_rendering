"""训练/评估入口测试：冒烟、可复现性（同种子逐位一致）、D4 环境层防护。"""

import re
from pathlib import Path

import pytest

from agents.base import Transition
from core.rules import IllegalAction
from scripts.env import CardGameEnv
from scripts.evaluate import DEFAULT_CKPT, evaluate
from scripts.train import train

REPO = Path(__file__).resolve().parents[1]


class TestEnv:
    def test_reset_yields_four_dim_observation(self):
        env = CardGameEnv(seed=1)
        obs = env.reset()
        assert obs.shape == (4,)

    def test_legal_actions_non_empty_on_agent_turn(self):
        env = CardGameEnv(seed=1)
        env.reset()
        assert env.legal_actions()

    def test_stepping_finished_room_raises(self):
        """D4 环境层防护：对局结束后不得再行动。"""
        env = CardGameEnv(seed=3)
        env.reset()
        done = False
        for _ in range(200):
            legal = env.legal_actions()
            if not legal:
                break
            result = env.step(legal[-1])  # 优先弃牌/看牌，尽快结束
            done = result.done
            if done:
                break
        assert done, "对局未在 200 步内结束"
        with pytest.raises(IllegalAction):
            env.step(0)

    def test_reward_only_nonzero_at_end(self):
        env = CardGameEnv(seed=5)
        env.reset()
        rewards = []
        done = False
        while not done:
            legal = env.legal_actions()
            if not legal:
                break
            result = env.step(legal[0])
            rewards.append(result.reward)
            done = result.done
        assert all(r == 0 for r in rewards[:-1])
        assert rewards[-1] != 0


class TestTrain:
    def test_smoke_produces_checkpoint_and_summary(self, tmp_path):
        summary = train(episodes=2, seed=11, out_dir=tmp_path, verbose=False)
        assert summary["episodes"] == 2
        assert 0.0 <= summary["win_rate"] <= 1.0
        assert Path(summary["checkpoint"]).exists()
        assert (tmp_path / "summary_seed11.json").exists()

    def test_same_seed_is_bitwise_reproducible(self, tmp_path):
        """验收：同种子两次训练权重逐位一致。"""
        first = train(episodes=3, seed=2026, out_dir=tmp_path / "a", verbose=False)
        second = train(episodes=3, seed=2026, out_dir=tmp_path / "b", verbose=False)
        assert first["weights_hash"] == second["weights_hash"]
        assert first["avg_reward"] == second["avg_reward"]

    def test_different_seed_differs(self, tmp_path):
        first = train(episodes=3, seed=1, out_dir=tmp_path / "a", verbose=False)
        second = train(episodes=3, seed=2, out_dir=tmp_path / "b", verbose=False)
        assert first["weights_hash"] != second["weights_hash"]

    def test_training_run_is_fast_enough(self, tmp_path):
        """验收：可复现性验证限定 ≤20 回合、CPU-only、≤10 分钟。"""
        summary = train(episodes=5, seed=3, out_dir=tmp_path, verbose=False)
        assert summary["elapsed_sec"] < 60


class TestEvaluate:
    def test_smoke_with_keeper_checkpoint(self, tmp_path):
        summary = evaluate(rounds=5, seed=9, checkpoint=DEFAULT_CKPT, out_dir=tmp_path, verbose=False)
        assert summary["rounds"] == 5
        assert 0.0 <= summary["win_rate"] <= 1.0
        assert summary["checkpoint"].endswith("dqn_model_1.pth")
        assert (tmp_path / "eval_seed9.json").exists()

    def test_action_distribution_is_concentrated(self, tmp_path):
        """D9 旁证：加载权重的策略不会均匀乱选。"""
        summary = evaluate(rounds=20, seed=9, checkpoint=DEFAULT_CKPT, out_dir=tmp_path, verbose=False)
        dist = summary["action_distribution"]
        assert dist, "动作分布为空"
        assert max(dist.values()) > 0.4, f"动作分布过于分散: {dist}"


class TestLayering:
    def test_scripts_do_not_import_pygame(self):
        pattern = re.compile(r"^\s*(?:import\s+pygame|from\s+pygame[\s.])", re.MULTILINE)
        offenders = [
            p.name for p in (REPO / "scripts").glob("*.py")
            if pattern.search(p.read_text(encoding="utf-8"))
        ]
        assert not offenders, f"scripts/ 不应依赖 pygame: {offenders}"

    def test_no_import_time_torch_load(self):
        for path in (REPO / "scripts").glob("*.py"):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "torch.load" in line and not line.startswith((" ", "\t")):
                    pytest.fail(f"{path.name}:{lineno} 模块顶层 torch.load")

    def test_transition_helper(self):
        env = CardGameEnv(seed=2)
        state = env.reset()
        result = env.step(env.legal_actions()[0])
        transition = Transition(state, 0, result.reward, result.observation, result.done)
        assert transition.state.shape == (4,)
        assert transition.next_state.shape == (4,)
