"""D5 回归：手牌归属必须无歧义（不存在信息泄漏）。

P0 基线（修复前）：``__init__`` 打印「机器人的手牌是 cards1」，
而 ``show_inform`` 打印「玩家0的手牌是 cards1」—— 同一份牌被描述成两个归属。
实测确认 get_state 读的是本人手牌（无泄漏），真实问题只是标签矛盾。
现由 core.GameRoom 的具名访问器 own_hand / opponent_hand 消除歧义。
"""

from common import check, h, hand, summary

from core.rules import GameRoom

STRONG = hand(("SPADE", 14), ("HEART", 14), ("DIAMOND", 14))
WEAK = hand(("SPADE", 2), ("HEART", 3), ("DIAMOND", 5))


def main():
    h("D5 手牌归属具名化（回归检查）")

    room = GameRoom.new([STRONG, WEAK])
    passed = failed = 0

    cases = [
        ("own_hand(0) == 玩家0的牌", room.own_hand(0) == STRONG),
        ("opponent_hand(0) == 玩家1的牌", room.opponent_hand(0) == WEAK),
        ("own_hand(1) == 玩家1的牌", room.own_hand(1) == WEAK),
        ("opponent_hand(1) == 玩家0的牌", room.opponent_hand(1) == STRONG),
    ]
    for name, ok in cases:
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
        check(name, ok)

    # 状态编码必须使用本人手牌
    from agents.dqn import StateEncoder
    from core.strength import beats_probability

    encoder = StateEncoder()
    state = encoder.encode(room.snapshot(), 0, room.own_hand(0))
    ok = abs(float(state[3]) - beats_probability(STRONG)) < 1e-6
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    check("玩家0 的状态特征来自自己的手牌（无信息泄漏）", ok,
          f"state[3]={float(state[3]):.4f} vs 本人手牌胜率 {beats_probability(STRONG):.4f}")

    summary("D5", passed, failed, "具名访问器消除 cards1/cards2 归属歧义")


if __name__ == "__main__":
    main()
