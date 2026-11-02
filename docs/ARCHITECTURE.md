# game_rendering 架构知识库

> 生成时 commit：`a6adf487be9f3bb29bbac496120f23462b45bfd4`（本 worktree `git rev-parse HEAD`）。
> 本文档全部事实性结论取自 `management/evidence/` 下 5 份已提交的只读调查报告，`file:line` 直接引用报告原文，未做重新推导。报告说 UNKNOWN 之处本文档同样标 UNKNOWN。

## 1. 概览

**项目是什么**：一个 pygame 实现的双人、每人 3 张牌的扑克类对战游戏（对局级不变式：2 名玩家、每人 3 张，rules.py:80-81）。核心玩法为 ante 底注 + 四档押注（10/20/50/100，rules.py:26）+ 弃牌/看牌结算（rules.py:160-170）；牌型共六类（HIGH_CARD/PAIR/STRAIGHT/FLUSH/STRAIGHT_FLUSH/TRIPS，evaluator.py:18-24），牌力判定使用 C(52,3)=22100 手全量穷举精确强度表（strength.py:24-27，test_strength.py:19-20）。AI 对手为 DQN（agents/dqn.py:96-120）与策略 Robot（agents/robot.py:81-91）。交互入口是根目录 `draw_me_vs_DQN_Plus.py`（README.md:12,82；draw_me_vs_DQN_Plus.py:11,14），无头训练/评估入口为 `scripts/train.py` / `scripts/evaluate.py`（README.md:83-84）。

**生成时 commit**：`a6adf487be9f3bb29bbac496120f23462b45bfd4`。

**证据来源清单**（均在 `management/evidence/`，全部已提交）：

| 报告 | 覆盖范围 |
|---|---|
| `report-A-domain-core.md` | `core/` 全部 6 文件 + `algorithm.py` + `const.py`：数据模型不变式、牌型判定、精确强度表建表时机、发牌、rules.py 状态机、RepeatedTimer、逐文件 import 清单（Q10 依赖禁令核查） |
| `report-B-agents-scripts.md` | `agents/` 全部（BaseAgent/DQN/from_checkpoint/回放/目标网络/Robot）+ `scripts/` 全部 + 根目录交互入口 `draw_me_vs_DQN_Plus.py` + `mymath/robot2.py` 关系确认 |
| `report-C1-ui.md` | `ui/` 表现层（app/clock/render/theme/__init__）：主循环零阻塞、deadline 机制、view/snapshot 一致性、import 清单、7 条问题发现 |
| `report-C2-tests-quality.md` | `tests/`（含 baseline/）全量「被测试锁定的行为清单」、pyproject.toml、CI、src/ 资源规模（**本文档第 6 节的直接来源，完整保留**） |
| `report-C2b-readme-consistency.md` | README 18 条逐条一致性核对（16 一致 / 2 不一致）、pyproject 配置、CI 行为序列、src/ 资源规模、robot2.py 归属确定结论 |
| `report-C-partial-ui-tests.md` | 早期被截断的 ui 报告，**仅作参考，不优先采信**（与 C1 的个别行数有出入，见第 8 节） |

**如何使用本文档**：做重构前先看第 6 节（哪些行为被测试钉死）与第 7 节（改哪里会牵连什么）；每条结论后附 `文件:行号`，可直接跳源码复核；凡标 UNKNOWN 的条目（第 8 节）不得当作事实使用。

## 2. 分层结构与依赖方向

四层职责（行数取自各报告文件表）：

| 层 | 模块 | 职责 |
|---|---|---|
| 领域层 | `core/`（cards 74 / evaluator 89 / strength 58 / dealing 68 / rules 176 / __init__ 31 行） | 牌、牌型判定、精确强度表、发牌、对局状态机与结算；纯 Python 标准库，零 pygame/numpy/scipy/torch（report-A Q10 逐文件 import 核查） |
| 智能体层 | `agents/`（base 57 / dqn 224 / robot 257 / __init__ 20 行） | BaseAgent 统一接口、DQN 网络与训练、Robot 对手策略；用 torch/numpy，不 import pygame（README.md:61；tests/test_agents.py:184-191） |
| 表现层 | `ui/`（app 283 / clock 75 / render 253 / theme 170 / __init__ 12 行） | 薄表现层：Controller 回合状态机（非阻塞）+ pygame 事件循环 + 只读渲染；状态唯一来源 `core.GameRoom.snapshot()`（app.py:150-171） |
| 入口层 | `scripts/`（env 158 / train 124 / evaluate 108 / __init__ 1 行）+ `draw_me_vs_DQN_Plus.py`（14 行，纯启动器） | 无头训练/评估、交互启动；只向下 import core/agents（scripts/env.py:13-17、train.py:23-24、evaluate.py:18-20，report-C2b 第 6 条） |

严格单向依赖图（依赖只能从上层指向下层，方向证据见各箭头标注）：

```
┌─ 入口层 ─────────────────────────────────────────────────────────────┐
│  draw_me_vs_DQN_Plus.py:11 from ui.app import main / :14 main()      │
│  scripts/{env,train,evaluate}  (scripts/env.py:13-17 等)             │
└──────────┬──────────────────────────────┬─────────────────────────────┘
           │ 仅向下依赖                    │ 仅向下依赖
           ▼                              ▼
┌─ 表现层 ─────────────────────┐  ┌─ 智能体层 ───────────────────────────┐
│ ui/app.py (Controller/App)   │  │ agents/{base,dqn,robot}             │
│ ui/{clock,render,theme}      │  │ (torch/numpy；不 import pygame，     │
│   仅依赖仓库根 const.py       │  │  tests/test_agents.py:184-191)      │
│  (ui/render.py:16、ui/theme  │  └──────────┬──────────────────────────┘
│  .py:16 → const；app.py:17-21)│             │ agents/robot.py:18-19、
└──────────┬────────────────────┘             │ dqn.py:80 (lazy import)
           │ ui/app.py:17-21                  ▼
           └──────────────► ┌─ 领域层 ────────────────────────────────────┐
                            │ core/{cards,evaluator,strength,dealing,     │
                            │       rules}  纯标准库                       │
                            │ (core/ 全目录零 pygame/numpy/scipy/torch，   │
                            │  report-A Q10；tests/test_purity.py:19-25)  │
                            └────────────────────────────────────────────┘
   另：根目录 UI 辅助 algorithm.py:17 → const.py（algorithm.py 自身 import pygame，algorithm.py:15，属根目录 UI 耦合件，非 core/ 成员）
```

同层内合法依赖：`core/__init__.py` → cards/evaluator/rules/strength（__init__.py:11-14）；`core/rules.py:23-24` → cards/evaluator；`core/strength.py:17-18` → cards/evaluator；`core/dealing.py:17-18` → cards/strength；`evaluator.py:15` → cards（report-A 调用关系节）。agents 内部仅引 agents.base/core/mymath/numpy/torch（report-C2b 第 6 条 grep 结论）。

**「不得依赖」清单**（均有代码核查 + 测试守护双重证据）：

- `core/` 不得 import pygame/numpy/scipy/torch（README.md:60；report-A Q10 逐文件核查无命中；守护 tests/test_purity.py:19-25、55-63，其中 :55 额外覆盖 matplotlib；另有「摘除 pygame 后 core 六模块仍可导入」守护 tests/test_purity.py:28-52）。
- `agents/`、`scripts/` 不得 import pygame（README.md:61；grep 无 import 命中，report-C2b 第 9 条；守护 tests/test_agents.py:184-191、tests/test_scripts.py:104-110）。
- 不得在模块 import 期加载权重（README.md:62；全部 `torch.load` 均在函数体内，dqn.py:64、141、210；守护 tests/test_agents.py:183、193、tests/test_scripts.py:112-116，及子进程拦截 open/torch.load 证明不触盘 tests/test_agents.py:201-219）。
- `ui/`、`scripts/` 不得出现 time.sleep（README.md:63；ui/ 仅 docstring 提及 ui/app.py:5、ui/clock.py:1，scripts/ 零命中；守护 tests/test_ui.py:63-65）。
- `ui/render`、`ui/theme`、`ui/clock` 不 import core/agents，只依赖仓库根 const.py（ui/render.py:10-17；report-C1 第 8 条 import 清单）。

**README 架构图箭头方向有误（提示）**：README.md:44-48 的架构图把箭头画成 `core/agents ▼→ scripts`，与代码实际方向（scripts → core/agents，scripts/env.py:13-17 等）相反，且与 README.md:52 自己的文字描述自相矛盾（report-C2b 第 6 条、问题 1）。本文档依赖方向一律以 README.md:52 文字 + 代码证据为准。

## 3. 模块职责表

| 路径 | 行数 | 职责 | 关键公开符号 | file:line |
|---|---|---|---|---|
| `core/__init__.py` | 31 | core 包公开 API 重导出；`__all__` 白名单 | `__all__`（不含 `strength_ordinal`、`strongest_hand` 及 dealing 全部符号，只能经模块直接导入） | __init__.py:11-14（重导出）、16-31（白名单） |
| `core/cards.py` | 74 | 牌与牌堆数据模型（frozen dataclass） | `Suit`(IntEnum)、`Card`、`full_deck()`、`Card.from_legacy/to_legacy`、`hand_from_legacy/hand_to_legacy` | cards.py:13-17（Suit 域）、33-34（MIN/MAX_RANK）、37-46（Card 不变式）、55-61、64-66、69-74 |
| `core/evaluator.py` | 89 | 三张牌牌型判定与比大小 | `HandType`、`HAND_TYPE_NAMES`、`HandRank`（frozen，`key()` 可排序比较键）、`evaluate()`、`compare()` | evaluator.py:18-24、27、30-45、53-83、86-89 |
| `core/strength.py` | 58 | 穷举精确强度表（C(52,3)=22100，惰性建表 + 二分查询） | `beats_probability()`、`strength_ordinal()`、`strength_bin()`、`table_size()`、`strongest_hand()`、`BIN_THRESHOLDS` | strength.py:21、24-27（lru_cache 全量枚举）、34-37、48-54、57-58 |
| `core/dealing.py` | 68 | 发牌（默认均匀；偏置路径仅供复现历史实验） | `new_deck()`、`deal_uniform()`、`deal_strength_biased()`、`verify_uniformity()`、`EmptyDeckError` | dealing.py:3-5（docstring 契约 D-R1）、20、27-38、41-61、64-68 |
| `core/rules.py` | 176 | 对局状态机与结算（权威状态单点持有） | `GameRoom`（`new/hand/own_hand/opponent_hand/legal_actions/snapshot/apply` 及私有 `_bet/_fold/_compare/_finish`）、`Action`、`Player`、`IllegalAction`、`BET_OPTIONS/DEFAULT_ANTE/DEFAULT_MONEY` | rules.py:26-28、31-45、48-53、56-175；snapshot 107-121；apply 123-142 |
| `algorithm.py` | 120 | 根目录 UI 辅助（字体绘制 + RepeatedTimer + 规则文案）；import pygame | `RepeatedTimer`（daemon、stop 幂等、异常隔离；新版 UI 已改用 ui.clock.Ticker，本类保留供脚本/旧接口）、`show_font()`、`RULES_LINES`、`show_help_font()` | algorithm.py:15（import pygame）、20-86、89-97、100-111、114-120 |
| `const.py` | 82 | 资源路径/颜色/布局常量（不依赖 pygame.init()，docstring 声明与代码一致） | `ROOT/SRC`、资源目录常量、`Background/Card_Back`、`FONT_MAIN/FONT_UI`、`Color`、`BG_MUSIC`、`asset_exists()` | const.py:6-7、15-24、30-34、38-44、51-63、67-78、81-82 |
| `agents/base.py` | 57 | BaseAgent 统一接口 + `Transition`（frozen dataclass） | `Transition`、`BaseAgent`（唯一抽象方法 `act`；`observe/reset` 默认空实现；`save/load` 默认 NotImplementedError）、`_pick_legal`（非法动作兜底，保证返回值 ∈ legal_actions） | base.py:4、19-25、28-31、33-35、37-47、49-57 |
| `agents/dqn.py` | 224 | DQN 网络/超参/智能体/`from_checkpoint` 工厂/权重指纹 | `DQNConfig`、`DQN`（fc1/fc2/fc3，relu→relu→linear）、`StateEncoder`（4 维编码）、`DQNAgent`、`checkpoint_dims`、`from_checkpoint`、`weights_hash` | dqn.py:29-32、35-46、49-59、62-67、70-93、96-120、123-145、215-224 |
| `agents/robot.py` | 257 | 对手策略 Robot（由 mymath/robot2.py 迁入，行为保持等价） | `RobotConfig`（25 超参，`aggressive()` 默认=原 Robot2 参数、`conservative()`）、`Robot`、`OPTION_INDEX` | robot.py:1-9（迁入自述）、25、28-72、81-91 |
| `agents/__init__.py` | 20 | 包导出（无 pygame import，仅 docstring 提及） | — | agents/__init__.py:3（report-C2b 第 7 条） |
| `scripts/env.py` | 158 | `CardGameEnv` 环境封装（观测编码 + 回合推进） | 无 pygame import（docstring 提及） | scripts/env.py:3、16-17（→ core.dealing/core.rules） |
| `scripts/train.py` | 124 | 无头训练入口（argparse：`--episodes/--seed/--device{cpu,cuda}/--out`） | 训练循环（冒烟与可复现性由测试守护） | train.py:23-24（imports）、114-117（参数） |
| `scripts/evaluate.py` | 108 | 无头评估入口（argparse：`--rounds/--seed/--checkpoint/--out`） | 动作名与 `core.rules.Action` 对应 | evaluate.py:18-20（imports）、19（→ rules.Action）、62-69（action_names）、96-99（参数） |
| `scripts/__init__.py` | 1 | 仅 docstring | — | — |
| `draw_me_vs_DQN_Plus.py` | 14 | 唯一交互入口（纯启动器：9 行 docstring + 3 行可执行代码） | `main()` 调用 | draw_me_vs_DQN_Plus.py:11（`from ui.app import main`）、14（`main()`） |
| `ui/app.py` | 283 | `Controller`（回合状态机，非阻塞）+ `App`（pygame 事件循环）+ `main()` | `Controller`（update/human_action/view/_schedule/_ai_move/_auto_human_move）、`App`（run/step_frame/pump_events/_on_key/_on_click）、`DEFAULT_CHECKPOINT`、`main` | app.py:25、74-85、88-106、131-139、150-171、185-200、202-226、229-251、257-275 |
| `ui/clock.py` | 75 | `TickPolicy` 枚举（REAL/FIXED/IMMEDIATE）+ `Ticker` 节奏器 | `Ticker`（begin_frame/end_frame/now/deadline/due；REAL 模式惰性建 pygame.time.Clock 限帧 60） | clock.py:18-22、24、36-51、54-67 |
| `ui/render.py` | 253 | 薄渲染层（只绘制不记账，不算胜负） | `Renderer.draw(surface, view)`（状态全部取自 view dict） | render.py:101-118、243（`won = view["winner"] == 0`） |
| `ui/theme.py` | 170 | 资源路径映射 + `Layout` 布局常量 | `Layout`、`asset_paths()`、`button_image_path/avatar_image_path/coin_image_path`、`missing_assets()` | theme.py:20-41、44-53、57-74、77-90、92-123 |
| `ui/__init__.py` | 12 | 包导出：`__all__ = ["TickPolicy","Ticker","Layout","asset_paths"]`（App/Controller/Renderer 未重导出） | 重导自 ui.clock(9)、ui.theme(10) | ui/__init__.py:12 |

补充说明（report-A Q1）：`strength_ordinal`、`strongest_hand` 及 dealing 全部符号**不在** core `__all__` 白名单中（__init__.py:16-31），跨模块使用需直接 import 子模块（如 ui/app.py:20-21 直接引 core.rules/core.strength、app.py:18-19 引 core.dealing/core.evaluator）。

## 4. 关键调用链

### 4.1 交互链路：入口 → ui/app → core.GameRoom → agents

```
python draw_me_vs_DQN_Plus.py
  → draw_me_vs_DQN_Plus.py:11  from ui.app import main
  → draw_me_vs_DQN_Plus.py:14  main()
  → ui/app.py:257 main()
      → 构造 Controller(app.py:267) / Renderer(app.py:268) / Ticker(app.py:273) → App.run(app.py:275)
      → 权重加载：DEFAULT_CHECKPOINT = dqn_model_1.pth（app.py:25）
         - 该 .pth 仓库内不存在（find 无结果）→ 启动走回退：未训练策略 + print 提示（app.py:57-62，设计内回退）
         - 加载走 DQNAgent.from_checkpoint（agents/dqn.py:123-145；维度按 checkpoint 推断 dqn.py:136）
  → App.run  app.py:247-251   while self.running: self.step_frame()   （无 sleep；60fps 限帧 ui/clock.py:44-51）
  → step_frame  app.py:229-245
      ① Ticker.begin_frame（clock.py:36-42）→ now（clock.py:54-61）→ set_now（app.py:232）
      ② pump_events（app.py:185-200）：pygame.event.get()（:191，非阻塞取空队列）
         QUIT → running=False（:195-196）；KEYDOWN → _on_key（:197-198）；左键 → _on_click（:199-200）
      ③ _on_key（app.py:202-216：Esc/R/1-4/f/c）或 _on_click（app.py:218-226：按钮碰撞 :222-225）
         → Controller.human_action（app.py:131-139）
            → 回合/合法性校验（:132-135）→ _apply（:136）
            → core.GameRoom.apply（rules.py:123-142）→ _bet/_fold/_compare（rules.py:132-137）
            → _schedule(last_now)（app.py:137 → 74-85）
      ④ Controller.update（app.py:88-106，guard<64 死循环防护 :90）
         AI 回合：now < ai_deadline → return（app.py:93-94）；到期 → _ai_move（app.py:108）
            → StateEncoder.encode（agents/dqn.py:70-93）+ agent.act（base.py:33-35）→ room.apply（rules.py:123）
         人类自动回合：auto_human 到期 → _auto_human_move（app.py:116）
      ⑤ Renderer.draw（ui/render.py:101-118）
         数据 = Controller.view()（app.py:150-171）← room.snapshot()（rules.py:107-121）
      ⑥ display.flip（app.py:243）→ Ticker.end_frame（clock.py:44-51）
```

### 4.2 训练链路：scripts/train.py → scripts/env.py → core/agents

```
python scripts/train.py --episodes N --seed S --device {cpu,cuda} --out DIR   （train.py:114-117）
  → scripts/train.py:23-24  imports（report-C2b 第 6 条：scripts 只 import core/agents）
  → scripts/env.py:16-17  → core.dealing / core.rules   （CardGameEnv 环境封装）
  → 观测编码：StateEncoder 4 维（BOARD_FEATURES=3 + CARD_FEATURES=1，dqn.py:29-31；编码 dqn.py:70-93，
     盘面 circle/10、bets/1000、bets[1-player]/1000（dqn.py:86-88）+ 手牌 beats_probability（dqn.py:92））
  → DQN 训练：DQNAgent（dqn.py:96-120）observe 写回放（dqn.py:165-166）→ 采样（dqn.py:171）
     → TD 更新（dqn.py:180-188）→ 目标网络同步（dqn.py:193-198）
```

测试/CI 佐证：env 观测 4 维（tests/test_scripts.py:18-21）、合法动作非空（tests/test_scripts.py:23-26）、train 冒烟 episodes/win_rate/checkpoint 存在/summary_seed11.json（tests/test_scripts.py:62-67）、同种子 2026 两次 train 的 `weights_hash` 与 `avg_reward` 严格相等（tests/test_scripts.py:69-74）、evaluate 冒烟默认 ckpt=dqn_model_1.pth（tests/test_scripts.py:88-93）；CI 无头冒烟 train --episodes 2 --seed 5 + evaluate --rounds 5 + UI 600 帧（断言整局完成且 agent.epsilon==0.0 即已加载训练权重）（.github/workflows/ci.yml:60-82），可复现性比对 weights_hash（ci.yml:84-97）。

**UNKNOWN**：`train.py → env.CardGameEnv` 这一直接调用边在现存报告片段中无直接 file:line 证据（report-B 文件在 Q5 处截断，scripts/ 内部证据缺失），标 UNKNOWN。

### 4.3 评估链路：scripts/evaluate.py

`scripts/evaluate.py:96-99`（`--rounds/--seed/--checkpoint/--out`）；imports 仅 core/agents（evaluate.py:18-20），其中 evaluate.py:19 → `core.rules.Action`；动作语义 0-3=押 10/20/50/100、4=弃牌、5=比牌（`DEFAULT_ACTION_DIM=6`，dqn.py:32；映射证据 `OPTION_INDEX` robot.py:25、action_names 与 core.rules.Action 对应 evaluate.py:62-69）。

## 5. 数据流与状态管理

**权威状态在哪**：`core.GameRoom` 单点持有（rules.py:56-175），docstring 明示「UI 不得自行记账」（rules.py:107-121，尤其 rules.py:108）。字段集合（无显式 State 枚举，rules.py:56-66）：`hands`(rules.py:58)、`players`(rules.py:59)、`whose_turn`(rules.py:60)、`rest_option`(rules.py:61)、`circle`(rules.py:62)、`all_bet`(rules.py:63)、`finish`(rules.py:64)、`winner`(rules.py:65)、`history`(rules.py:66)，叠加每玩家 `money/bet/folded`（rules.py:50-53）。唯一读取通道是 `GameRoom.snapshot()`（rules.py:107-121）；测试锁定：snapshot 只读视图字段相等（tests/test_rules.py:141-146）、view 与 snapshot 五字段逐字段相等（tests/test_ui.py:124-134）。

**UI 如何只读消费**：`Controller.view()`（app.py:150-171）以 `room.snapshot()` 为数据源（app.py:151）生成 view dict；`Renderer.draw(surface, view)`（ui/render.py:101-118）状态全部取自 view。render 层只 import const 与 ui.theme（render.py:10-17），不 import core/agents、不算胜负：`won = view["winner"] == 0`（ui/render.py:243），winner 来自 snapshot（app.py:158）。
- 隐式耦合点（report-C1 问题 5）：view 恒含对手真手牌（app.py:156），靠 render 阶段克制——未结算只画背面（render.py:159-171）；结算时 view 向 UI 暴露对手真实牌型（app.py:169；render.py:176-178 显示）。改 view 键名或 render 取值逻辑时注意这条隐式约定。

**状态机推进方式**：宏观两态——进行中 `finish=False`（rules.py:100/124 判断）/ 已结束 `finish=True`（rules.py:173 置位）；弃牌以 `folded` 标记（rules.py:157）。推进唯一入口 `apply()`（rules.py:123-142）：结束后任何行动抛 `IllegalAction`（rules.py:124-125）→ 未知动作抛 `IllegalAction`（rules.py:126-129）→ 分发 bet/fold/compare（rules.py:132-137）→ 记 history（rules.py:138）→ 未结束时换手 `whose_turn = 1 - actor`（rules.py:140）→ 回到玩家 0 时 `circle += 1`（rules.py:141-142）。合法动作 `legal_actions()`（rules.py:99-102）：结束后返回空，否则 rest_option 起的押注档 + FOLD + COMPARE。关键不变式：`rest_option = max(rest_option, action)` 单调不减（rules.py:154），低于 rest_option 的降档押注抛 `IllegalAction`（rules.py:145-148）。结算：`_compare`（rules.py:160-170）费用 = `BET_OPTIONS[rest_option]`（rules.py:162），仅看牌方付款（rules.py:164-166），完全平局时看牌方输（rules.py:168-170，注释明确此约定）；`_finish`（rules.py:172-175）置 finish、记录 winner、赢家拿走全部押注池 `money += all_bet`（rules.py:175）。UI 侧对应推进在 `Controller.update`（app.py:88-106），每帧上限 guard<64（app.py:90，死循环防护而非忙等）。

**AI 回合与人类回合的 deadline 表达**：`_schedule()`（app.py:74-85）按回合方设置 `ai_deadline/human_deadline`（app.py:80-85）。AI 回合：`if now < self.ai_deadline: return`（app.py:93-94）——**等待 = 提前 return，不是忙等**；到期 → `_ai_move`（app.py:95）→ `_schedule`（app.py:97）→ 若仍 AI 回合再 return（app.py:98-99）。人类回合：非 auto_human（或未到 deadline）直接 return（app.py:101-102），控制权交还主循环，由其持续重绘（app.py:237-243）并每帧响应 QUIT/按键（app.py:195-199）；auto_human 到期自动随机出牌（app.py:103）。时钟来源 `Ticker.now()`（ui/clock.py:54-61）：REAL=perf_counter（:57）/ FIXED=虚拟时钟（:59）/ IMMEDIATE=每帧 1 秒步长（:61，供测试整局零等待）；`deadline()`（:63-64）、`due()`（:66-67）。

## 6. 被测试锁定的行为清单

本节完整保留 report-C2-tests-quality.md 的「被测试锁定的行为清单」全部条目（tests/ 全量），未删减。

### 6.1 tests/test_rules.py（D1/D2/D4 + 回合/命名）

| 测试文件 | 守护的约束 | file:line |
|---|---|---|
| tests/test_rules.py | D1 看牌结算方向：4 参数化用例（whose_turn×强弱手）必须「比输者输」 | test_rules.py:28-40（assert :39-40） |
| tests/test_rules.py | 看牌收费 = 当前最低注 | test_rules.py:42-48 |
| tests/test_rules.py | 加注后按加注档收费（BET_100→BET_OPTIONS[3]） | test_rules.py:50-58 |
| tests/test_rules.py | 平局判非行动方胜 | test_rules.py:60-64 |
| tests/test_rules.py | D2 rest_option 单调：BET_100 后 rest_option==3，降档 BET_10 抛 IllegalAction 且 rest_option 不回退 | test_rules.py:68-78 |
| tests/test_rules.py | 合法动作集 = 高挡位∪弃牌∪看牌，低档被剔除 | test_rules.py:80-85 |
| tests/test_rules.py | 押注更新底池/个人注/金币（开局各押 5：all_bet=10+20） | test_rules.py:87-92 |
| tests/test_rules.py | D4 结束后拒绝行动：finish 后 apply 抛 IllegalAction、legal_actions()==() | test_rules.py:96-103 |
| tests/test_rules.py | FOLD 判对方胜、底池全归对方、金币守恒 40000 | test_rules.py:105-121 |
| tests/test_rules.py | 回合交替 | test_rules.py:125-131 |
| tests/test_rules.py | own_hand/opponent_hand 具名访问器（D5） | test_rules.py:133-139 |
| tests/test_rules.py | snapshot 只读视图字段相等 | test_rules.py:141-146 |
| tests/test_rules.py | 接受 legacy dict 手牌 | test_rules.py:148-154 |

### 6.2 tests/test_dealing.py（D6 发牌）

| 测试文件 | 守护的约束 | file:line |
|---|---|---|
| tests/test_dealing.py | 均匀发牌 3 张不重复 | test_dealing.py:43-47 |
| tests/test_dealing.py | 牌堆不足抛 EmptyDeckError | test_dealing.py:50-52 |
| tests/test_dealing.py | 400 手均匀样本强度分位均值 ∈(0.44,0.56)（基线 0.489） | test_dealing.py:56-59 |
| tests/test_dealing.py | 最强档（>0.95）占比 <0.08（理论 5%，基线实测 0.013） | test_dealing.py:62-66 |
| tests/test_dealing.py | 偏置路径（三抽一）均值须比均匀高 >0.15（基线 0.766 vs 0.489） | test_dealing.py:69-75 |
| tests/test_dealing.py | 偏置路径每发 1 手丢弃 9 张不回堆 | test_dealing.py:78-83 |
| tests/test_dealing.py | 默认均匀路径不触发 22100 手建表（lru_cache 命中为 0） | test_dealing.py:86-95 |
| tests/test_dealing.py | 全牌堆 52 张唯一 | test_dealing.py:98-101 |

### 6.3 tests/test_ui.py（时序/一致性/贴图/性能/入口）

| 测试文件 | 守护的约束 | file:line |
|---|---|---|
| tests/test_ui.py | Ticker IMMEDIATE 不等待（<50ms） | test_ui.py:40-45 |
| tests/test_ui.py | FIXED 虚拟时钟推进 ≥dt | test_ui.py:47-53 |
| tests/test_ui.py | deadline/due 语义 | test_ui.py:55-61 |
| tests/test_ui.py | 零 sleep 守护（仅扫 ui/） | test_ui.py:63-65 |
| tests/test_ui.py | D7-b QUIT 在等待期间被响应：post QUIT 后 step_frame → running is False | test_ui.py:69-77（assert :77） |
| tests/test_ui.py | QUIT 在 AI 思考（think_seconds=5.0, TickPolicy.REAL）期间被响应 | test_ui.py:80-91（assert :91） |
| tests/test_ui.py | 无人输入帧持续推进（10 帧→frames==10） | test_ui.py:94-100 |
| tests/test_ui.py | 零等待 400 帧内整局跑完 | test_ui.py:102-108 |
| tests/test_ui.py | 按 R 重开新局 | test_ui.py:110-119 |
| tests/test_ui.py | UI 不记账：view() 与 room.snapshot() 五字段（money/bets/all_bet/finish/winner）逐字段相等 | test_ui.py:124-134 |
| tests/test_ui.py | min_bet 来自 core（BET_100 后 view["min_bet"]==100） | test_ui.py:137-140 |
| tests/test_ui.py | 人类回合合法动作非空（未断言 AI 回合为空） | test_ui.py:142-148 |
| tests/test_ui.py | 性能：core 单步 <5ms（基线 1530.8ms） | test_ui.py:152-165（assert :165） |
| tests/test_ui.py | 性能：UI 路由+控制单帧 <50ms | test_ui.py:167-173（assert :173） |
| tests/test_ui.py | 入口薄化：draw_me_vs_DQN_Plus.py 无星号导入/sleep/load_state_dict，import 期无 pygame.init() | test_ui.py:177-183 |
| tests/test_ui.py | const 可无 pygame 导入、路径绝对且不含 myclient | test_ui.py:185-189 |
| tests/test_ui.py | dummy 驱动下 Renderer 可绘制 | test_ui.py:191-202 |
| tests/test_ui.py | asset_paths 必含 5 键 | test_ui.py:204-208 |
| tests/test_ui.py | 原始贴图：6 个动作按钮贴图存在且 2:1 比例 | test_ui.py:214-230 |
| tests/test_ui.py | 头像 human/ai 存在、AVATAR_LIBRARY 四元神 | test_ui.py:232-241 |
| tests/test_ui.py | variant 生效（cat_spirit→喵喵.png） | test_ui.py:243-249 |
| tests/test_ui.py | 金币贴图尺寸 = layout.coin_size | test_ui.py:251-258 |
| tests/test_ui.py | 贴图缺失回退文本绘制不崩溃（monkeypatch 指向不存在目录） | test_ui.py:260-280 |
| tests/test_ui.py | 布局不重叠（手牌≤按钮 y、信息栏不侵入、暗牌不压底池、按钮不出界） | test_ui.py:282-293 |
| tests/test_ui.py | 窗口 4:3 | test_ui.py:295-298 |
| tests/test_ui.py | missing_assets()==[] | test_ui.py:300-303 |

> 注：上行「人类回合合法动作非空」对应 test_ui.py:142-148（`test_legal_actions_gated_to_human_turn`），其实际断言范围仅为两项——`view["is_human_turn"] is True`（test_ui.py:147）与人类回合 `view["legal_actions"]` 非空（test_ui.py:148）；该测试**没有**断言 AI 回合合法动作为空（R2 审核发现，原措辞「仅在人类回合非空」偏强，已校准）。

### 6.4 tests/test_strength.py（精确强度表）

| 测试文件 | 守护的约束 | file:line |
|---|---|---|
| tests/test_strength.py | 表规模恰 22100（C(52,3)） | test_strength.py:19-20 |
| tests/test_strength.py | 确定性：同一手 50 次调用值唯一 | test_strength.py:23-27 |
| tests/test_strength.py | 边界：概率∈[0,1)；最强手（三条A）胜率 >0.9998 且 <1.0 | test_strength.py:30-35 |
| tests/test_strength.py | 单调：弱<中<强 | test_strength.py:38-42 |
| tests/test_strength.py | 牌型键大者胜率不更小（200 次抽样成对校验） | test_strength.py:45-53 |
| tests/test_strength.py | strength_bin ∈{1..6}（500 抽样） | test_strength.py:56-61 |
| tests/test_strength.py | 单次查询 <100µs（基线蒙特卡洛 30.8ms） | test_strength.py:64-72（assert :72） |
| tests/test_strength.py | 建表一次性（lru_cache，二次查询 <10ms） | test_strength.py:75-80 |

### 6.5 tests/test_evaluator.py（牌型判定）

| 测试文件 | 守护的约束 | file:line |
|---|---|---|
| tests/test_evaluator.py | 六类牌型判定 | test_evaluator.py:18-35 |
| tests/test_evaluator.py | 边界：A-K-Q 是顺子、A-2-3 不是（HIGH_CARD）、同点三张=TRIPS | test_evaluator.py:38-47 |
| tests/test_evaluator.py | 非 3 张抛 ValueError | test_evaluator.py:50-53 |
| tests/test_evaluator.py | rank 越界（15/1）抛 ValueError | test_evaluator.py:54-58 |
| tests/test_evaluator.py | 排序：单张<对子<顺子<金花<顺金<三张（两两 compare ±1） | test_evaluator.py:62-74 |
| tests/test_evaluator.py | 对子点>踢脚、同对踢脚决胜、顺子比最大、金花比最大 | test_evaluator.py:76-95 |
| tests/test_evaluator.py | 花色决胜：同点黑桃胜；完全相同=0；反对称 | test_evaluator.py:98-112 |

### 6.6 tests/test_agents.py（D8/D9/契约）

| 测试文件 | 守护的约束 | file:line |
|---|---|---|
| tests/test_agents.py | D8 维度自适应：KEEPER_CKPT=dqn_model_1.pth 实际维度 (4,6) | test_agents.py:27-30 |
| tests/test_agents.py | from_checkpoint 构建 agent.input_dim==4、action_dim==6、model.fc1.in_features==4 | test_agents.py:32-37 |
| tests/test_agents.py | 硬编码 DQN(9,6) 加载 4 维权重必须 RuntimeError | test_agents.py:39-46 |
| tests/test_agents.py | 缺文件抛 FileNotFoundError | test_agents.py:48-50 |
| tests/test_agents.py | D9 真正加载权重：加载后 epsilon==0.0（贪心） | test_agents.py:54-56 |
| tests/test_agents.py | 同状态 20 次 act 输出唯一 | test_agents.py:58-63 |
| tests/test_agents.py | 与 epsilon=1.0 随机策略动作分布 L1 距离 >0.5 | test_agents.py:65-84（assert :84） |
| tests/test_agents.py | 契约：act 只返回合法动作（30 次×3 组） | test_agents.py:88-93 |
| tests/test_agents.py | 空合法集抛 ValueError | test_agents.py:95-98 |
| tests/test_agents.py | 同种子同序列 | test_agents.py:100-106 |
| tests/test_agents.py | save/load 往返动作一致 | test_agents.py:108-114 |
| tests/test_agents.py | replay 返回非负 loss 且 epsilon 按 decay 降至 0.5 | test_agents.py:116-125 |
| tests/test_agents.py | Robot：act 合法、强牌 win_rate>弱牌、预设差异、robot.py 无星号导入（显式 import numpy）、强牌加注占比>弱牌（400 次统计） | test_agents.py:141-180 |
| tests/test_agents.py | 分层：agents/ 无 pygame（正则扫描） | test_agents.py:184-191 |
| tests/test_agents.py | load_state_dict 不得在模块顶层 | test_agents.py:193-199 |
| tests/test_agents.py | import agents 子进程拦截 open/torch.load 证明不触盘 | test_agents.py:201-219 |

### 6.7 tests/test_scripts.py（训练/评估入口）

| 测试文件 | 守护的约束 | file:line |
|---|---|---|
| tests/test_scripts.py | env 观测 4 维 | test_scripts.py:18-21 |
| tests/test_scripts.py | 合法动作非空 | test_scripts.py:23-26 |
| tests/test_scripts.py | D4 环境层防护：done 后再 step 抛 IllegalAction | test_scripts.py:28-43 |
| tests/test_scripts.py | 奖励仅终局非零 | test_scripts.py:45-58 |
| tests/test_scripts.py | train 冒烟：episodes/win_rate/checkpoint 存在/summary_seed11.json | test_scripts.py:62-67 |
| tests/test_scripts.py | 可复现性：同种子（2026）两次 train，weights_hash 与 avg_reward 严格相等 | test_scripts.py:69-74 |
| tests/test_scripts.py | 异种子 hash 不等 | test_scripts.py:76-79 |
| tests/test_scripts.py | 5 回合 <60s | test_scripts.py:81-84 |
| tests/test_scripts.py | evaluate 冒烟（默认 ckpt=dqn_model_1.pth） | test_scripts.py:88-93 |
| tests/test_scripts.py | D9 旁证：动作分布最大占比 >0.4 | test_scripts.py:95-100 |
| tests/test_scripts.py | 分层：scripts/ 无 pygame | test_scripts.py:104-110 |
| tests/test_scripts.py | torch.load 不得在模块顶层 | test_scripts.py:112-116 |
| tests/test_scripts.py | Transition 4 维 | test_scripts.py:118-124 |

### 6.8 tests/test_purity.py（分层纯度）

| 测试文件 | 守护的约束 | file:line |
|---|---|---|
| tests/test_purity.py | core/ 有源文件 | test_purity.py:15-16 |
| tests/test_purity.py | core/ 不 import pygame（正则 `PYGAME_IMPORT`，test_purity.py:8） | test_purity.py:19-25 |
| tests/test_purity.py | 摘除 pygame 后 core 六模块仍可导入（meta_path 注入 _Blocker，test_purity.py:43-49） | test_purity.py:28-52 |
| tests/test_purity.py | core/ 不依赖 numpy/scipy/torch/matplotlib/pygame（逐文件正则，test_purity.py:60-63） | test_purity.py:55-63 |

### 6.9 tests/baseline/ 回归脚本（D1-D7 历史缺陷红转绿的守护）

| 测试文件 | 守护的约束 | file:line |
|---|---|---|
| tests/baseline/common.py | 自述：现断言「修复后的正确行为（绿）」，红证据在 docs/BASELINE-REPORT.md 与提交 97a2737 | tests/baseline/common.py:4-5 |
| tests/baseline/common.py | 注入 REPO_ROOT 到 sys.path；check() 打印 PASS/FAIL；summary() 打印 BASELINE_RESULT | tests/baseline/common.py:11-13、35-37、40-46 |
| tests/baseline/repro_d1_showcards.py | D1 看牌结算 4 用例循环 | tests/baseline/repro_d1_showcards.py:21-34（check :34，summary :36） |
| tests/baseline/repro_d2_rest_option.py | D2 rest_option 单调 | tests/baseline/repro_d2_rest_option.py:20-34 |
| tests/baseline/repro_d2_rest_option.py | D2b const 路径无 myclient/`..` 前缀且解析进仓库 | tests/baseline/repro_d2_rest_option.py:37-46 |
| tests/baseline/repro_d2_rest_option.py | D2c AST 解析 const.py 导入集合不含 pygame | tests/baseline/repro_d2_rest_option.py:48-57 |
| tests/baseline/repro_d4_lagging_done.py | D4：FOLD 后 finish/合法动作为空/再行动抛异常/金币守恒 40000 | tests/baseline/repro_d4_lagging_done.py:18-39 |
| tests/baseline/repro_d5_wiring.py | D5：own_hand/opponent_hand 四向校验 + StateEncoder 编码 state[3]==beats_probability(本人手牌)（无信息泄漏） | tests/baseline/repro_d5_wiring.py:22-41 |
| tests/baseline/repro_d6_dealing.py | D6：均匀/偏置 300 手分位均值对比（`:47-53` 子细节在报告截断处缺失，UNKNOWN） | tests/baseline/repro_d6_dealing.py:28-53 |
| tests/baseline/repro_d7_timing.py | D7 修复前基线：单步墙钟≈1530.8ms、time.sleep(1.5) 占 98.0%；check_button_click 忙等且不处理 QUIT；RepeatedTimer 未 start 就 stop() 抛 AttributeError 且线程非 daemon；import 期 load_state_dict 致 import 即崩 | tests/baseline/repro_d7_timing.py:1-10（各条 :4-:7） |
| tests/baseline/repro_d7_timing.py | D7 现回归检查：零 sleep；QUIT 立即退出；零等待整局<1s；定时器加固+daemon；无 import 期权重加载 | tests/baseline/repro_d7_timing.py:35-41、43-59、68-73、75-93、98-106 |
| （CI 汇总） | CI 逐个跑 tests/baseline 下 repro_d1/d2/d4/d5/d6/d7 共 6 个回归脚本，任一失败 exit 1 | .github/workflows/ci.yml:50-58 |

注：tests/baseline/ 编号缺 D3（现有 d1/d2/d4/d5/d6/d7 + common.py，ci.yml:53-54 与之吻合），D3 缺号原因 UNKNOWN（report-C2b 问题 6）。

## 7. 重构风险点

### 7.1 核心状态契约：GameRoom.snapshot 与 UI view 的逐字段相等

- `snapshot()`（rules.py:107-121）是 UI 唯一数据源（app.py:151），`Controller.view()`（app.py:150-171）生成 view，`Renderer.draw`（render.py:101-118）只从 view 取值，`won = view["winner"] == 0`（render.py:243）。
- 测试钉死：view 与 snapshot 五字段（money/bets/all_bet/finish/winner）逐字段相等（tests/test_ui.py:124-134）；snapshot 只读视图字段相等（tests/test_rules.py:141-146）；min_bet 来自 core（tests/test_ui.py:137-140）。
- **风险**：增删或改名 snapshot 字段、view 键名，或让 render 自行计算状态，会立即打红 test_ui.py:124-134 / test_rules.py:141-146；render 字段消费还有贴图/布局测试兜底（tests/test_ui.py:191-202、282-293）。

### 7.2 D1-D9 历史缺陷已被哪些测试钉住

| 缺陷 | 被钉住的测试 | file:line |
|---|---|---|
| D1 看牌结算方向/收费/平局 | tests/test_rules.py:28-40、42-48、50-58、60-64；tests/baseline/repro_d1_showcards.py:21-34 |
| D2 rest_option 单调（含 const 路径/导入卫生 D2b/D2c） | tests/test_rules.py:68-78、80-85；tests/baseline/repro_d2_rest_option.py:20-34、37-46、48-57 |
| D3 | 编号缺失，无对应基线脚本，原因 UNKNOWN（report-C2b 问题 6；ci.yml:53-54） |
| D4 结束后拒绝行动 | tests/test_rules.py:96-103；tests/test_scripts.py:28-43（环境层）；tests/baseline/repro_d4_lagging_done.py:18-39 |
| D5 手牌接线（具名访问器、无信息泄漏） | tests/test_rules.py:133-139；tests/baseline/repro_d5_wiring.py:22-41 |
| D6 默认均匀发牌 | tests/test_dealing.py:43-101（分布 :56-66、不建表 :86-95 关键）；tests/baseline/repro_d6_dealing.py:28-53 |
| D7 时序与事件循环 | tests/test_ui.py:40-65（Ticker/零 sleep）、69-108（QUIT/推进）、152-173（性能）；tests/baseline/repro_d7_timing.py:35-106；algorithm.py RepeatedTimer 加固（daemon algorithm.py:59、stop 幂等 :71-78、异常隔离 :51-54） |
| D8 权重维度自适应 | tests/test_agents.py:27-50 |
| D9 真正加载已训练权重 | tests/test_agents.py:54-84；tests/test_scripts.py:95-100；ci.yml:60-82（UI 冒烟断言 agent.epsilon==0.0） |

**风险**：这些缺陷均已修复且被回归钉住；任何「顺手重构」触及对应路径都会让对应测试变红，改动前应先跑对应测试文件。

### 7.3 精确强度表的建表时机（惰性，勿改回 import 期）

- 惰性建表：模块级（strength.py:11-21）只有 import 与 `BIN_THRESHOLDS`（strength.py:21），无模块级代码调用 `combinations`/`evaluate`/`_ranked_keys`；首次调用 `table_size`/`beats_probability`/`strength_ordinal`/`strength_bin`（strength.py:31/36/45/50）之一才触发 C(52,3)=22100 全量枚举与排序（strength.py:24-27），之后命中 `@lru_cache(maxsize=1)`（strength.py:24）；注释自述「首次调用约数十毫秒，之后命中缓存」（strength.py:26）。表只在进程内存，无磁盘持久化。
- 查询路径为二分：`bisect_left`（strength.py:36-37、45）；`strongest_hand()` 不走缓存（strength.py:58）。
- 测试钉死：表规模恰 22100（test_strength.py:19-20）、建表一次性且二次查询 <10ms（test_strength.py:75-80）、**默认均匀发牌路径不触发建表（lru_cache 命中为 0，test_dealing.py:86-95）**、单次查询 <100µs（test_strength.py:64-72）。
- **风险**：把建表挪到 import 期、去掉 lru_cache、或让均匀发牌路径调用强度查询，都会打红 test_dealing.py:86-95 与 test_strength.py:75-80。

### 7.4 权重维度自适应（from_checkpoint）

- 机制：网络维度不由调用方声明，而由 checkpoint 张量形状决定——`checkpoint_dims` 读 `fc1.weight.shape[1]`（input_dim）与 `fc3.weight.shape[0]`（output_dim）（dqn.py:62-67），`from_checkpoint` 按实际维度构建（dqn.py:136→140），随后 `torch.load` + `load_state_dict`（dqn.py:141-142）、`model.eval()`（dqn.py:143）、同步目标网络（dqn.py:144）。全部 `torch.load` 在函数体内（dqn.py:64、141、210），import 期零磁盘 IO。
- 测试钉死：(4,6) 维度推断（test_agents.py:32-37）、硬编码 DQN(9,6) 加载 4 维权重必须 RuntimeError（test_agents.py:39-46）、缺文件 FileNotFoundError（test_agents.py:48-50）、import 期不触盘（test_agents.py:201-219、193-199）。
- **风险**：恢复「调用方声明维度」的旧接口或跳过 `checkpoint_dims`，会复现 D8 并打红 test_agents.py:27-50。

### 7.5 D6 默认均匀发牌与偏置开关（函数名注意）

- 默认路径是均匀发牌：`new_deck()` 洗牌（dealing.py:27-31，`rng` 可注入 dealing.py:30）+ `deal_uniform(deck, n=3)`（dealing.py:34-38）；模块 docstring 明确「默认 `deal_uniform`…`deal_strength_biased` 默认不启用，仅供复现历史实验（契约 D-R1）」（dealing.py:3-5）。
- **任务书/历史文档所用的 `draw_strength_biased()` 开关在代码中不存在**：全仓 `.py` grep `draw_strength_biased` 零匹配（仅 legacy 管理文档 r4 plan 用过此名）；实际函数名是 **`deal_strength_biased`**（dealing.py:41-61，report-A Q5）。
- 偏置路径行为：抽 `candidates`（默认 `DEFAULT_CANDIDATES=3`，dealing.py:20）组各 n 张候选（dealing.py:55-56），逐组 `beats_probability` 打分（dealing.py:57），保留最强一组（dealing.py:58-59），其余弃置不回堆（dealing.py:46 注释）；牌堆不足 `n*candidates` 抛 `EmptyDeckError`（dealing.py:50-52）。
- 测试钉死：偏置均值比均匀高 >0.15（test_dealing.py:69-75）、每发 1 手丢弃 9 张不回堆（test_dealing.py:78-83）、均匀分布约束（test_dealing.py:56-66）。
- **风险**：若把偏置路径设为默认，会打红 test_dealing.py:56-66 与 :86-95（偏置路径会触发 22100 手建表）；启用开关时调用 `deal_strength_biased`，不要按不存在的 `draw_strength_biased` 名找代码。

### 7.6 README 与代码的不一致与 overclaim（详见第 8 节）

- README.md:28「draw_me_vs_DQN_Plus.py (6 行)」实际为 14 行（report-C2b 第 4 条）。
- README.md:44-48 架构图箭头方向错误（report-C2b 第 6 条）。
- README.md:63「ui/、scripts/ 无 time.sleep」的守护声明超出测试范围：test_no_sleep_in_source 只扫 ui/（tests/test_ui.py:63-65），scripts/ 无 sleep 目前仅 grep 证实（R2 审核发现①，第 8 节第 3 条）。
- **风险**：照 README 图接线的开发者会搞反依赖方向；引用 README 行数/模块清单时以代码为准；误以为 scripts/ 零 sleep 有测试守护，会使其混入 sleep 时没有任何测试变红——引用测试守护范围时以 tests/ 实际扫描范围为准。

### 7.7 其它已知小风险（report-C1 问题清单，均带 file:line）

- `Action(key - pygame.K_1)` 键码差值映射 1→Action(0)，小键盘/特殊布局下不触发（ui/app.py:212）。
- 资源自检过粗：只查 `const.ROOT/"src"` 存在性；`theme.missing_assets()`（ui/theme.py:77-90）已提供精确检查但未被使用（ui/app.py:269-271）。
- `button_rects` 返回注解为 `dict[int, "object"]`，应为 `pygame.Rect`（ui/theme.py:130，注解不精确）。
- checkpoint 缺失时启动走回退：未训练策略 + print 提示（ui/app.py:25、57-62，设计内回退但需文档注明）。
- view 恒含对手真手牌（ui/app.py:156），信息克制依赖 render 阶段（render.py:159-171、176-178），耦合偏隐式（见 5 节）。
- `last_now` 为类级属性（未写于 `__init__`），`set_now`（ui/app.py:143-144）覆盖为实例属性，风格不统一（ui/app.py:141）。
- `_on_click` 在 renderer=None 时 rects 为空 dict，鼠标输入失效（键盘仍可用）（ui/app.py:222）。
- core `__all__` 白名单不含 `strength_ordinal`/`strongest_hand`/dealing 符号（core/__init__.py:16-31），依赖这些符号的代码只能直接 import 子模块。

## 8. 遗留疑点与未核实项

### 8.1 各报告 UNKNOWN 汇总（照抄报告结论，不用 README 自述补齐）

| 来源 | UNKNOWN 项 |
|---|---|
| report-A-domain-core.md | git status：只读角色无 bash 工具，无法实时核验活体工作区（本次调查零写入） |
| report-C1-ui.md | git status：只读角色无 bash 工具，无法执行（未修改/创建任何文件） |
| report-C1-ui.md | pygame/numpy 具体版本号：C1 未读 pyproject（标 UNKNOWN）；report-C2b 后续已给出版本锁定证据 pyproject.toml:15-19（pygame==2.6.1、numpy>=2.3,<2.4、scipy>=1.17,<1.18、matplotlib>=3.11,<3.12、torch>=2.13,<2.14） |
| report-C2b-readme-consistency.md | src/ 总大小：UNKNOWN（无 stat/du 工具），含 38 个音频文件，估计数十 MB 量级（仅估计） |
| report-C2b-readme-consistency.md | D3 编号缺失原因：UNKNOWN |
| report-C2b-readme-consistency.md | README.md:19 的 cu130 torch index URL 可用性：UNKNOWN（未联网验证） |
| report-C2b-readme-consistency.md | git status：该 reader 无 bash 工具无法运行（纯只读；.git/HEAD = refs/heads/main） |
| 本报告编写时（worker） | 4.2 节 `train.py → env.CardGameEnv` 直接调用边：现存报告片段无直接 file:line 证据，UNKNOWN |

### 8.2 报告文件截断说明（影响可信度的来源限制）

- `report-A-domain-core.md` 落盘文件在「调用关系 → 测试：tests/test_evaluator.py:5-6、」处截断，其后内容（含 UNKNOWN 清单全表）缺失；本文档仅引用截断点之前可见的内容。
- `report-B-agents-scripts.md` 落盘文件在 Q5「`_hand_strength` 用 core 穷举精确值 `beats_probability`（7」处截断；scripts/ 内部调用细节、机器人行为核心全貌、以及该报告对 ui/app.py 的跨边界行号取证（25/49/57-62/257-278）正文缺失。其中 ui/app.py:25、57-62、257-275 的等价证据已由 report-C1 独立给出（app.py:25、57-62、257-275），其余缺失处本文档标 UNKNOWN 或不引用。
- `report-C2-tests-quality.md` 落盘文件在「关键代码位置 → repro_d6_dealing.py … `:47-53`」处截断；第 6 节所需的核心「被测试锁定的行为清单」在截断点之前**完整存在**，已全量保留；repro_d6_dealing.py:47-53 的子细节缺失。
- `report-C-partial-ui-tests.md`（早期被截断的 ui 报告）与 report-C1 存在行数出入：partial 记 ui/app.py 282 / render.py 252 / theme.py 165，C1 记 283 / 253 / 170；按任务约定 partial 仅作参考、不优先采信，本文档一律采用 report-C1 数值。

### README 与代码的不一致

已知 3 处（report-C2b 第 4、6 条 + R2 审核发现①）：

1. **行数描述错误**：README.md:28 称「draw_me_vs_DQN_Plus.py (6 行)」，实际文件 14 行（9 行 docstring + 3 行可执行代码；draw_me_vs_DQN_Plus.py:11,14）。
2. **架构图箭头方向与文字相反**：README.md:44-48 把箭头画成 `core/agents ▼→ scripts`，实际代码方向是 `scripts → core/agents`（scripts/env.py:13-17、train.py:23-24、evaluate.py:18-20），与 README.md:52 的文字描述自相矛盾。
3. **「无 time.sleep」声明超出测试守护范围（overclaim）**：README.md:63 声称「ui/、scripts/ 无 `time.sleep`」并指认守护测试为 `tests/test_ui.py::TestTicker::test_no_sleep_in_source`，但该测试实际只扫描 `ui/`（`(REPO / "ui").glob("*.py")`，tests/test_ui.py:63-65），未覆盖 `scripts/`；`scripts/` 当前无 sleep 仅由 grep 核实（零命中），没有测试守护。即 README 声明范围（README.md:63：ui/ + scripts/）与测试实际守护范围（tests/test_ui.py:63-65：仅 ui/）不符。

`mymath/robot2.py` 历史说明（确定结论，report-C2b 特别核对 B）：

- `mymath/robot2.py` **已不在仓库**（ls mymath/ 仅 `__init__.py`（空）、`func_const.py`、`probability_func.py`、纯文本「概率大小映射」21 行概率表）。
- robot2 的实现是 `agents/robot.py`：robot.py:1-9 自述「由 mymath/robot2.py 迁入，行为保持等价」，Robot/Robot2 两类合并为一个类 + `RobotConfig` 参数化（robot.py:28-72）；CHANGELOG.md:85 记录「mymath/robot2.py → agents.robot.Robot（行为等价留证 L1=0.076）」；docs/FINAL-REPORT.md:33 记录 mymath/robot2.py 随 commit `e0263e1` 删除。
- management/legacy/project/r5/contract.json:17,26,39 的「保留 mymath/robot2.py」是 r5 计划期陈旧表述，最终按 r5/PLAN.md:33（T3.3 迁入 agents/）落地为「删除 + 迁移」。
- README 本身并未声称保留 mymath/robot2.py（README.md:73 只列 func_const·probability_func），故此项 README 与代码一致。

补充（report-C2b 问题清单中另有两条轻微项，非上述 3 条正式条目）：pyproject.toml:42 ruff extend-exclude 含已不存在的「备份」目录（历史残留，无害）；mymath/ 的非代码文件「概率大小映射」未出现在 README.md:73 目录说明中（轻微遗漏）。

### 行号校准说明

两份审核报告（review-R1-line-sampling.md、review-R2-tests-readme.md）指出的 9 条行号边界偏差，已逐条打开源码复核（reviewer 抽样核验后本次再逐条核对），以 worktree HEAD（a6adf48）为准：

- **已修正（3 条，涉及 5 处引用）**：
  - core/__init__.py `__all__` 白名单 16-30 → **16-31**（右括号 `]` 在 :31，文件共 31 行；§3 表、§3 补充说明、§7.7 共 3 处）；
  - tests/test_agents.py「同种子同序列」100-105 → **100-106**（assert 右括号在 :106；§6.6）；
  - tests/test_dealing.py 偏置路径 69-74 → **69-75**（assert 右括号在 :75；§6.2、§7.5 共 2 处）。
- **保持不变（6 条，复核后确认原引用正确、报告建议值有误）**：
  - pyproject.toml 五个版本锁恰在 **:15-19**（:14 是 `dependencies = [` 行，pygame==2.6.1 在 :15、torch 在 :19）；
  - rules.py `_compare` 恰为 **:160-170**，费用行 `cost = BET_OPTIONS[self.rest_option]` 恰在 **:162**（:173 `finish=True`、:175 `money += all_bet` 亦与原文一致）；
  - tests/test_purity.py 三个测试函数边界 **15-16 / 19-25 / 28-52** 均正确（def 分别在 :15、:19、:28，文件共 63 行）。
