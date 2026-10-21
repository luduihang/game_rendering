"""对局环境：把 core.GameRoom 包成 (obs, reward, done) 接口，供训练与评估复用。

不依赖 pygame，可无头运行。
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from agents.base import Transition
from agents.dqn import StateEncoder
from agents.robot import Robot
from core.dealing import deal_uniform, new_deck
from core.rules import BET_OPTIONS, Action, GameRoom, IllegalAction

MAX_STEPS = 200


@dataclass
class StepResult:
    observation: np.ndarray
    reward: float
    done: bool
    legal_actions: tuple[int, ...]
    info: dict


class CardGameEnv:
    """DQN 智能体（默认玩家0）对战 Robot（玩家1）。"""

    def __init__(self, seed: int | None = None, opponent: Robot | None = None, agent_player: int = 0):
        self.seed = seed
        self.rng = random.Random(seed)
        self.agent_player = agent_player
        self.opponent = opponent if opponent is not None else Robot("1", seed=seed)
        self.encoder = StateEncoder()
        self.room: GameRoom | None = None
        self.steps = 0

    # ---------- 生命周期 ----------
    def reset(self) -> np.ndarray:
        deck = new_deck(self.rng)
        hands = [deal_uniform(deck), deal_uniform(deck)]
        self.room = GameRoom.new(hands)
        self.steps = 0

        opponent_seat = 1 - self.agent_player
        self.opponent.reset()
        self.opponent.init_dick(["1", "0"], hands[opponent_seat])

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
        self._notify_opponent(actor, action)

        reward = 0.0
        done = room.finish
        if done:
            reward = self._settle_reward()
        else:
            self._advance_opponent_until_agent_turn()
            done = room.finish
            if done:
                reward = self._settle_reward()
        if self.steps >= MAX_STEPS and not done:
            done = True

        return StepResult(
            observation=self._observation(),
            reward=reward,
            done=done,
            legal_actions=room.legal_actions(),
            info={"winner": room.winner, "steps": self.steps, "pot": room.all_bet},
        )

    # ---------- 内部 ----------
    def _observation(self) -> np.ndarray:
        room = self.room
        snapshot = room.snapshot()
        return self.encoder.encode(snapshot, self.agent_player, room.own_hand(self.agent_player))

    def _settle_reward(self) -> float:
        room = self.room
        if room.winner == self.agent_player:
            return float(room.all_bet)
        return float(-room.players[self.agent_player].bet)

    def _advance_opponent_until_agent_turn(self) -> None:
        room = self.room
        guard = 0
        while not room.finish and room.whose_turn != self.agent_player and guard < MAX_STEPS:
            guard += 1
            snapshot = self._opponent_snapshot()
            action = self.opponent.act(snapshot, room.legal_actions())
            actor = room.whose_turn
            room.apply(action)
            self.steps += 1
            self._notify_opponent(actor, action)

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


__all__ = ["CardGameEnv", "StepResult", "to_transition", "BET_OPTIONS"]
