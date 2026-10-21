"""UI 层测试：时序契约（无 sleep / 响应 QUIT / 零等待跑完）、UI↔core 一致性、性能。"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import time
from pathlib import Path

import pytest

from core.rules import Action, GameRoom, IllegalAction
from ui.app import App, Controller
from ui.clock import Ticker, TickPolicy

REPO = Path(__file__).resolve().parent.parent
ENTRY = REPO / "draw_me_vs_DQN_Plus.py"


@pytest.fixture(scope="session", autouse=True)
def _pygame_display():
    """整个模块共用 dummy 显示，避免每个用例重复初始化。"""
    import pygame

    pygame.init()
    pygame.display.set_mode((640, 480))
    yield
    pygame.quit()


def make_app(seed=1, policy=TickPolicy.IMMEDIATE, renderer=None, auto_human=True):
    controller = Controller(seed=seed, auto_human=auto_human, think_seconds=0.0, settle_seconds=0.0)
    controller.new_round(now=0.0)
    app = App(controller, renderer=renderer, ticker=Ticker(policy))
    return app


class TestTicker:
    def test_immediate_does_not_wait(self):
        ticker = Ticker(TickPolicy.IMMEDIATE)
        ticker.begin_frame()
        start = time.perf_counter()
        ticker.end_frame()
        assert time.perf_counter() - start < 0.05

    def test_fixed_advances_virtual_time(self):
        ticker = Ticker(TickPolicy.FIXED, fixed_dt=0.1)
        first = ticker.now()
        ticker.begin_frame()
        ticker.end_frame()
        second = ticker.now()
        assert second - first >= 0.1 - 1e-9

    def test_deadline_and_due(self):
        ticker = Ticker(TickPolicy.IMMEDIATE)
        deadline = ticker.deadline(0.5)
        assert ticker.due(deadline) is False
        ticker.begin_frame()
        ticker.begin_frame()
        assert ticker.due(deadline) is True

    def test_no_sleep_in_source(self):
        for path in (REPO / "ui").glob("*.py"):
            assert "time.sleep(" not in path.read_text(encoding="utf-8"), f"{path.name} 含 time.sleep"


class TestEventLoop:
    def test_quit_is_handled_during_wait(self):
        """D7-b：等待期间收到 SDL_QUIT 必须立即退出，而不是卡死。"""
        import pygame

        app = make_app()
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        app.step_frame()
        assert app.running is False
        pygame.event.clear()

    def test_quit_handled_while_thinking(self):
        """AI 思考等待期间也必须能退出（旧实现会在这里卡住）。"""
        import pygame

        controller = Controller(seed=4, auto_human=False, think_seconds=5.0)
        controller.new_round(now=0.0)
        controller.room.whose_turn = controller.ai_player
        app = App(controller, renderer=None, ticker=Ticker(TickPolicy.REAL))
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        app.step_frame()
        assert app.running is False
        pygame.event.clear()

    def test_frames_keep_advancing_without_input(self):
        """无人输入时窗口仍持续重绘（帧数递增，不阻塞）。"""
        app = make_app(auto_human=False)
        app.controller.room.whose_turn = app.controller.human_player
        for _ in range(10):
            app.step_frame()
        assert app.frames == 10

    def test_full_game_completes_with_zero_wait(self):
        app = make_app(seed=7)
        for _ in range(400):
            app.step_frame()
            if app.controller.room.finish:
                break
        assert app.controller.room.finish

    def test_restart_starts_new_round(self):
        import pygame

        app = make_app(seed=8, auto_human=False)  # 不让新一局自动打完
        app.controller.room.apply(Action.FOLD)
        assert app.controller.room.finish
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        app.step_frame()
        assert not app.controller.room.finish, "按 R 后应开始新一局"
        pygame.event.clear()


class TestUICoreConsistency:
    def test_view_matches_core_snapshot(self):
        """UI 不自行记账：渲染所用的值必须与 core.snapshot() 逐字段相等。"""
        app = make_app(seed=11, auto_human=False)
        for _ in range(3):
            view = app.controller.view()
            snapshot = app.controller.room.snapshot()
            assert view["money"] == snapshot["money"]
            assert view["bets"] == snapshot["bets"]
            assert view["all_bet"] == snapshot["all_bet"]
            assert view["finish"] == snapshot["finish"]
            assert view["winner"] == snapshot["winner"]
            app.controller.room.apply(app.controller.room.legal_actions()[0])

    def test_min_bet_comes_from_core(self):
        app = make_app(seed=12, auto_human=False)
        app.controller.room.apply(Action.BET_100)
        assert app.controller.view()["min_bet"] == 100

    def test_legal_actions_gated_to_human_turn(self):
        app = make_app(seed=13, auto_human=False)
        app.controller.room.whose_turn = app.controller.ai_player
        app.controller.room.apply(Action.BET_10)  # 交给人类
        view = app.controller.view()
        assert view["is_human_turn"] is True
        assert view["legal_actions"]


class TestPerformance:
    def test_core_step_under_5ms(self):
        room = GameRoom.new([
            [{"suit": "黑桃", "value": 14}, {"suit": "红心", "value": 14}, {"suit": "方块", "value": 14}],
            [{"suit": "黑桃", "value": 2}, {"suit": "红心", "value": 3}, {"suit": "方块", "value": 5}],
        ])
        start = time.perf_counter()
        steps = 0
        try:
            room.apply(Action.BET_10)
            steps += 1
        except IllegalAction:
            pass
        elapsed = (time.perf_counter() - start) / max(steps, 1)
        assert elapsed < 0.005, f"core step {elapsed * 1000:.2f}ms 超过 5ms（基线 1530.8ms 含 sleep）"

    def test_routing_and_controller_cost_is_small(self):
        start = time.perf_counter()
        app = make_app(seed=21)
        for _ in range(50):
            app.step_frame()
        per_frame = (time.perf_counter() - start) / 50
        assert per_frame < 0.05, f"单帧 {per_frame * 1000:.1f}ms 超过 50ms"


class TestEntryAndAssets:
    def test_entry_is_thin(self):
        """入口不得含星号导入、sleep 或 import 期副作用。"""
        text = ENTRY.read_text(encoding="utf-8")
        assert "import *" not in text
        assert "time.sleep" not in text
        assert "load_state_dict" not in text
        assert "pygame.init()" not in text.split("if __name__")[0]

    def test_const_importable_without_pygame(self):
        import const

        assert Path(const.Background).is_absolute()
        assert "myclient" not in str(const.bgm_directory)

    def test_renderer_draws_under_dummy_driver(self):
        import pygame

        from ui.render import Renderer

        pygame.init()
        surface = pygame.display.set_mode((640, 480))
        renderer = Renderer()
        app = make_app(seed=31, renderer=renderer)
        app.step_frame()
        renderer.draw(surface, app.controller.view())
        pygame.display.flip()

    def test_missing_assets_are_reported(self):
        from ui.theme import asset_paths, missing_assets

        assert set(asset_paths()) >= {"background", "card_back", "card_dir", "font_main", "font_ui"}
        assert isinstance(missing_assets(), list)
