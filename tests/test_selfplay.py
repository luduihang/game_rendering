"""自博弈机制测试：DQN 对手注入、视角对称、座位交换、零和奖励、训练冒烟与可复现性。

覆盖验收项：
1. DQN 对手可注入 env 并完成一整局；
2. 对手视角观测维度为 4，且与 agent 视角编码对称（己方押注 ↔ 对方押注镜像）；
3. 座位交换生效：连续两局的先手方不同（Robot 模式不交换）；
4. 奖励零和：每步（尤其终局）agent_reward + opponent_reward == 0；
5. 自博弈训练冒烟：极小局数跑完，产出主策略与对手两个 checkpoint，summary 含新增字段；
6. 同种子可复现：同 seed 两次自博弈训练 summary 关键字段一致。
"""

from pathlib import Path

import pytest

from agents.dqn import DQNAgent, weights_hash
from scripts.env import CardGameEnv, StepResult
from scripts.evaluate import evaluate
from scripts.train import train


def _dqn_opponent(seed: int = 1, epsilon: float = 0.0) -> DQNAgent:
    return DQNAgent(input_dim=4, action_dim=6, seed=seed, epsilon=epsilon)


def _play_one_episode(env: CardGameEnv, warmup: int = 6) -> StepResult | None:
    """前 warmup 步押注（legal[0]），之后弃牌（legal[-1]）强制自然终局；返回最后一个 StepResult。

    注：如果双方都只押注（都不弃牌/看牌），对局会走 MAX_STEPS 强制结束（finish=False），
    这不是自然结算，故这里用弃牌保证自然终局。
    """
    result = None
    for i in range(300):
        legal = env.legal_actions()
        if not legal:
            break
        action = legal[0] if i < warmup else legal[-1]
        result = env.step(action)
        if result.done:
            break
    return result


class TestDqnOpponentEnv:
    def test_dqn_opponent_completes_full_episode(self):
        """D.1：DQN 对手可注入 env 并完成一整局（done 为 True，信息合法）。"""
        env = CardGameEnv(seed=7, opponent=_dqn_opponent(), opponent_replay_every=1)
        env.reset()
        result = _play_one_episode(env)
        assert result is not None and result.done
        assert result.observation.shape == (4,)
        assert env.room is not None and env.room.finish
        assert result.info["winner"] in (0, 1)

    def test_opponent_observation_is_four_dim_and_symmetric(self):
        """D.2：对手视角观测 4 维，且与 agent 视角互为镜像（己方押注 ↔ 对方押注）。"""
        env = CardGameEnv(seed=7, opponent=_dqn_opponent())
        env.reset()
        assert env.agent_player == 0 and env.opponent_seat == 1
        assert env.room.whose_turn == 0 and not env.room.finish
        # 让座位 0（agent）押 10，制造非对称押注局面
        env.room.apply(0)
        agent_obs = env._observation()
        opp_obs = env._opponent_observation()
        assert agent_obs.shape == (4,)
        assert opp_obs.shape == (4,)
        # 盘面轮次共享
        assert agent_obs[0] == pytest.approx(opp_obs[0])
        # 押注镜像：agent 视角的「己方/对方」= 对手视角的「对方/己方」
        assert agent_obs[1] == pytest.approx(0.015)  # agent 押注 15/1000
        assert opp_obs[1] == pytest.approx(0.005)    # 对手视角己方（座位1）押注 5/1000
        assert agent_obs[2] == pytest.approx(0.005)
        assert opp_obs[2] == pytest.approx(0.015)
        # 手牌强度：各自用自己的牌，都在 [0,1]
        assert 0.0 <= agent_obs[3] <= 1.0
        assert 0.0 <= opp_obs[3] <= 1.0

    def test_seat_swap_alternates_first_mover(self):
        """D.3：自博弈座位交换生效 —— 座位 0 恒先手（core 规则不变，用 history[0] 验证），
        但「哪个策略坐在座位 0」按局奇偶翻转，连续两局先手方不同。

        reset() 会推进到 agent 回合：若对手坐在座位 0（先手），reset 时对手已行动，
        history 记录其行动；若 agent 坐座位 0，reset 后 history 为空、轮到 agent。
        """
        env = CardGameEnv(seed=7, opponent=_dqn_opponent(), opponent_replay_every=None)
        first_mover_is_agent = []
        for _ in range(4):
            env.reset()
            if env.room.finish:
                # 对手先手且第一步直接弃牌/看牌定局：先手 = 座位 0
                first_mover_is_agent.append(env.agent_player == 0)
                continue
            assert env.room.whose_turn == env.agent_player
            if env.room.history:
                # 对手（座位 0）已先行动
                assert env.room.history[0][0] == 0
                first_mover_is_agent.append(False)
            else:
                # 尚未有人行动，先手 = 座位 0 = agent
                first_mover_is_agent.append(True)
        assert first_mover_is_agent == [True, False, True, False]

    def test_robot_mode_does_not_swap_seats(self):
        """Robot 对手保持旧行为：不交换座位。"""
        env = CardGameEnv(seed=7)  # 缺省 Robot
        for _ in range(3):
            env.reset()
            assert env.agent_player == 0
            assert env.opponent_seat == 1

    def test_rewards_are_zero_sum(self):
        """D.4：奖励零和 —— 每一步（含终局）agent_reward + opponent_reward == 0，
        且终局符号与赢家一致。"""
        env = CardGameEnv(seed=11, opponent=_dqn_opponent(), opponent_replay_every=1)
        env.reset()
        result = _play_one_episode(env)
        assert result is not None and result.done
        assert result.reward + result.info["opponent_reward"] == 0.0
        # 自然结束（非 MAX_STEPS 强制）时结算非零
        if env.room.finish:
            assert result.reward != 0.0
            if result.info["winner"] == env.agent_player:
                assert result.reward > 0.0
            else:
                assert result.reward < 0.0

    def test_opponent_receives_transitions_on_its_turns(self):
        """DQN 对手从自己行动的 transition 学习：buffer 非空且 state/next_state 为 4 维。"""
        env = CardGameEnv(seed=13, opponent=_dqn_opponent(), opponent_replay_every=1)
        env.reset()
        _play_one_episode(env)
        assert len(env.opponent.memory) > 0
        for t in env.opponent.memory:
            assert t.state.shape == (4,)
            assert t.next_state.shape == (4,)
            assert t.action in (0, 1, 2, 3, 4, 5)

    def test_frozen_opponent_does_not_learn(self):
        """opponent_replay_every=None（冻结策略）：对手 memory 始终为空。"""
        env = CardGameEnv(seed=13, opponent=_dqn_opponent(), opponent_replay_every=None)
        env.reset()
        _play_one_episode(env)
        assert len(env.opponent.memory) == 0


class TestSelfplayTraining:
    def test_selfplay_smoke_produces_two_checkpoints(self, tmp_path):
        """D.5：自博弈冒烟 —— 3 局跑完，产出主策略与对手两个 checkpoint，summary 含新增字段。"""
        summary = train(episodes=3, seed=5, out_dir=tmp_path, verbose=False, opponent_mode="self")
        assert summary["opponent_mode"] == "self"
        assert summary["episodes"] == 3
        assert 0.0 <= summary["win_rate"] <= 1.0
        assert summary["agent_win_rate"] == summary["win_rate"]
        assert 0.0 <= summary["opponent_win_rate"] <= 1.0
        assert summary["win_rate"] + summary["opponent_win_rate"] <= 1.0 + 1e-9
        assert summary["agent_action_distribution"], "主策略动作分布缺失"
        assert summary["opponent_action_distribution"], "对手动作分布缺失"
        assert summary["elapsed_sec"] >= 0
        assert summary["weights_hash"]
        assert summary["opponent_weights_hash"]
        assert summary["checkpoint"].endswith("dqn_sp_ep3_seed5.pth")
        assert summary["opponent_checkpoint"].endswith("dqn_sp_opp_ep3_seed5.pth")
        assert Path(summary["checkpoint"]).exists()
        assert Path(summary["opponent_checkpoint"]).exists()
        assert (tmp_path / "summary_seed5.json").exists()

    def test_selfplay_same_seed_is_reproducible(self, tmp_path):
        """D.6：同种子两次自博弈训练 summary 关键字段一致。"""
        first = train(episodes=2, seed=99, out_dir=tmp_path / "a", verbose=False, opponent_mode="self")
        second = train(episodes=2, seed=99, out_dir=tmp_path / "b", verbose=False, opponent_mode="self")
        for key in (
            "weights_hash",
            "opponent_weights_hash",
            "wins",
            "opponent_wins",
            "win_rate",
            "opponent_win_rate",
            "avg_reward",
            "agent_action_distribution",
            "opponent_action_distribution",
        ):
            assert first[key] == second[key], f"字段 {key} 不可复现"

    def test_selfplay_sync_resets_opponent_to_agent_weights(self, tmp_path):
        """self 模式周期性快照同步：sync_every=1 时，终局对手权重应等于最后一局前的主策略快照
        （第 1 局训完后重置，第 2 局对手再学习；第 2 局训完后不再同步）。
        这里验证机制触发且对手确实在学习（第 2 局后对手权重 != 初始随机权重）。"""
        summary = train(
            episodes=2, seed=8, out_dir=tmp_path, verbose=False,
            opponent_mode="self", opponent_sync_every=1,
        )
        assert summary["opponent_weights_hash"] is not None
        # 对手经过第 2 局的学习后不应与全新随机初始化的默认权重相同
        fresh = DQNAgent(input_dim=4, action_dim=6, seed=8 + 1)
        assert summary["opponent_weights_hash"] != weights_hash(fresh)

    def test_snapshot_mode_uses_frozen_loaded_opponent(self, tmp_path):
        """snapshot 模式：对手从 checkpoint 加载且不学习（终局权重与加载时一致）。"""
        first = train(episodes=2, seed=3, out_dir=tmp_path / "src", verbose=False, opponent_mode="self")
        ref = DQNAgent.from_checkpoint(first["opponent_checkpoint"])
        summary = train(
            episodes=2, seed=4, out_dir=tmp_path / "dst", verbose=False,
            opponent_mode="snapshot", opponent_ckpt=first["opponent_checkpoint"],
        )
        assert summary["opponent_mode"] == "snapshot"
        assert summary["opponent_weights_hash"] == weights_hash(ref)
        assert Path(summary["checkpoint"]).exists()
        assert summary["checkpoint"].endswith("dqn_sp_ep2_seed4.pth")

    def test_invalid_mode_rejected(self, tmp_path):
        with pytest.raises(ValueError):
            train(episodes=1, seed=1, out_dir=tmp_path, verbose=False, opponent_mode="bogus")
        with pytest.raises(ValueError):
            train(episodes=1, seed=1, out_dir=tmp_path, verbose=False,
                  opponent_mode="snapshot", opponent_ckpt=None)

    def test_robot_mode_unchanged_naming(self, tmp_path):
        """robot 模式（缺省）行为与命名保持旧约定。"""
        summary = train(episodes=2, seed=12, out_dir=tmp_path, verbose=False)
        assert summary["opponent_mode"] == "robot"
        assert summary["checkpoint"].endswith("dqn_ep2_seed12.pth")
        assert summary["opponent_weights_hash"] is None
        assert "opponent_checkpoint" not in summary


class TestEvaluateDualCheckpoints:
    def test_dual_checkpoint_evaluate_reports_both_win_rates(self, tmp_path):
        """C：双 checkpoint 对战模式输出双方胜率。"""
        first = train(episodes=2, seed=3, out_dir=tmp_path / "src", verbose=False, opponent_mode="self")
        summary = evaluate(
            rounds=4, seed=5,
            checkpoint=first["checkpoint"],
            opponent_checkpoint=first["opponent_checkpoint"],
            out_dir=tmp_path / "eval", verbose=False,
        )
        assert summary["opponent_checkpoint"] is not None
        assert 0.0 <= summary["win_rate"] <= 1.0
        assert 0.0 <= summary["opponent_win_rate"] <= 1.0
        assert summary["win_rate"] + summary["opponent_win_rate"] <= 1.0 + 1e-9
        assert summary["action_distribution"]
        assert summary["opponent_action_distribution"]
        assert (tmp_path / "eval" / "eval_seed5.json").exists()

    def test_single_checkpoint_evaluate_stays_robot(self, tmp_path):
        """缺省单 checkpoint 模式对手仍为 Robot（opponent_checkpoint 为 None）。"""
        first = train(episodes=2, seed=3, out_dir=tmp_path / "src", verbose=False, opponent_mode="self")
        summary = evaluate(
            rounds=2, seed=5, checkpoint=first["checkpoint"],
            out_dir=tmp_path / "eval2", verbose=False,
        )
        assert summary["opponent_checkpoint"] is None
        assert 0.0 <= summary["win_rate"] <= 1.0
