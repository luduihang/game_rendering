"""智能体层测试：接口契约、D8（维度自适应）、D9（真正加载权重）、行为等价。"""

import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from agents import DQN, DQNAgent, DQNConfig, Robot, RobotConfig, checkpoint_dims
from core.cards import Card, Suit

REPO = Path(__file__).resolve().parent.parent
KEEPER_CKPT = REPO / "dqn_model_1.pth"


def hand(*specs):
    return tuple(Card(Suit[s], r) for s, r in specs)


STRONG = hand(("SPADE", 14), ("HEART", 14), ("DIAMOND", 14))
WEAK = hand(("SPADE", 2), ("HEART", 3), ("DIAMOND", 5))


class TestCheckpointDims:
    def test_keeper_checkpoint_is_four_dim(self):
        input_dim, action_dim = checkpoint_dims(KEEPER_CKPT)
        assert input_dim == 4
        assert action_dim == 6

    def test_from_checkpoint_matches_actual_dims(self):
        """D8：工厂按 checkpoint 实际维度构建，不再硬编码 DQN(9,6)。"""
        agent = DQNAgent.from_checkpoint(KEEPER_CKPT)
        assert agent.input_dim == 4
        assert agent.action_dim == 6
        assert agent.model.fc1.in_features == 4

    def test_mismatched_dims_raise_clear_error(self):
        """硬编码 9 维去加载 4 维权重必须报错（这正是原实现的崩溃点）。"""
        model = DQN(9, 6)
        import torch

        state = torch.load(str(KEEPER_CKPT), map_location="cpu", weights_only=True)
        with pytest.raises(RuntimeError):
            model.load_state_dict(state)

    def test_missing_file_raises_filenotfound(self):
        with pytest.raises(FileNotFoundError):
            DQNAgent.from_checkpoint(REPO / "no_such_model.pth")


class TestD9LoadedPolicyInEffect:
    def test_epsilon_defaults_to_zero_after_load(self):
        agent = DQNAgent.from_checkpoint(KEEPER_CKPT)
        assert agent.epsilon == 0.0, "加载权重后必须走贪心，否则等于随机策略（D9）"

    def test_loaded_policy_is_deterministic(self):
        """贪心策略对同一状态应稳定输出同一动作。"""
        agent = DQNAgent.from_checkpoint(KEEPER_CKPT)
        state = np.array([0.1, 0.105, 0.005, 0.83], dtype=np.float32)
        actions = {agent.act(state, list(range(6))) for _ in range(20)}
        assert len(actions) == 1

    def test_loaded_policy_differs_from_random(self):
        """D9 验收：加载权重后的动作分布必须与随机策略显著不同。"""
        loaded = DQNAgent.from_checkpoint(KEEPER_CKPT)
        random_agent = DQNAgent(input_dim=4, action_dim=6, epsilon=1.0, seed=7)

        states = [np.array([c / 10, b / 1000, 5 / 1000, p], dtype=np.float32)
                  for c in (1, 3, 6, 9) for b in (5, 55) for p in (0.2, 0.6, 0.9)]
        legal = [0, 1, 2, 3, 4, 5]

        loaded_counts = np.zeros(6)
        random_counts = np.zeros(6)
        for s in states:
            loaded_counts[loaded.act(s, legal)] += 1
            for _ in range(20):
                random_counts[random_agent.act(s, legal)] += 1

        loaded_dist = loaded_counts / loaded_counts.sum()
        random_dist = random_counts / random_counts.sum()
        l1 = np.abs(loaded_dist - random_dist).sum()
        assert l1 > 0.5, f"加载权重后动作分布与随机差异过小（L1={l1:.2f}）"


class TestAgentContract:
    def test_act_only_returns_legal_actions(self):
        agent = DQNAgent(input_dim=4, epsilon=0.5, seed=1)
        state = np.zeros(4, dtype=np.float32)
        for legal in ([2, 3, 4, 5], [4, 5], [0, 1, 2, 3]):
            for _ in range(30):
                assert agent.act(state, legal) in legal

    def test_empty_legal_actions_raise(self):
        agent = DQNAgent(input_dim=4, seed=1)
        with pytest.raises(ValueError):
            agent.act(np.zeros(4, dtype=np.float32), [])

    def test_deterministic_with_same_seed(self):
        a = DQNAgent(input_dim=4, epsilon=1.0, seed=42)
        b = DQNAgent(input_dim=4, epsilon=1.0, seed=42)
        state = np.zeros(4, dtype=np.float32)
        assert [a.act(state, list(range(6))) for _ in range(20)] == [
            b.act(state, list(range(6))) for _ in range(20)
        ]

    def test_save_load_roundtrip(self, tmp_path):
        agent = DQNAgent(input_dim=4, seed=3, epsilon=0.0)  # 贪心，便于比对
        path = tmp_path / "weights.pth"
        agent.save(path)
        other = DQNAgent.from_checkpoint(path)
        state = np.array([0.2, 0.1, 0.05, 0.7], dtype=np.float32)
        assert agent.act(state, list(range(6))) == other.act(state, list(range(6)))

    def test_replay_reduces_epsilon_and_returns_loss(self):
        cfg = DQNConfig(batch_size=4, epsilon_start=1.0, epsilon_decay=0.5)
        agent = DQNAgent(input_dim=4, config=cfg, seed=5)
        from agents.base import Transition

        for i in range(8):
            agent.observe(Transition(np.zeros(4, np.float32), i % 6, 0.0, np.zeros(4, np.float32), False))
        loss = agent.replay()
        assert loss is not None and loss >= 0
        assert agent.epsilon == pytest.approx(0.5)


class TestRobot:
    SNAPSHOT = {
        "circle": 2,
        "bets": (25, 25),
        "money": (19900, 19900),
        "all_bet": 50,
        "rest_option": 0,
        "whose_turn": 1,
        "finish": False,
        "legal_actions": (0, 1, 2, 3, 4, 5),
        "hand": STRONG,
    }

    def test_act_returns_legal_action(self):
        robot = Robot(seed=1)
        robot.init_dick(["1", "0"], STRONG, hand=STRONG)
        for _ in range(50):
            assert robot.act(self.SNAPSHOT, (0, 1, 2, 3, 4, 5)) in range(6)

    def test_strong_hand_bets_more_than_weak(self):
        strong = Robot(seed=11)
        strong.init_dick(["1", "0"], STRONG, hand=STRONG)
        weak = Robot(seed=11)
        weak.init_dick(["1", "0"], WEAK, hand=WEAK)
        assert strong.win_rate > weak.win_rate

    def test_config_presets_differ(self):
        agree = RobotConfig.aggressive()
        safe = RobotConfig.conservative()
        assert agree.extra_bet_scale > safe.extra_bet_scale
        assert safe.give_up_weight > agree.give_up_weight

    def test_no_star_import_leak(self):
        """原实现靠星号导入泄漏 numpy（ruff 一清理就崩）。"""
        text = (REPO / "agents" / "robot.py").read_text(encoding="utf-8")
        assert "import numpy as np" in text
        star_imports = [
            line for line in text.splitlines()
            if line.strip().startswith(("from ", "import ")) and line.strip().endswith("import *")
        ]
        assert not star_imports, f"不应存在星号导入: {star_imports}"

    def test_strong_hand_is_more_aggressive(self):
        """行为合理性：强牌比弱牌更倾向加注（迁移后不再依赖 legacy Robot2 对比）。"""
        def bet_share(hand_cards):
            robot = Robot(seed=99)
            robot.init_dick(["1", "0"], hand_cards, hand=hand_cards)
            counts = np.zeros(6)
            for _ in range(400):
                counts[robot.cal_final_option()["option"]] += 1
            return counts[[0, 1, 2, 3]].sum() / counts.sum()

        assert bet_share(STRONG) > bet_share(WEAK)


class TestLayeringAndImportPurity:
    def test_agents_do_not_import_pygame(self):
        pattern = re.compile(r"^\s*(?:import\s+pygame|from\s+pygame[\s.])", re.MULTILINE)
        offenders = [
            p.name
            for p in (REPO / "agents").glob("*.py")
            if pattern.search(p.read_text(encoding="utf-8"))
        ]
        assert not offenders, f"agents/ 不应依赖 pygame: {offenders}"

    def test_no_import_time_checkpoint_loading(self):
        """D7-d：load_state_dict 只能出现在函数体内。"""
        for path in (REPO / "agents").glob("*.py"):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if "load_state_dict" in stripped and not line.startswith((" ", "\t")):
                    pytest.fail(f"{path.name}:{lineno} 在模块顶层加载权重: {stripped}")

    def test_importing_agents_does_not_touch_disk(self):
        """import agents 不应读取任何 .pth 文件。"""
        code = (
            "import sys, pathlib\n"
            "import builtins\n"
            "orig = builtins.open\n"
            "touched = []\n"
            "def spy(f, *a, **k):\n"
            "    if str(f).endswith('.pth'): touched.append(str(f))\n"
            "    return orig(f, *a, **k)\n"
            "builtins.open = spy\n"
            "import torch\n"
            "torch.load = lambda *a, **k: (_ for _ in ()).throw(AssertionError('torch.load at import'))\n"
            "import agents\n"
            "assert not touched, touched\n"
            "print('OK')\n"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
        assert "OK" in result.stdout, result.stderr
