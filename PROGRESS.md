# Progress

> Rolling session summaries, newest first.



<!-- session-in-progress:start=2026-10-21T09:09:58.050Z -->
## 2026-10-21 17:57 — P2 完成（commit `4696aa8`）。当前进度汇总：

## 已完成

| 阶段 | 提交 | 内容 |
|---|---|---|
| **P0**... _(in progress)_
P2 完成（commit `4696aa8`）。当前进度汇总：

## 已完成

| 阶段 | 提交 | 内容 |
|---|---|---|
| **P0** | `97a2737` | 环境修复 + 基线报告 + 6 个缺陷复现脚本 |
| **P1** | `38c427d` `b3272e8` | 卫生改造 + **单一策略清理**（删 16 文件 + `备份/`，仓库 284M→106M） |
| **P2** | `4696aa8` | **core/ 核心包 + D1/D2/D4/D6 修复** |

## P2 关键成果

**新增 `core/`（纯逻辑，零重依赖）**
`cards.py` · `evaluator.py` · `strength.py` · `dealing.py` · `rules.py`

**先红后绿证据（同一脚本，修复前后对比）**

| 缺陷 | 修复前 | 修复后 |
|---|---|---|
| **D1** 看牌结算 | `passed=0 bug=4` | **`passed=4 bug=0`** |
| **D2** r...
<!-- end-session-in-progress -->
## 2026-10-21 17:08 — Line 6 is empty — so it's 5 real events plus a trailing newline, exactly as befo...
Line 6 is empty — so it's 5 real events plus a trailing newline, exactly as before. No corruption, no stale lock. Your data is clean.

## 可以复原，而且复原是对的

垃圾桶的元数据完好（`Path=/home/kipley/Documents/code/learning/game_exercise`），账本 5 条事件完好，`writer.lock` 不存在。但**直接 `gio trash --restore` 会失败或产生嵌套目录**，因为目标路径已被那个不完整的树占着（里面有 `draw.py` `const.py` `mymath/` `src/`，但没 `.git`）。

Trash 复原遇到同名目录，Nautilus/gio 通常会拒绝，或者建出 `game_exercise.2` 之类的嵌套。所以需要一个「先腾位、再复原、后合并」的流程。

## 关键判断：哪个版本的代码是你要的

这是整个回合唯一真正的风险点，请务必先回答。

...
## 2026-10-21 15:14 — 草稿已记录为 **revision 1（DRAFT，未批准）**。

## 需要你确认的几个点

1
草稿已记录为 **revision 1（DRAFT，未批准）**。

## 需要你确认的几个点

1. **看牌结算 bug 的定性**：现有 `dqn_*.pth` 模型是在错误规则下训练的，修复后旧模型行为不再有意义。计划默认"归档不删除"，你同意吗？
2. **中文资产文件重命名**（`src/card_pic/红心2.png` 等、`mymath/概率大小映射`、`introduction`）：影响面广，我把它列为**可选审批项**，可以推迟或跳过。
3. **`备份/` 归档到仓库外**：需要指定归档位置（如 `../game_exercise_backup_2026/`），批准时告诉我。
4. **预算与资源**：项目预算 3M tokens、maxDepth=1、maxConcurrent=2，合并入 main 由你手动执行。如无异议。

## 批准方式

确认（或提出修改意见）后，请执行：

```
node .pi/governance/cli.ts project approve 1
```

批准后我将按 P0→P6 创建内部任务并逐阶段推进，遇到触发人工审...
