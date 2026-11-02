Investigation complete — all claims verified against source. Writing the final report.

## 调查目标

按 ARCHITECTURE.md 第 7/8 节对 game_rendering 做只读核对，产出带实际 file:line 的重构清单（调研 F）。本角色无 bash 工具，无法执行 `git status`；已读 `.git/HEAD` 确认分支 main；contract 授权 writeWorkspace=false，本次零写入。

## 涉及文件（含行数）

| 文件 | 行数 | 文件 | 行数 |
|---|---|---|---|
| ui/app.py | 283 | core/__init__.py | 31 |
| ui/render.py | 253 | core/rules.py | 175 |
| ui/theme.py | 165（report-C1 记 170，有出入，以实读为准） | core/strength.py | 58 |
| ui/clock.py | 88 | core/dealing.py | 68 |
| const.py | 82 | scripts/train.py | 122 |
| scripts/env.py | 158 | scripts/evaluate.py | 107 |
| README.md | 108 | pyproject.toml | 49 |
| .github/workflows/ci.yml | 96 | tests/test_ui.py | 303 |
| tests/test_rules.py | 155 | tests/test_dealing.py | 101 |
| tests/test_agents.py | 219 | tests/test_strength.py | 80 |
| tests/test_scripts.py | 125 | tests/test_purity.py | 63 |
| tests/baseline/repro_d7_timing.py | 112 | docs/ARCHITECTURE.md | 445（调查依据） |

## 第 7.7 节 10 个小问题逐条清单

| # | 问题 | 实际位置 | 最小改法 | 打红测试 | 级 |
|---|---|---|---|---|---|
| 1 | 键码差值映射 | ui/app.py:211-212 | 改显式映射 | 无 | M |
| 2 | 资源自检过粗 | ui/app.py:269-271；theme.py:77-90 未被使用 | main() 改用 missing_assets() | 无（main 无覆盖） | M |
| 3 | button_rects 注解 | ui/theme.py:130 | `dict[int,"pygame.Rect"]` | 无 | S |
| 4 | checkpoint 回退未文档化 | ui/app.py:25、57-62；.gitignore:18 | 文档注明 | 无 | S |
| 5 | view 恒含对手真手牌 | ui/app.py:155（文档写 156，实为 155）、169；ui/render.py:159-170、178-180 | 文档化 S / 结构重构 L | render 系测试 | S/L |
| 6 | last_now 类属性 | ui/app.py:141、143-144、138 | 移入 __init__ | 无 | S |
| 7 | _on_click renderer=None | ui/app.py:222 | 文档化 / App 持 Layout | 无 | S/M |
| 8 | core __all__ 缺符号 | core/__init__.py:14-15、16-31 | 补 8 个符号 | 无（保持惰性） | M |
| 9 | theme 路径/'../' 现状 | const.py:16-17、20-25；const.py:4-5、19；theme.py:44-53 | 坏路径已清除，无需改 | 无 | 已完成/S |
| 10 | 其它可动项 | pyproject.toml:42；README.md:73 | 删"备份"、补 README | 无 | S×2 |

**详细条目**

1. **键码映射**：`ui/app.py:212` `self.controller.human_action(int(Action(key - pygame.K_1)))`，前置 `elif key in (pygame.K_1…K_4)`（:211）。四键在标准布局下连续故不致崩溃，但小键盘/特殊布局下语义不可靠。改法：`_on_key`（app.py:202-216）内改 `self.controller.human_action({pygame.K_1: Action.BET_10, pygame.K_2: Action.BET_20, pygame.K_3: Action.BET_50, pygame.K_4: Action.BET_100}[key])`。无测试守护（tests/test_ui.py 仅有 K_r 用例 :110-121，无 1/2/3/4 模拟）。M。
2. **资源自检**：`ui/app.py:269` 两个名字查同一条件 `Path(const.ROOT/"src").exists()`，:270-271 打印。`theme.missing_assets()`（ui/theme.py:77-90，查 6 关键资源+6 按钮+2 头像）现仅被 test_ui.py:204-208、300-303 使用。改法：main()（app.py:257 起）在 :261 旁 `from ui.theme import missing_assets`，:269-271 替换为 `missing = missing_assets(); if missing: print(f"[提示] 缺失资源: {missing}（将使用占位绘制）")`。无测试覆盖 main()。M。
3. **注解**：`ui/theme.py:130` `def button_rects(self, legal_actions) -> dict[int, "object"]:`，方法体内已 `import pygame`（:132）。改注解为 `dict[int, "pygame.Rect"]`（字符串前向引用避免模块级 import pygame）。无测试读注解。S。
4. **checkpoint 回退**：`ui/app.py:25` `DEFAULT_CHECKPOINT = REPO/"dqn_model_1.pth"`；:57-62 `_load_agent` 捕获 (FileNotFoundError, ValueError, RuntimeError) 后 print 并回退 `DQNAgent(4, 6, epsilon=0.15)`（:62）。该 .pth 被 `.gitignore:18`（`*.pth`）排除，未入 git（.git/index 无此文件名），本工作区不存在 → 当前每次启动必走回退。改法：app.py 模块 docstring（:1-8）与 README「快速开始」注明"权重不随仓库分发，缺失时回退未训练策略；可先 `python -m scripts.train` 并复制产物"。S（纯文档）。
5. **信息克制隐式**：view 恒含 `"opponent_hand"`（app.py:155）与 `opponent_rank`（app.py:169，finish 前为 None）；render 靠 `render.py:160-162`（未结算只画背面）与 :167-170（结算露真牌）、:178-180（结算才显示牌型）克制。最小改法 A：view() 加 docstring 声明该隐式契约（S，无测试）。改法 B（结构）：finish 前 view 不暴露真手牌，需同步改 render.py:159-170 与 app.py:169——会触及 test_ui.py:191-202（dummy 驱动绘制）、:260-280（缺图回退绘制）的输入语义，须先补「finish 前 view 不含对手真牌」测试。L，建议本次只做 A。
6. **last_now**：类属性 `ui/app.py:141` `last_now: float = 0.0`；`set_now` :143-144 覆盖为实例属性；消费点 :138（human_action→_schedule）与 :232（step_frame→set_now）。改法：`__init__`（app.py:40-54）加 `self.last_now = 0.0`，删 :141。无测试直接调 human_action（grep tests/ 无命中）。S。
7. **_on_click**：`ui/app.py:222` `rects = self.renderer.layout.button_rects(...) if self.renderer else {}`，renderer=None 时鼠标输入静默失效（键盘可用）。改法 A：文档注明（S）；改法 B：App（app.py:176 起 __init__）持有独立 `Layout` 供 _on_click 使用（M，需新增构造参数默认值以不破坏 test_ui.py:35-38 make_app）。无测试守护。
8. **core __all__**：`core/__init__.py:14` 仅导入 `beats_probability, strength_bin, table_size`；:16-31 白名单 14 名，缺 `strength_ordinal`、`strongest_hand`（strength.py:40、57 定义）与 dealing 符号（new_deck/deal_uniform/deal_strength_biased/EmptyDeckError/verify_uniformity，dealing.py:27/34/41/23/64）。改法：:13 后加 `from core.dealing import EmptyDeckError, deal_strength_biased, deal_uniform, new_deck, verify_uniformity`，:14 补 `strength_ordinal, strongest_hand`，__all__ 追加 8 名。惰性建表不被触发（import 不建表，strength.py:24-27），test_purity.py:28-52（逐个 import 子模块）与 test_dealing.py:86-95（currsize==0）保持绿。M（单文件）。
9. **路径解析/'../' 现状**：坏路径已清除——const.py:16-17（ROOT/SRC 包根）、:20-25（六个资源目录全相对 SRC），docstring :4-5 与注释 :19 自述；全仓 `.py` grep `\.\./` 仅命中 const.py:4-5（docstring）与 tests/baseline/repro_d2_rest_option.py:5（注释）。theme.py:44-53 `asset_paths()` 消费 const.*，`Path(const.X)` 二次包裹冗余（const 已是 Path）可顺手简化（S，纯外观）。**残留问题即第 2 条**（app.py:269 粗检）。test_ui.py:185-189 守护 const 绝对路径且无 "myclient"。
10. **其它可动项**（7.7/8 可落地）：(a) pyproject.toml:42 `extend-exclude = ["备份", ...]` 中"备份"目录不存在（根目录 ls 无）→ 从列表删除（S）；(b) README.md:73 目录说明漏 mymath/ 非代码文件「概率大小映射」（ls mymath/ 确认存在，共 4 项）→ 行尾补注（S）；(c) 次要观察：src/ 下存在 `card_pic备用/`、`login/` 残留资源目录（ls src/），const.py:9 已声明登录页布局移除但素材未清——建议单独立项清理，本次不动（涉及 test_ui.py:204-208 资源集合断言，勿顺手删）。

## 第 7.1-7.6 节高风险项判定表

| 节 | 判定 | 守护测试（file:line） | 说明 |
|---|---|---|---|
| 7.1 snapshot/view 契约 | **不可碰**（改既有键/字段必红）；仅"新增 view 键"安全 | test_ui.py:124-135（五字段逐字段）、:137-140（min_bet）；test_rules.py:141-146；test_ui.py:191-202、:282-293（渲染/布局消费） | snapshot rules.py:107-121 是唯一数据源；render 不算状态（render.py:243 winner 取自 view） |
| 7.2 D1-D9 回归 | **避开**（触及对应路径必红） | D1 test_rules.py:25-64+baseline/repro_d1；D2 test_rules.py:68-85；D4 test_rules.py:96-103、test_scripts.py:28-43；D5 test_rules.py:133-139；D6 test_dealing.py:56-66、:86-95；D7 test_ui.py:40-65、:69-121、:152-173+algorithm.py:51-54、:59、:71-78；D8 test_agents.py:27-50、:193-219；D9 test_agents.py:54-84、test_scripts.py:95-100、ci.yml:60-82（epsilon==0.0 在 :80） | 7.7 各条均不触碰上述路径（第 8 条仅动 __init__ 导入，不触 D 路径） |
| 7.3 22100 惰性建表 | **不可碰**（挪 import 期/去 lru_cache/均匀路径查强度必红） | test_strength.py:19-20（==22100）、:64-72（<100µs）、:75-80（一次性）；test_dealing.py:86-95（currsize==0） | 建表 strength.py:24-27 惰性；查询 bisect :37、:45；strongest_hand :57-58 不走缓存 |
| 7.4 from_checkpoint 自适应 | **不可碰**（恢复调用方声明维度=D8 回归） | test_agents.py:27-30（(4,6) 推断）、:32-37（fc1.in_features==4）、:39-46（9 维加载必 RuntimeError）、:48-50（FileNotFoundError）、:193-219（import 零触盘） | dqn.py:62-67 推断、:124-150 构建加载；DQN-vs-DQN 新 4×6 权重可直接加载，**无需改此机制** |
| 7.5 D6 均匀默认+偏置开关 | **不可碰**（偏置设为默认必红）；复用开关安全 | test_dealing.py:56-66（均匀分布）、:69-75（偏置强>0.15）、:78-83（弃 9 张）、:86-95 | 默认 new_deck+deal_uniform（dealing.py:27-38）；开关为 `deal_strength_biased`（dealing.py:41-61，非文档旧名 draw_strength_biased，全仓零匹配） |
| 7.6 README 不一致 | **可安全做**（无测试读 README；test_ui.py:177-183 只守护入口文件文本） | 无 | 三处修法见下节 |

## 第 8 节遗留疑点处置建议

| 疑点 | 本次是否值得查清 | 结论/路径 |
|---|---|---|
| git status（3 处） | 不值得 | 只读角色无 bash，维持 UNKNOWN；分支 main（.git/HEAD）；本次零写入不受影响 |
| pygame/numpy 版本 | 已解决 | pyproject.toml:15-19：pygame==2.6.1、numpy>=2.3,<2.4、scipy>=1.17,<1.18、matplotlib>=3.11,<3.12、torch>=2.13,<2.14 |
| src/ 总大小 | 不值得 | 无 du 工具，UNKNOWN 维持；ls src/ 确认 7 个子目录（含 card_pic备用/、login/ 残留） |
| D3 编号缺失原因 | 低价值 | 已确认"缺失"事实：tests/baseline/ 仅 d1/d2/d4/d5/d6/d7 六脚本；ci.yml:53-54 循环无 D3；README.md:97-107 缺陷表无 D3 行。缺失原因仍 UNKNOWN（仓库无历史记载），建议查 management/legacy 各期 PRD/PLAN，不阻塞本次重构 |
| README.md:18 cu130 URL 可用性 | 不值得 | 无网络，UNKNOWN 维持；可顺手在 README 注明"需对应该 CUDA 版本的网络源" |
| train.py→env.CardGameEnv 调用边（§4.2 UNKNOWN） | **已解决** | train.py:24 `from scripts.env import CardGameEnv, to_transition`；train.py:53 `env = CardGameEnv(seed=seed)`（train() 函数体内，:38 起） |
| 8.2 报告截断 | 已规避 | 本报告全部行号直接实读源码复核，未依赖截断报告数值 |

## README 3 处不一致的修法

1. **行数**（README.md:28）：`draw_me_vs_DQN_Plus.py (6 行)` → `(14 行)`。实读 14 行：docstring 9 行 + `from ui.app import main`（:11）+ `if __name__` 守卫 2 行（:13-14）+ 空行 2。
2. **架构图箭头**（README.md:44-48）：图中 core/、agents/ 的框底用 `┬/▼` 向下指向 scripts/（:46-48 `┌───────────▼────────────────────▼──────────┐`），与 :52 文字"ui → core/agents，scripts → core/agents"及实际 import（scripts/env.py:13-17、train.py:23-24、evaluate.py:18-20）矛盾。修法：把 scripts/ 框（:48-50）整体上移至顶部入口层，与 draw_me_vs_DQN_Plus.py（:27-29）并排，箭头由 scripts 框底向下指向 core/ 与 agents/；删除 :44-48 中 core/agents 指向 scripts 的两条下箭头；:52 文字保持不变。ui→core/agents 的箭头（:37-43）本就正确（ui/app.py:21-24 同时 import agents 与 core，图已有 ui→agents 支）。
3. **sleep 声明 overclaim**（README.md:63）：pytest 守护实际只扫 ui/（tests/test_ui.py:63-65 `(REPO/"ui").glob("*.py")`）；但 baseline 脚本确扫 ui+scripts（tests/baseline/repro_d7_timing.py:36-41，CI 步骤 ci.yml:50-58 执行，非 pytest）。推荐改法（不 overclaim 且不失守护）：表格行改为两行——"`ui/` 无 time.sleep ｜ tests/test_ui.py::TestTicker::test_no_sleep_in_source" 与 "`scripts/` 无 time.sleep ｜ tests/baseline/repro_d7_timing.py（CI 缺陷回归步骤，非 pytest）"。备选：把 test_ui.py:64 的 glob 扩到 ui+scripts 两目录（已 grep 确认 scripts/ 当前零 sleep：train.py:16 仅用 time.perf_counter），使单一守护覆盖声明，但属测试改动需随 PR 说明。

## 重构可行性总评（S/M/L 计数 + 前置条件）

- **S（约 9 条）**：7.7-3 注解、7.7-4 回退文档、7.7-5 文档版、7.7-6 last_now、7.7-7 文档版、7.7-9（已完成/Path 冗余可选）、7.7-10a pyproject"备份"、7.7-10b README:73、7.6 README 三处（:28/:44-48/:63）。全部无测试依赖，可并行一次合入。
- **M（3 条）**：7.7-1 键码映射（app.py:202-216）、7.7-2 资源自检（app.py:261,269-271）、7.7-8 core __all__（core/__init__.py:14-31）。7.7-7 若选 Layout 方案亦 M。三者互不冲突。
- **L（1 条，缓办）**：7.7-5 结构版（view 隐藏对手手牌，app.py:150-171 + render.py:159-180）。
- **必须先补测试**：仅 7.7-5 结构版（先加"finish 前 view 无对手真手牌"断言）。S/M 各条均"无现有测试守护"，属低风险顺手项，建议随改动补一条回归（如 key 映射表、missing_assets 接入 main 的 mock 打印）但不强制。
- **依赖 DQN-vs-DQN 训练结果**：10 条中无直接依赖。两个交点：(a) **前置风险**——`dqn_model_1.pth` 不在仓库（.gitignore:18、.git/index 无、工作区 ls 无、全仓 find 无 *.pth），fresh clone 下 D8/D9 守护（test_agents.py:27-84）与 evaluate 冒烟（test_scripts.py:88-100）将 FileNotFoundError 报错，CI（ci.yml:48 pytest 在 :63 训练步骤之前）在干净检出上应为红——**重构开工前需先经 scripts.train 生成权重放置仓库根（或调整该组测试/CI 顺序），否则无法验证"改动不打红现有测试"**；(b) 自博弈产出的 4×6 权重（状态空间 dqn.py:29-31 不变）可经 from_checkpoint（dqn.py:124-150）直接加载，DEFAULT_CHECKPOINT（app.py:25）与回退（app.py:57-62）保持不动即可接入。
- **不可碰**：7.1 契约、7.2 全部 D 路径、7.3 建表时机、7.4 维度自适应、7.5 均匀默认。

## UNKNOWN 清单

1. git 工作区实时状态（无 bash 工具；分支 main 已核 .git/HEAD）。
2. src/ 总大小（无 du/stat）。
3. D3 缺陷编号缺失的历史原因（仅确认缺失事实：tests/baseline/、ci.yml:53-54、README.md:97-107）。
4. README.md:18 cu130 torch index URL 网络可用性。
5. CI 在干净检出的实际红绿状态（无法执行 CI；依据文件缺失证据推断 pytest 阶段会报错，未实测）。
6. ui/theme.py 行数 165（实读）与 report-C1 记载 170 存在 5 行出入，原因未明（不影响本报告行号，全部以实读 grep 为准）。
7. ARCHITECTURE.md:7.7 记"view 恒含对手真手牌（ui/app.py:156）"实为 :155；7.6 其余行号经复核一致（app.py:212/25/57-62/141/143-144/222/269-271，theme.py:77-90/130，core/__init__.py:16-31 均确认）。