"""薄渲染层：只把 core 的状态画出来，不持有任何游戏规则或记账。

贴图策略：优先使用仓库内原始素材
- 动作按钮  ← src/button/{十注,二十注,五十注,一百注,弃牌,看牌}.png
- 玩家头像  ← src/character/{火花, 雪影娃娃第三阶段}.png
- 金币图标  ← src/item_pic/金币.png
任一贴图缺失时回退为文本/占位绘制，保证不崩溃。
"""

from __future__ import annotations

from pathlib import Path

import pygame

import const
from ui.theme import Layout, asset_paths, avatar_image_path, button_image_path, coin_image_path


class Renderer:
    def __init__(self, layout: Layout | None = None, avatars: dict[str, str] | None = None):
        self.layout = layout or Layout()
        self.avatars = avatars or {}
        pygame.font.init()
        self.paths = asset_paths()
        self._card_cache: dict[str, pygame.Surface] = {}
        self._button_cache: dict[int, pygame.Surface | None] = {}
        self._avatar_cache: dict[str, pygame.Surface | None] = {}

        self.font_title = self._font(self.paths["font_main"], 34)
        self.font_body = self._font(self.paths["font_ui"], 22)
        self.font_small = self._font(self.paths["font_ui"], 18)
        self.font_button = self._font(self.paths["font_main"], 24)

        self.background = self._load_background()
        self.card_back = self._load_scaled(self.paths["card_back"], const.CARD_SIZE_SMALL)
        self.coin = self._load_scaled(coin_image_path(), (self.layout.coin_size, self.layout.coin_size))

    # ---------- 资源 ----------
    @staticmethod
    def _font(path, size):
        try:
            return pygame.font.Font(str(path), size)
        except (FileNotFoundError, OSError):
            return pygame.font.SysFont("sans", size)

    def _load_background(self) -> pygame.Surface | None:
        path = self.paths["background"]
        if not Path(path).exists():
            return None
        try:
            image = pygame.image.load(str(path)).convert()
            return pygame.transform.smoothscale(image, (self.layout.width, self.layout.height))
        except pygame.error:
            return None

    @staticmethod
    def _load_scaled(path, size) -> pygame.Surface | None:
        if path is None or not Path(path).exists():
            return None
        try:
            return pygame.transform.smoothscale(pygame.image.load(str(path)).convert_alpha(), size)
        except pygame.error:
            return None

    def card_surface(self, card, size) -> pygame.Surface:
        key = f"{card.suit.cn}{card.rank}@{size}"
        if key not in self._card_cache:
            path = self.paths["card_dir"] / f"{card.suit.cn}{card.rank}.png"
            surface = self._load_scaled(path, size)
            if surface is None:
                surface = self._placeholder_card(card, size)
            self._card_cache[key] = surface
        return self._card_cache[key]

    def button_surface(self, action: int) -> pygame.Surface | None:
        action = int(action)
        if action not in self._button_cache:
            self._button_cache[action] = self._load_scaled(
                button_image_path(action), (self.layout.button_width, self.layout.button_height)
            )
        return self._button_cache[action]

    def avatar_surface(self, who: str) -> pygame.Surface | None:
        if who not in self._avatar_cache:
            size = self.layout.avatar_rect(who).size
            self._avatar_cache[who] = self._load_scaled(
                avatar_image_path(who, self.avatars.get(who)), size
            )
        return self._avatar_cache[who]

    def _placeholder_card(self, card, size) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((250, 250, 250))
        pygame.draw.rect(surface, (30, 30, 30), surface.get_rect(), 2)
        text = self.font_small.render(f"{card.suit.cn}{card.rank}", True, (20, 20, 20))
        surface.blit(text, (8, size[1] // 2 - 10))
        return surface

    # ---------- 绘制 ----------
    def draw(self, surface: pygame.Surface, view: dict) -> None:
        """view 必须完全来自 core.snapshot()（外加手牌与结算信息）。"""
        if self.background is not None:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill(const.Color.dark)

        self._draw_panel(surface, pygame.Rect(0, 0, self.layout.width, self.layout.height),
                         const.Color.black, alpha=90)
        self._draw_opponent(surface, view)
        self._draw_own(surface, view)
        self._draw_pot(surface, view)
        self._draw_status(surface, view)
        if view["finish"]:
            self._draw_result(surface, view)
        else:
            self._draw_buttons(surface, view)

    def _draw_panel(self, surface, rect, color, alpha=180):
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((*color, alpha))
        surface.blit(panel, rect.topleft)

    def _text(self, surface, text, pos, font, color=const.Color.white, center=True):
        rendered = font.render(str(text), True, color)
        rect = rendered.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        surface.blit(rendered, rect)
        return rect

    def _text_with_coin(self, surface, label, value, pos, font, color=const.Color.white):
        """「标签 + 金币图标 + 数值」一行绘制（使用原始金币贴图）。"""
        x, y = pos
        rect = self._text(surface, label, (x, y), font, color, center=False)
        x = rect.right + 8
        if self.coin is not None:
            cy = rect.centery - self.layout.coin_size // 2
            surface.blit(self.coin, (x, cy))
            x += self.layout.coin_size + 4
        else:
            x = self._text(surface, "¥", (x, y), font, const.Color.golden, center=False).right + 4
        self._text(surface, value, (x, y), font, const.Color.golden, center=False)
        return y + rect.height + 6

    def _draw_avatar(self, surface, who: str) -> None:
        rect = self.layout.avatar_rect(who)
        avatar = self.avatar_surface(who)
        if avatar is not None:
            surface.blit(avatar, rect)
            pygame.draw.rect(surface, const.Color.panel_light, rect, 2, border_radius=6)
        else:
            pygame.draw.rect(surface, const.Color.panel_light, rect, border_radius=6)
            pygame.draw.rect(surface, const.Color.dim, rect, 2, border_radius=6)
            self._text(surface, "头像", rect.center, self.font_small, const.Color.dim)

    def _draw_opponent(self, surface, view) -> None:
        for rect in self.layout.opponent_card_rects(len(view["opponent_hand"])):
            if view["finish"]:
                continue  # 结算时下方统一露出真牌
            if self.card_back is not None:
                surface.blit(self.card_back, rect)
            else:
                pygame.draw.rect(surface, const.Color.panel_light, rect, border_radius=6)
        if view["finish"]:
            for card, rect in zip(view["opponent_hand"],
                                  self.layout.opponent_card_rects(len(view["opponent_hand"]))):
                surface.blit(self.card_surface(card, const.CARD_SIZE_SMALL), rect)

        self._draw_avatar(surface, "ai")
        x, y = self.layout.opponent_info_pos
        label = "对手（DQN）" + ("  已弃牌" if view["folded"][1] else "")
        self._text(surface, label, (x, y), self.font_small, center=False)
        y = self._text_with_coin(surface, "金币", view["money"][1], (x, y + 26), self.font_small)
        self._text_with_coin(surface, "押注", view["bets"][1], (x, y), self.font_small)
        if view["opponent_rank"]:
            self._text(surface, f"牌型 {view['opponent_rank'].type_name}",
                       (x, y + 30), self.font_small, const.Color.golden, center=False)

    def _draw_own(self, surface, view) -> None:
        for card, rect in zip(view["own_hand"], self.layout.own_card_rects(len(view["own_hand"]))):
            surface.blit(self.card_surface(card, const.CARD_SIZE), rect)

        self._draw_avatar(surface, "human")
        x, y = self.layout.own_info_pos
        label = "你" + ("  已弃牌" if view["folded"][0] else "")
        self._text(surface, label, (x, y), self.font_small, center=False)
        y = self._text_with_coin(surface, "金币", view["money"][0], (x, y + 26), self.font_small)
        y = self._text_with_coin(surface, "押注", view["bets"][0], (x, y), self.font_small)
        if view["own_rank"]:
            # 窄栏：牌型与胜率合并为一行，避免侵入手牌区
            self._text(surface, f"{view['own_rank'].type_name} · {view['own_win_rate']:.0%}",
                       (x, y + 4), self.font_small, const.Color.golden, center=False)

    def _draw_pot(self, surface, view) -> None:
        pygame.draw.circle(surface, const.Color.panel_light, self.layout.pot_pos, 64)
        pygame.draw.circle(surface, const.Color.golden, self.layout.pot_pos, 64, 2)
        self._text(surface, "底池", (self.layout.pot_pos[0], self.layout.pot_pos[1] - 18),
                   self.font_small, const.Color.dim)
        self._text(surface, view["all_bet"], self.layout.pot_pos, self.font_title, const.Color.golden)

    def _draw_status(self, surface, view) -> None:
        if view["finish"]:
            return
        if view["is_human_turn"]:
            text = f"轮到你行动 · 最低可押 {view['min_bet']}"
            color = const.Color.green
        elif view["thinking"]:
            text = "对手思考中…"
            color = const.Color.gray
        else:
            text = "对手回合"
            color = const.Color.gray
        rendered = self.font_body.render(text, True, color)
        panel = pygame.Rect(0, 0, rendered.get_width() + 32, rendered.get_height() + 14)
        panel.center = self.layout.status_pos
        self._draw_panel(surface, panel, const.Color.panel, alpha=150)
        surface.blit(rendered, rendered.get_rect(center=self.layout.status_pos))

    def _draw_buttons(self, surface, view) -> None:
        rects = self.layout.button_rects(view["legal_actions"])
        for action, rect in rects.items():
            enabled = view["is_human_turn"]
            image = self.button_surface(action)
            if image is not None:
                if not enabled:
                    image.set_alpha(120)
                surface.blit(image, rect)
                image.set_alpha(255)
            else:
                # 缺图回退：纯文本按钮
                base = const.Color.panel_light if enabled else const.Color.panel
                pygame.draw.rect(surface, base, rect, border_radius=8)
                label = self.layout.button_labels.get(action, str(action))
                self._text(surface, label, rect.center, self.font_button,
                           const.Color.white if enabled else const.Color.dim)
            if enabled:
                pygame.draw.rect(surface, const.Color.golden, rect, 2, border_radius=8)

    def _draw_result(self, surface, view) -> None:
        won = view["winner"] == 0
        banner = pygame.Rect(0, 0, 520, 120)
        banner.center = (self.layout.width // 2, self.layout.height // 2 - 20)
        self._draw_panel(surface, banner, const.Color.panel, alpha=230)
        pygame.draw.rect(surface, const.Color.golden, banner, 2, border_radius=10)
        text = "你赢了！" if won else "对手获胜"
        self._text(surface, text, (banner.centerx, banner.centery - 16),
                   self.font_title, const.Color.golden if won else const.Color.red)
        self._text(surface, "按 R 再来一局 · Esc 退出",
                   (banner.centerx, banner.centery + 32), self.font_small, const.Color.dim)
