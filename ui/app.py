"""事件驱动主循环：人类（玩家0）对战 DQN（玩家1）。

设计要点（对应契约 D7）：
- 主循环每帧无条件 ``pump_events()``，等待期间窗口持续重绘并响应 QUIT（D7-b）
- 没有任何 ``time.sleep``：AI 思考延迟由 ``Ticker.deadline()`` 表达（D7-a）
- 权重加载只发生在**构造时**（人类显式启动），不在 import 期（D7-d）
- 所有渲染数据来自 ``core.GameRoom.snapshot()``，UI 不自行记账
"""

from __future__ import annotations

import os
import pickle
import random
from pathlib import Path

import numpy as np

from agents.dqn import DQNAgent, StateEncoder
from core.dealing import deal_uniform, new_deck
from core.evaluator import evaluate
from core.rules import BET_OPTIONS, Action, GameRoom, IllegalAction
from core.strength import beats_probability
from ui.clock import Ticker, TickPolicy

REPO = Path(__file__).resolve().parents[1]
# 自博弈训练产出的部署策略（scripts/train.py SELFPLAY_V1，100 局 seed=7），
# 即 run/final/dqn_sp_ep100_seed7.pth 的副本（权重被 .gitignore 忽略，不进版本库）。
DEFAULT_CHECKPOINT = REPO / "dqn_model_1.pth"
CHECKPOINT_ENV_VAR = "DQN_CHECKPOINT"


def resolve_checkpoint(arg: str | Path | None = None, env: dict | None = None) -> Path:
    """解析 DQN 权重路径，优先级：CLI 参数 > 环境变量 DQN_CHECKPOINT > 默认值。

    - ``arg``：命令行 ``--checkpoint`` 传入的路径（可为绝对路径或相对路径）；
    - 环境变量 ``DQN_CHECKPOINT``：``arg`` 缺省/为空时生效；
    - 默认：仓库根目录下的 ``dqn_model_1.pth``。

    相对路径一律按仓库根目录（``REPO``）解析，与当前工作目录无关。
    """
    env = os.environ if env is None else env
    raw = arg if arg not in (None, "") else env.get(CHECKPOINT_ENV_VAR)
    if raw in (None, ""):
        return DEFAULT_CHECKPOINT
    path = Path(str(raw))
    return path if path.is_absolute() else REPO / path


def key_to_action_map() -> dict[int, Action]:
    """显式键码 → Action 映射表。

    不用「键码差值」（如 ``Action(key - pygame.K_1)``）：差值映射在小键盘 /
    非标准键盘布局下会错位。逐键显式对应，且覆盖全部 Action 成员（见
    ``core.rules.Action``）。pygame 延迟导入，保持模块 import 期无 pygame 依赖。
    """
    import pygame

    return {
        pygame.K_1: Action.BET_10,
        pygame.K_2: Action.BET_20,
        pygame.K_3: Action.BET_50,
        pygame.K_4: Action.BET_100,
        pygame.K_f: Action.FOLD,
        pygame.K_c: Action.COMPARE,
    }


def check_assets() -> list[str]:
    """启动资源自检：用 ``ui.theme.missing_assets()`` 精确列出缺失资源名。"""
    from ui.theme import missing_assets

    return missing_assets()


class Controller:
    """对局控制器：把「谁的回合 / 何时行动」表达为截止时间，而非阻塞等待。"""

    def __init__(
        self,
        seed: int | None = None,
        checkpoint: Path | str | None = None,
        human_player: int = 0,
        think_seconds: float = 0.6,
        settle_seconds: float = 0.4,
        auto_human: bool = False,
    ):
        self.seed = seed
        self.human_player = human_player
        self.ai_player = 1 - human_player
        self.think_seconds = think_seconds
        self.settle_seconds = settle_seconds
        self.auto_human = auto_human
        self.rng = random.Random(seed)
        self.encoder = StateEncoder()

        self.checkpoint = resolve_checkpoint(checkpoint)
        self.agent, self.trained = self._load_agent(self.checkpoint)
        self.policy_source = str(self.checkpoint) if self.trained else "untrained-random(epsilon=0.15)"
        self.room: GameRoom = None  # type: ignore[assignment]
        self.first_player = human_player
        self.ai_deadline: float | None = None
        self.human_deadline: float | None = None
        self.last_now: float = 0.0
        self.new_round()

    # ---------- 初始化 ----------
    def _load_agent(self, checkpoint: Path) -> tuple[DQNAgent, bool]:
        """加载训练权重；失败时回退为未训练随机策略，但必须给出醒目告警（不再静默）。"""
        try:
            agent = DQNAgent.from_checkpoint(checkpoint, seed=self.seed)
        except (FileNotFoundError, ValueError, RuntimeError, pickle.PickleError) as exc:
            print(f"[警告] 未能加载训练权重 {checkpoint}（{exc}）")
            print("[警告] 当前机器方为**未训练随机策略（epsilon=0.15）**，不是训练出的策略，走位纯随机！")
            print(f"[警告] 请将自博弈训练产出的权重放到默认位置 {DEFAULT_CHECKPOINT}，"
                  f"或用 --checkpoint / 环境变量 {CHECKPOINT_ENV_VAR} 指定权重路径。")
            return DQNAgent(input_dim=4, action_dim=6, seed=self.seed, epsilon=0.15), False
        print(f"[信息] 已加载训练权重 {checkpoint}（epsilon=0.0 贪心策略）")
        return agent, True

    def new_round(self, now: float | None = None) -> None:
        deck = new_deck(self.rng)
        hands = [deal_uniform(deck), deal_uniform(deck)]
        self.room = GameRoom.new(hands)
        self.room.whose_turn = self.first_player
        self.first_player = 1 - self.first_player
        self.ai_deadline = None
        self.human_deadline = None
        self._schedule(now)

    def _schedule(self, now: float | None) -> None:
        """根据当前回合方设置「该谁在什么时候行动」。"""
        if self.room.finish:
            self.ai_deadline = self.human_deadline = None
            return
        now = 0.0 if now is None else now
        if self.room.whose_turn == self.ai_player:
            self.ai_deadline = now + self.think_seconds
            self.human_deadline = None
        else:
            self.human_deadline = now + (self.settle_seconds if not self.auto_human else 0.0)
            self.ai_deadline = None

    # ---------- 每帧推进 ----------
    def update(self, now: float) -> None:
        guard = 0
        while not self.room.finish and guard < 64:
            guard += 1
            if self.room.whose_turn == self.ai_player and self.ai_deadline is not None:
                if now < self.ai_deadline:
                    return
                self._ai_move()
                now = self.ai_deadline or now
                self._schedule(now)
                if self.room.whose_turn == self.ai_player:
                    return
            elif self.room.whose_turn == self.human_player:
                if not (self.auto_human and self.human_deadline is not None and now >= self.human_deadline):
                    return
                self._auto_human_move()
                self._schedule(now)
            else:
                return

    def _ai_move(self) -> None:
        legal = self.room.legal_actions()
        if not legal:
            return
        state = self._observation(self.ai_player)
        action = self.agent.act(state, legal)
        self._apply(action)

    def _auto_human_move(self) -> None:
        legal = self.room.legal_actions()
        if not legal:
            return
        action = self.rng.choice(list(legal))
        self._apply(action)

    def _apply(self, action: int) -> bool:
        try:
            self.room.apply(action)
        except IllegalAction:
            return False
        return True

    # ---------- 人类输入 ----------
    def human_action(self, action: int) -> bool:
        if self.room.finish or self.room.whose_turn != self.human_player:
            return False
        if action not in self.room.legal_actions():
            return False
        ok = self._apply(action)
        if ok:
            self._schedule(self.last_now)
        return ok

    def set_now(self, now: float) -> None:
        self.last_now = now

    # ---------- 视图 ----------
    def _observation(self, player: int) -> np.ndarray:
        return self.encoder.encode(self.room.snapshot(), player, self.room.own_hand(player))

    def view(self) -> dict:
        snapshot = self.room.snapshot()
        own_hand = self.room.own_hand(self.human_player)
        return {
            "own_hand": own_hand,
            "opponent_hand": self.room.opponent_hand(self.human_player),
            "money": snapshot["money"],
            "bets": snapshot["bets"],
            "folded": snapshot["folded"],
            "all_bet": snapshot["all_bet"],
            "finish": snapshot["finish"],
            "winner": snapshot["winner"],
            "legal_actions": tuple(
                a for a in snapshot["legal_actions"] if snapshot["whose_turn"] == self.human_player
            ) or tuple(snapshot["legal_actions"]),
            "is_human_turn": (not snapshot["finish"]) and snapshot["whose_turn"] == self.human_player,
            "thinking": (not snapshot["finish"]) and snapshot["whose_turn"] == self.ai_player,
            "min_bet": BET_OPTIONS[snapshot["rest_option"]],
            "own_rank": evaluate(own_hand),
            "opponent_rank": evaluate(self.room.opponent_hand(self.human_player)) if snapshot["finish"] else None,
            "own_win_rate": beats_probability(own_hand),
        }


class App:
    """pygame 事件循环。``step_frame()`` 供测试逐帧驱动，``run()`` 供真实运行。"""

    def __init__(self, controller: Controller, renderer=None, ticker: Ticker | None = None):
        self.controller = controller
        self.ticker = ticker or Ticker(TickPolicy.REAL)
        self.renderer = renderer
        self.running = True
        self.frames = 0

    # ---------- 事件 ----------
    def pump_events(self) -> None:
        import pygame

        if not pygame.get_init():
            return  # 纯逻辑模式（无显示），不处理事件
        try:
            events = pygame.event.get()  # 非阻塞：一次取空队列
        except pygame.error:
            return
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._on_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_click(event.pos)

    def _on_key(self, key: int) -> None:
        import pygame

        key_map = key_to_action_map()
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key == pygame.K_r:
            self.controller.new_round(self.ticker.now())
        elif self.controller.room.finish:
            return
        elif key in key_map:
            self.controller.human_action(int(key_map[key]))

    def _on_click(self, pos) -> None:
        if self.controller.room.finish:
            return
        view = self.controller.view()
        rects = self.renderer.layout.button_rects(view["legal_actions"]) if self.renderer else {}
        for action, rect in rects.items():
            if rect.collidepoint(pos):
                self.controller.human_action(action)
                return

    # ---------- 帧 ----------
    def step_frame(self) -> None:
        self.ticker.begin_frame()
        now = self.ticker.now()
        self.controller.set_now(now)
        self.pump_events()
        if not self.running:
            return
        self.controller.update(now)
        if self.renderer is not None:
            import pygame

            surface = pygame.display.get_surface()
            if surface is not None:
                self.renderer.draw(surface, self.controller.view())
                pygame.display.flip()
        self.ticker.end_frame()
        self.frames += 1

    def run(self, max_frames: int | None = None) -> None:
        while self.running:
            self.step_frame()
            if max_frames is not None and self.frames >= max_frames:
                break

    def close(self) -> None:
        self.running = False


def main(argv=None) -> int:
    import argparse

    import pygame

    import const
    from ui.render import Renderer

    parser = argparse.ArgumentParser(description="炸金花：人类 vs DQN")
    parser.add_argument(
        "--checkpoint",
        default=None,
        help=(
            f"DQN 权重 .pth 路径（绝对路径或相对仓库根目录）；缺省时依次读环境变量 "
            f"{CHECKPOINT_ENV_VAR}，再缺省用 {DEFAULT_CHECKPOINT.name}"
        ),
    )
    args = parser.parse_args(argv)

    pygame.init()
    pygame.display.set_caption("炸金花 · 人类 vs DQN")
    pygame.display.set_mode((const.GAME_WIDTH_SIZE, const.GAME_HEIGHT_SIZE))

    controller = Controller(seed=None, checkpoint=args.checkpoint)
    renderer = Renderer()
    missing = check_assets()
    if missing:
        print(f"[提示] 缺失资源: {', '.join(missing)}（将使用占位绘制）")

    app = App(controller, renderer=renderer, ticker=Ticker(TickPolicy.REAL))
    try:
        app.run()
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
