"""发牌测试：默认均匀（D6 修复）与遗留偏置路径（默认关闭）。"""

import random

import pytest

from core.cards import full_deck
from core.dealing import (
    EmptyDeckError,
    deal_strength_biased,
    deal_uniform,
    new_deck,
    verify_uniformity,
)
from core.strength import beats_probability

SAMPLE = 400
TOP_BUCKET = 0.95


def _sample_uniform(n):
    rng = random.Random(20261021)
    deck = new_deck(rng)
    hands = []
    for _ in range(n):
        if len(deck) < 3:
            deck = new_deck(rng)
        hands.append(deal_uniform(deck))
    return hands


def _sample_biased(n):
    rng = random.Random(20261021)
    deck = new_deck(rng)
    hands = []
    for _ in range(n):
        if len(deck) < 9:
            deck = new_deck(rng)
        hands.append(deal_strength_biased(deck))
    return hands


def test_deal_uniform_returns_three_distinct_cards():
    deck = new_deck(random.Random(1))
    hand = deal_uniform(deck)
    assert len(hand) == 3
    assert len(set(hand)) == 3


def test_deal_uniform_raises_when_deck_too_small():
    deck = new_deck(random.Random(1))[:2]
    with pytest.raises(EmptyDeckError):
        deal_uniform(deck)


def test_uniform_mean_percentile_is_near_half():
    """验收：均匀发牌手牌强度分位均值≈0.5（基线实测 0.489）。"""
    mean = verify_uniformity(_sample_uniform(SAMPLE))
    assert 0.44 < mean < 0.56, f"均匀发牌均值 {mean:.3f} 偏离 0.5 过多"


def test_uniform_top_bucket_matches_theory():
    """最强档（>0.95）理论占比 5%，基线实测 0.013（低方差下的观测）。"""
    hands = _sample_uniform(SAMPLE)
    share = sum(1 for h in hands if beats_probability(h) > TOP_BUCKET) / len(hands)
    assert share < 0.08, f"均匀发牌最强档占比 {share:.3f} 偏高"


def test_biased_path_is_significantly_stronger():
    """D6：三抽一取最优必须被检出显著偏强（基线实测 0.766 vs 0.489）。"""
    uniform_mean = verify_uniformity(_sample_uniform(SAMPLE))
    biased_mean = verify_uniformity(_sample_biased(SAMPLE))
    assert biased_mean - uniform_mean > 0.15, (
        f"偏置路径未显著更强：{biased_mean:.3f} vs {uniform_mean:.3f}"
    )


def test_biased_path_discards_cards():
    """遗留行为：候选组未命中的牌直接丢弃，不回牌堆。"""
    deck = new_deck(random.Random(3))
    before = len(deck)
    deal_strength_biased(deck)
    assert len(deck) == before - 9


def test_uniform_path_does_not_import_strength_table():
    """默认发牌路径不应触发 22100 手建表（保证默认路径轻量）。"""
    from core import strength

    strength._ranked_keys.cache_clear()
    deck = new_deck(random.Random(5))
    deal_uniform(deck)
    # 建表信息现在是空的（未被触发）
    assert strength._ranked_keys.cache_info().hits == 0
    assert strength._ranked_keys.cache_info().currsize == 0


def test_full_deck_is_52_unique_cards():
    deck = full_deck()
    assert len(deck) == 52
    assert len(set(deck)) == 52
