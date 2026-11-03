# r4 基线终审报告：9 条 successCriteria 逐条核验

> **项目**：`game_rendering` · Project `0c68bf5a-2104-498a-9532-7a2f2384f3` · 基线 **r4（ACTIVE）**
> **核验主体**：Main Agent（全程实测），每个 Task 的实现另有独立 reviewer 复核（报告见 `management/evidence/investigation/`）
> **核验时点**：2026-11-03，main = `4e7f13a`（T1~T5 全部合并）
> **方法**：所有结论均来自实际执行的命令，证据以 `文件路径:行号` 或命令输出给出；无法确认的标 UNKNOWN

---

## 0. 结论摘要

| # | successCriteria | 判定 |
|---|---|---|
| 1 | `scripts/train.py` 支持自博弈模式，产出双 checkpoint，summary 含双方胜率与动作分布 | ✅ 通过 |
| 2 | 自博弈消除先手偏置：座位逐局交换；双方奖励零和 | ✅ 通过 |
| 3 | 存在真实权重；UI 默认加载后 `epsilon == 0.0`，动作分布与随机显著不同 | ✅ 通过 |
| 4 | 交互界面仍是人类 vs 机器模式，可完整走完一局 | ✅ 通过 |
| 5 | `scripts/evaluate.py` 支持双 checkpoint 对战评估并输出双方胜率 | ✅ 通过 |
| 6 | 7.7 节 S/M 条目全部完成；7.6 节 README 三处不一致全部修正 | ✅ 通过 |
| 7 | pytest 与 ruff 全绿，无既有测试被打红 | ✅ 通过 |
| 8 | `docs/ARCHITECTURE.md` 已同步更新（训练章节 / 接线变化 / 权重说明） | ✅ 通过 |
| 9 | 「不可碰」清单零改动 | ✅ 通过 |

**9/9 全部通过。** 遗留与风险见 §3。

---

## 1. 逐条核验

### SC1 — 自博弈模式、双 checkpoint、summary 字段 ✅

**实测**：
```sh
python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out /tmp/audit_sc1
```
产出 `dqn_sp_ep100_seed7.pth`、`dqn_sp_opp_ep100_seed7.pth`、`_sync_tmp_seed7.pth`。

`summary_seed7.json` 实测字段：`agent_win_rate` / `opponent_win_rate` / `agent_action_distribution` / `opponent_action_distribution` / `elapsed_sec` / `episodes` 齐备；`episodes=100`，胜率 `0.56` vs `0.44`。

**证据**：`scripts/train.py:44`（`OPPONENT_MODES`）、`:51`（`SELFPLAY_V1`）、`:236`/`:240`（双产物命名）、`:208-233`（summary 字段写入）。

### SC2 — 座位逐局交换 + 严格零和 ✅

**座位交换实测**：同一 `CardGameEnv` 连续 6 局 `reset()`，`agent_player` = `[0,1,0,1,0,1]`，**逐局翻转**。
> 注：`room.whose_turn` 恒从 0 开始是 `core/rules.py:60`「座位 0 恒先手」的既有规则（红线，未改）；两个 DQN 的相对座位由 `agent_player` 翻转实现。

**零和实测**：5 个 seed × 20 局、**119 个环境步**逐步断言 `reward + opponent_reward == 0.0`，**残差非 0 的步数 = 0**（严格零和，IEEE-754 精确相等）。

**证据**：`scripts/env.py:112-121`（座位翻转）、`:172`/`:173`（agent 押注项与对手对消）、`:186`（被动跟注项）、`:187-189`（`net_shaping` 汇总）、`:226-232`（`_settle_rewards` 的 `±all_bet`，**本轮未改**）。
**测试锁定**：`tests/test_selfplay.py`（15 用例）、`tests/test_selfplay_preset.py::TestStepwiseZeroSumWithShaping`（420 步、覆盖 360 个非零塑形押注步，变异测试验证能抓到破坏）。

### SC3 — 真实权重、UI 加载后 epsilon=0.0、与随机显著不同 ✅

**权重实测**：`dqn_model_1.pth` 与 `run/final/dqn_sp_ep100_seed7.pth` 的 sha256 **逐位一致**（`52144d10…`）；`run/final/` 下 3 个产物的 `fc1` 均为 `(128,4)`（默认架构，保证 UI 侧按默认 config 可加载）。

**UI 加载实测**：
```
[信息] 已加载训练权重 .../dqn_model_1.pth（epsilon=0.0 贪心策略）
trained=True  epsilon=0.0
```
（回退路径是 `epsilon=0.15`，两者可区分 —— `Controller.trained` / `Controller.policy_source` 提供可观测性）

**动作分布 vs 随机（2000 个真实状态）**：
| | 分布 | 最大动作占比 |
|---|---|---|
| 训练策略 | `{bet_20: 556, bet_100: 1444}` | **0.722** |
| 随机策略（ε=1.0） | `{0:325, 1:349, 2:330, 3:337, 4:319, 5:340}` | 0.174 |

**显著不同**，且训练策略**随手牌强弱改变动作**：弱牌（p≤0.3）大注占比 0.000、中牌（0.3<p≤0.6）0.7353、强牌（p>0.6）**1.000**（主引用 `docs/selfplay_train_report.md` §5；另有两次独立复测 0.0083/0.8415/1.000 与 0.1491/0.9650/1.000，差异来自盘面随机种子，稳定判据是「最大占比 <0.95」与「分档单调序」）。

**证据**：`ui/app.py:29`（DEFAULT_CHECKPOINT）、`:33`（`resolve_checkpoint`）、`:98-99`（`trained`/`policy_source`）、`:108-119`（`_load_agent` 三行告警 + 回退）、`agents/dqn.py:129`（`from_checkpoint` 的 epsilon 默认 0.0）。

### SC4 — 人类 vs 机器模式，可完整走完一局 ✅

**headless 端到端实测**（`SDL_VIDEODRIVER=dummy`，人类经 `Controller.human_action` 公开入口输入，机器走 `Controller.update` 的 AI 分支）：
```
对局走通: finish=True winner=0 底池=210 步数=2
回合交替: True | 座位序列=[1, 0]
机器 epsilon=0.0 trained=True
```
独立 reviewer 另测 11 步版本：座位序列 `[0,1]×5+0` 严格交替、人类 6 手 / 机器 5 手、winner=1、底池 1020、**资金守恒 19485+20515=40000**。

**证据**：`ui/app.py:188`（`human_action`）、`:250-254`（按键响应）、`:267-268`（键码映射到动作）；`tests/test_trained_ui.py::TestHeadlessEndToEnd`（3 用例）。

### SC5 — 双 checkpoint 对战评估与双方胜率 ✅

**实测**：
```sh
python -m scripts.evaluate --checkpoint … --opponent-checkpoint … --rounds 30 --seed 7
```
→ 双方胜率 `0.5 / 0.5`、`natural_end_rate = 1.0`、`avg_pot = 25`（正常牌局，非撞上限）。

**证据**：`scripts/evaluate.py:35`（`_hidden_of` 隐藏层自适应）、`:49`（`evaluate`）、`natural_end_rate` 字段写入点；`tests/test_scripts.py`。

### SC6 — 7.7 节 S/M 条目 + 7.6 节 README 三处 ✅

**7.7 节 8 条风险逐条处置**（`docs/ARCHITECTURE.md` 7.7 节，每条含 file:line 与处置结论）：

| 条目 | 处置 | 证据 |
|---|---|---|
| 键码差值映射 `Action(key - pygame.K_1)` | **已处置** | `ui/app.py:50` `key_to_action_map()`；`:260` 调用 |
| 资源自检过粗、`missing_assets()` 未用 | **已处置** | `ui/app.py:69` `check_assets()`；`:334` 调用 |
| `button_rects` 注解为 `"object"` | **已处置** | `ui/theme.py:134` → `dict[int, pygame.Rect]` |
| checkpoint 缺失静默回退 | **升级** | `ui/app.py:113-116` 三行醒目告警 + `:98-99` 可观测标志 |
| view 恒含对手真手牌 | 保留 | 本轮未改（信息克制依赖 render 阶段） |
| `last_now` 为类级属性 | **已处置** | `ui/app.py:79` `__init__`、`:104` 实例属性 |
| `_on_click` 在 renderer=None 时 rects 为空 | 保留 | 本轮未改（键盘仍可用） |
| core `__all__` 缺 `strength_ordinal` 等符号 | **已处置** | `core/__init__.py:24-25` import、`:43` `__all__` 条目 |

**7.6 节 README 三处**：
1. **行数**：文档写「6 行」→ 实测 `draw_me_vs_DQN_Plus.py` 为 **14 行**，已修正
2. **架构图箭头方向**：已把 `scripts/` 上移为入口层、箭头方向与实测 import 方向一致（ui→core/agents、scripts→core/agents）
3. **`time.sleep` overclaim**：已拆为 `ui/`（pytest 守护）与 `scripts/`（CI baseline 守护，**非 pytest**）两行 —— reviewer 实测 `test_no_sleep_in_source` 的 glob 仅为 `(REPO/"ui").glob("*.py")`，原声明范围与守护范围不符

**证据**：`docs/ARCHITECTURE.md` 7.6/7.7 节；`README.md:12,18,19,39,59,74,75`。

### SC7 — pytest 与 ruff 全绿，无既有测试被打红 ✅

**实测（main，160 项）**：
```
160 passed in 13.66s
```
**ruff**：`All checks passed!`（含 `management/evidence/` 下的校验脚本）。

**无既有测试被打红 —— 用基线逐条比对**：
| | 基线 `6bd6253` | 现在 |
|---|---|---|
| 失败集合 | 8 个（`TestCheckpointDims`×3、`TestD9LoadedPolicyInEffect`×3、`TestEvaluate`×2） | **完全相同的 8 个** |
| 通过数 | 110 | 160 |

那 8 个失败的根因是 `dqn_model_1.pth` 不存在（被 `.gitignore` 的 `*.pth` 排除、从未入库）—— **权重就位后它们全部转绿**（实测 137→160 全绿）。T1/T2/T3 的每个交付点都做过同样的失败集合 diff，结论一致：**无新增失败**。

**证据**：`management/evidence/logs/train100-pytest.txt`、`t3-pytest.txt`、`.gitignore:17`（`*.pth`）、`:23`（`run/`）。

### SC8 — ARCHITECTURE.md 已同步更新 ✅

**实测**：439 → **578 行**；引用总数 422 → **498**，**越界 0 处**（校验脚本 `management/evidence/arch-ref/check_refs.py`）。

**新增**：`4.4` 自博弈环境 · `4.5` 根因与解法 · `4.6` 训练与评估入口 · `4.7` 机器对手接线 · `4.8` 权重获取与存放 · `6.10/6.11/6.12` 三份新测试清单 · 7.6/7.7 逐条处置标注。

**引用行号有效性**：Main 抽查 **14/14 命中**，reviewer 抽查 **15/15 通过**；129 处因重构失效的旧引用已逐条重定位（108 自动 + 21 锚点/人工），其中 3 处机械匹配误命中的引用由 worker 语义裁决修正，reviewer 复核确认更准确。

### SC9 — 「不可碰」清单零改动 ✅

**逐字节比对**（基线 `6bd6253` vs main）：

| 文件 | sha256（前 16 位） | 结果 |
|---|---|---|
| `core/rules.py` | `e805f711bc11977e` | ✅ 逐字节一致 |
| `core/strength.py` | `5459ad564d6a541f` | ✅ 逐字节一致 |
| `agents/dqn.py` | `57d03552f0ffa36e` | ✅ 逐字节一致 |
| `core/dealing.py` | `388f3d0444bafc12` | ✅ 逐字节一致 |

**其余红线逐条实测**：
- `core/rules.py` 的 Action 枚举仍为 `BET_10=0 … COMPARE=5`（6 个座位无关动作）✅
- 状态编码仍 **4 维输入 / 6 维动作**（`DEFAULT_STATE_DIM=4`、`DEFAULT_ACTION_DIM=6`）✅
- `ui/` 的 snapshot 五字段契约：`money`/`bets`/`all_bet`/`finish`/`winner` 齐全，额外键（`circle`/`folded`/`legal_actions`/`rest_option`/`whose_turn`）符合「只允许新增 view 键」；**snapshot 不含手牌** ✅
- 惰性建表机制：`core/__init__.py` 补齐 `__all__` 但模块级无 `table_size`/`beats_probability`/`strength_ordinal` 调用；`tests/test_dealing.py::test_uniform_path_does_not_import_strength_table` 单独运行通过 ✅
- `from_checkpoint` 维度自适应：`agents/dqn.py` 逐字节未变 ✅
- 无新增/升级/删除第三方依赖（`pyproject.toml` 仅移除已不存在的「备份」排除项）✅
- 无删除/重命名/移动既有源码文件 ✅
- `.pth` 未纳入版本库、`.gitignore` 对权重的处理未改 ✅
- 训练局数 **100 局**（上限内，未触发人工审批）✅
- 委派深度固定 1、`maxConcurrent=3` ✅
- 合并到 main 由**人工执行**（`integrateBranch=false`，Main 未自行合并）✅

---

## 2. 目标达成情况（r4 goal 原文）

> 「按 docs/ARCHITECTURE.md 第 7 节完成 S/M 级重构与 README 三处不一致修正；实现 DQN 对抗 DQN 自博弈训练，用训练产出的真实权重驱动交互界面的机器对手（保持人类 vs 机器模式），消除当前因权重缺失而静默回退为随机策略的问题。」

| 分句 | 达成 |
|---|---|
| 第 7 节 S/M 级重构 | ✅ 8 条全部处置（SC6） |
| README 三处不一致修正 | ✅ 3 处全部修正（SC6） |
| DQN 对抗 DQN 自博弈训练 | ✅ 100 局 CPU 自博弈，产出双 checkpoint（SC1/SC2） |
| 用真实权重驱动 UI 机器对手 | ✅ `epsilon=0.0`、`trained=True`（SC3） |
| 保持人类 vs 机器模式 | ✅ headless 端到端走通（SC4） |
| 消除静默回退为随机策略 | ✅ 回退改为三行醒目告警 + 可观测标志（SC3/SC6） |

---

## 3. 遗留与风险

### 3.1 需要人工处理

| # | 事项 | 说明 |
|---|---|---|
| R1 | **权重不在版本库** | `.gitignore` 排除 `*.pth` 与 `run/`。新环境需 `python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out run/final` 重训（约 1 秒），或拷贝 `run/final/dqn_sp_ep100_seed7.pth` 为仓库根 `dqn_model_1.pth` |
| R2 | **合并到 main 需人工执行** | 治理基线 `integrateBranch=false`。本报告出具时 main 已由用户授权合并至 `4e7f13a`；后续如再合并需重新授权 |

### 3.2 已知技术债（不阻塞本轮验收）

| # | 事项 | 影响 |
|---|---|---|
| T1 | `view` 恒含对手真手牌，信息克制依赖 render 阶段 | 耦合偏隐式，本轮未改 |
| T2 | `_on_click` 在 `renderer=None` 时 rects 为空，鼠标失效（键盘可用） | headless 场景不影响 |
| T3 | `_load_agent` 的 except 元组非穷举白名单（现覆盖 `FileNotFoundError`/`ValueError`/`RuntimeError`/`pickle.PickleError`） | 罕见异常类型仍会崩溃 |
| T4 | 策略强度未优化 | 本轮明确不追求（r4 outOfScope）。当前 ε=0 贪心下强牌大注占比 1.000、弱牌 0.000，**单调但未精细** |
| T5 | `run/` 下仍有历史实验目录 | gitignored，不入库；`run/final/` 为唯一权威产物目录 |

### 3.3 治理侧遗留

- `final-audit` Task 本身既未取消也未验收（其唯一的 Run 被取消）；已由 `arch-ref-fix` + `arch-doc-update` 两个 Task 接替，实际工作已完成并验收。
- `dqn-vs-dqn-investigation` Task 已批准未验收（其产出为只读调查报告，无代码交付）。
- 委派复盘见 `management/DELEGATION-RETROSPECTIVE.md`：30 次运行的量化分析与下次派发的操作规则。

---

## 4. 核验方法与可复算性

本报告每个数字均可复算：

| 指标 | 复算命令 |
|---|---|
| 训练产物与 summary | `python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out /tmp/x` |
| 双 checkpoint 评估 | `python -m scripts.evaluate --checkpoint … --opponent-checkpoint … --rounds 30 --seed 7` |
| 塌缩现象复现 | `python -m scripts.train --episodes 100 --seed 7 --opponent-mode self --strength-shaping 0 --out /tmp/c` + evaluate |
| 文档引用有效性 | `python management/evidence/arch-ref/check_refs.py` |
| 测试与 lint | `python -m pytest tests/ -v --tb=no` / `python -m ruff check .` |
| 红线零改动 | `git diff --stat 6bd6253..HEAD -- core/rules.py core/strength.py agents/dqn.py core/dealing.py`（输出为空）+ 逐文件 sha256 |

---

*本报告由 Main Agent 出具，全部结论基于实际执行的命令与逐字节比对。实现部分另有 5 份独立 reviewer 报告（`management/evidence/investigation/review-*.md`）。*
