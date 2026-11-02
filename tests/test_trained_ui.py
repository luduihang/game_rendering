"""训练策略接入 UI 的验收测试（headless，不依赖 pygame 显示）。

覆盖治理任务 human-vs-machine 的核心验收：
- checkpoint 路径可配置：CLI 参数 > 环境变量 DQN_CHECKPOINT > 默认值
- 权重加载成功 → ``controller.trained is True`` 且 ``epsilon == 0.0``
- 权重缺失 → 明确可见的中文告警 + ``trained is False``（epsilon=0.15 回退）
- headless 端到端一局：人类输入（human_action）→ 机器应招 → 回合交替 → 结算
- 机器动作确实来自训练权重（与独立参考 agent 的 argmax 逐回合一致，
  且与 epsilon=1.0 随机策略的分布显著不同）

全程只用 ``ui.app.Controller`` 公开入口与 ``core`` 规则，无窗口、无 sleep。
"""

from __future__ import annotations

import random
from collections import Counter
from pathlib import Path

import pytest

from agents.dqn import DQNAgent, StateEncoder
from core.dealing import deal_uniform, new_deck
from core.rules import DEFAULT_MONEY, Action, GameRoom
from ui.app import CHECKPOINT_ENV_VAR, DEFAULT_CHECKPOINT, REPO, Controller, resolve_checkpoint

CKPT = DEFAULT_CHECKPOINT  # REPO / "dqn_model_1.pth"（自博弈训练产出）

HUMAN = 0
AI = 1


def make_controller(seed=7, **kwargs) -> Controller:
    kwargs.setdefault("think_seconds", 0.0)
    kwargs.setdefault("settle_seconds", 0.0)
    kwargs.setdefault("auto_human", False)
    return Controller(seed=seed, **kwargs)


# ---------- 任务 1：checkpoint 路径可配置 ----------
class TestCheckpointResolution:
    def test_default_is_trained_policy_file(self):
        """DEFAULT_CHECKPOINT 指向仓库根的 dqn_model_1.pth（自博弈训练产出的部署副本）。"""
        assert DEFAULT_CHECKPOINT == REPO / "dqn_model_1.pth"

    def test_default_when_nothing_given(self, monkeypatch):
        monkeypatch.delenv(CHECKPOINT_ENV_VAR, raising=False)
        assert resolve_checkpoint() == DEFAULT_CHECKPOINT
        assert resolve_checkpoint(None) == DEFAULT_CHECKPOINT
        assert resolve_checkpoint("") == DEFAULT_CHECKPOINT

    def test_env_var_when_no_arg(self, monkeypatch):
        monkeypatch.setenv(CHECKPOINT_ENV_VAR, "/tmp/env_model.pth")
        assert resolve_checkpoint() == Path("/tmp/env_model.pth")
        assert resolve_checkpoint(None) == Path("/tmp/env_model.pth")

    def test_cli_wins_over_env(self, monkeypatch):
        monkeypatch.setenv(CHECKPOINT_ENV_VAR, "/tmp/env_model.pth")
        assert resolve_checkpoint("/tmp/cli_model.pth") == Path("/tmp/cli_model.pth")
        assert resolve_checkpoint("cli_rel.pth") == REPO / "cli_rel.pth"

    def test_relative_resolved_against_repo(self, monkeypatch):
        monkeypatch.delenv(CHECKPOINT_ENV_VAR, raising=False)
        assert resolve_checkpoint("run/final/dqn_sp_ep100_seed7.pth") == (
            REPO / "run" / "final" / "dqn_sp_ep100_seed7.pth"
        )

    def test_explicit_env_mapping(self):
        """resolve_checkpoint 接受显式 env 映射，便于不污染环境变量测试。"""
        assert resolve_checkpoint(None, env={CHECKPOINT_ENV_VAR: "a/b.pth"}) == REPO / "a" / "b.pth"
        assert resolve_checkpoint("c.pth", env={CHECKPOINT_ENV_VAR: "a/b.pth"}) == REPO / "c.pth"

    def test_controller_honours_explicit_relative_checkpoint(self):
        c = make_controller(seed=1, checkpoint="run/final/dqn_sp_ep100_seed7.pth")
        assert c.checkpoint == REPO / "run" / "final" / "dqn_sp_ep100_seed7.pth"
        assert c.trained is True
        assert c.agent.epsilon == 0.0


# ---------- 任务 2/5：训练标志与可见告警 ----------
class TestTrainedFlagAndWarnings:
    def test_loaded_weights_give_trained_greedy_agent(self, capsys):
        c = make_controller(seed=3)
        assert c.trained is True
        assert c.policy_source == str(CKPT)
        assert c.agent.epsilon == 0.0, "加载训练权重后必须是 epsilon=0.0 贪心，而不是回退的 0.15"
        out = capsys.readouterr().out
        assert str(CKPT) in out
        assert "epsilon=0.0" in out

    def test_missing_weights_are_loud_and_flagged(self, capsys, tmp_path):
        c = make_controller(seed=3, checkpoint=tmp_path / "missing.pth")
        assert c.trained is False
        assert c.policy_source == "untrained-random(epsilon=0.15)"
        assert c.agent.epsilon == 0.15
        out = capsys.readouterr().out
        assert "未训练随机策略" in out
        assert "0.15" in out
        assert "不是训练出的策略" in out
        assert "--checkpoint" in out and CHECKPOINT_ENV_VAR in out, "告警必须提示如何提供权重"
        assert str(CKPT) in out, "告警必须提示默认权重位置"

    def test_corrupt_weights_also_loud(self, capsys, tmp_path):
        bad = tmp_path / "bad.pth"
        bad.write_bytes(b"not a torch file")
        c = make_controller(seed=3, checkpoint=bad)
        assert c.trained is False
        assert c.agent.epsilon == 0.15
        out = capsys.readouterr().out
        assert "未训练随机策略" in out


# ---------- 任务 3：headless 端到端一局 ----------
class TestHeadlessEndToEnd:
    @pytest.fixture()
    def game(self):
        """人类前 5 手押最小档，第 6 手看牌结算；机器每回合动作与独立参考 agent 的 argmax 对比。"""
        controller = make_controller(seed=20260102, checkpoint=CKPT)
        reference = DQNAgent.from_checkpoint(CKPT, seed=999)  # 独立加载的同一权重
        encoder = StateEncoder()
        assert controller.trained is True
        assert controller.agent.epsilon == 0.0

        human_bets_done = 0
        ai_moves_checked = 0
        now = 0.0
        max_steps = 60
        while not controller.room.finish and max_steps > 0:
            max_steps -= 1
            controller.set_now(now)
            room = controller.room
            if room.whose_turn == AI:
                # 机器应招：先算参考 agent 的期望动作，再让 Controller 走内部 AI 分支
                state = encoder.encode(room.snapshot(), AI, room.own_hand(AI))
                expected = reference.act(state, room.legal_actions())
                controller.update(now)
                actor, action = room.history[-1]
                assert actor == AI, "这一步应由机器行动"
                assert action == expected, (
                    f"机器动作 {action} 与训练权重 argmax {expected} 不一致（回合 {len(room.history)}）"
                )
                ai_moves_checked += 1
            else:
                legal = room.legal_actions()
                if human_bets_done < 5:
                    human_action = legal[0]  # 当前最低可押档（bet，不终结）
                    assert Action(human_action).is_bet
                else:
                    human_action = Action.COMPARE  # 人类主动看牌 → 触发结算
                assert controller.human_action(human_action), "人类动作必须经 human_action 成功提交"
                if human_bets_done < 5:
                    human_bets_done += 1
            now += 1.0

        yield controller, ai_moves_checked

    def test_full_game_completes_with_winner_and_pot(self, game):
        controller, _ = game
        room = controller.room
        assert room.finish is True, "对局应自然结束（看牌结算），而不是步数耗尽"
        assert room.winner is not None
        assert room.all_bet > 0, "底池必须大于 0"

    def test_turns_alternate_between_human_and_ai(self, game):
        controller, ai_moves_checked = game
        room = controller.room
        actors = [actor for actor, _ in room.history]
        assert len(room.history) >= 4, "对局应有足够的交替回合"
        for a, b in zip(actors, actors[1:]):
            assert a != b, f"回合没有交替：连续两个 {a}"
        assert HUMAN in actors and AI in actors, "双方都必须行动过"
        assert actors.count(AI) == ai_moves_checked >= 2, "机器至少应招两次"
        assert actors.count(HUMAN) >= 2, "人类至少行动两次"

    def test_settlement_pays_winner_the_pot(self, game):
        controller, _ = game
        room = controller.room
        winner = room.winner
        assert room.players[winner].money > DEFAULT_MONEY, "赢家应净得底池"
        loser = 1 - winner
        assert room.players[loser].money < DEFAULT_MONEY, "输家应净亏"
        # 资金守恒：投入底池的钱全数归赢家，两人资金总和不变（core/rules.py 的 _finish 语义）
        assert room.players[0].money + room.players[1].money == 2 * DEFAULT_MONEY


# ---------- 任务 4：机器动作确实来自训练权重，而非随机 ----------
def known_state(seed: int, rest_option: int = 0) -> tuple[GameRoom, StateEncoder, list[int]]:
    """用真实发牌构造一个已知状态：new_deck + deal_uniform，强度由 core.strength 计算。"""
    deck = new_deck(random.Random(seed))
    hands = [deal_uniform(deck), deal_uniform(deck)]
    room = GameRoom.new(hands)
    room.rest_option = rest_option
    room.whose_turn = AI
    return room, StateEncoder(), list(room.legal_actions())


class TestActionsComeFromTrainedWeights:
    @pytest.mark.parametrize("state_seed,rest_option", [(11, 0), (22, 0), (33, 3)])
    def test_loaded_agent_matches_independent_reference_and_beats_random(
        self, state_seed: int, rest_option: int
    ):
        room, encoder, legal = known_state(state_seed, rest_option)
        assert len(legal) >= 2, "测试状态至少要有 2 个合法动作，随机分布才可对比"
        state = encoder.encode(room.snapshot(), AI, room.own_hand(AI))

        # 独立参考 agent（同一权重、不同 RNG seed）：期望动作
        reference = DQNAgent.from_checkpoint(CKPT, seed=state_seed)
        expected = reference.act(state, legal)
        assert expected in legal

        # Controller 加载的 agent 在相同状态下必须与参考 argmax 完全一致
        controller = make_controller(seed=state_seed, checkpoint=CKPT)
        assert controller.trained is True and controller.agent.epsilon == 0.0
        assert controller.agent.act(state, legal) == expected

        # 确定性：加载权重的 agent 同一状态多次调用结果恒定
        loaded_actions = [reference.act(state, legal) for _ in range(21)]
        assert set(loaded_actions) == {expected}, "贪心训练策略在相同状态下必须恒定"
        loaded_top_freq = Counter(loaded_actions).most_common(1)[0][1] / len(loaded_actions)
        assert loaded_top_freq == 1.0

        # 未加载权重的 epsilon=1.0 随机 agent：分布必须显著不同（更分散）
        random_agent = DQNAgent(input_dim=4, action_dim=6, seed=state_seed, epsilon=1.0)
        random_actions = [random_agent.act(state, legal) for _ in range(200)]
        random_top_freq = Counter(random_actions).most_common(1)[0][1] / len(random_actions)
        assert len(set(random_actions)) >= 2, "epsilon=1.0 的随机策略 200 次不应全部相同"
        assert loaded_top_freq > random_top_freq, (
            f"训练策略分布（top1={loaded_top_freq}）应明显比随机（top1={random_top_freq}）集中"
        )

    def test_controller_ai_move_equals_checkpoint_argmax_in_live_game(self):
        """对局中：Controller 实际执行的机器动作 == 独立参考 agent 对同一状态的 argmax。"""
        controller = make_controller(seed=555, checkpoint=CKPT)
        reference = DQNAgent.from_checkpoint(CKPT, seed=777)
        encoder = StateEncoder()

        room = controller.room
        now = 0.0
        checked = 0
        while not room.finish and checked < 6:
            controller.set_now(now)
            if room.whose_turn == AI:
                state = encoder.encode(room.snapshot(), AI, room.own_hand(AI))
                expected = reference.act(state, room.legal_actions())
                controller.update(now)
                assert room.history[-1] == (AI, expected), (
                    f"Controller 执行的机器动作 {room.history[-1]} 不是 checkpoint argmax {(AI, expected)}"
                )
                checked += 1
            else:
                # 人类跟最小档，把球打回机器
                assert controller.human_action(room.legal_actions()[0])
            now += 1.0
        assert checked >= 3, "应至少核对 3 次机器动作"
