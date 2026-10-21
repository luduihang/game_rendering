"""ui 主题：资源路径解析、原始贴图映射与布局。

贴图来源（全部为仓库内原始素材，不做重绘）：
- 动作按钮：``src/button/``（十注/二十注/五十注/一百注/弃牌/看牌）
- 玩家头像：``src/character/``（角色原图）
- 金币图标：``src/item_pic/金币.png``

pygame.Rect 一律在运行时创建（不在模块或类体定义期）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import const

# ---- 原始贴图映射 ----
# 动作索引（与 core.rules.Action 一致）→ 按钮贴图文件名
BUTTON_IMAGES: dict[int, str] = {
    0: "十注.png",
    1: "二十注.png",
    2: "五十注.png",
    3: "一百注.png",
    4: "弃牌.png",
    5: "看牌.png",
}

COIN_IMAGE = "金币.png"

# 角色头像（原 all_spirit 映射：fire/ice/water/cat）
AVATAR_IMAGES: dict[str, str] = {
    "human": "火花.png",
    "ai": "雪影娃娃第三阶段.png",
}
AVATAR_LIBRARY: dict[str, str] = {
    "fire_spirit": "火花.png",
    "ice_spirit": "雪影娃娃第三阶段.png",
    "water_spirit": "水蓝蓝.png",
    "cat_spirit": "喵喵.png",
}


def asset_paths() -> dict[str, Path]:
    return {
        "background": Path(const.Background),
        "card_back": Path(const.Card_Back),
        "card_dir": Path(const.card_directory),
        "font_main": Path(const.FONT_MAIN),
        "font_ui": Path(const.FONT_UI),
        "button_dir": Path(const.button_directory),
        "character_dir": Path(const.character_directory),
        "item_dir": Path(const.item_pic_directory),
    }


def button_image_path(action: int) -> Path | None:
    name = BUTTON_IMAGES.get(int(action))
    if name is None:
        return None
    return Path(const.button_directory) / name


def avatar_image_path(who: str, variant: str | None = None) -> Path | None:
    if variant and variant in AVATAR_LIBRARY:
        return Path(const.character_directory) / AVATAR_LIBRARY[variant]
    name = AVATAR_IMAGES.get(who)
    if name is None:
        return None
    return Path(const.character_directory) / name


def coin_image_path() -> Path:
    return Path(const.item_pic_directory) / COIN_IMAGE


def missing_assets() -> list[str]:
    """返回缺失的关键资源（供启动自检）。"""
    required = {
        "background": Path(const.Background),
        "card_back": Path(const.Card_Back),
        "card_dir": Path(const.card_directory),
        "font_main": Path(const.FONT_MAIN),
        "font_ui": Path(const.FONT_UI),
        "coin": coin_image_path(),
    }
    required.update({f"button_{a}": p for a in BUTTON_IMAGES if (p := button_image_path(a))})
    required.update({f"avatar_{k}": p for k in AVATAR_IMAGES if (p := avatar_image_path(k))})
    return [name for name, path in required.items() if not Path(path).exists()]


@dataclass
class Layout:
    width: int = const.GAME_WIDTH_SIZE
    height: int = const.GAME_HEIGHT_SIZE

    # 手牌（底部手牌上沿 424 + 172 = 596，与按钮区 660 不重叠）
    own_hand_origin: tuple[int, int] = (356, 424)
    own_card_gap: int = 132
    opponent_hand_origin: tuple[int, int] = (410, 64)
    opponent_card_gap: int = 92

    # 头像（原角色贴图）
    own_avatar: tuple[int, int, int, int] = (40, 356, 120, 128)
    opponent_avatar: tuple[int, int, int, int] = (40, 60, 96, 93)

    # 信息文字（左侧窄栏，不侵入手牌区 x>=356）
    own_info_pos: tuple[int, int] = (170, 352)
    opponent_info_pos: tuple[int, int] = (152, 66)
    pot_pos: tuple[int, int] = (500, 316)
    status_pos: tuple[int, int] = (500, 34)

    # 按钮（原始贴图比例 2:1）
    button_width: int = 150
    button_height: int = 75
    button_gap: int = 12
    button_y: int = 660
    button_labels: dict[int, str] = field(
        default_factory=lambda: {0: "押 10", 1: "押 20", 2: "押 50", 3: "押 100", 4: "弃牌", 5: "看牌"}
    )

    # 金币图标尺寸
    coin_size: int = 22

    def avatar_rect(self, who: str):
        import pygame

        return pygame.Rect(self.own_avatar if who == "human" else self.opponent_avatar)

    def button_rects(self, legal_actions) -> dict[int, "object"]:
        """按合法动作动态生成按钮矩形（运行时创建 pygame.Rect）。"""
        import pygame

        legal = list(legal_actions)
        if not legal:
            return {}
        total = len(legal) * self.button_width + (len(legal) - 1) * self.button_gap
        start_x = (self.width - total) // 2
        return {
            action: pygame.Rect(
                start_x + index * (self.button_width + self.button_gap),
                self.button_y,
                self.button_width,
                self.button_height,
            )
            for index, action in enumerate(legal)
        }

    def own_card_rects(self, count: int):
        import pygame

        return [
            pygame.Rect(self.own_hand_origin[0] + i * self.own_card_gap,
                        self.own_hand_origin[1], *const.CARD_SIZE)
            for i in range(count)
        ]

    def opponent_card_rects(self, count: int):
        import pygame

        return [
            pygame.Rect(self.opponent_hand_origin[0] + i * self.opponent_card_gap,
                        self.opponent_hand_origin[1], *const.CARD_SIZE_SMALL)
            for i in range(count)
        ]
