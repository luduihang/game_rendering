# 交接

目标：在 CPU 上完成 ≤100 局 DQN 对抗 DQN 自博弈训练，产出「真正会因手牌强弱而改变动作」的可加载策略文件，并把它固化成可一条命令复现的训练配置。上一次委派的 worker 在 worktree 中留下了未验证的 strength_shaping 实现与 --preset selfplay-v1（已实测：修好了坍缩，但对局贪心策略仍是恒定动作，未满足状态依赖），本次要求在其基础上收敛到达标并提交交付。Main Agent 只做调度与编排，编码与训练全部由子 Agent 完成。
验收：先完成 5 局测速并记录墙钟耗时；完成一轮不超过 100 局的 CPU 自博弈训练，实际产出可加载的策略文件（.pth）；训练 summary 含双方胜率、双方动作分布、耗时、局数；确认无塌缩：双方胜率不一边倒，训练期动作分布不退化为单一动作；关键：部署用贪心策略（epsilon=0）不得退化为单一动作 —— 必须用 epsilon=0 的 checkpoint 在 ≥2000 个真实状态上实测，给出动作分布，且动作分布需随手牌强度（beats_probability）变化；对局能自然结束：epsilon=0 双 checkpoint 评估的 natural_end_rate ≥ 0.9，不得全部撞 MAX_STEPS 强停；策略文件能被 DQNAgent.from_checkpoint 正常加载，input_dim=4 / action_dim=6，且隐藏层宽度为默认 (128,64) 以保证 UI 侧可直接加载；固定种子下训练可复现；训练超参固化进 scripts/train.py（一条命令可复现），并产出训练报告（命令、耗时、胜率、产物路径）
权限：{"commitBranch":true,"integrateBranch":false,"paths":["scripts","tests","run","docs"],"readRepository":true,"tools":["bash","read","edit","write","grep","find","ls"],"writeWorkspace":true}
当前工作空间：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100
基线：6bd6253bf9e122fe1df982f50e20b1b47f050db0
未提交文件：M .agent/telemetry-state.json； M .agent/telemetry.jsonl； M .pi/agents/reviewer.md； M .pi/settings.json； M PROGRESS.md；?? docs/review_train_100_final.md
最新交付：7d58d4ebfc91913c5fa1153eeed94f91a61f65dd
交付文件：A docs/selfplay_train_report.md；A management/evidence/logs/selfplay-pytest.txt；A management/evidence/logs/selfplay-ruff.txt；A management/evidence/logs/train100-pytest.txt；A management/evidence/logs/train100-ruff.txt；A management/evidence/logs/train100-train.txt；M scripts/env.py；M scripts/evaluate.py；M scripts/train.py；A tests/test_selfplay.py；A tests/test_selfplay_preset.py
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
