"""D5 复核（T0.4）：DQN 的 get_state 读到的到底是谁的牌？

r2 曾断言这里存在「信息泄漏」（玩家0 读到对手手牌）。r3 依据源码接线判断该结论
不成立。本脚本用实测复核，避免把错误结论带进 Phase 3。

判定依据（全部来自运行期实测，不依赖注释）：
1. Game_room.__init__ 的 print 标签说 cards1 是「机器人」的牌；
2. show_inform 的标签说 cards1 是「玩家0」的牌 —— 二者矛盾；
3. opponent_robot.init_dick(['1','0'], room.cards2) → 机器人实际持有 cards2；
4. DQNAgent.get_state(room, 0) 的特征来自 cards1。
→ 若 3 与 4 同时成立，则玩家0(DQN) 看 cards1 = 自己的牌，无泄漏。
"""

import contextlib
import io

from common import check, h, summary

import game_room_deepseek_cp as G
from card_deck import Cards_Probability
from mymath.robot2 import Robot2


def hand_str(cards):
    return " ".join(f"{c['suit']}{c['value']}" for c in cards)


def main():
    h("D5 接线复核：DQN 状态特征来自哪一份手牌")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        room = G.Game_room()
    init_prints = [ln for ln in buf.getvalue().splitlines() if "手牌" in ln]

    print("Game_room.__init__ 的标签输出:")
    for ln in init_prints:
        print(f"  {ln}")
    print("\nshow_inform 的标签输出（同一房间）:")
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        room.show_inform()
    for ln in buf2.getvalue().splitlines():
        if "手牌" in ln:
            print(f"  {ln}")

    contradictory = (
        any("机器人的手牌" in ln for ln in init_prints)
        and any("玩家0的手牌" in ln for ln in buf2.getvalue().splitlines())
    )
    check("__init__ 与 show_inform 的手牌标签自洽", not contradictory,
          "两处都把 cards1 描述成不同的归属 → 遗留脏标签（D5 降级后的真实问题）")

    # 3) 机器人实际拿到哪份牌
    robot = Robot2("1")
    robot.init_dick(["1", "0"], room.cards2)
    robot_has_cards2 = robot.cards == room.cards2
    print(f"\ncards1 (玩家0? 机器人?) : {hand_str(room.cards1)}")
    print(f"cards2 (玩家1?)          : {hand_str(room.cards2)}")
    print(f"Robot2('1').init_dick(..., room.cards2) 后，机器人持有 cards2: {robot_has_cards2}")

    # 4) DQN 玩家0 的状态特征来自哪份牌
    p_cards1 = Cards_Probability(room.cards1).get_state()
    p_cards2 = Cards_Probability(room.cards2).get_state()
    state_p0 = G.DQNAgent.get_state(None, room, 0)  # 仅用参数，不需要实例
    onehot_index = int(state_p0[3:].argmax()) + 1

    from_cards1 = onehot_index == p_cards1
    from_cards2 = onehot_index == p_cards2
    print(f"\n玩家0 的 get_state 档位 = {onehot_index}"
          f"（cards1 档位={p_cards1}, cards2 档位={p_cards2}）")
    print(f"特征来源 = cards1: {from_cards1} | = cards2: {from_cards2}")

    no_leak = robot_has_cards2 and from_cards1
    check("玩家0(DQN) 的状态特征来自自己持有的 cards1（无信息泄漏）", no_leak,
          "机器人持 cards2、DQN 读 cards1 → 各自读自己的牌" if no_leak
          else "接线与 r3 结论不符，需挂起请示")

    passed = int(no_leak) + int(not contradictory)
    bugs = 2 - passed
    summary("D5", passed, bugs,
            "无信息泄漏；唯一缺陷是 __init__ 标签与 show_inform 矛盾")


if __name__ == "__main__":
    main()
