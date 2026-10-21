"""资源路径、颜色与基础布局常量。

相对旧版的改动：
- 全部路径改为 ``pathlib`` 相对**包根**解析，消除 ``'../game_exercise/'``
  与指向仓库外的 ``'../myclient/'`` 坏路径
- **不再 import pygame**，也不再在类体定义期调用 ``pygame.Rect``
  → ``import const`` 不再依赖 ``pygame.init()``（这是 core 无法脱离 pygame 的根因）
- 移除已废弃的三人桌/登录页布局（当前仅保留人类 vs DQN 的双人对局）
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# ---- 资源目录（全部相对包根，无 '../' 路径）----
item_pic_directory = SRC / "item_pic"
card_directory = SRC / "card_pic"
button_directory = SRC / "button"
font_directory = SRC / "Font"
character_directory = SRC / "character"
bgm_directory = SRC / "BGM"

# 兼容旧名（历史代码用 background_directory 指 item_pic）
background_directory = item_pic_directory

# ---- 关键资源 ----
Background = item_pic_directory / "桌面清晰.png"
Card_Back = card_directory / "扑克牌背面.png"

FONT_MAIN = font_directory / "ShangShouHanShuTi.ttf"
FONT_UI = font_directory / "HeiTi.ttf"

# ---- 窗口与卡牌尺寸 ----
# 背景原图为 1200x900（4:3），窗口保持同比例以免拉伸失真
GAME_WIDTH_SIZE = 1000
GAME_HEIGHT_SIZE = 750
BACKGROUND_W = 1000
BACKGROUND_H = 750

CARD_SIZE = (120, 172)          # 自己手牌
CARD_SIZE_SMALL = (80, 115)     # 对手暗牌 / 结算展示

# ---- 牌型名（与 core.evaluator.HAND_TYPE_NAMES 一致）----
card_type_arr = ["单张", "对子", "顺子", "金花", "顺金", "三张"]
select_option = ["10", "20", "50", "100", "throw_card", "compare_card"]


class Color:
    white = (255, 255, 255)
    black = (0, 0, 0)
    red = (220, 40, 40)
    green = (0, 200, 100)
    blue = (40, 110, 220)
    yellow = (255, 215, 0)
    golden = (255, 200, 60)
    gray = (150, 150, 150)
    dark = (30, 30, 36)
    panel = (24, 24, 30)
    panel_light = (48, 48, 58)
    dim = (110, 110, 120)


# ---- BGM（保留清单，路径已修正到 src/BGM）----
BG_MUSIC = [
    bgm_directory / "春节序曲.mp3",
    bgm_directory / "喜洋洋.mp3",
    bgm_directory / "鸟之诗.mp3",
    bgm_directory / "江南.mp3",
    bgm_directory / "克罗地亚狂想曲.mp3",
    bgm_directory / "月光.mp3",
    bgm_directory / "春庭雪.mp3",
    bgm_directory / "天行九歌.mp3",
    bgm_directory / "帝都.mp3",
    bgm_directory / "知否知否.mp3",
]


def asset_exists(path: Path) -> bool:
    return Path(path).exists()
