"""通用 UI 辅助与周期定时器。

相对旧版的改动：
- 移除与已删除的三人桌/登录页耦合的渲染函数，改为自包含的文字绘制
- 不再使用 ``from const import *``，不引用已不存在的符号
- ``RepeatedTimer`` 按契约 D7-c 加固（锁 / 幂等 stop / daemon / 异常隔离）
- 游戏规则文案保留在此，供 README 与帮助界面引用
"""

from __future__ import annotations

import threading
import time

import pygame

import const


class RepeatedTimer:
    """周期定时器（D7-c 加固版）。

    修复点：
    - 锁保护 ``is_running`` / ``_timer``，消除 start/stop 竞态
    - 未启动时 ``stop()`` 不再抛 ``AttributeError``（幂等）
    - 定时器线程为 **daemon**，未 stop 也不会阻止进程退出
    - 回调异常被隔离（记录到 ``last_error``），不影响后续调度

    注意：新版 UI 已改用 ``ui.clock.Ticker`` 的帧驱动方式，
    本类保留供脚本或旧接口使用。
    """

    def __init__(self, interval, function, *args, **kwargs):
        self._lock = threading.Lock()
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self._stopped = True
        self.next_call = time.time()
        self.last_error = None

    def _run(self):
        with self._lock:
            self.is_running = False
            if self._stopped:
                return
            self._schedule_locked()
        try:
            self.function(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001 - 回调异常必须被隔离
            self.last_error = exc

    def _schedule_locked(self):
        self.next_call += self.interval
        self._timer = threading.Timer(max(0.0, self.next_call - time.time()), self._run)
        self._timer.daemon = True
        self._timer.start()
        self.is_running = True

    def start(self):
        with self._lock:
            if self.is_running:
                return
            self._stopped = False
            self.next_call = time.time()
            self._schedule_locked()

    def stop(self):
        with self._lock:
            self._stopped = True
            self.is_running = False
            timer = self._timer
            self._timer = None
        if timer is not None:
            timer.cancel()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc_info):
        self.stop()
        return False


def show_font(surface, content, position, font_path=None, size=22, color=const.Color.white):
    """绘制一行文字。字体路径显式传入（不再从 const 星号导入全局符号）。"""
    path = str(font_path or const.FONT_MAIN)
    try:
        font = pygame.font.Font(path, size)
    except (FileNotFoundError, OSError):
        font = pygame.font.SysFont("sans", size)
    surface.blit(font.render(str(content), True, color), position)
    return surface


RULES_LINES = [
    "1. 每名玩家开局由系统发 3 张牌，牌型大小：",
    "   单张 < 对子 < 顺子 < 金花 < 顺金 < 三个。",
    "2. 开局自动押注 5，随后按顺序押注 10 / 20 / 50 / 100，",
    "   也可以选择弃牌或看牌。",
    "3. 最低可押档 = 当前所有玩家押注选项的最大值。",
    "   （例：前一名玩家已押 20，则下一位的可选档为 20 / 50 / 100）",
    "   弃牌：自动弃权，不收回本副牌筹码。",
    "   看牌：支付当前单注大小的费用后与对手比大小，",
    "         比输者输掉本局。",
    "4. 最后留在场上的玩家赢得全部押注池。",
]


def show_help_font(surface, origin=(60, 80), line_height=30):
    """绘制规则说明（供帮助界面使用）。"""
    x, y = origin
    show_font(surface, "游戏规则", (x + 180, y - 40), size=34, color=const.Color.golden)
    for index, line in enumerate(RULES_LINES):
        show_font(surface, line, (x, y + index * line_height), size=20)
    return surface
