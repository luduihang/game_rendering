"""D4 复现：训练循环使用滞后 done 标志。

game_room_deepseek_cp.py::main 的控制流：
    while not room.finish:
        room.get_choice(action)          # DQN 动作，可能已结束对局
        ...
        if not done:                      # done 此刻仍为 False（滞后）
            room.get_choice(opp)          # 对手在「已结束」的房间上继续行动

而 draw.py::__main__ 用的是 `if not room.finish:`，无此问题（r3 已订正 r2 的举证）。

本脚本按下述结构复刻该控制流，统计「对局已结束但仍被调用 get_choice」的次数。
"""

import os

from common import check, h, summary

import game_room_deepseek_cp as G


class CountingRoom(G.Game_room):
    def __init__(self):
        super().__init__()
        self.calls_total = 0
        self.calls_after_finish = 0

    def get_choice(self, action):
        if self.finish:
            self.calls_after_finish += 1
        self.calls_total += 1
        super().get_choice(action)


def lagging_loop(room):
    """复刻 main() 的 if not done 结构。DQN 首步即弃牌，对局立即结束。"""
    room.init_arg()
    done = False
    guard = 0
    while not room.finish and guard < 50:
        guard += 1
        room.get_choice(4)  # DQN 弃牌 → finish=True
        if not done:  # 滞后标志：此处 done 仍为 False
            room.get_choice(4)  # 对手在已结束房间上行动
        if room.finish:
            done = True


def fixed_loop(room):
    """对照组：用 room.finish 守卫（draw.py 的写法）。"""
    room.init_arg()
    guard = 0
    while not room.finish and guard < 50:
        guard += 1
        room.get_choice(4)
        if not room.finish:
            room.get_choice(4)


def main():
    h("D4 已结束房间是否被继续行动")

    lag = CountingRoom()
    lagging_loop(lag)
    print(f"\n滞后 done 版本: get_choice 总调用 {lag.calls_total} 次，"
          f"其中对局已结束后仍调用 {lag.calls_after_finish} 次")
    ok_lag = lag.calls_after_finish == 0
    check("滞后 done 版本不应在结束后继续行动", ok_lag,
          f"实际结束后调用 {lag.calls_after_finish} 次 → 污染经验回放")

    fix = CountingRoom()
    fixed_loop(fix)
    print(f"\nroom.finish 守卫版本: get_choice 总调用 {fix.calls_total} 次，"
          f"其中对局已结束后仍调用 {fix.calls_after_finish} 次")
    ok_fix = fix.calls_after_finish == 0
    check("room.finish 守卫版本不应在结束后继续行动", ok_fix)

    # 真实源码断言：修复后 game_room_deepseek_cp.py 的循环不得再用滞后 done 标志
    src = open(os.path.join(os.path.dirname(__file__), "..", "..",
                            "game_room_deepseek_cp.py"), encoding="utf-8").read()
    uses_lagging = "if not done:" in src
    uses_finish = "if not room.finish:" in src
    check("game_room_deepseek_cp.py 已改用 room.finish 守卫（不依赖滞后 done）",
          (not uses_lagging) and uses_finish,
          f"源码中 if not done: {uses_lagging} / if not room.finish: {uses_finish}")

    passed = int(ok_fix) + int((not uses_lagging) and uses_finish)
    bugs = int(not ok_lag)
    summary("D4", passed, bugs,
            "滞后 guard 仍作为「错误模式」保留在夹具中；真实源码已修复")


if __name__ == "__main__":
    main()
