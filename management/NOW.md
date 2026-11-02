# 项目现状

项目 ID：0c68bf5a-2104-498a-9532-7a2f6f2384f3

项目基线：r4 / ACTIVE；草稿：4。
任务 8；已验收 4；执行中 1；阻塞 1；待决策 1。

## 活跃 Agent

- reviewer：human-vs-machine / R-14cb6c25-afc2-4d9a-9e41-35986e27b782 / W-human-vs-machine；插件 running；注意 active_long_running

## 费用

- R-b9853e0d-6e92-4850-88e2-7ba398568e00: $0
- R-c087e5df-6c86-4acb-aef4-a315fb801999: $0
- R-148f4a06-7cfa-432c-81c0-17ccca18db30: $0
- R-c57e84c3-c2a9-4f49-872b-7aaf754dfe91: $0
- R-59b098c2-921a-4e06-bdd1-c027f6bae2a1: $0
- R-6277d607-f2cc-4fb1-990f-b740b4fb6c2d: $0
- R-e756980e-4a01-45c5-bd73-01681cdce55a: $0
- R-d54bff1a-f47b-4a96-834c-e80648fe70c1: $0
- R-7d6a65d2-d66a-43cc-bfee-67c85cd0416a: $0
- R-c0feb4e1-6de9-4e0f-8add-196900d2a697: $0
- R-31dae8ab-8645-4f6d-a1da-7c179c9222aa: $0
- R-3b7f69cb-4da6-43f2-b1ea-2741e27f651f: $0
- R-a76db659-51d1-48f0-a73b-f57628a4d889: $0
- R-30f786fa-07bc-45e5-8102-c936d9bc440d: $0
- R-f241bbd7-1559-42ee-b13e-23974b06e795: $0
- R-81abd01e-48ce-4f38-bc63-6d3063d46641: $0
- R-948ba62d-36c6-4b93-9e87-2db4f92db8c9: $0
- R-19d2f6bd-8e3a-4464-a95a-ab2cf8ba526e: $0
- R-9994d3e0-f2b2-4c02-99f9-30663d4f5165: 未知
- R-44ac84dd-8e85-4a6b-a120-6a76aaf0e431: $0
- R-645c1980-4d3a-41fe-a644-60ee2a64b1f8: $0
- R-dd2699b1-5cc3-4f78-91a2-1081a599975e: $0
- R-c1712b23-6c72-4d3e-983a-9976034da077: $0
- R-e6879920-cfcb-4958-94b9-1e802a3ef28f: $0
- R-2569c185-4b3b-4693-a102-cd8b1ad43986: $0
- R-f3136e0a-a69b-4dd4-8add-51a06956a570: $0
- R-f20e8e16-850c-4ad7-acfc-f3fe439648d5: $0
- R-0054a175-50bb-42b0-8a33-4f1feaa76bb7: $0
- R-14cb6c25-afc2-4d9a-9e41-35986e27b782: 未知

## 风险与遗留

- architecture-knowledge-base: 首次委派（Task architecture-survey）的 3 个 reader Run 全部因 reader 角色 timeoutMs=900000 超时失败；A/B 报告已从会话留存回收，C 被截断。已取消该 Task 并以更高超时 + 更小切分重做。
- architecture-knowledge-base: 本地 Qwen3.8-27B 的 provider maxTokens 原为 12288，reader 在 medium 思考下大量思考 token 触顶导致 stopReason=length 报告被截断；已提升至 32768，并把 reader/worker/reviewer 的 thinking 降为 minimal。
- architecture-knowledge-base: 首次 reviewer 单次委派范围过大（20 条行号 + 10 个测试文件）超时 abort；已拆分为 R1/R2 两个窄任务并行完成。
- architecture-knowledge-base: R2 判定「有条件通过」：6.3 节「合法动作仅在人类回合非空」措辞偏强（测试未断言 AI 回合为空），已修正；另新增 README time.sleep 守护 overclaim 一条不一致（tests/test_ui.py:63-65 只扫 ui/）。
- architecture-knowledge-base: R1/R2 指认的 6 处行号偏差经 worker 逐条重核后判定为报告方有误、原引用正确，保持不动；另 3 处确认后已修正。校准过程记录于文档第 8 节「行号校准说明」。
- architecture-knowledge-base: README 架构图箭头方向与文字描述相反、入口文件行数标注错误（6 行实为 14 行）两处 README 缺陷仅记录未修改（超出本 Task 范围）。
- architecture-knowledge-base: 文档未整合 governance 视图与 PROGRESS.md 的未提交改动，属既有工作区状态，非本 Task 产生。
- selfplay-engine: 8 个 pytest 失败全部为既有环境问题：仓库内不存在 dqn_model_1.pth（.gitignore 忽略 *.pth 且从未提交），导致 test_agents.py::TestCheckpointDims×3、TestD9LoadedPolicyInEffect×3、test_scripts.py::TestEvaluate×2 报 FileNotFoundError。基线 commit 6bd6253 实测同为 8 failed / 110 passed，本次为 8 failed / 125 passed，无既有测试被打红。修复该问题需要先产出权重文件，属下游 selfplay-train-100 Task 的范围。
- selfplay-engine: 零和奖励口径为「赢方 +all_bet / 输方 -all_bet」，相对原 robot 模式「输方 -agent_bet」是已披露的行为变更：方向与 core/rules.py 结算（赢家拿走全池）一致且严格反对称，但幅度更大。既有测试无任何依赖旧数值的断言（已由 reviewer 独立 grep 确认）。
- selfplay-engine: env.py:118 的 _opp_actions 每局清零，使 opponent_replay_every 实际语义为「单局内每 k 次行动」。短局（对手每局不足 4 次行动）时对手 replay 饥饿。实测 200 局下 agent.eps=0.3525 vs opp.eps=0.9801，衰减节奏相差一个数量级，防塌缩目标达成；建议后续把计数改为跨局累计。
- selfplay-engine: 未训练权重的双 checkpoint 贪心评估会出现 20/20 轮全部 MAX_STEPS=200 强停、双方胜率均为 0.0 的情形。机制本身正确输出双方胜率（epsilon=0.7 时为 0.3/0.7，和为 1.0），0/0 是未训练策略的产物，需在 evaluate 文档中说明解读方式。
- selfplay-engine: CUDA 路径未实测（本环境仅 CPU 验证），代码未区分设备，风险评估为低。
- cleanup-refactor: 8 个 pytest 失败全部为既有环境问题：仓库内不存在 dqn_model_1.pth（.gitignore 忽略 *.pth 且从未提交），导致 test_agents.py::TestCheckpointDims×3、TestD9LoadedPolicyInEffect×3、test_scripts.py::TestEvaluate×2 报 FileNotFoundError。reviewer 在 /tmp 基线 worktree 实测同为 8 failed / 110 passed，本次为 8 failed / 114 passed，无既有测试被打红。修复需先产出权重文件，属下游 selfplay-train-100 Task 范围。
- cleanup-refactor: README 架构图中 scripts 的下降线汇入一条横跨两框的横杆再分支到 core/ 与 agents/，方向可读且与正文一致，但不如两条独立垂直箭头直观，存在轻微误读空间（纯 ASCII 风格问题，reviewer 已逐列实测对齐与方向正确）。
- cleanup-refactor: agents 框底部仅一个 ┘ 而无底边，框未闭合，属视觉瑕疵，不影响对齐与方向。
- cleanup-refactor: 键码映射测试具体钉死 K_1/K_4/K_f/K_c 四个键，K_2/K_3 依赖覆盖性断言（reviewer 已独立实测 K_2 驱动路径，风险为零）。
- cleanup-refactor: environment 怪癖（非本次改动引入，基线同样如此）：pytest 9.1.1 在 -q 模式下最后一行不输出计数行，需用 -v 模式读计数。
- selfplay-train-100: 8 个 pytest 失败全部为既有环境问题：仓库内不存在 dqn_model_1.pth（.gitignore 忽略 *.pth 且从未提交），导致 test_agents.py::TestCheckpointDims×3、TestD9LoadedPolicyInEffect×3、test_scripts.py::TestEvaluate×2 报 FileNotFoundError。基线 6bd6253 实测同为 8 failed / 110 passed，本次 8 failed / 131 passed，失败名逐条一致，无新增失败。reviewer 额外实测：把训练产物复制为仓库根 dqn_model_1.pth 后 8 个失败全部转绿、套件 139 全绿（临时文件已删）。
- selfplay-train-100: ε=0 状态依赖的绝对占比是采样条件值：worker 报弱/中/强 = 0.000/0.7353/1.000，Main 复测 0.1491/0.9650/1.000，reviewer 复测 0.0083/0.8415/1.000。三者分档手数完全相同（751/714/935），差异全部来自前 3 维盘面特征的随机种子/取值范围不同（第 4 维 beats_probability 是确定性的）。三套结论一致：单调递增且非退化。稳定判据是最大动作占比 <0.95 与强度分档单调序，不是绝对值。
- selfplay-train-100: evaluate 对局的贪心动作偏置到 bet_100（≈0.97），符合验收条款（未违反 natural_end_rate 与状态依赖要求），但若后续追求策略强度需再迭代训练配方。
- selfplay-train-100: run/ 下仍有若干历史实验目录（base100/、k1/、k2a/、k2b/、robust_*/ 等），其中 hidden=(32,16) 的陈旧 checkpoint 已删除；仅 run/final/ 下保留 3 个 fc1=(128,4) 的当前产物（含 1 个 train.py:203 的对手同步临时文件 _sync_tmp_seed7.pth，非权威产物）。
- selfplay-train-100: 治理插曲：前两轮 reviewer 均无 bash 工具（.pi/settings.json 的 agentOverrides 覆盖了 agent 定义文件的 tools 且修改未提交），已修复并提交 d67a0c0 + e4e44f6，第三轮 reviewer 实跑 16 项全部通过。

## 最近事件

- 2026-11-02T16:15:21.068Z agent.action-result human-vs-machine 
- 2026-11-02T16:15:24.351Z agent.action-observed human-vs-machine R-14cb6c25-afc2-4d9a-9e41-35986e27b782
- 2026-11-02T16:15:24.876Z agent.action-result human-vs-machine R-14cb6c25-afc2-4d9a-9e41-35986e27b782
- 2026-11-02T16:15:32.568Z agent.action-observed human-vs-machine 
- 2026-11-02T16:15:32.994Z agent.action-result human-vs-machine 
- 2026-11-02T16:15:45.396Z agent.loop-settled human-vs-machine 
- 2026-11-02T16:16:11.801Z agent.request-observed human-vs-machine 
- 2026-11-02T16:16:12.224Z agent.loop-started human-vs-machine 
- 2026-11-02T16:16:19.347Z agent.action-observed human-vs-machine 
- 2026-11-02T16:16:19.752Z agent.action-result human-vs-machine 
- 2026-11-02T16:16:25.124Z agent.action-observed human-vs-machine 
- 2026-11-02T16:16:25.527Z agent.action-result human-vs-machine 

## 下一步

- 处理 management/INBOX.md 中的 1 项待决策
