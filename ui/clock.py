"""可注入的节奏器（替代散落的 time.sleep）。

三种模式：
- ``REAL``      跟随真实时钟（游戏运行时使用），用 pygame.time.Clock 限帧
- ``FIXED``     虚拟时钟按固定步长推进（录制/回放，不消耗真实时间）
- ``IMMEDIATE`` 虚拟时钟每帧直接跳到下一个截止点（测试用，整局零等待）

关键约定：**本模块不 sleep**。所有「等待」都表达为「检查 deadline 是否已到」，
由主循环每帧调用 ``now()`` 判断，因此等待期间窗口照常重绘、事件照常处理。
"""

from __future__ import annotations

import time
from enum import Enum


class TickPolicy(Enum):
    REAL = "real"
    FIXED = "fixed"
    IMMEDIATE = "immediate"


class Ticker:
    def __init__(self, policy: TickPolicy = TickPolicy.REAL, fps: int = 60, fixed_dt: float = 1 / 60):
        self.policy = policy
        self.fps = fps
        self.fixed_dt = fixed_dt
        self._virtual_start = time.perf_counter()
        self._frames = 0
        self._last_frame = time.perf_counter()
        self._dt = 0.0
        self._clock = None

    # ---------- 帧循环钩子 ----------
    def begin_frame(self) -> float:
        """返回本帧 dt（秒）。IMMEDIATE 下恒为 fixed_dt，不做任何真实等待。"""
        now = time.perf_counter()
        self._dt = now - self._last_frame
        self._last_frame = now
        self._frames += 1
        return self._dt

    def end_frame(self) -> None:
        """REAL 模式限帧；FIXED/IMMEDIATE 不做任何等待。"""
        if self.policy is TickPolicy.REAL:
            if self._clock is None:
                import pygame

                self._clock = pygame.time.Clock()
            self._clock.tick(self.fps)

    # ---------- 时间源 ----------
    def now(self) -> float:
        """统一的「游戏时间」。等待逻辑只用它判断，从不 sleep。"""
        if self.policy is TickPolicy.REAL:
            return time.perf_counter()
        if self.policy is TickPolicy.FIXED:
            return self._virtual_start + self._frames * self.fixed_dt
        # IMMEDIATE：每帧视为前进一大步，便于整局零等待跑完
        return self._virtual_start + self._frames * max(self.fixed_dt, 1.0)

    def deadline(self, seconds: float) -> float:
        return self.now() + max(0.0, seconds)

    def due(self, deadline: float | None) -> bool:
        return deadline is not None and self.now() >= deadline

    @property
    def frames(self) -> int:
        return self._frames

    @property
    def dt(self) -> float:
        return self._dt
