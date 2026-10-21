"""发牌。

默认 `deal_uniform`：从洗好的牌堆直接取牌，均匀分布（真实牌局语义）。
`deal_strength_biased`：保留原实现的「三抽一取最优」行为，默认不启用，
仅供复现历史实验（契约 D-R1）。

基线实测（docs/BASELINE-REPORT.md）：
    均匀发牌手牌强度分位均值 0.489、最强档(>0.95)占比 0.013
    三抽一取最优   均值 0.766、最强档占比 0.147（11 倍）
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from core.cards import Card, full_deck
from core.strength import beats_probability

DEFAULT_CANDIDATES = 3


class EmptyDeckError(RuntimeError):
    pass


def new_deck(rng: random.Random | None = None) -> list[Card]:
    """返回洗好的 52 张牌堆。"""
    deck = list(full_deck())
    (rng or random).shuffle(deck)
    return deck


def deal_uniform(deck: list[Card], n: int = 3) -> tuple[Card, ...]:
    """从牌堆取 n 张（均匀发牌，默认路径）。"""
    if len(deck) < n:
        raise EmptyDeckError(f"牌堆剩余 {len(deck)} 张，不足 {n} 张")
    return tuple(deck.pop() for _ in range(n))


def deal_strength_biased(
    deck: list[Card],
    n: int = 3,
    candidates: int = DEFAULT_CANDIDATES,
) -> tuple[Card, ...]:
    """【遗留行为，默认不使用】抽 candidates 组候选，保留最强的一组，其余弃置不回堆。

    这会破坏牌局公平性（有偏分布），仅为复现历史实验保留。
    """
    need = n * candidates
    if len(deck) < need:
        raise EmptyDeckError(f"牌堆剩余 {len(deck)} 张，不足 {need} 张")
    best: tuple[Card, ...] | None = None
    best_p = -1.0
    for _ in range(candidates):
        hand = tuple(deck.pop() for _ in range(n))
        p = beats_probability(hand)
        if p > best_p:
            best, best_p = hand, p
    assert best is not None
    return best


def verify_uniformity(hands: Sequence[Sequence[Card]]) -> float:
    """返回样本的平均强度分位；均匀发牌应趋近 0.5（供测试与验收使用）。"""
    if not hands:
        raise ValueError("样本为空")
    return sum(beats_probability(h) for h in hands) / len(hands)
