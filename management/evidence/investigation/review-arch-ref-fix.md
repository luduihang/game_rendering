# T5a 轻量复核报告：ARCHITECTURE.md 129 处行号引用校正

## 1. 改动范围 — ✅ 通过
`git diff --stat c30b4f9..7f59339`：仅 `docs/ARCHITECTURE.md`，88 增 88 删，无其他文件。工作区另有 3 个未提交无关文件（`.agent/*`、`PROGRESS.md`），不在提交内。

## 2. 引用整体有效性 — ✅ 通过（附工具缺陷提示）
按任务规范（裸文件名→仓库内唯一同名解析；多候选→UNRESOLVED）自写脚本，REPO=worktree：
- **总引用 422**（与期望一致；比官方正则多匹配 2 条 `.github/workflows/ci.yml`，与官方口径一致后恰好 422）
- **行号越界 0** ✅
- **文件缺失 1**：`r5/PLAN.md:33`（已知例外）✅
- **UNRESOLVED 23**：`__init__.py`×2（已知例外）+ `README.md`×19。19 处 README 均按上下文语义指向**根 README.md**，抽查 12/30/39/59/63/71-75/86/96-97 行内容全部吻合（启动命令、架构图、分层约束表、mymath 目录说明），判定解析成立。

⚠️ **工具缺陷**：`management/evidence/retrospective/check_refs.py` 把 `REPO` 硬编码为主仓路径，在 worktree 里跑出来的是"缺失 289"的假结果（它在检查主仓的旧文档）。worker 无法用该脚本在 worktree 复现"越界 0"，此脚本需参数化后重跑留证。

## 3. 20 条高风险抽样 — ⚠️ 部分通过（16 过 / 4 不过）
**4 条不通过**（行号均在范围内，错在**语义与代码不符**）：
- **doc 153**：`imports 仅 core/agents（evaluate.py:22-23），其中 23 → core.rules.Action` —— 23 行实为 `from scripts.env import ...`，且 evaluate.py 全文无 core.rules import。逐行归属错。
- **doc 426**：`pyproject.toml:42 extend-exclude 含「备份」目录` —— 现 42 行为 `["__pycache__",".venv","src"]`，全文件已无「备份」，条目整体过时。
- **doc 385**：`last_now 为类级属性（未写于 __init__）…（ui/app.py:104）` —— 104 行 `self.last_now: float = 0.0` 恰在 `__init__`（def 于 79 行）之内，表述与代码矛盾；`set_now` 198-199 本身正确。
- **doc 380**：行号 267-268 正确（key→action 映射分支），但"键码差值映射 `Action(key - pygame.K_1)`"机制在代码中已不存在（现用 `key_to_action_map()`，53 行 docstring 明示弃用差值）。

**3 处「未采用清单方案」裁决**：
1. doc 164 → `137-142`：**worker 对**。137-142 恰为按回合方设 deadline 的 if/else 块；清单的 155 是后续判断行。`_schedule` 函数本身 = 131-142 整函数，文档引用精确。
2. doc 164 → `154`：**worker 对**。154 是 AI 回合分支内 `_schedule(now)` 调用；清单的 161 是 auto_human 分支的另一处调用。文档语境为 AI 回合链（150-151/152/154/155-156/158-159/160 我逐一核对全部吻合）。
3. doc 380 → `267-268`：**行号裁决 worker 对**（清单 188 是 `def human_action` 方法定义，267-268 才是键码映射实际位置），但条目表述陈旧（见上 FAIL-D）。

## 必须返工项
1. **doc 153**：修正"23 → core.rules.Action"的逐行归属（23 实为 scripts.env）。
2. **doc 426**：「备份」已不在 extend-exclude，条目应改写或删除。
3. **doc 385**：last_now 条目表述与代码矛盾，应改写或删除。
4. **doc 380**（轻微）：键码差值机制已不存在，建议按合同第 1 条"改写为不依赖具体行号的表述"处理。

（以上 4 条中 2、3、4 属合同允许的"无法确认→改写"情形，worker 未改写也未在报告中列明。）

## 风险与遗留
- `check_refs.py` REPO 硬编码，验收证据"重跑校验脚本"无法在 worktree 复现，需修脚本后补跑。
- 非引用类遗留（超出本合同"行号校正"范围，不判返工）：doc 92 散文"19 (→ rules.Action)"所指 19 行为空行；doc 34 行数描述"env 158 / evaluate 108"与实际 337/160 行不符（baseline 原有）。
- 抽样覆盖 20/129（高风险 15 条全覆盖 + manual-verified 5/15），exact 类 99 条未抽。

**总体结论：部分通过** —— 范围与行号有效性达标，但 4 处"行号正确而表述失真"需返工修正。