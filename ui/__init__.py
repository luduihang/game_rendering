"""ui —— pygame 薄渲染层（事件驱动、零阻塞）。

约束：
- 不包含任何游戏规则（规则一律向 core 查询）
- 不使用 time.sleep；节奏由 TickPolicy 注入
- 主循环每帧都处理事件，等待期间窗口可持续重绘并响应 QUIT
"""

from ui.clock import Ticker, TickPolicy
from ui.theme import Layout, asset_paths

__all__ = ["TickPolicy", "Ticker", "Layout", "asset_paths"]
