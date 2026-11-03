# 交接

目标：为 docs/ARCHITECTURE.md 补充本轮新增内容：自博弈训练章节、机器对手接线章节、权重获取与存放说明、7.6/7.7 条目处置结果、第 6 节新增测试文件清单、CHANGELOG 记录。所有实测数据由 Main Agent 提供，worker 不需要自行探索。这是 final-audit 拆分后的第二个 Task。
验收：新增「自博弈训练」章节：scripts/env.py 的自博弈环境与零和口径、strength_shaping 稠密塑形及其根因（终局奖励 ±all_bet 量级随押注额线性增长 → Q 单调偏好最大押注 → 贪心恒为 bet_100、对局永不自然结束、动作分布退化为单一动作；解法必须按押注额而非底池计酬）、scripts/train.py 的三种对手模式与 --preset selfplay-v1 配方、scripts/evaluate.py 的双 checkpoint 评估与 natural_end_rate；新增「机器对手接线」与「权重获取与存放」两节：ui/app.py 的 resolve_checkpoint 优先级（CLI > DQN_CHECKPOINT > 默认）、Controller.trained/policy_source、缺失或损坏权重的三行告警与回退、--checkpoint 用法；以及训练命令、产物路径（run/final/dqn_sp_ep100_seed7.pth 与 run/final/dqn_sp_opp_ep100_seed7.pth）、部署方式（复制为仓库根 dqn_model_1.pth 或用 --checkpoint 指定）、权重不入版本库的原因（.gitignore 的 *.pth 与 run/）、如何复现训练；第 7.6/7.7 条目逐条标注处置结果（已处置/保留/说明）、第 6 节补入 tests/test_selfplay.py、tests/test_selfplay_preset.py、tests/test_trained_ui.py 三份测试的断言摘要、CHANGELOG.md 追加本轮变更记录；新增章节中的每条 file:line 引用必须与当前代码实际一致
权限：{"commitBranch":true,"integrateBranch":false,"paths":["docs","README.md","CHANGELOG.md"],"readRepository":true,"tools":["bash","read","edit","write","grep","find","ls"],"writeWorkspace":true}
当前工作空间：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/arch-doc-update
基线：c30b4f996f0208b256a36a8e58b5bc647c6b9e8b
未提交文件：M .agent/telemetry-state.json； M .agent/telemetry.jsonl； M PROGRESS.md
最新交付：7144fbe4105e4dfa87e2a48e055c6131d9ecafd0
交付文件：M CHANGELOG.md；M docs/ARCHITECTURE.md
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
