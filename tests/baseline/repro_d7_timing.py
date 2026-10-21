"""D7 回归：时序与事件循环（人工提出的问题）。

P0 基线（修复前）：
- D7-a 单步墙钟 ≈1530.8ms，其中 sleep(1.5) 占 98.0%
- D7-b check_button_click 忙等且完全不处理 pygame.QUIT
- D7-c RepeatedTimer 未 start 就 stop() 抛 AttributeError；定时器线程非 daemon
- D7-d import 期 load_state_dict 导致 4 个脚本 import 即崩

现在全部改为：可注入节奏器 + 事件驱动 + 安全定时器 + 显式权重加载。
"""

import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from common import check, h, summary

REPO = Path(__file__).resolve().parents[2]


def main():
    h("D7 时序与事件循环（回归检查）")
    passed = failed = 0

    def record(name, ok, detail=""):
        nonlocal passed, failed
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
        return check(name, ok, detail)

    # D7-a 零 sleep
    sleep_hits = []
    for folder in ("ui", "scripts"):
        for path in (REPO / folder).glob("*.py"):
            if "time.sleep(" in path.read_text(encoding="utf-8"):
                sleep_hits.append(path.name)
    record("ui/ 与 scripts/ 中不存在 time.sleep", not sleep_hits, f"违规: {sleep_hits}")

    # D7-b 事件循环非阻塞 + 响应 QUIT
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 200))

    from ui.app import App, Controller
    from ui.clock import Ticker, TickPolicy

    controller = Controller(seed=1, auto_human=True, think_seconds=0.0, settle_seconds=0.0)
    controller.new_round(now=0.0)
    app = App(controller, renderer=None, ticker=Ticker(TickPolicy.IMMEDIATE))

    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    app.step_frame()
    record("等待期间收到 SDL_QUIT 立即退出循环", app.running is False)
    pygame.event.clear()

    # 整局零等待跑完（节奏器 immediate）
    controller = Controller(seed=2, auto_human=True, think_seconds=0.0, settle_seconds=0.0)
    controller.new_round(now=0.0)
    app = App(controller, renderer=None, ticker=Ticker(TickPolicy.IMMEDIATE))
    started = time.perf_counter()
    for _ in range(400):
        app.step_frame()
        if controller.room.finish:
            break
    elapsed = time.perf_counter() - started
    record("immediate 节奏器可零等待跑完整局", controller.room.finish, f"耗时 {elapsed * 1000:.1f}ms")
    record("整局耗时 < 1s（无阻塞等待）", elapsed < 1.0, f"{elapsed:.3f}s")

    # D7-c RepeatedTimer 加固
    import algorithm

    timer = algorithm.RepeatedTimer(0.05, lambda: None)
    try:
        timer.stop()
        record("未 start 时 stop() 不抛异常", True)
    except Exception as exc:  # noqa: BLE001
        record("未 start 时 stop() 不抛异常", False, f"{type(exc).__name__}: {exc}")

    fired = []

    def boom():
        fired.append(1)
        raise RuntimeError("callback failure")

    timer2 = algorithm.RepeatedTimer(0.05, boom)
    timer2.start()
    record("定时器线程为 daemon（不阻止进程退出）", timer2._timer is not None and timer2._timer.daemon)
    time.sleep(0.3)
    timer2.stop()
    record("回调异常被隔离且不中断调度", len(fired) >= 3, f"触发 {len(fired)} 次，last_error={timer2.last_error}")

    # D7-d 无 import 期权重加载
    offenders = []
    for folder in ("agents", "ui", "scripts"):
        for path in (REPO / folder).glob("*.py"):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if ("load_state_dict" in line or "torch.load" in line) and not line.startswith((" ", "\t")):
                    offenders.append(f"{path.name}:{lineno}")
    record("无模块在 import 期加载权重", not offenders, f"违规: {offenders}")

    summary("D7", passed, failed, "零 sleep + 事件驱动 + 安全定时器 + 显式权重加载")


if __name__ == "__main__":
    main()
