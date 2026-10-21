"""牌与牌堆。

花色强度：黑桃 > 红心 > 方块 > 梅花（与原实现的 suit_list 顺序一致）。
牌面强度：2 < 3 < ... < 13(K) < 14(A)，A 为最大牌。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Suit(IntEnum):
    SPADE = 0
    HEART = 1
    DIAMOND = 2
    CLUB = 3

    @property
    def cn(self) -> str:
        return SUIT_CN[self]


SUIT_CN = {
    Suit.SPADE: "黑桃",
    Suit.HEART: "红心",
    Suit.DIAMOND: "方块",
    Suit.CLUB: "梅花",
}

SUIT_FROM_CN = {v: k for k, v in SUIT_CN.items()}

MIN_RANK = 2
MAX_RANK = 14


@dataclass(frozen=True)
class Card:
    suit: Suit
    rank: int

    def __post_init__(self) -> None:
        if not isinstance(self.rank, int):
            raise TypeError(f"rank 必须是 int，收到 {type(self.rank).__name__}")
        if not MIN_RANK <= self.rank <= MAX_RANK:
            raise ValueError(f"rank 必须在 {MIN_RANK}..{MAX_RANK}，收到 {self.rank}")

    @property
    def name(self) -> str:
        return f"{self.suit.cn}{self.rank}"

    def __str__(self) -> str:
        return self.name

    @classmethod
    def from_legacy(cls, item: dict) -> "Card":
        """兼容旧实现的 {'suit': '黑桃', 'value': 7} 字典格式。"""
        return cls(SUIT_FROM_CN[item["suit"]], int(item["value"]))

    def to_legacy(self) -> dict:
        return {"suit": self.suit.cn, "value": self.rank}


def full_deck() -> tuple[Card, ...]:
    """返回 52 张牌（未洗）。"""
    return tuple(Card(suit, rank) for suit in Suit for rank in range(MIN_RANK, MAX_RANK + 1))


def hand_from_legacy(items) -> tuple[Card, ...]:
    return tuple(Card.from_legacy(i) for i in items)


def hand_to_legacy(hand) -> list[dict]:
    return [c.to_legacy() for c in hand]
