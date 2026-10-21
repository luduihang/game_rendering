"""穷举精确强度表测试：确定性、正确性、性能（对比基线的 30.8ms 蒙特卡洛）。"""

import itertools
import random
import time

from core.cards import Card, Suit, full_deck
from core.evaluator import evaluate
from core.strength import beats_probability, strength_bin, strongest_hand, table_size


def h(*specs):
    return tuple(Card(Suit[s], r) for s, r in specs)


SPADE, HEART, DIAMOND, CLUB = "SPADE", "HEART", "DIAMOND", "CLUB"


def test_table_covers_all_hands():
    assert table_size() == 22100


def test_deterministic_across_calls():
    """同一手牌任意次调用必须返回完全相同的结果（原实现每次抖动）。"""
    hand = h((SPADE, 9), (HEART, 9), (DIAMOND, 5))
    values = {beats_probability(hand) for _ in range(50)}
    assert len(values) == 1


def test_probability_bounds():
    assert 0.0 <= beats_probability(h((SPADE, 2), (HEART, 3), (DIAMOND, 5))) < 1.0
    # 最强手牌为三条 A（共 4 种组合，其中 3 种含黑桃 A 因而共享同一比较键）
    top = beats_probability(strongest_hand())
    assert top > 0.9998
    assert top < 1.0


def test_monotonic_with_hand_strength():
    weakest = h((SPADE, 2), (HEART, 3), (DIAMOND, 5))
    middle = h((SPADE, 8), (HEART, 8), (DIAMOND, 2))
    strong = h((SPADE, 12), (SPADE, 13), (SPADE, 14))
    assert beats_probability(weakest) < beats_probability(middle) < beats_probability(strong)


def test_monotonic_matches_exhaustive_pairwise():
    """随机抽样校验：若 A 的牌型键更大，则 A 的胜率必须不小于 B。"""
    deck = list(full_deck())
    rng = random.Random(20261021)
    for _ in range(200):
        a = tuple(rng.sample(deck, 3))
        b = tuple(rng.sample(deck, 3))
        if evaluate(a).key() > evaluate(b).key():
            assert beats_probability(a) >= beats_probability(b)


def test_strength_bin_ranges():
    combos = list(itertools.combinations(full_deck(), 3))
    sample = random.Random(7).sample(combos, 500)
    bins = {strength_bin(tuple(hand)) for hand in sample}
    assert bins <= {1, 2, 3, 4, 5, 6}
    assert min(bins) >= 1 and max(bins) <= 6


def test_query_performance():
    """验收标准：单次查询 < 0.1ms（基线对比：蒙特卡洛 30.8ms/次）。"""
    hands = [tuple(random.Random(i).sample(list(full_deck()), 3)) for i in range(200)]
    beats_probability(hands[0])  # 预热建表
    start = time.perf_counter()
    for hand in hands:
        beats_probability(hand)
    per_query = (time.perf_counter() - start) / len(hands)
    assert per_query < 0.0001, f"单次查询 {per_query * 1e6:.1f}µs 超过 100µs"


def test_table_build_cost_is_one_time():
    """建表应只发生一次（lru_cache），后续调用近乎零成本。"""
    beats_probability(h((SPADE, 2), (HEART, 7), (DIAMOND, 14)))
    start = time.perf_counter()
    beats_probability(h((SPADE, 3), (HEART, 8), (DIAMOND, 13)))
    assert time.perf_counter() - start < 0.01
