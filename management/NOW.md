# 项目现状

项目 ID：0c68bf5a-2104-498a-9532-7a2f6f2384f3

项目基线：r4 / ACTIVE；草稿：4。
任务 10；已验收 8；执行中 0；阻塞 0；待决策 0。

## 活跃 Agent

暂无活跃 Agent。

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
- R-14cb6c25-afc2-4d9a-9e41-35986e27b782: $0
- R-fbe3fe00-4658-4bb9-b3fc-d50d73c6e843: 未知
- R-547c30ef-be71-469c-99f7-8d7721ef7cfe: $0
- R-260d66ae-1c6b-4fca-9a15-5b358a0c2494: $0
- R-9505e508-673a-4e7c-b7c9-b3d60efa0bdf: $0
- R-5470b352-ac58-40cd-bf08-ea54afe835e9: $0
- R-b6b3baa6-0a8d-4358-aeb2-abb543a459b6: $0
- R-2afb34fe-40f0-4705-b3b7-0cab101ceae2: $0

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
- human-vs-machine: 权重被 .gitignore 排除（*.pth 在第 17 行、run/ 在第 23 行），不进版本库。部署需把 run/final/dqn_sp_ep100_seed7.pth 复制为仓库根的 dqn_model_1.pth，或用 --checkpoint / DQN_CHECKPOINT 指定路径。
- human-vs-machine: docs/TRAINED-WEIGHTS-UI.md 中 3 处 ui/app.py 行号引用漂移 2~10 行（文档写 27/31/83-84，实际为 29/33/71-73），不影响理解。reviewer 判为可选修正项，未列为必须返工。
- human-vs-machine: _load_agent 的 except 元组非穷举白名单：若 from_checkpoint 未来抛出该 4 类之外的异常类型仍会崩溃。reviewer 实测 torch 2.6 下 FileNotFoundError / ValueError / RuntimeError / PickleError 四类常见路径均已覆盖。
- human-vs-machine: 本 Task 的证据日志提交 bfa9881 含 management/evidence/logs/ 路径，严格说在 Task 的 authority.paths（ui/tests/docs/README.md）之外，但与本仓既有的 test(evidence) 提交惯例一致且无功能改动，reviewer 判为可接受。
- arch-ref-fix: 4 处内容级过期（行号正确但描述与当前代码不符），属 T5b（arch-doc-update）范围，已记录于 management/evidence/arch-ref/CONTENT-STALE.md 与 reviewer 报告：doc 153 的 core.rules.Action 逐行归属错（23 行实为 from scripts.env import）、doc 426 的 pyproject.toml extend-exclude 已无「备份」条目、doc 385 称 last_now 为类级属性但实际在 __init__ 内、doc 380 仍描述已废弃的 Action(key - pygame.K_1) 差值映射。
- arch-ref-fix: 23 处 UNRESOLVED 为同名多候选（__init__.py×2、README.md×19 等），行号本身在候选文件范围内；reviewer 抽查 12/30/39/59/63/71-75/86/96-97 行内容全部吻合，判定按上下文语义指向根 README.md 成立。
- arch-ref-fix: check_refs.py 原将 REPO 硬编码为主仓路径，导致在 worktree 中复跑得到假阳性（reviewer 发现）。已参数化为环境变量 ARCH_REF_REPO，并修正裸文件名的同名候选解析与 worktree 路径被误过滤的问题；修正后 worktree 与主仓复跑结果一致。
- arch-doc-update: reviewer 首轮复核提出 2 项必须返工（4.5 分桶数字的出处与所引文件不符、底池 20060 缺可复现命令）+ 1 项建议（56/44 未标口径）。已全部修正并复验：分桶主引用改为 docs/selfplay_train_report.md §5（弱 0.000 / 中 0.7353 / 强 1.000，区间 0.3<p≤0.6），另两次独立复测各附真实出处（review-train-100-final.md、review-train-100.md 第 5 项），并说明差异来自盘面随机种子、稳定判据是最大占比<0.95 与分档单调序；现象段补上完整复现命令与输出并标注 --opponent-mode self 与 --strength-shaping 0 两参数缺一不可；56/44 加「训练期」限定并补 ε=0 评估为 0.5/0.5。
- arch-doc-update: 返工过程中 worker 就「第二次复测的出处文件」提出指令与仓库证据冲突（Main 原指定的 review-arch-doc-update.md 不含 0.1491/0.9650）。经 Main 独立复核确认 worker 正确、原指令指错文件，已按选项 A 更正为 review-train-100.md 第 5 项。
- arch-doc-update: 整体校验 498 处引用中 0 处越界；7 处「文件缺失」为同名多候选（__init__.py、README.md 等）无法自动唯一解析，已逐条按上下文语义核对成立。
- dqn-vs-dqn-investigation: 该 Task 为只读调查，无代码交付，产物为三份 markdown 报告。
- dqn-vs-dqn-investigation: 报告成文于 T1~T4 实施之前，其中若干 file:line 已因后续重构漂移（尤其 ui/app.py、scripts/*）；报告结论的**技术判断**仍有效，但引用行号应按 T5a 校正后的 docs/ARCHITECTURE.md 对照阅读。
- dqn-vs-dqn-investigation: 13 处 UNKNOWN 是当时的真实限制（reader 角色无 bash 工具、src/ 总大小未 stat、cu130 URL 未联网验证等），其中部分已在后续 Task 中被实际核验填补。

## 最近事件

- 2026-11-03T02:54:25.222Z agent.action-observed arch-doc-update 
- 2026-11-03T02:54:25.687Z agent.action-result arch-doc-update 
- 2026-11-03T02:54:35.168Z agent.action-observed arch-doc-update 
- 2026-11-03T02:54:35.638Z agent.action-result arch-doc-update 
- 2026-11-03T02:54:46.058Z verification.recorded dqn-vs-dqn-investigation R-f241bbd7-1559-42ee-b13e-23974b06e795
- 2026-11-03T02:54:47.855Z agent.action-observed arch-doc-update 
- 2026-11-03T02:54:48.325Z agent.action-result arch-doc-update 
- 2026-11-03T02:54:56.363Z task.accepted dqn-vs-dqn-investigation 
- 2026-11-03T02:54:58.204Z agent.action-observed arch-doc-update 
- 2026-11-03T02:54:58.679Z agent.action-result arch-doc-update 
- 2026-11-03T02:55:07.679Z agent.action-observed arch-doc-update 
- 2026-11-03T02:55:08.148Z agent.action-result arch-doc-update 

## 下一步

- 跟踪 management/views/TASKS.md；Run 出错查看对应任务 STATUS.md
