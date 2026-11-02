# T3 独立复核报告：玩家 vs 机器对抗接线（4e6570a + bfa9881）

复核人：reviewer（只读，未改源码、未提交）。bash 可用；HEAD=bfa9881；权重已就位。
以下数字全部为复核人本人实测。

## 逐条判定

1. **DEFAULT_CHECKPOINT 指向自博弈产物 — 通过**
   `ui/app.py:29` DEFAULT_CHECKPOINT=REPO/"dqn_model_1.pth"。
   sha256(dqn_model_1.pth)=sha256(run/final/dqn_sp_ep100_seed7.pth)=52144d10…37b22，逐位一致；
   checkpoint_dims 实测 (4,6)，即 T2 权威产物 run/final/*.pth 的部署副本。

2. **路径可配置（CLI>env>默认）— 通过**
   实测 resolve_checkpoint：默认→REPO/dqn_model_1.pth；env=/tmp/from_env.pth 生效；
   CLI+env 同时→CLI；相对 run/final/...→按 REPO 解析；绝对路径不变。
   `draw_me_vs_DQN_Plus.py --help` 显示 --checkpoint；实跑
   `SDL_VIDEODRIVER=dummy python draw_me_vs_DQN_Plus.py --checkpoint run/final/dqn_sp_opp_ep100_seed7.pth`
   → `[信息] 已加载 …/run/final/dqn_sp_opp_ep100_seed7.pth（epsilon=0.0 贪心策略）`，对局循环正常启动。
   入口 argparse 读 sys.argv，透传属实。

3. **缺失/损坏权重可见告警 — 通过**
   缺失（/tmp/nonexistent.pth）：三行 [警告]，明写「未训练随机策略（epsilon=0.15），不是训练出的策略」，
   trained=False、policy_source=untrained-random(epsilon=0.15)。
   损坏（5000 随机字节）：不崩溃（torch 2.6 weights_only 异常被捕获），同样三行警告 + 回退 0.15。

4. **加载训练权重后 epsilon==0.0 — 通过**
   实测 from_checkpoint 的 agent.epsilon=0.0，input_dim=4、action_dim=6。

5. **headless 端到端 — 通过**（复核人独立驱动脚本，seed=20260102，前5手最小档+其后 COMPARE）
   11 步自然结束；history [(0,0),(1,3),(0,3),(1,3),(0,3),(1,3),(0,3),(1,3),(0,3),(1,3),(0,5)]，
   座位序列 [0,1]×5+0 严格交替；人类 6 手/机器 5 手；winner=1、底池 1020、资金守恒
   （19485+20515=40000）；机器 5 手全部等于独立参考 agent 的 argmax（0 处不一致）。
   说明：Main 报告的 5 步 history [0,1,0,1,0] 是不同 COMPARE 时机的驱动策略，非代码差异。

6. **动作来自训练权重（断言强度+变异测试）— 通过**
   断言强度：逐回合与独立加载参考 agent 的 argmax 一致（含 in-game ≥3 次）+ 同状态 21 次确定性 +
   与 epsilon=1.0 随机策略分布对比。
   本人变异（app.py:84 from_checkpoint→DQNAgent(input_dim=4,action_dim=6,epsilon=0.15)）：
   pytest tests/test_trained_ui.py → **6 FAILED + 3 ERROR**；还原后 git diff 为空、17 passed。能抓到换随机。

7. **pytest/ruff 全绿 + 无既有测试被打红 — 通过**
   HEAD：156 passed in 14.95s；ruff All checks passed。
   基线 7d58d4e（临时 worktree + 权重）：139 passed / 0 failed，ruff 绿；139+17 新=156。
   test_ui.py(27)/test_agents.py(20)/test_scripts.py(13) 全绿。提交证据日志 t3-pytest.txt 与实测一致。

8. **红线 — 通过**
   git diff 7d58d4e..HEAD --stat：README.md、docs/TRAINED-WEIGHTS-UI.md、tests/test_trained_ui.py、
   ui/app.py、management/evidence/logs/t3-{pytest,ruff}.txt（bfa9881 仅证据日志 21 行）。
   core/、agents/ 零改动（diff 为空）；ui/app.py 改动仅限 checkpoint 解析/_load_agent/main argparse，
   view 五字段契约未变；4 维输入/6 维动作未变。
   注：bfa9881 的 evidence 日志不在契约 paths 内，但符合本仓 "test(evidence)" 惯例（基线 7d58d4e 同类），无功能改动。

9. **pickle.PickleError 健壮性扩改 — 恰当**
   实测损坏权重不再崩溃、走可见告警回退；改动局限于 _load_agent 的 except 元组，不改行为。可接受。

10. **docs/README 属实性 — 通过（小瑕疵）**
    权重来源、优先级、缺失/损坏行为、测试覆盖描述均与实现一致；.gitignore `*.pth`(17 行)+`run/`(23 行) 属实。
    瑕疵：docs 中行号引用 ui/app.py:27/31/83-84 实为 29/33/71-73（漂移 2–10 行），不影响理解。

11. **其他调用方 — 通过**
    tests/test_ui.py(2 处)、tests/baseline/repro_d7_timing.py(2 处) 不带 checkpoint 构造 Controller，
    None→默认解析，全部通过；入口脚本实启动正常。

## 必须返工项
无。（可选：修正 docs/TRAINED-WEIGHTS-UI.md 中 3 处行号引用。）

## 风险与遗留
- 权重被 gitignore，不进版本库；新环境需重训或拷贝（文档已说明）。
- except 元组非穷举白名单：若 from_checkpoint 未来抛其他类型异常（如 OSError 之外的罕见类型）仍会崩溃；当前 torch 2.6 实测已覆盖 FileNotFoundError/ValueError/RuntimeError/PickleError 常见路径。
- 工作区存在与本任务无关的既有未提交改动（.pi/settings.json、PROGRESS.md、telemetry）。

## UNKNOWN
无（11 项均亲自实测）。
