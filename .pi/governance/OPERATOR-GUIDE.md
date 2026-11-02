# 项目内 Governance 操作指南

本文件随 `gov init` 安装到 `.pi/governance/OPERATOR-GUIDE.md`，随 `gov upgrade` 更新。Main Agent 接到自然语言归档、重置或决策请求时先读本文件，再按操作需要查看 `management/PROJECT.md`、`management/NOW.md` 或 `management/INBOX.md`。日常使用无需读 Governance 源码。以下命令均在项目 Git 主工作树运行。

## 选择操作

| 用户意图 | 命令 | 当前视图变化 |
| --- | --- | --- |
| 归档整个项目工作区，从头制定 Management 与 Plan | `workspace archive` | 旧基线、草稿、Task、活动、生成的 PRD/Plan 退出当前视图；保留项目 ID、原始账本、Subagent V3 与模型配置 |
| 只归档当前 Task 等工作历史，沿用已批准的项目基线 | `project archive` | 清空当前 Task/Delegation/Run/交付视图；基线继续有效 |
| 撤销当前治理基线与授权，保留工作历史 | `project reset` | 回到 DRAFT；旧批准不再授权新执行 |
| 拒绝一个待决策项 | `decision reject` 或对应的 `project reject` | 记录拒绝；不改写历史决策 |

项目 ID 从 `.pi/governance/installation.json` 读取；归档/重置命令要求把它作为确认参数。原因要写明，不能用空字符串。不要把三种项目级操作用于处理单个决策。当前没有“重置单个已完成 Decision”的命令；用户提出此类请求时，先指出这一限制，再按实际对象选择新修订或拒绝待决策项。不要通过编辑 JSONL、Management 生成视图或数据库伪造撤销。

## 完整工作区归档

用户明确要求“整个项目从头开始”“旧 Plan 和 Management 归档后重新规划”时，使用：

```sh
node .pi/governance/cli.ts workspace archive <项目ID> "归档原因"
node .pi/governance/cli.ts views check
```

归档会拒绝活跃 Run；先检查并处理它们，不要绕过。命令在 Git Common Dir 的 `agent-governance-v0.1/workspace-archives/` 下创建带时间戳的快照，保存归档前账本及 SHA-256，不删除历史事件，也不覆盖同名快照。成功后读 `management/PROJECT.md` 和 `management/NOW.md` 确认当前项目为 DRAFT；重新提交下一版 Project 草稿并批准，委派前还需重新批准保留的 Subagent 策略。报告归档 ID、快照路径和当前状态。`management/README.md` 与项目策略保留。不要默认打印完整 `state show`：它会包含全部历史归档，输出可能很大。

## 只归档工作或只撤销授权

```sh
node .pi/governance/cli.ts project archive <项目ID> "归档原因"
node .pi/governance/cli.ts project reset <项目ID> "重置原因"
```

`project archive` 保留项目基线，不是“整个项目从零开始”。`project reset` 撤销基线，不负责清空旧 Task 工作视图。两者均会拒绝活跃 Run，并保留原始账本。

## 单个决策

先看 `management/INBOX.md`，必要时查询 `node .pi/governance/cli.ts audit events decision`，确认 Decision ID、关联对象和当前状态。待决策项可用：

```sh
node .pi/governance/cli.ts decision reject <Decision-ID> "拒绝范围"
```

项目草稿可用 `project reject <修订号> "原因"`。已完成的决策不可覆盖或删除；需要改变结果时，应对对应 Project/Task 提交新修订并走新的批准流程。不要把 `project reset` 当作单个决策撤销。

## 事实与边界

- 命令返回成功后，核对账本投影和生成视图；不要仅凭自然语言回复宣称已归档。
- Main/Child 的 `bash`、`write`、`edit` 是可观察的基本工具，Bridge 不按命令或路径拦截。正式 Task 与委派仍走治理准入；当前没有 OS 沙箱。
- Pi 的 `/gov-archive` 只对应 `project archive`，不是完整的 `workspace archive`。Main Agent 处理完整工作区归档时用上面的 CLI。
