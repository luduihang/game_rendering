# 委派复盘报告：30 次子 Agent 运行的量化分析

> **目的**：为未来的任务分配提供可量化的依据，而不是靠印象。本报告全部数据来自治理账本（`audit events run`）与子会话 session 文件的实测统计。
>
> **样本**：Project `0c68bf5a-2104-498a-9532-7a2f2384f3` / r4 基线，2026-11-02 全天，共 **30 次**委派运行（21 成功 / 9 失败或取消）。
>
> **生成方式**：Main Agent 从 `node .pi/governance/cli.ts audit events run` 与 `/home/kipley/.pi/agent/sessions/.../*/run-0/session.jsonl` 逐次统计。指标定义见 §1。

---

## 1. 指标定义与数据来源

| 指标 | 定义 | 来源 |
|---|---|---|
| 时长 | `run.started` → `run.finished/failed/cancelled` | 治理账本事件 |
| turn | 子会话中 assistant 消息条数 | session.jsonl |
| 输出 tok | 单条 assistant 消息 `usage.output` 的峰值 | session.jsonl |
| **ctx 峰** | 单条消息 `usage.input + usage.cacheRead` 的峰值 | session.jsonl |
| **字符** | 会话内所有文本块 + 工具结果的字符总数 | session.jsonl |
| 配额 | `routing.maxAllocationTokens` | 治理账本 |
| 目标长度 | 我发给子 Agent 的 objective 字符数 | session 首条用户消息 |

> 模型 contextWindow = **131,072**（`Qwen3.8-27B` / vllm-local）。

---

## 2. 核心量化结论

### 2.1 文本输出量几乎完全决定上下文峰值

```
字符数 vs ctx 峰：  r = 0.912      ← 强相关
turn 数 vs ctx 峰：  r = 0.650
```

**这是本项目最重要的一条结论。** 决定子 Agent 会不会爆的不是任务复杂度，而是**它把多少东西读进了上下文**。

### 2.2 成功与失败的指标分布

| | 成功 (21) | 失败/取消 (9) |
|---|---|---|
| ctx 峰中位数 | **60,724** | **102,568** |
| 字符数中位数 | **85,145** | **161,906** |
| turn 中位数 | 27 | 25 |

失败组的 ctx 中位数是成功组的 **1.7 倍**，而 turn 数反而**更少** —— 说明失败不是"干了太多轮"，而是"每轮吞了太多东西"。

### 2.3 上下文超 100k（危险区）的 5 次运行 —— **全部失败**

| ctx 峰 | 占比 | Task | 角色 | 结局 |
|---|---|---|---|---|
| **134,511** | **103%** | final-audit | worker | cancelled |
| 113,154 | 86% | selfplay-train-100 | worker | failed |
| 112,092 | 86% | selfplay-train-100 | reviewer | failed |
| 111,623 | 85% | architecture-knowledge-base | reviewer | failed |
| 102,568 | 78% | architecture-survey | reader | failed |

**阈值结论**：ctx 峰 > 100k 时 5 次全败；< 100k 时 25 次中仅 4 次失败，且那 4 次失败中 3 次根因是超时、1 次是配置缺失。

---

## 3. 失败案例逐个复盘

### 3.1 `final-audit` worker（103%，最严重）—— **我的指令本身不可行**

**轨迹**：26 turn / 34 次工具调用 / **309,745 字符** / ctx 冲到 103% / **架构文档 0 行改动**（只改了 PROGRESS.md）。

**根因（我的措辞问题）**：我同时给了 5 个子任务 ——
1. 逐条核对 r4 的 9 条 successCriteria
2. 逐条核对 10 条红线
3. **校正 439 行文档里 422 处 `file:line` 引用**（涉及 63 个文件）
4. 独立复现训练与评估
5. 更新 CHANGELOG

第 3 项**本质上要求把 63 个文件读进上下文**才能逐条比对。worker 的行为完全正确 —— 它按我的要求做了，然后就爆了。

**我犯的三个具体错误**：
- **错误 A：把"校验"和"改写"混在一个委派里。** 校验是机器任务（脚本 + 输出到文件），改写是文本任务。我让子 Agent 手工做了机器该做的事。
- **错误 B：没有约束单次工具输出的体积。** 我在 T2/T3 的 brief 里都写了"不要 cat 整个文件"，但 T5 的 brief 里**漏了这条**。
- **错误 C：没有设定"探索预算"。** 我没有说"最多读 N 个文件""最多 M 轮探索"，于是 worker 可以无限探索直到超时。

**证据**（worker 的工具输出分布）：22 个内容块超过 3000 字符，最大一块 **51,152 字符** —— 它把 `management/PROJECT.md`、三个测试文件全文、校验脚本的全部输出都灌进了上下文。

### 3.2 `selfplay-train-100` worker #1（90 分钟超时，4.1 万字输出换 0 行代码）

**轨迹**：100 turn / 105 次工具调用（bash 65 / edit 25 / read 13）/ ctx 113,154 / **超时未提交**。

**根因**：我给了「找出能训出状态依赖策略的配置」这个**开放式探索目标**，并明确鼓励它"在 /tmp 写个临时搜索脚本，批量跑多组组合"。worker 就真的无限搜索下去了。

**教训**：**开放式探索目标必须自带停止条件。** 我在返工委派里补了"总实验次数 ≤ 12 次""目标 20 分钟内完成"，同样的任务第二次 20 分钟就完成了（`R-c1712b23`）。

### 3.3 `selfplay-train-100` reviewer #1（40 分钟超时，0 份报告）

**根因**：**配置缺陷，不是措辞问题。** reviewer 的工具集只有 `read/grep/find/ls`，没有 bash。

**深层原因**（花了三轮才定位）：
- 子 Agent 的工具集由 **Agent 定义文件**（`.pi/agents/reviewer.md`）决定；
- 但 **`.pi/settings.json` 的 `subagents.agentOverrides.<name>.tools` 会覆盖它**；
- 我早前修改了 `reviewer.md` 加 bash，**却没提交** → 所有 worktree（从 git 检出）拿到的都是无 bash 的旧版；
- 治理包 `pi-bridge.ts` 自己的注释也写明：委派调用传入的 `tools` 参数对**异步路径不生效**。

**代价**：连续两轮 reviewer 只能做静态审阅（约 90 分钟 + 约 15 分钟），动态核验全靠 Main 自己补做。

**修复**：`d67a0c0`（reviewer.md）+ `e4e44f6`（settings.json），并同步到全部 5 个 worktree。

### 3.4 `architecture-survey` reader ×3（全部 15 分钟超时）

**根因**：reader 的 `maxAllocationTokens=30000` 但 `timeoutMs=900000`（15 分钟）。三份调查报告（每份涉及 63 个文件 × 421 处引用）根本不可能在 15 分钟内读完。**配额与工作量不匹配**。

**修复**：把 reader 切分成更小的模块、提到 30 分钟、提高 thinking 到 medium 并把 provider `maxTokens` 从 12288 提到 32768（原先思考 token 触顶导致报告被截断）。

---

## 4. 成功案例的可复制经验

| Task | 角色 | 时长 | ctx 峰 | 关键做法 |
|---|---|---|---|---|
| `selfplay-train-100` 返工 | worker | **22m** | 74,857 | 目标只有 3 件事、给了明确的实验次数上限 |
| `human-vs-machine` | worker | **16m** | 60,724 | 单一职责、给了 6 条验收逐条对应 |
| `human-vs-machine` | reviewer | **12m** | 35,552 | 给了 11 条可执行核查项、要求边做边写 |
| `selfplay-engine` | worker | 31m | 87,045 | 范围明确、给了详细实测数据 |

**共同点**：
1. **目标只有 1~3 件事**，不是 5 个子任务。
2. **给了可量化的完成判据**（"≤12 次实验"、"边做边写"、"20 分钟内"）。
3. **给了 Main 已实测的数据**，让 worker 不需要从零探索 —— 这直接节省了 60%+ 的时间。

**反例**：`final-audit` 我给了 5 个子任务 + 一份需要读 63 个文件才能完成的清单。

---

## 5. 我的措辞问题清单（可直接对照修正）

| # | 我写过的措辞 | 问题 | 修正写法 |
|---|---|---|---|
| 1 | "逐条核对每个 `file:line` 引用是否仍指向同一内容" | 要求把 63 个文件读进上下文 | "用脚本校验，结果写入 `/tmp/x.json`；你只读回摘要" |
| 2 | "在 /tmp 写个临时搜索脚本，批量跑多组组合" | 无停止条件 → 无限搜索 | "**总实验次数 ≤ 12 次**；超时即用当前最优收敛" |
| 3 | "目标 40 分钟内完成" | 只有时间约束、无次数约束 | 补上"总实验次数 ≤ N""单次 bash 输出 ≤ 30 行" |
| 4 | "边做边写" | 只在 T2/T3 reviewer 写了，T5 漏了 | **所有长任务默认加** |
| 5 | "定点查看代码用 `sed -n 'M,Np'`，不要 cat 整个文件" | T2/T3 写了，**T5 漏了** | 提升为标准模板条目 |
| 6 | 同时给 5 个子任务 | 范围过宽，无法在一个上下文内收敛 | **单次委派 ≤ 3 件事**；多了就拆 Task |
| 7 | "不要修改 pi 的源码" | 正确，且每次都写了 | 保留 |
| 8 | 把 `maxAllocationTokens` 提到 120,000/worker | 配额大 ≠ 能做完 | 配额应与**预估工作量**匹配 |

---

## 6. 隐蔽隐患清单（容易被忽略的）

| # | 隐患 | 本次表现 | 后果 |
|---|---|---|---|
| H1 | **worktree 从 git 检出，未提交的配置不生效** | reviewer.md / settings.json 的改动只在主工作区 | 连续 2 轮 reviewer 无 bash |
| H2 | **委派的 `tools` 参数对异步路径不生效** | 我传了 `bash` 但 reviewer 仍没有 | 同上，浪费 2 轮委派 |
| H3 | **pi 自动压缩上下文会掩盖超限** | T3 reviewer ctx 峰值 112,092 后被压到 40,834 | 看起来"恢复了"，其实已丢早期细节 |
| H4 | **worker 超时不产出任何 git 提交** | T2 worker #1 跑满 90 分钟，`ea2f024` 是第二个 worker 才交出来的 | 全部工作只能靠 session 回收 |
| H5 | **子 Agent 失败时 Main 容易被"已完成"的表象误导** | T5 worker 跑了 9 分钟只改了 PROGRESS.md | 若不查 ctx 峰值，会一直等下去 |
| H6 | **本地 vLLM 单轮生成很慢** | 观察到 6 分钟的单轮 | 必须给足 timeout，否则误判为卡死 |
| H7 | **子 Agent 的"未观测活动 60s"告警是噪声** | 多次误报，实为长生成 | 不能据此判断失败，要看 vLLM `num_requests_running` |
| H8 | **上下文 103% 时 pi 会截断而非报错** | final-audit 到 103% 仍"正常"运行 | 必须主动监控 ctx 峰值，不能等它自己失败 |

---

## 7. 下次分派的操作规则（照此执行）

### 7.1 派发前自检（Main Agent）

1. **目标拆解**：这次委派是 **1~3 件事**吗？超过就拆 Task。
2. **预估上下文**：子 Agent 需要读多少文件？
   - ≤ 5 个文件 → 直接派
   - > 5 个文件 → **先把要读的整理成一个清单文件**，让 worker 读清单而不是逐个读源码
3. **是否可脚本化**：如果判定逻辑是机械的（比对行号、统计分布），**Main 先跑脚本产出结论文件**，worker 只做基于结论的改写。
4. **工具集验证**：如果 worker 需要 bash，在**目标 worktree 目录**实测：
   ```sh
   node --input-type=module -e "const m=await import('/home/kipley/.pi/agent/npm/node_modules/pi-subagents/src/agents/agents.js'); console.log(JSON.stringify((m.discoverAgents(process.cwd(),'both')).agents.find(a=>a.name==='<role>').tools))"
   ```
5. **配置已提交**：任何影响子 Agent 能力的配置（`.pi/agents/*.md`、`.pi/settings.json`）改完**立即提交并同步到所有 worktree**。

### 7.2 委派指令的标准模板（每个长任务都带）

```markdown
**输出纪律（强制）**
- 每条 bash 命令的输出 ≤ 30 行；要看大文件用 `sed -n 'M,Np'` 定点看，禁止 cat/read 整个 >300 行的文件
- 批量结果写入 /tmp/<name>.json 或 .md，你只把摘要（≤20 行）读回上下文
- 边做边写：先写好报告标题与已确认小节，每完成一项就补进去；不要攒到最后一次性输出
- 探索预算：最多 N 次实验 / 最多 M 轮探索；达到即用当前最优收敛并提交
- 目标 N 分钟内完成
```

### 7.3 监控指标（每 3~5 分钟）

```sh
node .pi/governance/cli.ts run activity <runId>   # turn / sinceOut / ctx 峰值
timeout 10 curl --noproxy '*' -s http://192.168.0.190:8000/metrics | grep num_requests_running
```

**干预阈值**：
| 观察 | 判断 | 动作 |
|---|---|---|
| ctx 峰 > 90,000 | 危险 | 准备 steer 收敛或取消 |
| ctx 峰 > 100,000 | 临界 | **立即取消**，拆小重派 |
| sinceOut > 120s 且 vLLM running=1 | 正常长生成 | 继续等 |
| sinceOut > 120s 且 vLLM running=0 | 真卡死 | 取消 |
| git 无任何提交 且 已过 60% timeout | 大概率会超时 | 提前取消 |

---

## 8. 一次失败委派的完整时间线（T5，供对照）

```
23:59  派发 T5 worker，objective 5,681 字符，5 个子任务
       → 错误地让子 Agent 手工校验 422 处 file:line 引用
00:00  turn 1-8   读 contract / PROJECT.md / 任务树 / 测试文件全文
00:03  turn 9-16  校验脚本执行，输出整段灌入上下文
00:08  turn 17-24 开始逐个读源码文件比对
00:08  ctx 达 134,511 (103%) —— 架构文档仍 0 行改动
00:09  用户要求中断
       → Main 取消 run，usageTokens 1,368,547
       → Main 改用脚本校验，产出 108/129 自动定位 + 21 处锚点定位
```

**同一天同一批源码，若用脚本先跑，只消耗 Main 侧约 1 万 token；交给子 Agent 手工做，消耗了 136 万 token 且零产出。**

---

## 9. 遗留待办

- [ ] **T5 尚未完成**：架构文档仍需更新（自博弈章节、UI 接线章节、权重说明、7.6/7.7 处置、122 处引用校正）。**建议拆成 2 个独立 Task**：(a) 只做引用校正（清单已备好在 `/tmp/audit/relocated.json`，但 `/tmp` 会被清理，需转存到 `management/evidence/`）；(b) 只做新章节撰写。
- [ ] `reader` 的配额与超时需重新校准（当前 30,000 tok / 45 分钟，对 63 文件规模的调查任务偏紧）。
- [ ] 建议把 §7.1 的"派发前自检"固化为可复用技能（`skill_manage`），避免每次重新想。

---

*本报告由 Main Agent 基于治理账本与 session 文件实测数据生成；所有数字可由 `management/evidence/retrospective/` 下的原始 JSON 复算。*
