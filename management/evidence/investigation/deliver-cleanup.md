## 交付报告

**分支**：`governance/cleanup-refactor`，commit `5170642`（基线 `6bd6253`）。7 项改动全部完成，零行为风险。

### 逐项改动结果

**1. ui/app.py 键码映射** — `ui/app.py:28-44`（`key_to_action_map()`）+ `:230-238`（`_on_key`）
- 改前（原 :211-214）：`Action(key - pygame.K_1)` 差值映射 + K_f/K_c 两个独立分支
- 改后：显式映射表 `{K_1: BET_10, K_2: BET_20, K_3: BET_50, K_4: BET_100, K_f: FOLD, K_c: COMPARE}`；`_on_key` 统一走 `key_map[key]`
- **Action 真实成员与顺序**（`core/rules.py:31-37`，IntEnum）：`BET_10=0, BET_20=1, BET_50=2, BET_100=3, FOLD=4, COMPARE=5`。0..3 恰好是四个押注档，但我没有假设——逐一核对了 `rules.py:24-37`、`BET_OPTIONS=(10,20,50,100)`、`legal_actions()` 的 `tuple(range(rest_option, 4)) + (FOLD, COMPARE)` 以及 theme.py 的 BUTTON_IMAGES（0-3 押注、4 弃牌、5 看牌），映射与 README 操作说明（1-4 押 10/20/50/100、F 弃牌、C 看牌）一致。端到端验证：dummy 驱动下 post `K_2` 事件 → `history[-1]==(0,1)`（BET_20）、bet 5→25。
- 映射表放在函数里（惰性返回）而非模块级常量，保持 app.py「模块 import 期不 import pygame」的现有风格。

**2. ui/app.py 资源自检** — `ui/app.py:47-51`（`check_assets()`）+ `:291-293`（`main()`）
- 改前：`missing = [name for name in ("background","card_dir") if not Path(const.ROOT/"src").exists()]`（名字与判断对象都对不上）
- 改后：`missing = check_assets()` → `ui.theme.missing_assets()`；缺失时打印 `"[提示] 缺失资源: background, button_0, …（将使用占位绘制）"`（实际运行验证过输出）。

**3. ui/theme.py 注解** — `ui/theme.py:134`
- 改前 `dict[int, "object"]` → 改后 `dict[int, pygame.Rect]`（未加引号，符合任务要求）。依赖 `from __future__ import annotations`（:11）使注解不求值，运行时惰性 `import pygame` 风格不变；因 ruff F821 对注解求名，补了 `if TYPE_CHECKING: import pygame`（:15、:19-20，运行时零开销、零 import 行为变化）。

**4. ui/app.py last_now** — 删掉原类级属性 `last_now: float = 0.0`（原 :141），移入 `__init__`（`ui/app.py:80`，紧跟两个 deadline 之后，`set_now` :168-169 不变）。`tests/test_ui.py` 全绿（含 31 个原有 UI 用例）。

**5. core/__init__.py __all__** — `core/__init__.py:12-30`（import）+ `:32-55`（`__all__` 21 项）
- 补入：`strength_ordinal`、`strongest_hand`、dealing 的 `new_deck`、`deal_uniform`、`deal_strength_biased`、`verify_uniformity`、`EmptyDeckError`。
- **惰性性验证**（全新解释器，两条命令均实际执行）：
  - `python -c "import core; from core import strength; i=strength._ranked_keys.cache_info(); …"` → 输出 `CacheInfo(hits=0, misses=0, maxsize=1, currsize=0)`，LAZY OK
  - 测试 `test_import_core_does_not_build_strength_table` 用 `subprocess([sys.executable, "-c", …])` 在全新解释器里断言 `hits==0 and currsize==0`，通过
  - 基线守护 `tests/test_dealing.py::test_uniform_path_does_not_import_strength_table` 仍绿
  - 原理：`core/strength.py` 模块级只有 import + `BIN_THRESHOLDS`，建表在 `_ranked_keys` 首次**调用**时；新增 import 只是模块级 `from`，不触发任何建表函数。

**6. README.md 三处**（行号已按实际文件核实，与调研记录略有偏移）
- `README.md:29`：图中 `(6 行)` → `薄入口（14 行）`（`awk END` 实测 `draw_me_vs_DQN_Plus.py` 为 14 行）
- `README.md:26-49`：架构图重绘——scripts/ 框上移至顶部入口层，与 draw 入口并排；箭头：draw→ui（列 39）、ui→core（列 29）、ui→agents（列 54）、scripts→core（列 79 下行后水平左折，经 ┼ 交汇点下入 core）、scripts→agents（同路径在 agents 交汇点下入）；**删除了原 core/agents→scripts 的向下箭头**。用 Python 按显示列宽（CJK=2 列）生成并逐行校验了所有框线/箭头列坐标一致（22 行图，24 个框角/箭符列位全部对齐）
- `README.md:63-64`：拆为两行——「`ui/` 无 `time.sleep` ｜ `tests/test_ui.py::TestTicker::test_no_sleep_in_source`」和「`scripts/` 无 `time.sleep` ｜ `tests/baseline/repro_d7_timing.py`（CI 缺陷回归步骤，非 pytest）」。未动 pytest 扫描范围。

**7. 文档/配置同步**
- `pyproject.toml:42`：ruff `extend-exclude` 删除已不存在的 `"备份"`（CHANGELOG 记载 `备份/` 已整目录删除，工作区 `ls -a` 确认不存在）
- `README.md:76`：`src/` 说明改为「美术与音频资源（button/card_pic/character/Font/item_pic/BGM；另有 card_pic备用/、login/ 等未被引用的残留目录）」（grep 确认 const.py 未引用这两个残留目录）
- `CHANGELOG.md`：末尾追加 `[0.2.1]` 记录（版本号为本次清理取的下一修订号，UNKNOWN：主 Agent 是否另有版本计划）

### 新增测试清单（4 条）
| 测试 | 验证 |
|---|---|
| `tests/test_ui.py:68-83` `TestKeyMapping::test_key_map_covers_all_actions_with_unique_keys` | 映射表值集合 == set(Action) 且长度相等（每个 Action 恰好一个键码），并钉死 K_1/K_4/K_f/K_c 具体对应 |
| `tests/test_ui.py:227-239` `test_startup_asset_check_reports_specific_missing` | monkeypatch const 路径到不存在位置，断言自检报出 `background` 与 `button_0..5` 具体资源名 |
| `tests/test_ui.py:242-252` `test_button_rects_return_pygame_rects` | `Layout().button_rects()` 每个值 `isinstance(rect, pygame.Rect)` |
| `tests/test_purity.py:66-85` `test_import_core_does_not_build_strength_table` | 子进程全新解释器 `import core` 后 `_ranked_keys.cache_info()` hits/currsize 均为 0 |

### 实际执行的命令与真实输出
- **基线**（改动前）`python -m pytest tests/ -q`：118 collected，**8 failed, 110 passed**；8 个失败全部为 `FileNotFoundError: dqn_model_1.pth`（test_agents 6 + test_scripts 2），与任务预告一致，未修
- **改动后** `python -m pytest tests/ --tb=no`：**8 failed, 114 passed in 4.92s**（122 = 118+4 新增）；FAILED 清单与基线逐条相同，**无新增失败**
- `python -m ruff check .`：基线 `All checks passed!` → 改动后 `All checks passed!`（中间曾触发 I001/F821，已修复）
- 惰性验证：`CacheInfo(hits=0, misses=0, maxsize=1, currsize=0)` + `core re-exports OK: 6 actions`
- 端到端：K_2 事件 → `history[-1]=(0,1)`、bets `(5,5)→(25,5)`；缺失资源自检打印 `background, button_0..5`

### 遗留项 / 风险
- 禁止改动路径零触碰：`git show --stat` 确认只动了 ui/app.py、ui/theme.py、core/__init__.py、tests/、README.md、CHANGELOG.md、pyproject.toml；core/rules.py、core/strength.py、core/dealing.py、scripts/、agents/ 未动
- `.agent/telemetry-*.json*` 为接管前已存在的运行时改动，未提交（不在授权范围）
- 架构图 scripts→core 用了水平折线（┼ 交汇），语义正确但较原图复杂；docs/ARCHITECTURE.md 中 7.6 节引用的旧行号（:28/:44-48/:63）在本次修正后失效（docs 不在本次授权范围，未改，留给后续）
- 环境里 pytest 最终汇总行经管道时偶发缺失，已用 `--tb=no` 与 `grep` 双重确认计数