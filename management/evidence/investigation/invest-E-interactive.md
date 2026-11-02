# 调研 E 报告：交互侧 —— 机器对手接线与替换点

## 调查目标
只读调查 game_rendering 交互侧（ui/app.py、ui/render.py、ui/theme.py、draw_me_vs_DQN_Plus.py、const.py、algorithm.py），给出机器对手接线、状态编码一致性、checkpoint 替换点、theme 资源自检、4 个已知小问题、RepeatedTimer 与 const.py 的 file:line 证据。

## 涉及文件（含行数）
| 文件 | 行数 | 角色 |
|---|---|---|
| ui/app.py | 282 | 控制器+事件循环+入口 main |
| ui/render.py | 254 | 薄渲染层 |
| ui/theme.py | 164 | 资源路径映射+Layout |
| draw_me_vs_DQN_Plus.py | 14 | 唯一启动入口 |
| const.py | 82 | 路径/颜色/尺寸常量 |
| algorithm.py | 120 | RepeatedTimer+文字绘制 |
| 交叉引用（仅取证，不深入） | — | agents/dqn.py:225 行、scripts/env.py:160 行、core/rules.py:31-37、agents/robot.py:81 |

Git 状态：本角色无 shell 工具，无法执行 `git status`（见 UNKNOWN）；.git/HEAD 显示当前分支 `main`。本会话零写入，未引入任何工作区改动。

## 关键代码位置（file:line + 该处做什么）
- draw_me_vs_DQN_Plus.py:11 `from ui.app import main`；:13-14 `if __name__ == "__main__": raise SystemExit(main())`
- ui/app.py:17-22 import 块（仅 agents.dqn 的 DQNAgent/StateEncoder、core、ui.clock，无 pygame 顶层 import、无 agents.robot）
- ui/app.py:24-25 `REPO`/`DEFAULT_CHECKPOINT = REPO / "dqn_model_1.pth"`
- ui/app.py:31-54 `Controller.__init__`（:34 checkpoint 参数、:45 rng、:47 encoder、:49 `self.agent = self._load_agent(checkpoint)`、:54 new_round）
- ui/app.py:57-62 `_load_agent`（from_checkpoint + 回退）
- ui/app.py:64-72 `new_round`（发牌、GameRoom.new、轮换先手）
- ui/app.py:74-86 `_schedule`（AI 回合设 ai_deadline=now+think_seconds，:81）
- ui/app.py:88-106 `update`（帧推进，:92-95 到点调 `_ai_move`）
- ui/app.py:108-114 `_ai_move`；:116-121 `_auto_human_move`；:123-128 `_apply`（room.apply + IllegalAction 捕获）
- ui/app.py:131-139 `human_action`（:138 用 `self.last_now` 重新调度）
- ui/app.py:141 类级 `last_now: float = 0.0`；:143-144 `set_now`
- ui/app.py:147-148 `_observation`；:150-171 `view`
- ui/app.py:185-200 `pump_events`；:202-216 `_on_key`；:218-226 `_on_click`；:229-245 `step_frame`（:231-232 set_now）；:247-252 `run`
- ui/app.py:257-278 `main`（:258 import pygame、:260 import const、:261 `from ui.render import Renderer`、:263-265 init/set_caption/set_mode、:267 `Controller(seed=None)`、:268 `Renderer()`、:269-271 资源自检、:273 App、:274-277 run/quit、:278 return 0）
- ui/render.py:21-45 `Renderer.__init__`；:47-57 背景/缩放加载（缺失回 None）；:101-120 `draw`；:159-180 `_draw_opponent`；:182-199 `_draw_own`；:222-240 `_draw_buttons`；:242-253 `_draw_result`
- ui/theme.py:20-27 BUTTON_IMAGES；:44-55 asset_paths；:57-62 button_image_path；:64-71 avatar_image_path；:73-75 coin_image_path；:77-90 `missing_assets`；:93-164 `Layout`（button_rects :138-154、opponent_card_rects :160-164，pygame.Rect 全部运行时创建）
- const.py:15-16 ROOT/SRC；:19-27 资源目录；:30-31 Background/Card_Back；:33-34 字体；:38-44 窗口/卡尺寸；:47-48 牌型/选项；:51-65 Color；:67-78 BG_MUSIC；:81-82 asset_exists
- algorithm.py:20-86 RepeatedTimer（见下）；:89-98 show_font；:100-112 RULES_LINES；:114-120 show_help_font

## 交互入口与机器对手接线
**入口**：draw_me_vs_DQN_Plus.py 全文仅 14 行：:11 import main，:13-14 调 `main()`，不传 argv、无游戏逻辑。ui/app.py:257-278 main() 初始化 pygame 显示（:265 用 const.GAME_WIDTH_SIZE/H=1000x750，const.py:38-39），:267 构造 Controller（不传 checkpoint → 走默认），:268 构造 Renderer，:273-275 跑 App 事件循环。

**默认 checkpoint 与加载**：
- 默认值：app.py:25 `DEFAULT_CHECKPOINT = REPO / "dqn_model_1.pth"`（REPO=仓库根，app.py:24）；Controller 参数默认 app.py:34。
- 加载点：app.py:49（__init__ 内）→ app.py:57-62 `_load_agent` → agents/dqn.py:124-146 `from_checkpoint`（:131-132 不存在抛 FileNotFoundError；:136 `checkpoint_dims` 从 fc1/fc3 权重推断维度，dqn.py:62-68；:140 epsilon 用默认 0.0）。

**加载失败回退**：app.py:58-62 捕获 `(FileNotFoundError, ValueError, RuntimeError)`，仅 print 提示后返回 `DQNAgent(input_dim=4, action_dim=6, seed=self.seed, epsilon=0.15)`（app.py:62）——未训练随机权重、15% 随机动作的"伪 DQN"。

**机器推理**：`_ai_move`（app.py:108-114）：legal=room.legal_actions() → state=`_observation(self.ai_player)`（app.py:147-148，即 StateEncoder.encode(room.snapshot(), 1, room.own_hand(1))）→ `self.agent.act(state, legal)`（dqn.py:153-164：epsilon 命中随机选 legal，否则 Q 值在 legal 上 mask argmax）→ `_apply`（app.py:123-128 → room.apply(int)）。触发时机：_schedule 设 ai_deadline=now+0.6s（app.py:81、40 think_seconds=0.6），update() 到点执行（app.py:92-95）。**epsilon**：训练权重路径恒 0.0（dqn.py:129 from_checkpoint 默认，app.py 未覆盖）；回退路径 0.15（app.py:62）。

**动作映射**：agent 输出 int（dqn.py:164 `int(np.argmax(masked))`）→ app.py:113-114 → `_apply` → `self.room.apply(action)`（app.py:125，core GameRoom 接受 int；合法集见 core/rules.py:102，Action 值 BET_10..COMPARE=0..5，rules.py:31-37）。人类按键侧：app.py:211-212 `int(Action(key - pygame.K_1))` 映射 1-4 键到 BET_10..BET_100，:213-214 F、:215-216 C 映射 FOLD/COMPARE。

## 状态编码一致性核对
**结论：一致**（同一类、同一调用约定、同维度）。
- UI 侧：app.py:19（import StateEncoder）、app.py:47（实例化）、app.py:147-148 `encode(self.room.snapshot(), player, self.room.own_hand(player))`，player=ai_player（app.py:112）。
- 训练侧：scripts/env.py:14（import StateEncoder）、env.py:39（实例化）、env.py:97-100 `_observation` → `self.encoder.encode(snapshot, self.agent_player, room.own_hand(self.agent_player))`。
- 编码实现唯一来源 agents/dqn.py:70-94 `StateEncoder.encode`（:83-94）：`[circle/10, bets[视角方]/1000, bets[对方]/1000, beats_probability(本方手牌)]`，4 维 float32；维度常量 dqn.py:29-32（BOARD_FEATURES=3、CARD_FEATURES=1、DEFAULT_STATE_DIM=4、DEFAULT_ACTION_DIM=6）。手牌强度用 core.strength.beats_probability（dqn.py:78-81 默认注入，app.py:21 同函数）。
- 差异核对：env.py:120-123 `_opponent_snapshot` 向 snapshot 注入 `hand` 键，但 StateEncoder.encode 只读显式 hand 参数与 circle/bets 字段，不读 `snapshot["hand"]` → 对编码无影响。两侧唯一差别是视角参数（UI=1，env 默认=0），编码对视角对称，语义一致。
- 前提确认：自博弈权重只要仍为 4 维输入/6 维输出（from_checkpoint 自动读维度，dqn.py:136），即可直接接入交互界面。

## 换 checkpoint 的改动点清单
把机器换成自博弈权重，ui/ 侧需改（最小集）：
1. **ui/app.py:267** `Controller(seed=None)` → 传入目标 checkpoint（Controller 已支持参数，app.py:34，无需改签名）。
2. **ui/app.py:257-258 + 267** `main(argv=None)` 当前忽略 argv、无 argparse → 新增 `--checkpoint` 解析（argparse），这是新增参数逻辑。
3. **draw_me_vs_DQN_Plus.py:14** `main()` 未传 argv → 改 `main(sys.argv[1:])`（需加 `import sys`），否则命令行参数到不了 main（替代方案：环境变量 `DQN_CHECKPOINT`，改 app.py:24-25 处读取）。
4. **启动校验**：在 main() 中（app.py:267 之前）加 `if not Path(checkpoint).exists(): print/return 1`；现状 from_checkpoint 的 FileNotFoundError 被 app.py:58-62 静默吞掉回退随机策略，"校验存在"必须显式做，或把 _load_agent 回退改为仅告警+可配置 fail-fast。
5. 可选：**ui/app.py:25** DEFAULT_CHECKPOINT 改指自博弈权重路径（或保留为回退默认）。
6. 无需改动：ui/render.py、ui/theme.py（纯渲染，不接触策略）；app.py:59-62 回退逻辑可保留；agents/dqn.py:124-146 维度自适应，无需改。若自博弈权重维度≠4/6，则需同步改 StateEncoder（dqn.py:70-94）与 env.py，超出 ui/ 范围。

## ui/theme.py 资源自检
- `missing_assets()`：theme.py:77-90，返回缺失资源名列表，覆盖 background、card_back、card_dir、font_main、font_ui、coin（:79-86）+ 6 个按钮 `button_0..5`（:87）+ 2 个头像 `avatar_human/ai`（:88），比现有自检全面得多。
- app.py 未用它的原因：UNKNOWN（无注释/历史说明可证）。客观情况：app.py:269 自行内联实现 `missing = [name for name in ("background","card_dir") if not Path(const.ROOT/"src").exists()]`——只检查 src 目录是否存在，名字与实际检查对象不符；theme 在 app.py 中仅经 ui.render 间接可用（render.py:16 `from ui.theme import ...`，app.py:261 才 import Renderer）。
- 改法（最小）：app.py:269 前加 `from ui.theme import missing_assets`，:269 替换为 `missing = missing_assets()`；:270-271 提示文案可保留。约 2 行改动。

## 4 个已知小问题的准确行号与最小改法
1. **键码差值映射** app.py:211-212：`key in (K_1..K_4)` 后 `Action(key - pygame.K_1)`，依赖 pygame 中 K_1..K_4 键码连续（当前 pygame 中 K_0..K_9=48..57 连续，故可用，但属隐式假设）。最小改法：建显式表 `{pygame.K_1: Action.BET_10, pygame.K_2: Action.BET_20, pygame.K_3: Action.BET_50, pygame.K_4: Action.BET_100}`，:211 改 `elif key in _KEY_MAP:`，:212 改 `int(_KEY_MAP[key])`。
2. **_on_click renderer=None** app.py:218-226：:222 `rects = ... if self.renderer else {}` → 无渲染器（headless 逻辑模式）时点击静默无效。最小改法：_on_click 开头（:219 附近）加 `if self.renderer is None: return`，语义显式化（行为不变，低风险）。
3. **last_now 类级属性** app.py:141 `last_now: float = 0.0`（类属性）vs :143-144 `set_now` 写实例属性，使用点 :138。风格不统一且新实例依赖 set_now 先于 human_action 调用（step_frame :232 保证）。最小改法：删 :141，在 `Controller.__init__`（如 :47 后）加 `self.last_now = 0.0`。
4. **view 恒含对手真手牌** app.py:155 `"opponent_hand": self.room.opponent_hand(self.human_player)` 无条件包含。抑制在渲染层：render.py:159-166 `_draw_opponent` 未 finish 时只画卡背 card_back（缺失则占位矩形，:165-166），绝不画真牌；render.py:167-170 仅 finish 时画真牌；render.py:178-180 仅 `if view["opponent_rank"]` 才显示对手牌型，而 app.py:169 已保证非 finish 时 opponent_rank=None（第二道闸）。残余风险：view 数据本身仍携带真牌，未来任何新渲染消费方可能泄漏；可改为 finish 前不放入该键（改 app.py:155 为条件值），但会动 view 契约（测试依赖，见 tests/test_ui.py）。

## RepeatedTimer 现状与调用点
- 现状：algorithm.py:20-86，D7-c 加固版已就位——锁 algorithm.py:34；stop 幂等 :71-78（未 start 时 `_timer is None` 安全，:75-78 不抛异常）；daemon :59（`self._timer.daemon = True`）；异常隔离 :51-54（回调异常记入 `last_error`，:43 初始化，不掐断调度链）；支持 with 语法 :80-86。
- 调用点（grep 全仓）：**生产代码零调用**。UI 已改用 ui.clock.Ticker 帧驱动（app.py:24 import、:186 默认 `Ticker(TickPolicy.REAL)`）。仅 tests/baseline/repro_d7_timing.py:78、:91 实例化（D7-c 基线复现脚本）。其余命中均为 docs/、management/ 历史文档（如 docs/ARCHITECTURE.md:84、management/evidence/report-A-domain-core.md:81-83）。

## const.py 与资源路径
- 持有：ROOT/SRC（const.py:15-16）、6 个资源目录（:19-24，全 `SRC / 子目录` 相对包根，无 `'../'` 坏路径）、兼容别名 background_directory（:27）、Background/Card_Back（:30-31）、字体（:33-34）、窗口 1000x750（:38-41）、卡尺寸（:43-44）、牌型/选项数组（:47-48）、Color 调色板（:51-65）、BG_MUSIC 清单（:67-78）、asset_exists（:81-82）。
- 路径解析：`Path(__file__).resolve().parent`（const.py:15）即仓库根，`SRC = ROOT / "src"`（:16），全部资源相对 src/ 解析（theme.py:44-55 asset_paths 直接引用 const 符号）。
- pygame 依赖：**无**。const.py 仅 import `pathlib.Path`（const.py:12）；模块 docstring const.py:7-9 明确"不再 import pygame、不在类体定义期调 pygame.Rect"；pygame.Rect 移至 ui/theme.py 运行时创建（theme.py:142-164 各方法内 `import pygame`）。

## 发现的问题
1. **仓库根不存在 dqn_model_1.pth**（ls 根目录核实；.gitignore:14 将 `*.pth` 排除版本库）→ 当前交互界面必然走 app.py:58-62 回退，"机器"实际是未训练网络+epsilon=0.15 的准随机策略，且只 print 提示、用户不易察觉（app.py:61）。
2. **checkpoint 无任何外部可配置通道**：main 不解析 argv（app.py:257），入口不传 argv（draw_me_vs_DQN_Plus.py:14），DEFAULT_CHECKPOINT 硬编码（app.py:25）。
3. **回退静默降级**：ValueError（权重维度/格式不符，如自博弈权重非 4/6 维）同样被 app.py:58 捕获并静默回退，训练产物维度漂移不会在交互侧报错。
4. **app.py:269 自检名不副实**：名为 background/card_dir 检查，实际只查 `src` 目录存在，且未用 theme.missing_assets（theme.py:77-90）。
5. view 契约携带对手真手牌（app.py:155），信息完整性依赖渲染层两道闸（render.py:159-170、178-180 + app.py:169）。
6. 三个风格/健壮性问题：app.py:212 键码差值、:141 类级 last_now、:222 renderer=None 空 rects（见上节）。
7. 机器对手标签写死"对手（DQN）"（render.py:174），换策略后文案会失真（小问题）。

## UNKNOWN 清单
- **git status 精确结果**：本角色无 shell 工具，未执行 `git status`；已知分支为 main（.git/HEAD），本会话零写入。工作区是否含他人未提交改动 UNKNOWN。
- **app.py 未用 missing_assets 的原始原因**：无代码注释或本仓文档直接说明，UNKNOWN（仅能从代码现状推断为内联简化实现）。
- **根目录 .pth 完整清单**：find 受 .gitignore 影响不可见 gitignored 文件；仅确认仓库根无 dqn_model_1.pth。全盘 .pth 清点属其他子任务范围，本任务不展开。
- **core.GameRoom.apply 对 int 的完整处理细节**：core/ 不在本任务范围，仅取证 rules.py:31-37、:102 用于键映射核对。