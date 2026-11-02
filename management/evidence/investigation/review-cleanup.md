# 独立核验报告 — cleanup-refactor @ 5170642（基线 6bd6253）

核验方式说明：除「读码」外，所有标注 **实测** 的结论均为我在 worktree 内以只读方式运行命令所得；临时脚本均在 `/tmp`，未改动 worktree 任何文件；基线对比 worktree 已 `git worktree remove` 清理（`git worktree list` 已确认）。

## 逐条结论

### 1. 改动范围核对 — **通过**（实测确认）
`git show --stat 5170642` 输出恰为 8 个文件，与 worker 声称完全一致：CHANGELOG.md +19 / README.md 53± / core/__init__.py 31± / pyproject.toml 2± / tests/test_purity.py +21 / tests/test_ui.py +39 / ui/app.py 42± / ui/theme.py 6±。`git show 5170642 -- scripts/ agents/ core/rules.py core/strength.py core/dealing.py` 为空 —— **无越权改动**。工作区未提交文件仅 `.agent/telemetry*`、`PROGRESS.md`（HANDOFF 记载的既有状态，非本 commit 内容）。

### 2. 键码映射 — **通过**（实测确认，无语义变化）
- Action 枚举实测值：BET_10=0, BET_20=1, BET_50=2, BET_100=3, FOLD=4, COMPARE=5（`core/rules.py:24-31`）；`legal_actions()` = `range(rest_option,4)+(FOLD,COMPARE)`（`core/rules.py:89-92`）。
- **实测驱动**（`/tmp/drv_key.py`）：`_on_key(K_2)` → `history[-1]==(0, 1)`、player0 bet **5→25**、`rest_option` 0→1、随后 `human_action(BET_10)` 被拒（降档非法，D2 语义生效）、未映射键 K_5 为 no-op。全部断言通过。
- **反向检查（重要）**：基线代码为 `key in (K_1..K_4): Action(key - pygame.K_1)`（`git show 6bd6253:ui/app.py:211-212`）。实测 pygame 键码 K_1..K_4 = 49,50,51,52（连续），故旧差值映射即 K_1→BET_10、K_2→BET_20、K_3→BET_50、K_4→BET_100，K_f/K_c 分支新旧一致。**新旧语义严格等价，无按键语义变化，不是重大发现。**
- 一致性：`BUTTON_IMAGES`（0:十注…5:看牌）与 `button_labels`（押10…看牌）、README「1/2/3/4 押 10/20/50/100、F 弃牌、C 看牌」三方一致。

### 3. 惰性建表 — **通过**（实测确认）
- `tests/test_dealing.py:86` `test_uniform_path_does_not_import_strength_table` 单独运行：**通过**（cache_clear 后 deal_uniform，hits=0 且 currsize=0）。
- **全新解释器实测**：`import core` 后 `core.strength._ranked_keys.cache_info()` = `CacheInfo(hits=0, misses=0, maxsize=1, currsize=0)`；`core.__all__` 全部符号可解析。
- 读码确认 `core/__init__.py` 模块级只有 import，**无** `table_size`/`beats_probability`/`strength_ordinal`/`strength_bin` 调用；`core/strength.py` 模块级仅 lru_cache 函数定义（真名 `_ranked_keys`）；`core/dealing.py` 模块级仅 import。注：基线 `__init__` 本就模块级 import strength 符号，「惰性」指建表惰性，本改动未破坏。
- **pygame 惰性实测**：`python -c "import ui.theme, sys; print('pygame' in sys.modules)"` → **False**；`import ui.app` 后同样 False。`TYPE_CHECKING` 导入（`ui/theme.py:15,19`）未破坏运行时惰性。

### 4. 资源自检 — **通过**（实测确认）
`ui/app.py:47-51` `check_assets()` → `theme.missing_assets()`；`main()` `:291-293` 缺失时仅 `print("[提示] 缺失资源: …（将使用占位绘制）")` 后继续，**非致命**（读码+实测）。实测：真实仓库 `missing_assets()==[]`；monkeypatch `const.Background/button_directory/card_directory` 指向不存在路径后返回 `['background','card_dir','button_0'..'button_5']`，**具体资源名齐全**，无异常。

### 5. last_now 归位 — **通过**（实测确认）
基线类级属性 `6bd6253:ui/app.py:141` 已删除；新代码仅 `ui/app.py:80`（`__init__` 内）、`:165`（human_action 读）、`:169`（set_now 写）。全仓 grep `last_now` 仅这 3 处，无类级残留。UI 测试全绿（计入 114 passed）。

### 6. button_rects 注解 — **通过**（实测确认）
`ui/theme.py:134` 为 `dict[int, pygame.Rect]`（无引号）；`:11` `from __future__ import annotations` 保证注解不求值。实测调用 `Layout().button_rects((0,1,4))` → keys `[0,1,4]`，返回值全部为真实 `pygame.Rect` 实例（样本 `<rect(425, 660, 150, 75)>`），且该调用不要求模块 import 期 pygame。

### 7. README 三处修正 — **通过**（实测确认，附 1 条观感注记）
1. `wc -l draw_me_vs_DQN_Plus.py` = **14**，README 图中「薄入口（14 行）」正确（原「6 行」确为错误）。
2. **ASCII 图逐列显示宽度实测**（CJK=2/框线=1，`/tmp/check_cols.py`）：五个框边全部严格对齐，无错位（draw 框 col 22-59；scripts 框 62-99；ui 框 22-59 L7-13；core 框 14-47 L17-24；agents 框 50-83 L17-22）。箭头连通性逐列验证：draw→ui（col 40，L4┬→L6│→L7▼）、ui→core（col 30，L13┬→L15┤→L17▼）、ui→agents（col 55，L13┬→L15┼→L17▼）、scripts 下降线 col 80（L5┬→L14│→L15┤）。**入口层置顶、箭头全部向下，无上行箭头**，与实测 import 方向一致（`ui/app.py` import core.*+agents.dqn；`scripts/*` import core.*+agents.*；无反向依赖）。
3. time.sleep 两行：`test_no_sleep_in_source` glob 仅为 `(REPO/"ui").glob("*.py")`（ui/ 行属实）；`repro_d7_timing.py` 扫描 `("ui","scripts")`（覆盖 scripts/），该文件非 `test_*` 前缀不被 pytest 收集，且 `ci.yml:54` 确在 CI repro 步骤中 —— 「非 pytest」表述属实，无 overclaim。

### 8. 测试真实性 — **通过**（读码确认）
4 条新测试均有实质断言，无空测试/skip/恒真：
- 键码：`set(values)==set(Action)` + 长度相等（一一映射）+ 4 个具体键（K_1/K_4/K_f/K_c）钉死；K_2/K_3 由覆盖性断言锁定（我已独立实测 K_2 驱动，风险为零）。
- 惰性建表：**subprocess 新解释器**运行，正确规避同进程污染陷阱。
- 缺失自检：monkeypatch 后断言 `background` + `button_0..5` 具体名。
- button_rects：`isinstance(rect, pygame.Rect)` + 键集合。
5 条相关用例（含既有 dealing 守护）单独运行：5 passed。

### 9. 回归 — **通过**（实测确认）
- worktree（5170642）：`python -m pytest tests/ -v --tb=no` → **`8 failed, 114 passed in 5.33s`**（122 collected）。8 个失败**逐个确认**均为 `FileNotFoundError: dqn_model_1.pth`（`agents/dqn.py:135` 或 torch/serialization），失败用例名：test_agents.py::TestCheckpointDims×3、TestD9LoadedPolicyInEffect×3、test_scripts.py::TestEvaluate×2。**无新增失败、无其它失败原因。**
- 基线复现（/tmp worktree @6bd6253）：**`8 failed, 110 passed in 5.16s`**，失败用例名逐个一致 → 相对基线 +4 恰为新增测试且全过，**无既有测试被打红**。
- `python -m ruff check .` → **All checks passed!**
- pyproject 移除 `extend-exclude` 中的 `备份/`：实测该目录不存在，移除正确。
- 基线 worktree 已清理。

## 必须返工的点
**无。**

## 不影响验收的小问题
1. README 图中 scripts 下降线在 L15 汇入一条横跨 col 30-80 的「汇流横杆」，再经两个 ▼ 到 core/agents。方向可读（与正文「scripts → core/agents」一致），但不如两条独立垂直箭头直观，存在轻微误读空间（agents↔scripts 互联观感）。纯 ASCII 风格问题。
2. agents 框底部仅一个 `┘`（L22），无底边/左下角，框未闭合 —— 视觉瑕疵，对齐与方向均无问题。
3. 键码测试具体钉死 4/6 个键，K_2/K_3 依赖覆盖性断言（已被我的实测补强，零风险）。
4. 环境怪癖（非本次改动引入，已验证基线 `-q` 输出同样缺最终计数行）：本环境 pytest 9.1.1 `-q` 模式最后一行是 FAILED 行而非计数行；`-v` 模式计数行正常。结论不受影响。

## UNKNOWN
无。所有核验点均已实测或读码确认。

**总体结论：通过。** 9 项清单全部通过；键码映射语义等价性与惰性建表两个重点均已独立实测证实；相对基线零回归。