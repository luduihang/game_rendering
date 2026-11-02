# 交接

目标：实现 DQN 对抗 DQN（自博弈）训练机制：在 scripts/env.py 与 scripts/train.py 上让两个 DQN 互相对弈，产出可加载的策略文件。本 Task 只做机制与测试，不跑长训练（训练由下游独立 Task 执行）。Main Agent 只调度编排，编码全部由子 Agent 完成。
验收：scripts/env.py 支持 opponent 为 BaseAgent（不限 Robot）：DQN 对手走自己的观测编码与 observe/replay 路径，Robot 对手行为不变；自博弈模式每局交换两个 DQN 的座位，消除先手偏置；双方奖励零和：agent_reward + opponent_reward == 0；scripts/train.py 新增 --opponent-mode {robot,self,snapshot} 及相关参数，产出主策略与对手策略两个 checkpoint，summary 含双方胜率与动作分布；新增测试覆盖：DQN 对手可完成整局、对手观测维度为 4 且视角对称、座位交换生效、奖励零和、自博弈训练冒烟（少量局数跑完并产出两个 checkpoint）、同种子可复现；agents/dqn.py、core/rules.py、core/strength.py、core/dealing.py 的既有机制零改动；pytest 全绿且相对改动前无既有测试被打红
权限：{"commitBranch":true,"integrateBranch":false,"paths":["scripts","tests"],"readRepository":true,"tools":["bash","read","edit","write","grep","find","ls"],"writeWorkspace":true}
当前工作空间：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-engine
基线：6bd6253bf9e122fe1df982f50e20b1b47f050db0
未提交文件：M .agent/telemetry-state.json； M .agent/telemetry.jsonl； M .pi/agents/reviewer.md； M .pi/settings.json； M PROGRESS.md
最新交付：7343ca76550af08d6b7beb6aa753d58be6ca6158
交付文件：A management/evidence/logs/selfplay-pytest.txt；A management/evidence/logs/selfplay-ruff.txt；M scripts/env.py；M scripts/evaluate.py；M scripts/train.py；A tests/test_selfplay.py
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
