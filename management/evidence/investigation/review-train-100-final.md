# T2 最终独立复核（R-f20e8e16，带 bash 动态核验）

分支 governance/selfplay-train-100，HEAD=7d58d4e，基线 6bd6253。复核范围 7343ca7..HEAD（4 提交：ea2f024/3b5226c/fad9206/7d58d4e）。
`git diff 7343ca7..HEAD --stat`：仅 scripts/(env,evaluate,train)、tests/test_selfplay_preset.py、docs/selfplay_train_report.md、management/evidence/logs/* —— agents/、core/、ui/ **零改动** ✓。

## 逐项判定

1. **5 局测速 通过**：实跑 `--preset selfplay-v1 --episodes 5 --seed 7`，墙钟 3.09s（含 torch 导入），summary `elapsed_sec=0.174`；run/speed5 亦 0.164s。100 局 summary `elapsed_sec=0.705`。
2. **≤100 局 通过**：训练循环 `for episode in range(1, episodes+1)`（scripts/train.py:155），CLI 固定 `--episodes 100`；run/final/summary episodes=100。
3. **summary 字段 通过**：双方胜率 0.56/0.44、双方 6 动作分布、elapsed_sec、episodes、natural_end_rate、weights_hash 齐全。
4. **训练期无塌缩 通过**：win_rate 0.56 vs 0.44 不一边倒；agent 动作分布 bet_100=0.8121 但 bet_20 0.0347/bet_10 0.026/bet_50 0.0116/fold 0.0376/compare 0.078，非单一动作。
5. **ε=0 状态依赖 通过（含分歧裁决）**：自写 /tmp 脚本，N=2400 真实状态（`new_deck`+`deal_uniform`+`beats_probability`；前 3 维 circle/10∈0.1~2.0、双方累计押注/1000 固定种子 `random.Random` 采样，第 4 维确定性），`from_checkpoint` 加载后 ε=0 贪心：
   - 总分布：bet_100=0.6517、bet_20=0.3483（max=0.6517 < 0.95）
   - 大注(bet_50+bet_100)占比：弱(≤0.3)=**0.0083**(n=725) / 中(0.3,0.6]=**0.8415**(n=738) / 强(>0.6)=**1.0000**(n=937)
   - 4 个不同盘面种子稳健性：总 bet_100 0.653~0.674；弱 0.008~0.017；中 0.84~0.86；强恒 1.0。弱→中→强单调 ✓，强≫弱 ✓。
   - **分歧 1 裁决**：worker(0.3917/0.6083) 与 Main(664/1736) 的三档手数完全相同(751/714/935)，说明手牌采样同种子同流程；差异全部来自**前 3 维盘面特征的随机种子/取值范围不同**——fc1 对 4 维权重均非零，盘面取值会翻转阈值附近（尤其弱/中档）状态的 argmax。两套数字都"正确"，差异非 bug。我的独立数字：见上（总 bet_100 0.6517，档占比 0.0083/0.8415/1.0000），落在两套之间，与两套结论一致（单调、非退化）。
6. **natural_end_rate 通过**：实跑 `python -m scripts.evaluate --checkpoint run/final/dqn_sp_ep100_seed7.pth --opponent-checkpoint run/final/dqn_sp_opp_ep100_seed7.pth --rounds 50 --seed 7` → `natural_end_rate=1.0` ≥0.9，evaluate 两侧 ε=0.0。
7. **from_checkpoint 通过**：加载无异常；input_dim=4、action_dim=6、fc1=(128,4)、fc2=(64,128)、fc3=(6,64)、epsilon=0.0；opp checkpoint 同样加载成功。
8. **可复现 通过**：我自己重跑 `--preset selfplay-v1 --episodes 100 --seed 7` 到 /tmp，产物 sha256 与 run/final 逐字节一致（agent 52144d10…、opp 528a3c64…）；run/repro2 的 weights_hash 亦与 final 相同（run/repro 是旧 [32,16]/shaping=0.5 实验，配置不同，不计入）。
9. **配置固化 通过**：`SELFPLAY_V1`（scripts/train.py:51-62）：strength_shaping=50.0、lr=3e-2、batch_size=4、epsilon_decay=0.99、opponent_replay_every=1、hidden 缺省(None→(128,64)) 全符合；docs/selfplay_train_report.md 存在(12.3KB)，数字与实测一致。
10. **变异测试 通过**：env.py:189 `opp_reward -= net_shaping`→`pass` 后 `pytest tests/test_selfplay_preset.py` → FAILED `TestSettleZeroSumWithShaping::test_settle_rewards_zero_sum_with_strength_shaping`（-26.38 + -20.0 ≠ 0）；`cp` 还原后 `git diff --stat scripts/env.py` 为空。
11. **checkpoint 可加载性测试 通过**：`test_preset_checkpoint_loadable_with_default_config`（tests/test_selfplay_preset.py:71）真实训练 100 局后用**默认 config**（不传 hidden）加载，断言 fc1 4→128、fc2→64、fc3→6、epsilon=0.0，双方 checkpoint 均断言。
12. **红线 通过**：diff 范围仅 scripts/tests/docs/management；agents/dqn.py 含 from_checkpoint 未被触碰。
13. **_settle_rewards 通过**：env.py:226-232 仍为赢方 `+all_bet`/输方 `-all_bet`，未缩放。
14. **pytest 失败集合 通过**：本分支 8 failed / 131 passed（共 139），FAILED 8 条与基线 /tmp/basecheck（6bd6253）逐条 diff **完全一致**（均为缺 dqn_model_1.pth 的既有 keeper 失败）；把 run/final/dqn_sp_ep100_seed7.pth 复制为根目录 dqn_model_1.pth 后全套件 0 failed（139 全绿），已删除临时文件。
15. **ruff 通过**：`python -m ruff check .` → All checks passed!
16. **run/ 产物 通过**：`find run -name '*.pth'` 仅 run/final/ 3 个（dqn_sp_ep100、dqn_sp_opp_ep100、_sync_tmp）；三者 torch.load fc1 均 (128,4)。_sync_tmp 为 train.py 对手同步临时文件，非权威产物，口径确认。

## 必须返工项
无。

## 风险与遗留
- evaluate 50 局对局中动作分布偏置（bet_100≈0.97），但 natural_end_rate=1.0，不违反任何验收条款；策略在真实对局路径上偏保守押法，UI 实际对战表现留待后续验证。
- run/repro（旧 [32,16] 实验目录）与多个中间目录（k1/k2a…）留在 run/ 下，属历史实验，不影响交付；可清理。
- 工作区存在未提交的 .agent/、.pi/、PROGRESS.md 改动（orchestration 元文件），不在本任务 diff 范围内，已忽略。
