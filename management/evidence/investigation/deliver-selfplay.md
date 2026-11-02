All verification complete. Here is the delivery report.

---

# 交付报告：DQN 对抗 DQN 自博弈训练机制

**提交**：`cb813cf` @ `governance/selfplay-engine`（worktree），4 文件，+576/-46。`agents/dqn.py` **零改动**；`core/`、`ui/`、`README.md` **零改动**；状态编码保持 4 维输入 / 6 维动作。

## 改了什么（逐文件逐处）

**scripts/env.py**
- `:34` 新增共享常量 `ACTION_NAMES`（供 train/evaluate 复用）。
- `:66-92` `__init__`：`opponent: BaseAgent | None`（缺省仍 `Robot("1", seed=seed)`）；新增 `swap_seats: bool | None = None`（None=自动：DQN 对手→交换，Robot→不交换）与 `opponent_replay_every: int | None = 1`（1=每次行动后 replay；k=每 k 次；None=冻结策略不学习）；`opponent_seat` 提为实例属性（`:73`）；新增 `_episodes`、`opponent_action_counts`、`_opp_pending`（对手待结算经验）、`_opp_actions`。
- `:94-97` `is_dqn_opponent` property：两条路径的分叉点。
- `:99-125` `reset()`：座位交换（`:100-111`，见下）；对手分支（`:120-123`）——Robot 保留 `reset()`+`init_dick(["1","0"], hands[opponent_seat])`（顺序与取值与旧实现逐字一致），DQN 只调 `reset()`。
- `:134-174` `step()`：`:145-146` Robot 才 `_notify_opponent`；`:148-157` 结算改双值；`:162-164` DQN 对手在结算后 finalize 待结算经验；`:169-174` info 新增 `opponent_reward`。
- `:182-186` **新增 `_opponent_observation()`**：`encoder.encode(snapshot, opp_seat, own_hand(opp_seat))`，对手视角 4 维。
- `:188-194` **`_settle_reward` → `_settle_rewards()`**：返回 `(agent_reward, opponent_reward)` 零和双值。
- `:196-210` `_advance_opponent_until_agent_turn()`：`:200-210` 分叉——DQN 走 `_dqn_opponent_act`；Robot 分支保持原 `snapshot→act→apply→notify` 顺序（`actor` 在 apply 前捕获，与旧实现一致）。
- `:212-227` **新增 `_dqn_opponent_act()`**：先 finalize 上一条经验 → 对手视角观测 → `opponent.act` → apply → 记录新 pending → 每 k 次 `replay()`。DQN 路径**不**复用吞异常的 `_notify_opponent`。
- `:229-243` **新增 `_finalize_opponent_transition()`**：把 pending 变成对手视角 `Transition`（终局带对手零和奖励、done=True）调 `opponent.observe()`。

**scripts/train.py**
- `:58-72` `train()` 增参：`opponent_mode("robot"|"self"|"snapshot")`、`opponent_ckpt`、`opponent_sync_every`（None=自动 max(1, episodes//4)，0=关）、`opponent_replay_every=4`、`opponent_epsilon`（None→self=1.0 / snapshot=0.0）。
- `:96-113` 对手构造分叉：self=在线 DQN（`seed+1` 独立 RNG 流，避免与主策略探索同步）+ 降频 replay；snapshot=`from_checkpoint` 且 `opponent_replay_every=None`（冻结）。
- `:119-122`、`:144` 双方动作计数。
- `:148-156` self 模式周期性 `agent.save(tmp)` + `opponent.load(tmp)` 快照重置对手（终局前不触发）。
- `:163-179` summary 新增：`opponent_mode`、`agent_win_rate`/`opponent_win_rate`（双方胜率）、`agent_action_distribution`/`opponent_action_distribution`、`opponent_weights_hash`；保留 `elapsed_sec`、`episodes`。
- `:181-192` checkpoint 命名：self/snapshot → `dqn_sp_ep{N}_seed{S}.pth` + `dqn_sp_opp_ep{N}_seed{S}.pth`；robot 沿用旧 `dqn_ep{N}_seed{S}.pth`（无对手 checkpoint）。
- `:201-244` `main()` 新增 5 个 CLI 参数。

**scripts/evaluate.py**
- `:35-58` `evaluate()` 增参 `opponent_checkpoint`：非空时对手为冻结 DQN（`epsilon=0`，`opponent_replay_every=None`），env 自动每轮交换座位；单 checkpoint 模式行为不变（对手 Robot）。
- `:92-98` summary 新增 `opponent_checkpoint`、`opponent_win_rate`、`opponent_action_distribution`。
- `:131` CLI `--opponent-checkpoint`。

## 零和奖励口径与理由
选**赢方 +all_bet、输方 -all_bet**（env.py:188-194）。理由：① 严格反对称，`agent_reward + opponent_reward == 0` 恒成立（旧口径输方 -己方已押，双方押注不等时不对称）；② 与规则结算一致（`rules.py _finish`：赢家拿走 all_bet 池）；③ 对称，座位交换后两方策略学到同一语义。副作用：robot 模式输局奖励由 `-agent_bet` 变为 `-all_bet`（任务要求改造 `_settle_rewards` 口径，属预期变更；既有测试不依赖具体数值，全部仍绿）。

## 座位交换实现
`scripts/env.py:100-111`（env 层，core 零改动）：`reset()` 按局序翻转 `agent_player = (base + (episode-1)) % 2`。座位 0 恒先手是 core 不变量，交换 `agent_player` 即交换「哪个策略先手」。自动启用条件：DQN 对手；Robot 对手默认关闭（`swap_seats` 可显式覆盖）。

## DQN vs Robot 两条路径分叉点（行号）
- `reset()` env.py:120-123（init_dick 仅 Robot）
- `step()` env.py:145-146（_notify_opponent 仅 Robot）、:162-164（finalize 仅 DQN）
- `_advance` env.py:200-210（`_dqn_opponent_act` vs 原 Robot 序列）

## agents/dqn.py 改动
**零改动**。act/observe/replay/save/load/from_checkpoint 全部够用。

## 新增测试（tests/test_selfplay.py，15 例）
1. `test_dqn_opponent_completes_full_episode` — DQN 对手完成整局，done=True，观测 4 维，winner 合法
2. `test_opponent_observation_is_four_dim_and_symmetric` — 对手观测 4 维；构造非对称押注局面验证镜像（agent[1]↔opp[2]、agent[2]↔opp[1]、circle 共享）
3. `test_seat_swap_alternates_first_mover` — 4 局 reset，先手方 [agent, opp, agent, opp] 交替，且 history[0] 验证座位 0 恒先手
4. `test_robot_mode_does_not_swap_seats` — Robot 不交换（旧行为保持）
5. `test_rewards_are_zero_sum` — 每步 agent+opponent==0，终局符号与赢家一致
6. `test_opponent_receives_transitions_on_its_turns` — 对手 buffer 非空、transition 4 维
7. `test_frozen_opponent_does_not_learn` — replay_every=None 时对手 memory 恒空
8. `test_selfplay_smoke_produces_two_checkpoints` — 3 局跑完、2 个 checkpoint 真实存在、summary 新字段齐全
9. `test_selfplay_same_seed_is_reproducible` — 同 seed 两次训练 9 个关键字段一致（含双方权重 hash）
10. `test_selfplay_sync_resets_opponent_to_agent_weights` — 快照同步机制触发、对手确在学习
11. `test_snapshot_mode_uses_frozen_loaded_opponent` — snapshot 对手终局权重==加载时权重（未学习）
12. `test_invalid_mode_rejected` — 非法 mode / 缺 ckpt 报错
13. `test_robot_mode_unchanged_naming` — robot 模式旧命名、无对手 checkpoint
14. `test_dual_checkpoint_evaluate_reports_both_win_rates` — 双 checkpoint 评估输出双方胜率
15. `test_single_checkpoint_evaluate_stays_robot` — 单 checkpoint 仍为 Robot 模式

## 实际执行的命令与真实输出
**基线**（改动前）：`python -m pytest tests/ --tb=no -q` → **118 collected：110 passed / 8 failed**（8 个失败全部是缺 `dqn_model_1.pth`：test_agents 6 例 + test_scripts TestEvaluate 2 例，任务说明已知，未修复）。`ruff check .` → All checks passed!

**改动后**：`python -m pytest tests/ --tb=no -q` → **133 collected：125 passed / 8 failed**（失败名单与基线逐条相同，**无新增失败**）。`ruff check .` → All checks passed!

**冒烟训练**（真实运行，3.0s）：`python -m scripts.train --episodes 3 --seed 424242 --opponent-mode self --out run/selfplay_smoke`，真实 summary JSON（节选）：
```json
{"opponent_mode": "self", "wins": 2, "win_rate": 0.667, "opponent_wins": 1,
 "opponent_win_rate": 0.333, "avg_reward": -10.0,
 "agent_action_distribution": {"bet_20": 0.4, "bet_100": 0.2, "compare": 0.4},
 "opponent_action_distribution": {"bet_20": 0.5, "bet_50": 0.25, "compare": 0.25},
 "weights_hash": "f20247…2433", "opponent_weights_hash": "f20247…2433",
 "checkpoint": "run/selfplay_smoke/dqn_sp_ep3_seed424242.pth",
 "opponent_checkpoint": "run/selfplay_smoke/dqn_sp_opp_ep3_seed424242.pth", "elapsed_sec": 0.06}
```
两个 .pth 真实生成（40317 / 40429 字节）。另真实运行：`--opponent-mode snapshot --opponent-ckpt …`（exit 0，`opponent_weights_hash` 与源 ckpt 一致 → 冻结确认）、`scripts.evaluate --opponent-checkpoint`（20 轮双 checkpoint 对战，输出双方胜率与分布）、robot 模式 `--episodes 5`（旧命名 `dqn_ep5_seed3.pth`，无 opponent_checkpoint）。

## 发现的问题与遗留项
1. 冒烟规模下 `weights_hash == opponent_weights_hash` 是**预期**：batch_size=32，3 局 transition 不足一批，双方都没发生梯度更新，同步时抄的是相同初始权重；长训练（下游 Task）才会分化。
2. 未训练贪心策略会一直 bet_100 直至 MAX_STEPS 强制结束（reward 0、无 winner）——既有环境语义，非机制缺陷；属于训练质量问题。
3. 快照同步临时文件 `_sync_tmp_seed{S}.pth` 留在 out_dir（run/ 已 gitignore），无害。
4. 仅 CPU 验证；CUDA 路径未跑（代码未区分设备，风险低）。
5. worktree 中 `PROGRESS.md` 与会话遥测文件被运行时自动修改，**不在授权范围，未提交**（已确认与本次改动无关）。
6. UNKNOWN：无。