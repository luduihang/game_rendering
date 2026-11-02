# 交付报告 — selfplay-train-100 (R-c1712b23)

**分支**：`governance/selfplay-train-100`，提交 `ea2f024`（基线 HEAD 7343ca7 + 上一位 worker 未提交成果，已评估、修复并接续）。全部 9 条验收通过。

## 1. 修复的两个缺陷
1. **CLI 崩溃**：`scripts/train.py:333` — `opponent_epsilon=p["opponent_epsilon"]` 改为 `p.get("opponent_epsilon")`，缺省 `None` 由 `train()` 按模式取缺省（self=1.0 / snapshot=0.0）。已实测 `python -m scripts.train --episodes 5 --seed 7 --opponent-mode self` 不再 KeyError。
2. **preset 超参不符**：`scripts/train.py:51` `SELFPLAY_V1` 由 `strength_shaping=0.5, hidden=(32,16)` 改为 `strength_shaping=50.0`，`hidden` 从 preset 移除（缺省 None = 默认 (128,64)），`lr=3e-2 / batch_size=4 / epsilon_decay=0.99 / opponent_replay_every=1` 保留。移除 hidden 的原因：`DQNAgent.from_checkpoint` 不推断隐藏宽度，(32,16) 会让下游 UI 加载 size mismatch。

## 2. preset 最终超参（scripts/train.py:51-61）
`opponent_mode=self, opponent_epsilon=0.25, opponent_replay_every=1, strength_shaping=50.0, hidden=缺省(128,64), lr=3e-2, gamma=0.95, batch_size=4, epsilon_start=0.5, epsilon_decay=0.99`，episodes=100。

## 3. 正式训练
```
python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out run/final
```
墙钟 **3.320 s**（纯训练 `elapsed_sec=0.702`；5 局测速墙钟 3.011 s / 纯训练 0.164 s）。summary 全文已附于 `docs/selfplay_train_report.md` §4；关键项：胜率 **56/44**、`natural_end_rate=1.0`、`total_steps=346`、双方动作分布各含 6 种动作（agent 最大 bet_100=0.8121，未单动作化）。

## 4. 贪心（ε=0）状态依赖 + 对抗评估
- 2400 个真实状态（真发牌 + `beats_probability`，前 3 维 `random.Random(20261102)`）：总分布 **{bet_20: 0.3917, bet_100: 0.6083}**（2 动作，max 0.608<0.95）。分档：**弱牌 p≤0.3（n=751）大注占比 0.000；中牌（n=714）0.7353；强牌 p>0.6（n=935）1.000**，强−弱差 +1.0，单调性成立。
- 双 checkpoint 50 轮（ε=0）：`natural_end_rate=1.0`，胜率 0.50/0.50（和=1.0）。

## 5. 复现性与加载
同 seed 两次训练（run/final vs run/repro2）sha256 一致：主 `52144d10…37b22`、对手 `528a3c64…e7`。`from_checkpoint` 加载无报错，`fc1=(128,4), fc2=(64,128), fc3=(6,64)`，hidden (128,64)。

## 6. 产物绝对路径
- `/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100/run/final/dqn_sp_ep100_seed7.pth`
- `/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100/run/final/dqn_sp_opp_ep100_seed7.pth`
- summary：`.../run/final/summary_seed7.json`；评估：`.../run/final_eval/eval_seed7.json`（run/ 被 gitignore，一条命令可再生）

## 7. 回归与检查
- pytest：**8 failed / 129 passed**（基线 8 failed/125 passed，8 个失败全为既有缺 `dqn_model_1.pth` 环境问题，**无新增失败**；+4 为新增测试 `tests/test_selfplay_preset.py`）
- ruff：All checks passed
- 新增 4 例测试：preset 超参防回归、preset 一条命令产出双 checkpoint（hidden=(128,64)）、非 preset CLI 不 KeyError、k=50 时 `_settle_rewards` 零和性（`scripts/env.py:226` 口径未动，`agent_reward+opponent_reward==0` 每步成立）

## 8. 与参考值的偏差（如实汇报）
seed=7 胜率实测 56/44（参考 42/58）；贪心强牌大注占比实测 1.000（参考 ≈0.40），弱牌 0.000（参考 ≈0.01）。均为同方向更强表现，验收标准全部满足，未做 seed 挑选或口径改动。无未达标项。

**遗留说明**：`PROGRESS.md`、`.agent/*` 为上一位 worker 的超范围未提交改动，按授权路径（scripts/tests/run/docs）未纳入本次提交，留待 Main Agent 处置。实验次数：8 次训练/评估 + 2 次 pytest + 2 次 ruff，远低于 12 次上限；全程约 25 分钟。