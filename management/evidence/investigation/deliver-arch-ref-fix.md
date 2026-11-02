## 交付报告（T5a：ARCHITECTURE.md file:line 引用校正）

**提交**：`7f59339`（governance/arch-ref-fix），仅改 `docs/ARCHITECTURE.md`（88 行，129 处引用），未碰源码。

### 1. 校正数量
- **129/129 全部应用**：108 条自动定位（exact 99 / contains 6 / anchor 6 / exact-multi 3）+ 15 条 manual-verified，另 **计划外修正 1 处**：`ci.yml:84-97→84-96`（docs/ARCHITECTURE.md:147；清单未覆盖——脚本把裸名 ci.yml 判为"文件缺失"而非越界，实际 `.github/workflows/ci.yml` 共 96 行，可复现性验证 step 在 84-96）。
- **未采用清单方案、改为定点核对结果（3 处，均为 exact-multi/anchor 误匹配）**：
  - doc 164 `app.py:80-85`：清单→155（update 循环内另一处同文），实际时限设置块 = **ui/app.py:137-142**（ui/app.py:137-142）
  - doc 164 `app.py:97`：清单→161，实际 `_ai_move()` 后的 `self._schedule(now)` = **ui/app.py:154**（161 对应旧 104 的 human 分支）
  - doc 380 `ui/app.py:212`：清单→188（anchor 误中 `human_action` 方法体），实际键码映射处理 = **ui/app.py:267-268**（`key_map = key_to_action_map()` 用法）

### 2. 范围型引用（79 条）扩展/收窄
| 类型 | 台数 | 明细（依据：旧版 git blob 与新文件逐行比对） |
|---|---|---|
| 收窄 | 2 | `evaluate.py:18-20`→`22-23`（4 处 doc 34/92/153/416：T2 删 `from core.rules import Action` 行，3→2）；`app.py:202-216`→`257-268`（doc 121：15→12 行，FOLD/COMPARE/K1-K4 分支被 key_map 合并） |
| 扩展 | 3 | `__init__.py:16-31`/`core/__init__.py:16-31`→`32-54`（doc 101/387：16→23 行，`__all__` 新增 8 符号）；`scripts/evaluate.py:96-99`→`138-146`（doc 153：4→9 行，argparse 块中间插入 `--opponent-checkpoint`，`--out` 移至 146）；`ui/app.py:212` 单行→`267-268` 两行 |
| 拆分 | 3 | `README.md:44-48`→`README.md:39,59`（doc 72/374/416，按清单 new_ref；入口层行 39 + dealing.py 行 59，README.md:39、README.md:59） |
| 平移保持宽度 | 71 | 如 `scripts/env.py:13-17`→`25-29`（4 处）、`train.py:23-24`→`38-39`（4 处）、`train.py:114-117`→`254-257`、`app.py:98-99`→`155-156`、tests/test_ui.py 30 处整体平移 ~17 行 |

### 3. 校验
- `check_refs.py`（原脚本 REPO 硬编码主仓，我跑了指向本 worktree 的同逻辑副本）：**总引用 422 | 越界 0 处 | 文件缺失 207 处**。207 处全部是脚本 resolver 不认裸文件名（`rules.py`、`test_rules.py`、`ci.yml` 等）的假阳性（修复前基线为 289 处，同性质）。
- 增强校验（裸名按仓库内唯一同名文件解析）：**422/422 处行号全部在文件范围内，OOB 0**。
- 遗留 3 处裸名无法唯一解析（脚本与增强校验均无法判定，行号本身在候选文件范围内）：doc 62/78 `__init__.py:11-14`（按文档自身惯例指 core/__init__.py，54 行内）、doc 423 `r5/PLAN.md:33`（治理草稿，任务明确可保留，文件 61 行）。

### 4. 抽查验证
- 129/129 条均用脚本做过内容级验证（旧版行 vs 新版新行号行逐行比对，非只核对行号）；其中 **exact-multi 3 + contains 6 + anchor 6 + manual-verified 15 共 30 条逐条人工 sed 定点核对**，17 条 range 部分匹配逐条人工裁决（即上表与 §1 的修正）。

### 5. 过程缺陷（已修复）
- 首轮批量应用把 13 条 manual-verified 引用的文件前缀丢掉了（清单 `new_ref` 字段只含行号部分，需与 `new_file` 拼接，我在 doc 153 还有 2 处同型遗漏）。已全部修复并复检：129 处新引用逐条确认在位、旧引用无残留、总引用数 422 与基线一致。

### 6. 未确认 / 风险
- **UNKNOWN**：无（行号层面 129/129 确认 + ci.yml 1 处）。
- 发现 3 处**内容级**过期（只改行号，未动措辞，超出本任务范围）：doc 426 称 pyproject.toml:42 extend-exclude 含「备份」目录，现该条目已不在文件中（行号 42 仍正确）；doc 381 称 `missing_assets()` 未被使用（现为 check_assets，ui/app.py:332-335）；doc 382 称 button_rects 注解为 `"object"`（现 ui/theme.py:134 已是 `pygame.Rect`）。建议 T6 或后续任务处理。
- `README.md:39,59` 这种逗号双行引用是清单给定的写法，check_refs 只解析其首段（README.md:39，在范围内）。