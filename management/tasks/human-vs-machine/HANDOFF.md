# 交接

目标：跑通「玩家 vs 机器」的对抗：ui/ 侧默认加载自博弈训练产出的策略文件，机器用训练出来的逻辑（epsilon=0.0 贪心）而不是随机概率，并做 headless 端到端验证一局完整走通。这是用户的第二优先事项。Main Agent 只调度编排，编码全部由子 Agent 完成。
验收：ui/app.py 的 DEFAULT_CHECKPOINT 指向自博弈训练产出的策略文件；checkpoint 路径可配置（CLI 参数或环境变量）；checkpoint 缺失时启动给出明确可见告警，而不是静默回退（回退可保留但必须可见）；机器加载训练权重后 epsilon == 0.0，不是回退的 0.15；headless 端到端测试：一局中人类输入 → 机器应招 → 回合交替 → 结算，全程走通；测试断言机器动作确实来自训练权重输出，而非随机采样；pytest 与 ruff 全绿，且相对改动前无既有测试被打红
权限：{"commitBranch":true,"integrateBranch":false,"paths":["ui","tests","docs","README.md"],"readRepository":true,"tools":["bash","read","edit","write","grep","find","ls"],"writeWorkspace":true}
当前工作空间：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/human-vs-machine
基线：6bd6253bf9e122fe1df982f50e20b1b47f050db0
未提交文件：M .agent/telemetry-state.json； M .agent/telemetry.jsonl； M .pi/agents/reviewer.md； M .pi/settings.json； M PROGRESS.md
最新交付：无
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
