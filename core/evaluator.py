"""牌型判定与比大小。

牌型大小（与游戏内「帮助」文案一致，见 algorithm.py::show_help_font）：
    单张 < 对子 < 顺子 < 金花 < 顺金 < 三张

同牌型比大小时，按「最大牌 → 次大 → 最小 → 花色」的词法顺序比较。
花色只用于最终打破平局：黑桃 > 红心 > 方块 > 梅花。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from core.cards import Card, Suit


class HandType(IntEnum):
    HIGH_CARD = 0      # 单张
    PAIR = 1           # 对子
    STRAIGHT = 2       # 顺子
    FLUSH = 3          # 金花
    STRAIGHT_FLUSH = 4 # 顺金
    TRIPS = 5          # 三张


HAND_TYPE_NAMES = ["单张", "对子", "顺子", "金花", "顺金", "三张"]


@dataclass(frozen=True)
class HandRank:
    hand_type: HandType
    values: tuple[int, int, int]  # 参与比较的值，按重要性降序（长度恒为 3）
    suit: Suit                    # 决胜花色（较大牌的牌面花色）

    @property
    def type_name(self) -> str:
        return HAND_TYPE_NAMES[int(self.hand_type)]

    def key(self) -> tuple:
        """可排序/可二分比较的键。花色取负值以便「越大越强」。"""
        return (int(self.hand_type), self.values, -int(self.suit))

    def __str__(self) -> str:
        return f"{self.type_name}{self.values}/{self.suit.cn}"


def _is_consecutive(values: tuple[int, int, int]) -> bool:
    """values 为降序元组，故检查逐项递减 1。"""
    return values[0] - 1 == values[1] and values[1] - 1 == values[2]


def evaluate(hand) -> HandRank:
    """计算三张牌的牌型与比较键。"""
    cards = tuple(hand)
    if len(cards) != 3:
        raise ValueError(f"炸金花手牌必须是 3 张，收到 {len(cards)} 张")
    for c in cards:
        if not isinstance(c, Card):
            raise TypeError(f"手牌元素必须是 Card，收到 {type(c).__name__}")

    ranks = sorted((c.rank for c in cards), reverse=True)
    values = (ranks[0], ranks[1], ranks[2])
    distinct = len(set(ranks))
    same_suit = cards[0].suit == cards[1].suit == cards[2].suit

    # 决胜花色：取最大牌所在的花色（三张同点则取最强花色）
    strongest = max(cards, key=lambda c: (c.rank, -int(c.suit)))

    if distinct == 1:
        return HandRank(HandType.TRIPS, values, strongest.suit)
    if distinct == 3 and same_suit and _is_consecutive(values):
        return HandRank(HandType.STRAIGHT_FLUSH, values, strongest.suit)
    if distinct == 3 and same_suit:
        return HandRank(HandType.FLUSH, values, strongest.suit)
    if distinct == 3 and _is_consecutive(values):
        return HandRank(HandType.STRAIGHT, values, strongest.suit)
    if distinct == 2:
        # 对子：对子点数为主，散牌为辅
        pair_rank = next(r for r in set(ranks) if ranks.count(r) == 2)
        kicker = next(r for r in ranks if r != pair_rank)
        return HandRank(HandType.PAIR, (pair_rank, pair_rank, kicker), strongest.suit)
    return HandRank(HandType.HIGH_CARD, values, strongest.suit)


def compare(left, right) -> int:
    """比较两副手牌：left 大返回 1，right 大返回 -1，完全相等返回 0。"""
    a, b = evaluate(left).key(), evaluate(right).key()
    return (a > b) - (a < b)
