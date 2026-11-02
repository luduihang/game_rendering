> **归档说明（Main Agent）**
> 本报告由 reviewer 运行 `R-f3136e0a-a69b-4dd4-8add-51a06956a570` 产出（静态核验版）。
> **该 reviewer 会话无 bash 工具** —— 根因：`.pi/settings.json` 的 `subagents.agentOverrides.reviewer.tools`
> 与 `.pi/agents/reviewer.md` 均未提交，而 `agentOverrides` 会**覆盖**定义文件的 tools，
> 导致所有 worktree 里的 reviewer 只有 read/grep/find/ls。
> 已修复并提交（`d67a0c0` + `e4e44f6`）。静态结论有效并已采纳；动态项由后续带 bash 的 reviewer 补跑。

Supervisor 已确认修复并指示我先探测 bash。我必须如实说明：**我的会话工具计划已固化**——本会话可用工具仍只有 `read/grep/find/ls/contact_supervisor`，函数表里没有 bash，我无法执行 `bash -lc 'echo TOOL_OK'` 探测（不是拒绝执行，是该工具不存在于本会话）。按指示不空等，直接返回已完成的全部静态核验结论作为最终报告。

---

# T2 最终复核报告（静态核验版 · 动态项未重跑）

**总体结论：证据不足**。静态可核项全部与交付一致（2 处分歧已由 supervisor 确认/定性），但任务核心的动态重跑（训练/pytest/ε=0 评估/sha256/变异/git diff/torch 形状）本会话一条都未执行，全部标 UNVERIFIED，需有 bash 的新 reviewer 补跑。

## 0. 环境
worktree 分支 reflog（`game_rendering/.git/worktrees/selfplay-train-100/logs/HEAD`，已读）：`6bd6253`（基线）→ `7343ca7`（merge selfplay-engine）→ `ea2f024`（功能）→ `3b5226c`（证据日志）→ `fad9206`（返工测试）→ **`7d58d4e`（新证据日志提交）**。HEAD=7d58d4e 与任务描述（fad9206）不符，supervisor 已确认是其追加提交；其改动文件范围**未核验**（git diff 需 bash）→ UNKNOWN。

## 1. 逐条结论

| # | 项 | 判定 | 我的证据 |
|---|---|---|---|
| 1 | 5 局测速 | UNVERIFIED | 产物级：`run/speed5/summary_seed7.json` episodes=5、elapsed_sec=0.164，与报告"纯训练 0.164s"一致；墙钟 3.011s 仅见报告文字，无原始日志 |
| 2 | ≤100 局 | 通过（静态） | summary episodes=100；循环 `train.py:155` `for episode in range(1, episodes+1)`（无硬上限，交付跑 100 局） |
| 3 | summary 字段 | 通过（静态） | `run/final/summary_seed7.json` 含 agent/opponent_win_rate、双方 action_distribution、elapsed_sec=0.705、episodes=100 |
| 4 | 训练无塌缩 | 通过（产物级） | 胜率 0.56/0.44 不一边倒；agent 分布 6 动作（bet_100 0.8121 主导但非单一）。未实跑重验 |
| 5 | ε=0 状态依赖 | UNVERIFIED | 未重跑。且两套数字矛盾：报告§5（{bet_20:0.3917, bet_100:0.6083}，弱0.000/中0.7353/强1.000）vs Main Agent（{664,1736}，max 0.7233，弱0.1491/中0.9650/强1.0）。n=751/714/935 相同但 bet_100 计数 1460 vs 1736 → 两次评估的盘面特征种子或加载 checkpoint 不一致，我无法裁决；两套均满足判据（max<0.95、强≫弱单调） |
| 6 | natural_end_rate | UNVERIFIED | 未重跑。产物级：`run/eval_seed7.json`（50 局、ε=0、双 checkpoint）natural_end_rate=1.0、胜率 0.5/0.5，达标 |
| 7 | from_checkpoint | 代码通过 + 执行 UNVERIFIED | `agents/dqn.py:123-143`：input/action 由 `checkpoint_dims` 自适应，hidden 取 `config or DQNConfig()` **不推断宽度** → 默认 config 加载仅当产物 hidden=(128,64) 才安全；实际加载未跑 |
| 8 | 可复现 | UNVERIFIED | sha256 未重算。报告§8 与 Main Agent 的哈希一致（52144d10…/528a3c64…），`run/repro2/summary_seed7.json` 证据文件仍在 |
| 9 | 配置固化+报告 | 通过（静态） | `SELFPLAY_V1` @ `train.py:51-61`（k=50.0、hidden 缺省、lr 3e-2、batch 4、decay 0.99、replay_every 1、opp_eps 0.25），CLI @ `train.py:304`；`docs/selfplay_train_report.md` 存在且含命令/耗时/胜率/产物路径/sha256/偏差说明 |
| 10 | 逐步零和变异测试 | 执行 UNVERIFIED；代码级非恒真 | `tests/test_selfplay_preset.py` `TestStepwiseZeroSumWithShaping`：确定性 `_AlwaysCallOpponent`、3 seeds×20 局、每步严格 `residual==0.0` 断言 + 防空转覆盖断言（`bet_steps_nonzero_shaping>0` 等）。若 `env.py:189` `opp_reward -= net_shaping` 被破坏，非零塑形押注步残差必非 0 → 逻辑上必 FAILED，但**变异实测输出缺失** |
| 11 | checkpoint 可加载测试 | 代码通过（静态） | `test_preset_checkpoint_loadable_with_default_config`：真实 CLI 跑 100 局 → `DQNAgent.from_checkpoint` **不传 hidden** → 断言 fc1 4→128、fc2 64、fc3 6、epsilon=0.0（主/对手均断言）。未实跑 |
| 12 | 红线 diff | UNKNOWN | `git diff 7343ca7..7d58d4e --stat` 未执行；reflog 仅证明 4 个提交标签为 feat(selfplay)/test(evidence)/test(selfplay)，文件清单未核验，`agents/ core/ ui/` 零改动**未证实** |
| 13 | _settle_rewards 未缩放 | 通过（静态） | `scripts/env.py:226-232`：`total=float(room.all_bet)`，返回 `(total,-total)/(-total,total)`，无缩放；塑形零和对冲在 `env.py:187-189` |
| 14 | run/ 产物唯一性 | 通过（目录级）+ 形状 UNVERIFIED | `run/final/` 恰好 3 个 .pth（2 权威 + `_sync_tmp_seed7.pth`）；其余 13 个实验子目录（base100/clireg/k1/k2a/k2b/probe_v1/repro/repro2/robust_1-3/robust_7/sped5/speed5）及 final_eval 均 0 个 .pth，仅 JSON 证据。fc1=(128,4) 未 torch.load 核验 |

## 2. 必须返工项
- **R1（文档表述，轻微）**：`docs/selfplay_train_report.md` §13「run/ 下现仅存 run/final/ 三个 .pth（§9 唯一权威产物）」与 §9（权威仅 2 个）矛盾。应按 supervisor 确认口径改为「2 个权威产物 + 1 个对手同步临时文件」，并建议 `train.py:203-205` 同步结束后删除 `_sync_tmp_*` 残留。
- 其余功能返工点：静态范围**无**（动态项以新 reviewer 重跑为准）。

## 3. 风险与遗留
1. 全部动态项未重跑，本报告不构成交付放行依据。
2. ε=0 评估两套数字矛盾（第 5 项），评估脚本的盘面特征种子/checkpoint 口径未固化，需新 reviewer 用固定脚本重算裁决。
3. `7d58d4e` 改动范围未核验（红线结论悬置）。
4. 墙钟 3.011s、pytest 8f/131p、ruff、变异 FAILED 输出均为二手声明，无原始日志归档于本 worktree（证据日志在 management/，我未逐一比对）。

## 4. 给新 bash reviewer 的最小命令清单
```bash
cd /home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100
time python -m scripts.train --preset selfplay-v1 --episodes 5 --seed 7 --out /tmp/rev5
python -m pytest tests/ -q        # 对比 /tmp/basecheck 失败集合
# ε=0 评估：固定脚本 new_deck+deal_uniform+beats_probability+random.Random，N≥2400
python -m scripts.evaluate --checkpoint run/final/dqn_sp_ep100_seed7.pth \
  --opponent-checkpoint run/final/dqn_sp_opp_ep100_seed7.pth --rounds 50 --seed 7
python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out /tmp/revA
python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out /tmp/revB
sha256sum /tmp/revA/*.pth /tmp/revB/*.pth
# 变异：sed -i 's/opp_reward -= net_shaping/pass/' scripts/env.py 后
python -m pytest tests/test_selfplay_preset.py::TestStepwiseZeroSumWithShaping -q   # 期望 FAILED
git checkout -- scripts/env.py && git diff --stat scripts/env.py   # 期望空
git diff 7343ca7..HEAD --stat
python -c "import torch; [print(f, torch.load(p,weights_only=True)['fc1.weight'].shape) for p in __import__('glob').glob('run/final/*.pth')]
```

## 5. 结论
静态核验 14 项中 7 项通过（静态/产物级）、4 项 UNVERIFIED（1/5/6/8）、2 项 UNKNOWN（12、14-形状）、1 项代码级通过待实跑（10/11 合并）。**不能放行**，待有 bash 的 reviewer 完成 §4 清单后出最终结论。