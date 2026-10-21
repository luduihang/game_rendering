"""D1 回归：看牌结算必须「比输者输」，且尊重 whose_turn。

P0 基线（修复前）：4/4 用例判胜相反 —— 代码是
    if cards1_value < cards2_value: winner = 0
既忽略 whose_turn，又把比较方向写反（牌小者获胜）。
现由 core.GameRoom 实现正确语义（契约 D-R2）。
"""

from common import check, h, hand, summary

from core.rules import Action, GameRoom

STRONG = hand(("SPADE", 14), ("HEART", 14), ("DIAMOND", 14))
WEAK = hand(("SPADE", 2), ("HEART", 3), ("DIAMOND", 5))


def main():
    h("D1 看牌结算（回归检查）")

    cases = [
        (0, STRONG, WEAK, 0, "玩家0看牌且牌大 → 玩家0胜"),
        (0, WEAK, STRONG, 1, "玩家0看牌且牌小 → 玩家1胜"),
        (1, STRONG, WEAK, 0, "玩家1看牌且牌小 → 玩家0胜"),
        (1, WEAK, STRONG, 1, "玩家1看牌且牌大 → 玩家1胜"),
    ]

    passed = failed = 0
    for whose_turn, hand0, hand1, expected, desc in cases:
        room = GameRoom.new([hand0, hand1])
        room.whose_turn = whose_turn
        room.apply(Action.COMPARE)
        ok = room.winner == expected
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
        check(f"whose_turn={whose_turn}", ok, f"{desc}；期望 {expected}，实际 {room.winner}")

    summary("D1", passed, failed, "修复后 4/4 判定正确（P0 时为 0/4）")


if __name__ == "__main__":
    main()
