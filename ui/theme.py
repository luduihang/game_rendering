"""ui 主题：资源路径解析与布局。pygame.Rect 在这里（而不是 const 的类体里）创建。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import const


def asset_paths() -> dict[str, Path]:
    return {
        "background": Path(const.Background),
        "card_back": Path(const.Card_Back),
        "card_dir": Path(const.card_directory),
        "font_main": Path(const.FONT_MAIN),
        "font_ui": Path(const.FONT_UI),
    }


def missing_assets() -> list[str]:
    return [name for name, path in asset_paths().items() if not Path(path).exists()]


@dataclass
class Layout:
    width: int = const.GAME_WIDTH_SIZE
    height: int = const.GAME_HEIGHT_SIZE

    # 手牌位置（左上角坐标）
    own_hand_origin: tuple[int, int] = (320, 470)
    own_card_gap: int = 132
    opponent_hand_origin: tuple[int, int] = (400, 90)
    opponent_card_gap: int = 92

    pot_pos: tuple[int, int] = (500, 340)
    status_pos: tuple[int, int] = (500, 60)
    own_info_pos: tuple[int, int] = (60, 470)
    opponent_info_pos: tuple[int, int] = (60, 110)
    help_pos: tuple[int, int] = (500, 620)

    button_width: int = 150
    button_height: int = 52
    button_gap: int = 14
    button_y: int = 640
    button_labels: dict[int, str] = field(
        default_factory=lambda: {0: "押 10", 1: "押 20", 2: "押 50", 3: "押 100", 4: "弃牌", 5: "看牌"}
    )

    def button_rects(self, legal_actions) -> dict[int, "object"]:
        """按合法动作动态生成按钮矩形（只在运行时创建 pygame.Rect）。"""
        import pygame

        legal = list(legal_actions)
        if not legal:
            return {}
        total = len(legal) * self.button_width + (len(legal) - 1) * self.button_gap
        start_x = (self.width - total) // 2
        rects = {}
        for index, action in enumerate(legal):
            x = start_x + index * (self.button_width + self.button_gap)
            rects[action] = pygame.Rect(x, self.button_y, self.button_width, self.button_height)
        return rects

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
