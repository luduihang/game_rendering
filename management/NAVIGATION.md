# management/ 目录导航

> **一句话**：`management/` 是 Agent Governance 的**账本阅读视图** + **本项目的证据与复盘档案**。
> 状态由治理账本自动生成，只有 `policies/` 和 `evidence/` 是可手写编辑的。
>
> 快速入口：**现在做到哪了 → `NOW.md`** ｜ **要批什么 → `INBOX.md`** ｜ **规则是什么 → `PROJECT.md`** ｜ **怎么操作 → `../.pi/governance/OPERATOR-GUIDE.md`**

---

## 一、目录树与各路径作用

```
management/
│
├── README.md                    ← 【先读这个】治理目录的说明 + 常用 CLI 命令清单
├── NOW.md                       ← 【进度】当前基线/任务数/已验收数/执行中/阻塞/待决策 一览
├── INBOX.md                     ← 【待办】需要人类拍板的事项清单；为空 = 无待决策
├── PROJECT.md                   ← 【契约】当前生效基线：目标、范围、预算、人工审批条件、审批策略
├── ARCHIVE.md                   ← 【历史】已不属于当前工作的历史与归档索引
├── DELEGATION-RETROSPECTIVE.md  ← 【复盘】30 次子 Agent 运行的量化分析 + 派发经验（手写）
│
├── project/                     ← 【项目基线快照】每个 Project 修订的契约/PRD/PLAN
│   ├── r1/ r2/ r3/ r4/          ←   contract.json + PRD.md + PLAN.md
│   │                              r4 = 当前生效版本（与 PROJECT.md 内容对应）
│
├── tasks/                       ← 【任务台账】每个 Task 的契约、交接记录、状态
│   ├── architecture-survey/         已取消（首次委派超时）
│   ├── architecture-knowledge-base/ 已验收（产出 docs/ARCHITECTURE.md）
│   ├── dqn-vs-dqn-investigation/    已批准（只读调查，产出 3 份调研报告）
│   ├── selfplay-engine/             已验收（T1：自博弈机制）
│   ├── cleanup-refactor/            已验收（T4：S/M 级清理）
│   ├── selfplay-train-100/          已验收（T2：训练产出权重）
│   ├── human-vs-machine/            已验收（T3：UI 接线）
│   ├── final-audit/                 原大 Task：其唯一的 Run 被取消，Task 本身未取消、未验收；
│   │                                已拆分为 arch-ref-fix + arch-doc-update 两个 Task 接替
│   ├── arch-ref-fix/                已验收（T5a：129 处行号校正）
│   └── arch-doc-update/             进行中（T5b：架构文档新章节）
│       每个任务目录下固定 3 个文件：
│         contract-rN.json  机器读的验收契约（acceptance 逐条 + 授权路径 + 预算）
│         HANDOFF.md       交接说明（派发时给子 Agent 的上下文来源）
│         STATUS.md        人读的状态摘要（批准状态、验收结果、工作空间、最新提交）
│
├── policies/                    ← 【策略】子 Agent 路由策略（可编辑，改后需重新批准）
│   └── subagents.json              reader/worker/reviewer 的工具集、token 配额、超时、模型档
│
├── views/                       ← 【生成视图】由 `views render` 从账本生成，不要手改
│   ├── TASKS.md                    任务树（父子关系、依赖）
│   ├── DELEGATIONS.md              委派流水（谁被派了做什么）
│   └── GIT.md                      Git 版本关系（每个 Task 对应的分支与 commit）
│
├── evidence/                    ← 【证据】本项目的调查/交付/复核报告与原始数据（手写）
│   ├── investigation/               16 个文件：invest-* 调查、deliver-* 交付、review-* 复核
│   ├── report-*.md                  架构调查的原始报告（A/B/C1/C2/C2b/partial）
│   ├── review-R1/R2*.md             架构文档的两轮审核（行号抽样、测试与 README 比对）
│   ├── logs/                        9 个 .txt：pytest / ruff / 训练的实际输出留证
│   ├── verification/                acceptance-checks.txt：架构阶段的机器验收结论
│   ├── retrospective/               委派复盘的原始数据（可复算 run-metrics 等）
│   └── arch-ref/                    引用重定位的预计算清单 + 校验脚本 + 待修措辞清单
│
└── legacy/                      ← 【归档】治理账本重置前的历史留档，不参与校验
    ├── README.md                   说明：这些不再由账本生成
    ├── project/r1..r5/             旧版本 Project 契约
    └── tasks/p0..p7/               Phase 0–7 的旧任务交接
```

---

## 二、按「我现在要做什么」查表

| 我要做什么 | 打开 |
|---|---|
| 看项目现在做到哪一步 | `NOW.md` |
| 看有没有等我拍板的事 | `INBOX.md` |
| 查规则边界（能不能做 X） | `PROJECT.md` 的「重要人工审批条件」 |
| 查某个 Task 的验收标准是什么 | `management/tasks/<id>/contract-rN.json` |
| 查某个 Task 的进度/工作空间/最新提交 | `management/tasks/<id>/STATUS.md` |
| 查子 Agent 的工具集/配额/超时 | `policies/subagents.json` |
| 查 Task 的分支与 commit 对应关系 | `views/GIT.md` |
| 查某个 Run 为什么失败 | `node .pi/governance/cli.ts run inspect <runId>` |
| 看某次实现到底改了什么 | `evidence/investigation/deliver-*.md` |
| 看 reviewer 抓到了什么问题 | `evidence/investigation/review-*.md` |
| 查历史架构调查的原始结论 | `evidence/report-*.md` |
| 查 pytest/ruff 的原始输出 | `evidence/logs/*.txt` |
| 学习怎么给子 Agent 派活 | `DELEGATION-RETROSPECTIVE.md` |
| 查架构文档里某处引用是否准确 | `evidence/arch-ref/check_refs.py` |

---

## 三、三类内容，区别很重要

| 类别 | 目录 | 能否手改 | 改动后 |
|---|---|---|---|
| **生成视图** | `NOW.md`、`INBOX.md`、`PROJECT.md`、`ARCHIVE.md`、`views/`、`tasks/*/` | ❌ 不要 | 会被 `views render` 覆盖；以账本为准 |
| **可编辑策略** | `policies/subagents.json` | ✅ 可以 | 需 `policy sync` → `policy approve` 才生效 |
| **档案/证据** | `evidence/`、`DELEGATION-RETROSPECTIVE.md` | ✅ 可以 | 不影响治理状态 |
| **历史留档** | `legacy/`、`project/r1..r3` | ❌ | 只读参考 |

> **关键**：改 `management/` 下的生成视图**不构成授权**。正式授权只来自治理 CLI 的审批命令。

---

## 四、配套位置（不在 management/ 下但常一起看）

| 路径 | 作用 |
|---|---|
| `.pi/governance/OPERATOR-GUIDE.md` | 归档/重置/决策的操作指南（自然语言请求前必读） |
| `.pi/governance/cli.ts` | 治理 CLI，所有正式操作入口 |
| `.pi/agents/{reader,worker,reviewer}.md` | 三个子 Agent 的定义（工具集在这里改，改完要提交） |
| `docs/ARCHITECTURE.md` | 架构知识库本体（8+ 章节，421 处 file:line 证据） |
| `docs/selfplay_train_report.md` | 自博弈训练报告（命令/耗时/胜率/产物路径） |
| `docs/TRAINED-WEIGHTS-UI.md` | 权重获取与 UI 接线说明 |
| `management/evidence/retrospective/` | 复盘原始数据（run-metrics.json 等，可复算报告里每个数字） |

---

*本文件为手写导航，不参与治理校验；治理状态以 `NOW.md` / `INBOX.md` 与 CLI 输出为准。*
