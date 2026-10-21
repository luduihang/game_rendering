"""牌型判定与比大小测试（六类 + 边界 + 平局 + 花色决胜）。"""

import pytest

from core.cards import Card, Suit
from core.evaluator import HandType, compare, evaluate


def h(*specs):
    """h(("黑桃", 14), ("红心", 13), ("方块", 12)) → 手牌元组"""
    return tuple(Card(Suit[s], r) for s, r in specs)


SPADE, HEART, DIAMOND, CLUB = "SPADE", "HEART", "DIAMOND", "CLUB"


class TestHandTypes:
    def test_trips(self):
        assert evaluate(h((SPADE, 7), (HEART, 7), (DIAMOND, 7))).hand_type is HandType.TRIPS

    def test_straight_flush(self):
        assert evaluate(h((SPADE, 12), (SPADE, 13), (SPADE, 14))).hand_type is HandType.STRAIGHT_FLUSH

    def test_flush(self):
        assert evaluate(h((SPADE, 2), (SPADE, 7), (SPADE, 14))).hand_type is HandType.FLUSH

    def test_straight(self):
        assert evaluate(h((SPADE, 12), (HEART, 13), (DIAMOND, 14))).hand_type is HandType.STRAIGHT

    def test_pair(self):
        assert evaluate(h((SPADE, 9), (HEART, 9), (DIAMOND, 2))).hand_type is HandType.PAIR

    def test_high_card(self):
        assert evaluate(h((SPADE, 2), (HEART, 7), (DIAMOND, 14))).hand_type is HandType.HIGH_CARD


class TestBorders:
    def test_ace_high_straight_is_straight(self):
        assert evaluate(h((SPADE, 12), (HEART, 13), (DIAMOND, 14))).hand_type is HandType.STRAIGHT

    def test_ace_low_is_not_straight(self):
        """A/2/3 不算顺子（与原实现一致：只认连续值）。"""
        assert evaluate(h((SPADE, 14), (HEART, 2), (DIAMOND, 3))).hand_type is HandType.HIGH_CARD

    def test_two_same_value_one_suit(self):
        """同点三张必然是三条，不可能是金花。"""
        assert evaluate(h((SPADE, 5), (HEART, 5), (CLUB, 5))).hand_type is HandType.TRIPS

    @pytest.mark.parametrize("bad", [[], [("SPADE", 2)], [("SPADE", 2), ("HEART", 3)]])
    def test_requires_three_cards(self, bad):
        with pytest.raises(ValueError):
            evaluate([Card(Suit[s], r) for s, r in bad])

    def test_rejects_out_of_range_rank(self):
        with pytest.raises(ValueError):
            Card(Suit.SPADE, 15)
        with pytest.raises(ValueError):
            Card(Suit.SPADE, 1)


class TestOrdering:
    def test_type_order(self):
        """单张 < 对子 < 顺子 < 金花 < 顺金 < 三张"""
        hands = [
            h((SPADE, 3), (HEART, 5), (DIAMOND, 14)),      # 单张
            h((SPADE, 4), (HEART, 4), (DIAMOND, 2)),       # 对子
            h((SPADE, 12), (HEART, 13), (DIAMOND, 14)),    # 顺子
            h((SPADE, 2), (SPADE, 7), (SPADE, 14)),        # 金花
            h((SPADE, 12), (SPADE, 13), (SPADE, 14)),      # 顺金
            h((SPADE, 2), (HEART, 2), (CLUB, 2)),          # 三张
        ]
        for weaker, stronger in zip(hands, hands[1:]):
            assert compare(stronger, weaker) == 1
            assert compare(weaker, stronger) == -1

    def test_pair_rank_beats_kicker(self):
        low_pair_high_kicker = h((SPADE, 5), (HEART, 5), (DIAMOND, 14))
        high_pair_low_kicker = h((SPADE, 9), (HEART, 9), (DIAMOND, 2))
        assert compare(high_pair_low_kicker, low_pair_high_kicker) == 1

    def test_same_pair_kicker_decides(self):
        a = h((SPADE, 8), (HEART, 8), (DIAMOND, 13))
        b = h((SPADE, 8), (HEART, 8), (DIAMOND, 5))
        assert compare(a, b) == 1

    def test_straight_compares_by_top_card(self):
        a = h((SPADE, 12), (HEART, 13), (DIAMOND, 14))
        b = h((SPADE, 10), (HEART, 11), (DIAMOND, 12))
        assert compare(a, b) == 1

    def test_flush_compares_by_high_card(self):
        a = h((SPADE, 2), (SPADE, 3), (SPADE, 14))
        b = h((SPADE, 5), (SPADE, 6), (SPADE, 13))
        assert compare(a, b) == 1


class TestSuitTiebreak:
    def test_identical_ranks_spade_wins(self):
        spade = h((SPADE, 9), (HEART, 9), (DIAMOND, 5))
        heart = h((HEART, 9), (DIAMOND, 9), (CLUB, 5))
        assert spade[0].rank == heart[0].rank
        assert compare(spade, heart) == 1

    def test_identical_ranks_and_suits_are_equal(self):
        a = h((SPADE, 9), (HEART, 9), (DIAMOND, 5))
        b = h((SPADE, 9), (HEART, 9), (DIAMOND, 5))
        assert compare(a, b) == 0

    def test_compare_is_antisymmetric(self):
        a = h((SPADE, 2), (SPADE, 7), (SPADE, 14))
        b = h((HEART, 3), (CLUB, 3), (SPADE, 2))
        assert compare(a, b) == -compare(b, a)
