"""D4 回归：对局结束后不得再行动。

P0 基线（修复前）：训练循环用滞后的 ``if not done:`` 守卫，
玩家动作已结束对局时，对手仍在已结束的房间上多行动一步（污染经验回放）。
"""

from common import check, h, hand, summary

from core.rules import Action, GameRoom, IllegalAction


def main():
    h("D4 结束后拒绝继续行动（回归检查）")

    room = GameRoom.new([
        hand(("SPADE", 14), ("HEART", 14), ("DIAMOND", 14)),
        hand(("SPADE", 2), ("HEART", 3), ("DIAMOND", 5)),
    ])

    passed = failed = 0
    room.apply(Action.FOLD)
    passed, failed = (passed + 1, failed) if room.finish else (passed, failed + 1)
    check("弃牌后对局结束", room.finish)

    passed, failed = (passed + 1, failed) if room.legal_actions() == () else (passed, failed + 1)
    check("结束后合法动作为空", True)

    try:
        room.apply(Action.BET_10)
        raised = False
    except IllegalAction:
        raised = True
    passed, failed = (passed + 1, failed) if raised else (passed, failed + 1)
    check("结束后再行动必须抛 IllegalAction", raised)

    # 结算：赢家拿走全部底池，金币守恒
    total = sum(p.money for p in room.players)
    passed, failed = (passed + 1, failed) if total == 40000 else (passed, failed + 1)
    check("结算后金币守恒（40000）", total == 40000, f"实际 {total}")

    summary("D4", passed, failed, "环境层与 core 层双重防护，不再多走一步")


if __name__ == "__main__":
    main()
