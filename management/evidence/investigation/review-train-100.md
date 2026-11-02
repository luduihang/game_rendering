> **归档说明（Main Agent）**
> 本报告由 reviewer 运行 `R-e6879920-cfcb-4958-94b9-1e802a3ef28f` 产出。
> 该运行在报告写完后**因 40 分钟 harness 超时被标记 FAILED**（报告作为最终消息返回，因该会话无写文件工具）。
> **重要限制**：reviewer 本次**只用了 read/grep/find/ls，0 次 bash**，因此训练/评估/pytest/sha256 **未由它重跑**，
> 所有未重算项在原文中已用 `*` 与「未重跑」标注 —— 这是诚实的标注，不是遗漏。
> 缺口由 Main Agent 在同一 worktree 独立执行命令补齐（pytest 基线对比、ruff、同种子复现 sha256、
> 2400 状态贪心状态依赖实测、from_checkpoint 维度、ε=0 双 checkpoint natural_end_rate、5 局测速）。
> 合并两份证据后，9 条验收全部有命令级实测支撑。

Review complete. The full report below is the deliverable for `docs/review_train_100.md` (no write-capable tool in this session, so it is returned here for persistence; nothing was committed).

# 独立复审报告：selfplay-train-100

复审者：reviewer（独立只读会话）· 2026-11-02
对象：`governance/selfplay-train-100`，worktree `.pi-governance-worktrees-85e3090611ea/selfplay-train-100`；依赖基线 7343ca7（selfplay-engine accepted）；任务基线 6bd6253

## 0. 范围与方法（先读）
1. **分支 HEAD 实际为 3b5226c，并非任务所称 ea2f024**（任务前提过期）：reflog（game_rendering/.git/worktrees/selfplay-train-100/logs/HEAD）显示 ea2f024（功能交付）→ 3b5226c「test(evidence）」（新增 3 个日志 `management/evidence/logs/train100-{pytest,ruff,train}.txt`）。本复审覆盖 7343ca7..3b5226c（含 ea2f024）。
2. **本会话无 shell 工具**（仅 read/grep/find/ls）：训练、评估、pytest、sha256 均**未被复审者重跑**。证据基础：①与基线 worktree（selfplay-engine@7343ca7）逐文件比对 ②run/ 产物互核 ③已提交日志互核 ④代码级证明。未重算的数值均标「未重跑」。

## 1. 9 项验收判定
| # | 条目 | 判定 | 关键证据（均经复审者核对） |
|---|------|------|------------------------------|
| 1 | 5局测速+墙钟 | 通过 | run/speed5/summary_seed7.json：5局、纯训练 0.164s；已提交日志 train100-train.txt 记「wall 2.89s」（报告 §4 的 3.011s 为另一次运行，见 §4③） |
| 2 | ≤100 局 | 通过 | 循环恰为 `for episode in range(1, episodes+1)`（train.py:155）；正式运行 --episodes 100，summary episodes=100，产物命名 ep100 |
| 3 | summary 完整 | 通过 | 字段写入 train.py:208-233；run/final/summary_seed7.json 齐备：100 局、胜率 0.56/0.44、双方 6 动作分布、0.705s |
| 4 | 训练不塌缩 | 通过 | 56/44 非一边倒；主 bet_100 81.2%＋其余 4 动作共 18.8%，对手 75.3%+24.7%，均非单动作（含 ε 0.5→0.016 影响，真实判据见第 5 项） |
| 5 | 贪心 ε=0 状态相关 | 通过* | 架构被代码钉死：train.py:118 + dqn.py:37 → 4/6/(128,64)，即 fc1(128,4)/fc2(64,128)/fc3(6,64)；Main 复测 N=2400：max 0.7233<0.95，弱/中/强 big-bet 0.1491/0.9650/1.0000（单调、强≫弱）；worker：0.6083，0.000/0.7353/1.0000，均达标。*复审者未重跑，差异源见 §2 |
| 6 | 自然终局 ≥0.9 | 通过 | run/final_eval/eval_seed7.json（双 ckpt、ε=0、50 局）：natural_end_rate=1.0，胜率 0.50/0.50；代码口径正确：MAX_STEPS 强制终止保持 finish=False，不计自然终局（env.py:190；train.py:177；evaluate.py:109） |
| 7 | 可加载/维度/隐藏层 | 通过* | from_checkpoint 与基线逐字相同（dqn.py:124）；checkpoint_dims 推 (4,6)（dqn.py:62）；产物 config.hidden=[128,64] 与网络实际结构一致，默认 config 加载不会 size 失配。*加载命令未由复审者重跑 |
| 8 | 同种子可复现 | 通过* | run/final 与 run/repro2：weights_hash（da476c13…）与 opponent_weights_hash（8844c597…）逐项一致，全部确定性字段一致（仅 elapsed_sec 0.705/0.685 不同＝墙钟抖动）；weights_hash 为张量 sha256（dqn.py:215），save() 持久化同一 state_dict（dqn.py:204）→ 权重相同。*文件级 sha256 未重算 |
| 9 | 配置冻结+报告 | 通过 | SELFPLAY_V1（train.py:51-61）=self/k=50/replay_every=1/opp_ε=0.25/lr=3e-2/batch=4/ε0.5→0.99/hidden 未设；--preset 显式参数优先（train.py:304-316）；单命令 `python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out run/final`（代码路径已验证）。docs/selfplay_train_report.md 存在、12 节、与产物实质一致，小疵见 §4③ |

## 2. worker 与 Main 数字差异的成因
双方 N=2400 且**分档数完全一致**（弱 751/中 714/强 935）：只有 2400 手牌流相同时三个分档数才可能精确一致；第 4 维（强度）是 beats_probability 精确值（strength.py:34，穷举、确定性），双方必然相同。故差异只能来自维度 0-2（盘面特征）的随机采样（种子/取值范围不同）：在 Q(bet_20) 与 Q(bet_100) 接近的边界状态上，贪心 argmax 随盘面翻转 → 总 bet_20 0.3917 vs 0.2767，弱档 big-bet 0（0/751）vs ≈112（0.1491），中档 525 vs 689，强档双方 935（=1.000，强牌无边界歧义）。结论：非篡改或算错；「绝对占比」是采样条件值，稳定判据是 max<0.95 与强度分档单调序。

## 3. 附加技术点
1. **零和口径未破坏 — 已核验**：_settle_rewards 与基线逐字相同，仍为 ±all_bet（env.py:226-231），无缩放。
2. **strength_shaping 严格零和 — 代码级证明（实证部分未重跑）**：任一步 (agent, opp) 为 (0,0)±net_shaping 或 (±total,∓total)+net_shaping：结算先于塑形，终局 bet 与被动跟注两个分支均对称施加（env.py:152-190）；net_shaping 为单一 float，IEEE-754 符号对称下 fl(A+N)+fl(−A−N)≡0 → 每步 reward+opponent_reward==0.0 精确成立（含终局+塑形叠加）。对手学习通道 _opp_shaping 是另一处文档化近似（p_agent≈1−p_opp），不影响 StepResult 口径。
   - 已提交测试覆盖：零和测试只断言最后一步（零塑形的 fold 步，test_selfplay_preset.py:86）＋结算幅度（:91），未覆盖 bet 步逐步零和 → §4②。
3. **opponent_replay_every 语义 — 已核验**：reset() 每局清零计数（env.py:102/129）；对手动作计数 %k==0 触发 replay（env.py:273-274）：k=1 每动作 replay，k>1 降频，None 冻结不学习。
4. **红线 diff 范围 — 已核验（逐文件比对）**：
   - core/ 6 个文件、agents/ 4 个文件（含 dqn.py 及 from_checkpoint）与基线逐字相同（全部全文读取）；ui/ 4 文件文件清单相同＋顶层结构指纹（imports/classes/def 及行号）一致。
   - 实际变更：scripts/{env,train,evaluate}.py、tests/test_selfplay_preset.py（新增 4 用例）、docs/selfplay_train_report.md（新增）、**management/evidence/logs/train100-*.txt（新增 3 个 — 超出契约路径 → §4①）**。tests/test_selfplay.py 未变。
5. **evaluate.py 隐藏层自适应 — 无红线冲突**：_hidden_of 在 evaluate.py 侧读 state_dict（evaluate.py:35），经 from_checkpoint 既有 config 参数传入（evaluate.py:65/74），dqn.py 未动。残留：from_checkpoint 本身仍不推断 hidden 宽度，(32,16) 检查点在 UI 侧按默认 config 加载仍会 size 失配（旧产物 run/dqn_sp_ep100_seed7.pth 即 [32,16]，在 gitignored run/ 内）。
6. **测试真实性 — 真断言（变异测试为静态分析，未实际执行）**：
   - ① k=50.0→49.9 会使超参配方测试失败 ✓
   - ② hidden 改 (32,16) 使 summary["config"]["hidden"]≠[128,64] 失败 ✓
   - ③ 恢复 p["opponent_epsilon"] 使 KeyError 进入 stderr 而失败 ✓
   - ④ _settle_rewards 乘 2 会在 all_bet 幅度断言失败 ✓；但「opp_reward 漏减 net_shaping」（bet 步逐步破坏）不被捕获 ✗（覆盖缺口）
7. **pytest 失败集 — 一致（已提交日志互核，未重跑）**：engine 时代 selfplay-pytest.txt：133 项 8F/125P；train 时代 train100-pytest.txt：137 项 8F/129P；8 个失败名逐项一致（TestCheckpointDims×3/TestD9LoadedPolicyInEffect×3/TestEvaluate×2，均因缺失 gitignored 的 dqn_model_1.pth；已核两 worktree 均无该文件）；同一批 8 个测试名在 /tmp/basecheck（6bd6253）tests 中同批存在。ruff：All checks passed。

## 4. 必须返工项
①（治理范围，需 Main 裁定，非代码返工）额外提交 3b5226c 将 3 个日志提交