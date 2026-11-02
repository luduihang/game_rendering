"""对局环境：把 core.GameRoom 包成 (obs, reward, done) 接口，供训练与评估复用。

不依赖 pygame，可无头运行。

对手类型：
- ``Robot``（缺省）：旧启发式威胁模型对手，走 ``init_dick`` / ``update_dick`` json 协议，
  行为与旧实现一致（每局不交换座位）。
- ``BaseAgent``（如 ``DQNAgent``）：自博弈对手。对手以**对手座位视角**编码观测
  （``_opponent_observation``），每次行动后用对手视角的 transition 调
  ``opponent.observe()`` / ``opponent.replay()``；``reset()`` 默认按局奇偶交换双方座位
  （``swap_seats``），消除 core.rules 中「座位 0 恒先手」的先手偏置。

奖励为零和：``agent_reward + opponent_reward == 0``。
结算口径（``_settle_rewards``）：赢方 +all_bet、输方 -all_bet（对称、零和）。
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

import numpy as np

from agents.base import BaseAgent, Transition
from agents.dqn import StateEncoder
from agents.robot import Robot
from core.dealing import deal_uniform, new_deck
from core.rules import BET_OPTIONS, Action, GameRoom, IllegalAction

MAX_STEPS = 200

# 动作名映射（与 scripts.evaluate 共用）
ACTION_NAMES = {
    int(Action.BET_10): "bet_10",
    int(Action.BET_20): "bet_20",
    int(Action.BET_50): "bet_50",
    int(Action.BET_100): "bet_100",
    int(Action.FOLD): "fold",
    int(Action.COMPARE): "compare",
}


@dataclass
class StepResult:
    observation: np.ndarray
    reward: float
    done: bool
    legal_actions: tuple[int, ...]
    info: dict


class CardGameEnv:
    """DQN 智能体（默认玩家0）对战对手（缺省 Robot 玩家1，或注入 BaseAgent 做自博弈）。

    参数：
    - ``opponent``：对手。缺省 ``Robot("1", seed=seed)``；传入 ``DQNAgent`` 等
      ``BaseAgent`` 即进入自博弈路径（不走 Robot 的 ``init_dick`` / ``update_dick`` 协议）。
    - ``swap_seats``：是否按局奇偶交换双方座位（消除先手偏置）。
      缺省 ``None`` 为自动：DQN 对手 → 交换；Robot 对手 → 不交换（保持旧行为）。
    - ``opponent_replay_every``：DQN 对手的行动回放频率。``1`` = 每次行动后 replay；
      ``k`` = 每 k 次行动 replay 一次（自博弈中给对手降频，避免双方探索同步塌缩）；
      ``None`` = 对手为冻结策略，不做任何 observe/replay（评估快照对手用）。
    """

    def __init__(
        self,
        seed: int | None = None,
        opponent: BaseAgent | None = None,
        agent_player: int = 0,
        swap_seats: bool | None = None,
        opponent_replay_every: int | None = 1,
    ):
        self.seed = seed
        self.rng = random.Random(seed)
        self._base_agent_player = agent_player
        self.agent_player = agent_player
        self.opponent_seat = 1 - agent_player
        self.opponent = opponent if opponent is not None else Robot("1", seed=seed)
        self._swap_seats = swap_seats
        self.opponent_replay_every = opponent_replay_every
        self.encoder = StateEncoder()
        self.room: GameRoom | None = None
        self.steps = 0
        self._episodes = 0
        self.opponent_action_counts: Counter[int] = Counter()
        # DQN 对手上一条「待结算」经验 (state, action)：
        # 对手行动时记录 (对手视角观测, 动作)，在下一对手行动前或对局结束时
        # 补齐 (reward, next_state, done) 再交给 opponent.observe()。
        self._opp_pending: tuple[np.ndarray, int] | None = None
        self._opp_actions = 0

    @property
    def is_dqn_opponent(self) -> bool:
        """对手是否为非 Robot 的 BaseAgent（自博弈路径）。"""
        return not isinstance(self.opponent, Robot)

    # ---------- 生命周期 ----------
    def reset(self) -> np.ndarray:
        self._episodes += 1
        swap = self._swap_seats
        if swap is None:
            swap = self.is_dqn_opponent
        if swap:
            # 按局奇偶交换座位：第 1 局（偶数序）保持基线座位，其后每局翻转。
            # 座位 0 恒先手（core.rules 不变），交换座位 = 交换「哪个策略先手」。
            self.agent_player = (self._base_agent_player + (self._episodes - 1)) % 2
        else:
            self.agent_player = self._base_agent_player
        self.opponent_seat = 1 - self.agent_player

        deck = new_deck(self.rng)
        hands = [deal_uniform(deck), deal_uniform(deck)]
        self.room = GameRoom.new(hands)
        self.steps = 0
        self._opp_pending = None
        self._opp_actions = 0

        self.opponent.reset()
        if not self.is_dqn_opponent:
            # Robot 专属初始化协议（行为与旧实现一致）
            self.opponent.init_dick(["1", "0"], hands[self.opponent_seat])

        self._advance_opponent_until_agent_turn()
        return self._observation()

    def observation(self) -> np.ndarray:
        return self._observation()

    def legal_actions(self) -> tuple[int, ...]:
        return self.room.legal_actions()

    # ---------- 交互 ----------
    def step(self, action: int) -> StepResult:
        room = self.room
        assert room is not None, "必须先 reset()"

        actor = room.whose_turn
        try:
            room.apply(action)
        except IllegalAction as exc:  # 训练循环不应再对已结束房间行动（D4）
            raise IllegalAction(f"环境收到非法动作 {action}: {exc}") from exc
        self.steps += 1
        if not self.is_dqn_opponent:
            self._notify_opponent(actor, action)

        agent_reward, opp_reward = 0.0, 0.0
        done = room.finish
        if done:
            agent_reward, opp_reward = self._settle_rewards()
        else:
            self._advance_opponent_until_agent_turn()
            done = room.finish
            if done:
                agent_reward, opp_reward = self._settle_rewards()
        if self.steps >= MAX_STEPS and not done:
            done = True

        if self.is_dqn_opponent:
            # 对手上一条待结算经验：对局结束时拿到终局对手奖励，否则奖励为 0
            self._finalize_opponent_transition(done=done, opp_reward=opp_reward)

        return StepResult(
            observation=self._observation(),
            reward=agent_reward,
            done=done,
            legal_actions=room.legal_actions(),
            info={
                "winner": room.winner,
                "steps": self.steps,
                "pot": room.all_bet,
                "opponent_reward": opp_reward,
            },
        )

    # ---------- 内部 ----------
    def _observation(self) -> np.ndarray:
        room = self.room
        snapshot = room.snapshot()
        return self.encoder.encode(snapshot, self.agent_player, room.own_hand(self.agent_player))

    def _opponent_observation(self) -> np.ndarray:
        """对手座位视角的 4 维观测（自博弈对称性基础，与 ``_observation`` 互为镜像）。"""
        room = self.room
        snapshot = room.snapshot()
        return self.encoder.encode(snapshot, self.opponent_seat, room.own_hand(self.opponent_seat))

    def _settle_rewards(self) -> tuple[float, float]:
        """零和结算：赢方 +all_bet、输方 -all_bet（对称口径，agent_reward + opponent_reward == 0）。"""
        room = self.room
        total = float(room.all_bet)
        if room.winner == self.agent_player:
            return total, -total
        return -total, total

    def _advance_opponent_until_agent_turn(self) -> None:
        room = self.room
        guard = 0
        while not room.finish and room.whose_turn != self.agent_player and guard < MAX_STEPS:
            guard += 1
            actor = room.whose_turn
            if self.is_dqn_opponent:
                self._dqn_opponent_act(room)
            else:
                snapshot = self._opponent_snapshot()
                action = self.opponent.act(snapshot, room.legal_actions())
                room.apply(action)
                self.opponent_action_counts[int(action)] += 1
                self._notify_opponent(actor, action)
            self.steps += 1

    def _dqn_opponent_act(self, room: GameRoom) -> None:
        """自博弈对手走一步：先结算上一条待结算经验，再行动并记录新的待结算经验。

        对手只从「自己行动」的 transition 学习（reward 用对手视角的零和奖励）；
        对局若在本步行动后结束，终局奖励在调用方（step/reset 后的结算处）补齐。
        """
        self._finalize_opponent_transition(done=False, opp_reward=0.0)
        obs = self._opponent_observation()
        action = self.opponent.act(obs, room.legal_actions())
        room.apply(action)
        self.opponent_action_counts[int(action)] += 1
        if self.opponent_replay_every is not None:
            self._opp_pending = (obs, action)
            self._opp_actions += 1
            if self._opp_actions % self.opponent_replay_every == 0:
                self.opponent.replay()

    def _finalize_opponent_transition(self, done: bool, opp_reward: float) -> None:
        """把对手上一条待结算经验变成 Transition 喂给 opponent.observe()。"""
        if self._opp_pending is None:
            return
        state, action = self._opp_pending
        self._opp_pending = None
        self.opponent.observe(
            Transition(
                state=np.asarray(state, dtype=np.float32),
                action=int(action),
                reward=float(opp_reward) if done else 0.0,
                next_state=np.asarray(self._opponent_observation(), dtype=np.float32),
                done=bool(done),
            )
        )

    def _opponent_snapshot(self) -> dict:
        room = self.room
        snapshot = room.snapshot()
        snapshot["hand"] = room.own_hand(1 - self.agent_player)
        return snapshot

    def _notify_opponent(self, actor: int, action: int) -> None:
        """把行动喂给 Robot 的威胁模型（沿用旧 json 协议）。"""
        room = self.room
        payload = {
            "game_process": "inform",
            "0": {"failure": False, "bet_money": room.players[0].bet},
            "1": {"failure": False, "bet_money": room.players[1].bet},
            "property": "table",
            "all_bets": room.all_bet,
            "whose_turn": actor,
            "rest_option": room.rest_option,
            "option": int(action),
            "target": -1,
        }
        if int(action) == int(Action.COMPARE) and room.finish:
            payload["battle_win"] = room.winner == 1 - self.agent_player
        try:
            self.opponent.update_dick(payload)
        except Exception:  # noqa: BLE001 - 威胁模型属于启发式，不应中断对局
            pass


def to_transition(state, action: int, result: StepResult) -> Transition:
    return Transition(
        state=np.asarray(state, dtype=np.float32),
        action=int(action),
        reward=float(result.reward),
        next_state=np.asarray(result.observation, dtype=np.float32),
        done=bool(result.done),
    )


__all__ = ["ACTION_NAMES", "CardGameEnv", "StepResult", "to_transition", "BET_OPTIONS"]
