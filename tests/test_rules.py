"""对局规则测试：D1（看牌结算）、D2（rest_option 单调）、D4（结束后拒绝行动）。"""

import pytest

from core.cards import Card, Suit
from core.rules import BET_OPTIONS, Action, GameRoom, IllegalAction


def cards(*specs):
    return tuple(Card(Suit[s], r) for s, r in specs)


SPADE, HEART, DIAMOND, CLUB = "SPADE", "HEART", "DIAMOND", "CLUB"

STRONG = cards((SPADE, 14), (HEART, 14), (DIAMOND, 14))   # 三条 A
WEAK = cards((SPADE, 2), (HEART, 3), (DIAMOND, 5))        # 单张


def room(hand0=STRONG, hand1=WEAK):
    return GameRoom.new([hand0, hand1])


class TestD1CompareSettlement:
    """基线 repro_d1_showcards.py 里 4/4 判胜相反的用例，这里必须全部正确。"""

    @pytest.mark.parametrize(
        "whose_turn,hand0,hand1,expected",
        [
            (0, STRONG, WEAK, 0),  # 玩家0看牌且玩家0牌大 → 玩家0胜
            (0, WEAK, STRONG, 1),  # 玩家0看牌且玩家0牌小 → 玩家1胜
            (1, STRONG, WEAK, 0),  # 玩家1看牌且玩家1牌小 → 玩家0胜
            (1, WEAK, STRONG, 1),  # 玩家1看牌且玩家1牌大 → 玩家1胜
        ],
    )
    def test_actor_with_weaker_hand_loses(self, whose_turn, hand0, hand1, expected):
        r = room(hand0, hand1)
        r.whose_turn = whose_turn
        r.apply(Action.COMPARE)
        assert r.finish
        assert r.winner == expected

    def test_compare_charges_current_minimum_bet(self):
        r = room()
        pot_before = r.all_bet
        bet_before = r.players[0].bet
        r.apply(Action.COMPARE)
        assert r.all_bet == pot_before + BET_OPTIONS[0]
        assert r.players[0].bet == bet_before + BET_OPTIONS[0]

    def test_compare_after_raise_charges_raised_amount(self):
        r = room()
        r.apply(Action.BET_100)      # 玩家0 押 100 → rest_option=3
        pot_before = r.all_bet
        bet_before = r.players[0].bet
        r.whose_turn = 0
        r.apply(Action.COMPARE)
        assert r.all_bet == pot_before + BET_OPTIONS[3]
        assert r.players[0].bet == bet_before + BET_OPTIONS[3]

    def test_tie_goes_to_non_acting_player(self):
        r = room(STRONG, STRONG)
        r.whose_turn = 0
        r.apply(Action.COMPARE)
        assert r.winner == 1


class TestD2RestOption:
    def test_rest_option_is_monotonic(self):
        """基线：draw.py 押注 100 后 rest_option 仍为 0。这里必须单调不减。"""
        r = room()
        assert r.rest_option == 0
        r.apply(Action.BET_100)
        assert r.rest_option == 3
        r.whose_turn = 0
        # 降档押注必须被拒绝
        with pytest.raises(IllegalAction):
            r.apply(Action.BET_10)
        assert r.rest_option == 3

    def test_legal_actions_respect_rest_option(self):
        r = room()
        r.apply(Action.BET_50)
        legal = r.legal_actions()
        assert set(range(0, 2)) .isdisjoint(set(legal)), "低档位不应出现在合法动作里"
        assert {2, 3, int(Action.FOLD), int(Action.COMPARE)} == set(legal)

    def test_bet_updates_pool_and_player_state(self):
        r = room()
        r.apply(Action.BET_20)
        assert r.all_bet == 10 + 20
        assert r.players[0].bet == 5 + 20
        assert r.players[0].money == 20000 - 5 - 20


class TestD4FinishedRoom:
    def test_no_action_after_finish(self):
        """基线：结束后对手仍多走一步。这里必须拒绝。"""
        r = room()
        r.apply(Action.FOLD)
        assert r.finish
        with pytest.raises(IllegalAction):
            r.apply(Action.BET_10)
        assert r.legal_actions() == ()

    def test_fold_awards_pot_to_other_player(self):
        r = room()
        pot = r.all_bet
        r.apply(Action.FOLD)
        assert r.winner == 1
        assert r.players[1].money == 20000 - 5 + pot
        assert r.players[0].folded

    def test_winner_takes_whole_pot(self):
        r = room()
        r.apply(Action.BET_50)
        r.whose_turn = 1
        r.apply(Action.COMPARE)   # 玩家1 手牌弱，看牌即输
        assert r.finish
        assert r.winner == 0
        # 押注池已结算给赢家，两人总金币守恒
        assert sum(p.money for p in r.players) == 40000


class TestTurnAndNaming:
    def test_turn_alternates(self):
        r = room()
        assert r.whose_turn == 0
        r.apply(Action.BET_10)
        assert r.whose_turn == 1
        r.apply(Action.BET_20)
        assert r.whose_turn == 0

    def test_own_and_opponent_hand_accessors(self):
        """D5：具名访问器消除 cards1/cards2 的归属歧义。"""
        r = room(STRONG, WEAK)
        assert r.own_hand(0) == STRONG
        assert r.opponent_hand(0) == WEAK
        assert r.own_hand(1) == WEAK
        assert r.opponent_hand(1) == STRONG

    def test_snapshot_is_read_only_view(self):
        r = room()
        snap = r.snapshot()
        assert snap["whose_turn"] == r.whose_turn
        assert snap["bets"] == tuple(p.bet for p in r.players)
        assert snap["money"] == tuple(p.money for p in r.players)

    def test_legacy_dict_hands_are_accepted(self):
        legacy = [[{"suit": "黑桃", "value": 14}, {"suit": "红心", "value": 14},
                   {"suit": "方块", "value": 14}],
                  [{"suit": "黑桃", "value": 2}, {"suit": "红心", "value": 3},
                   {"suit": "方块", "value": 5}]]
        r = GameRoom.new(legacy)
        assert r.own_hand(0)[0].rank == 14
