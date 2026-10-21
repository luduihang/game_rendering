"""对局状态机与结算。

规则（与 algorithm.py::show_help_font 一致）：
- 开局各押注底注（默认 5）
- 依次行动：押注 10/20/50/100、弃牌、看牌
- **最低可押档 = 已出现的最高押注档**（rest_option 单调不减）
- 看牌需支付当前单注（BET_OPTIONS[rest_option]），与对手比大小，**比输者输掉本局**
- 弃牌者输掉本局
- 结束时赢家拿走全部押注池

已修复的缺陷：
- D1：看牌结算不再忽略 whose_turn，且比较方向正确（原先牌小者反而获胜）
- D2：rest_option 单调不减，降档押注抛 IllegalAction
- D4：对局结束后任何行动都抛 IllegalAction（不会再「多走一步」）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Sequence

from core.cards import Card
from core.evaluator import compare, evaluate

BET_OPTIONS = (10, 20, 50, 100)
DEFAULT_ANTE = 5
DEFAULT_MONEY = 20000


class Action(IntEnum):
    BET_10 = 0
    BET_20 = 1
    BET_50 = 2
    BET_100 = 3
    FOLD = 4
    COMPARE = 5

    @property
    def is_bet(self) -> bool:
        return int(self) <= 3


class IllegalAction(ValueError):
    """非法动作（对局已结束、降档押注、索引越界等）。"""


@dataclass
class Player:
    name: str
    money: int
    bet: int = DEFAULT_ANTE
    folded: bool = False


@dataclass
class GameRoom:
    hands: tuple[tuple[Card, ...], ...]
    players: tuple[Player, ...]
    whose_turn: int = 0
    rest_option: int = 0
    all_bet: int = DEFAULT_ANTE * 2
    finish: bool = False
    winner: int | None = None
    history: list[tuple[int, int]] = field(default_factory=list)

    # ---------- 构造 ----------
    @classmethod
    def new(
        cls,
        hands: Sequence[Sequence],
        money: tuple[int, int] = (DEFAULT_MONEY, DEFAULT_MONEY),
        names: tuple[str, str] = ("玩家0", "玩家1"),
        ante: int = DEFAULT_ANTE,
    ) -> "GameRoom":
        parsed = tuple(
            tuple(c if isinstance(c, Card) else Card.from_legacy(c) for c in hand) for hand in hands
        )
        if len(parsed) != 2 or any(len(h) != 3 for h in parsed):
            raise ValueError("需要两名玩家、每人三张牌")
        players = (
            Player(names[0], money[0] - ante, ante),
            Player(names[1], money[1] - ante, ante),
        )
        return cls(hands=parsed, players=players, all_bet=ante * 2)

    # ---------- 查询 ----------
    def hand(self, player: int) -> tuple[Card, ...]:
        return self.hands[player]

    def own_hand(self, player: int) -> tuple[Card, ...]:
        """该玩家自己的手牌（D5：用具名访问器消除 cards1/cards2 的归属歧义）。"""
        return self.hands[player]

    def opponent_hand(self, player: int) -> tuple[Card, ...]:
        return self.hands[1 - player]

    def legal_actions(self) -> tuple[int, ...]:
        if self.finish:
            return ()
        return tuple(range(self.rest_option, len(BET_OPTIONS))) + (Action.FOLD, Action.COMPARE)

    def rank_of(self, player: int):
        return evaluate(self.hands[player])

    def snapshot(self) -> dict:
        """供 UI 渲染的只读状态快照（UI 不得自行记账）。"""
        return {
            "whose_turn": self.whose_turn,
            "rest_option": self.rest_option,
            "all_bet": self.all_bet,
            "bets": tuple(p.bet for p in self.players),
            "money": tuple(p.money for p in self.players),
            "folded": tuple(p.folded for p in self.players),
            "finish": self.finish,
            "winner": self.winner,
            "legal_actions": self.legal_actions(),
        }

    # ---------- 行动 ----------
    def apply(self, action: int) -> None:
        if self.finish:
            raise IllegalAction("对局已结束，不能再行动（D4）")
        try:
            action = Action(int(action))
        except ValueError as exc:
            raise IllegalAction(f"未知动作: {action}") from exc

        actor = self.whose_turn
        if action.is_bet:
            self._bet(actor, action)
        elif action is Action.FOLD:
            self._fold(actor)
        else:
            self._compare(actor)
        self.history.append((actor, int(action)))
        if not self.finish:
            self.whose_turn = 1 - actor

    def _bet(self, actor: int, action: Action) -> None:
        if int(action) < self.rest_option:
            raise IllegalAction(
                f"押注档位 {BET_OPTIONS[int(action)]} 低于当前最低可押档 {BET_OPTIONS[self.rest_option]}（D2）"
            )
        amount = BET_OPTIONS[int(action)]
        player = self.players[actor]
        player.bet += amount
        player.money -= amount
        self.all_bet += amount
        self.rest_option = max(self.rest_option, int(action))

    def _fold(self, actor: int) -> None:
        self.players[actor].folded = True
        self._finish(winner=1 - actor)

    def _compare(self, actor: int) -> None:
        """看牌：支付当前单注，与对手比大小，比输者输（D1）。"""
        cost = BET_OPTIONS[self.rest_option]
        player = self.players[actor]
        player.bet += cost
        player.money -= cost
        self.all_bet += cost

        outcome = compare(self.hands[actor], self.hands[1 - actor])
        # 平局时看牌方输（显式约定，避免原实现里「牌小者获胜」的方向错误）
        self._finish(winner=actor if outcome > 0 else 1 - actor)

    def _finish(self, winner: int) -> None:
        self.finish = True
        self.winner = winner
        self.players[winner].money += self.all_bet
