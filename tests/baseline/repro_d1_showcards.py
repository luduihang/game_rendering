"""D1 复现：看牌结算 (action=5) 忽略 whose_turn。

规则（show_help_font）：看牌方支付当前单注费用后与对手比大小，比输者输掉本局。
已确认语义（契约 D-R2）：当 whose_turn 手牌较小时 winner = 1 - whose_turn。

当前代码（game_room_deepseek_cp.py::Game_room.get_choice, action==5）：
    if self.cards1_value < self.cards2_value:
        self.winner = 0
只看牌面大小，完全不看 self.whose_turn。

预期基线：4 个用例中「看牌方牌小」的 2 个用例判胜反转。
"""

from common import check, h, summary

import game_room_deepseek_cp as G


def make_room(whose_turn, cards1_smaller):
    """绕过 __init__ 的随机发牌，构造牌面可控的房间。"""
    room = G.Game_room.__new__(G.Game_room)
    room.rest_option = 0
    room.circle = 1
    room.all_bet = 10
    room.player_bet = [5, 5]
    room.player_money = [20000, 20000]
    room.whose_turn = whose_turn
    room.finish = False
    room.winner = -1
    room.cards1_value = 100 if cards1_smaller else 900
    room.cards2_value = 900 if cards1_smaller else 100
    return room


def main():
    h("D1 看牌结算 (action=5) 是否尊重 whose_turn")

    cases = [
        (0, True, "玩家0看牌，玩家0牌小 → 应由玩家1获胜"),
        (0, False, "玩家0看牌，玩家0牌大 → 应由玩家0获胜"),
        (1, True, "玩家1看牌，玩家1牌大 → 应由玩家1获胜"),
        (1, False, "玩家1看牌，玩家1牌小 → 应由玩家0获胜"),
    ]

    passed = bugs = 0
    for whose_turn, cards1_smaller, desc in cases:
        # 看牌方自己的手牌是否较小
        player_smaller = cards1_smaller if whose_turn == 0 else (not cards1_smaller)
        expected = (1 - whose_turn) if player_smaller else whose_turn

        room = make_room(whose_turn, cards1_smaller)
        room.get_choice(5)  # 5 = compare_card（看牌）
        actual = room.winner

        ok = actual == expected
        if ok:
            passed += 1
        else:
            bugs += 1
        check(
            f"whose_turn={whose_turn} cards1<cards2={cards1_smaller}",
            ok,
            f"{desc}；期望 winner={expected}，实际 winner={actual}",
        )

    summary("D1", passed, bugs, "看牌方牌小的 2 个用例应判胜反转")


if __name__ == "__main__":
    main()
