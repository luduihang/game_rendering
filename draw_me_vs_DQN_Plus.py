"""炸金花 —— 人类对战 DQN（唯一策略入口）。

真正的实现位于 ``ui/``（渲染 + 事件循环）、``core/``（规则）、``agents/``（策略）。
本文件只做启动，不含任何游戏逻辑、不 import 星号、不 sleep、无 import 期副作用。

用法：
    python draw_me_vs_DQN_Plus.py
    SDL_VIDEODRIVER=dummy python draw_me_vs_DQN_Plus.py   # 无头（自动化验证）
"""

from ui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
