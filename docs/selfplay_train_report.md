# 自博弈 DQN 训练报告（selfplay-train-100, R-c1712b23）

**目标**：在 ≤100 局内训出「会因牌力改变动作」的 DQN 策略，并固化配置、提交交付。
**分支**：`governance/selfplay-train-100`
**日期**：2026-11-02
**结论**：全部 9 条验收通过（含最关键的「部署用贪心策略随牌力改变动作」）。

---

## 1. 问题根因与解法

终局奖励为 `±all_bet`（赢家拿走全池），量级随押注额线性增长（±数百到数千），
导致 Q 值天然单调偏好最大押注 → 贪心恒为 `bet_100` → 对局永不自然结束
（撞 `MAX_STEPS=200` 强停）、动作分布退化为单一动作。

解法：`scripts/env.py`（`CardGameEnv.strength_shaping`，`scripts/env.py:88`）引入
**按押注额计酬的稠密奖励塑形**（严格零和：`agent_reward + opponent_reward == 0`）：

- 某方押注 `B` 时：得 `+k·(p-0.5)·B`（`p` = 己方手牌击败随机手牌概率，
  `core.strength.beats_probability`）；对方同步记零和的对应量。
- 关键：**按「押注额」而非「底池」计酬**，避免大底池下 `Q(加注)` 自增强成死循环。
- `_settle_rewards` 的 `±all_bet` 终局零和口径**未改动**（`scripts/env.py:225`）。

## 2. 本轮修复的两个缺陷（上一位 worker 遗留）

1. **CLI 崩溃**：`scripts/train.py` `main()` 中 `opponent_epsilon=p["opponent_epsilon"]`
   无条件访问，非 preset 调用抛 `KeyError: 'opponent_epsilon'`。
   修复：改为 `p.get("opponent_epsilon")`，缺省 `None` 由 `train()` 按模式取缺省
   （self=1.0 / snapshot=0.0）—— `scripts/train.py:333`。
2. **preset 超参不符合验收配方**：`SELFPLAY_V1` 原为 `strength_shaping=0.5,
   hidden=(32,16)`。修复为验收版配方（见下）—— `scripts/train.py:48`。
   `hidden` 从 preset 中移除（缺省 `None` = DQNConfig 默认 `(128, 64)`），
   因为 `DQNAgent.from_checkpoint` 只自适应 input/action 维度、**不推断隐藏层宽度**，
   `(32,16)` 的 checkpoint 下游 UI 加载会报 `size mismatch for fc1.weight`。

## 3. preset 最终超参（`scripts/train.py:48` `SELFPLAY_V1`）

| 超参 | 值 |
|---|---|
| opponent_mode | `self` |
| opponent_epsilon | 0.25 |
| opponent_replay_every | 1 |
| strength_shaping (k) | **50.0** |
| hidden | 缺省 = **(128, 64)**（未覆盖） |
| lr | 3e-2 |
| gamma | 0.95 |
| batch_size | 4 |
| epsilon_start | 0.5 |
| epsilon_decay | 0.99 |
| episodes | 100（命令行 `--episodes`） |

## 4. 正式训练

**命令（一条命令可复现）**：

```bash
python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out run/final
```

**墙钟耗时**：`3.320 s`（含解释器/torch 启动约 2.6 s；summary 内纯训练
`elapsed_sec = 0.702`）。5 局测速：墙钟 `3.011 s`、纯训练 `0.164 s`
（`run/speed5/summary_seed7.json`）。

**summary JSON 全文**（`run/final/summary_seed7.json`）：

```json
{
  "episodes": 100,
  "seed": 7,
  "device": "cpu",
  "opponent_mode": "self",
  "strength_shaping": 50.0,
  "wins": 56,
  "win_rate": 0.56,
  "agent_win_rate": 0.56,
  "opponent_wins": 44,
  "opponent_win_rate": 0.44,
  "avg_reward": 2031.6961538461546,
  "agent_action_distribution": {
    "bet_10": 0.026,
    "bet_20": 0.0347,
    "bet_50": 0.0116,
    "bet_100": 0.8121,
    "fold": 0.0376,
    "compare": 0.078
  },
  "opponent_action_distribution": {
    "bet_10": 0.0449,
    "bet_20": 0.0169,
    "bet_50": 0.0169,
    "bet_100": 0.7528,
    "fold": 0.0478,
    "compare": 0.1208
  },
  "epsilon_final": 0.015916286619603974,
  "total_steps": 346,
  "avg_steps_per_episode": 3.46,
  "natural_end_rate": 1.0,
  "weights_hash": "da476c137eedfb30b4862c07efab2315813c56d153653a0ce2407239154cc661",
  "opponent_weights_hash": "8844c597c4bc537ec2492a7ee152d512e67d1dd85e03b87ef11125c907fd573c",
  "elapsed_sec": 0.702,
  "config": {
    "hidden": [128, 64],
    "lr": 0.03,
    "gamma": 0.95,
    "batch_size": 4,
    "buffer_size": 5000,
    "epsilon_start": 0.5,
    "epsilon_min": 0.01,
    "epsilon_decay": 0.99,
    "target_sync_every": 1,
    "device": "cpu"
  },
  "checkpoint": "run/final/dqn_sp_ep100_seed7.pth",
  "opponent_checkpoint": "run/final/dqn_sp_opp_ep100_seed7.pth"
}
```

## 5. 贪心（epsilon=0）状态依赖性评估 —— 最关键验收

临时脚本在 **N=2400 个真实状态**上评估（真发牌：`core.dealing.new_deck` +
`deal_uniform`，强度 = `core.strength.beats_probability`；前 3 维盘面特征用
`random.Random(20261102)` 取值），每状态调 `agent.act(obs, list(range(6)))`：

**总动作分布**：`{bet_20: 0.3917, bet_100: 0.6083}` —— 2 个动作，
最大占比 0.6083 < 0.95，**未退化为单一动作**。

**按手牌强度分组（bet_50+bet_100 记「大注」）**：

| 分组 | n | 动作分布 | 大注占比 |
|---|---|---|---|
| 弱牌（p ≤ 0.3） | 751 | bet_20: 1.0 | **0.000** |
| 中牌（0.3 < p ≤ 0.6） | 714 | bet_20: 0.2647, bet_100: 0.7353 | 0.7353 |
| 强牌（p > 0.6） | 935 | bet_100: 1.0 | **1.000** |

强牌 − 弱牌大注占比差 = **+1.0**：策略明确随牌力改变动作
（弱牌几乎不加大注、强牌恒定最大押注）。单调性 弱 < 中 < 强 成立。

## 6. 对局自然结束与对抗评估

命令：

```bash
python -m scripts.evaluate \
  --checkpoint run/final/dqn_sp_ep100_seed7.pth \
  --opponent-checkpoint run/final/dqn_sp_opp_ep100_seed7.pth \
  --rounds 50 --seed 7
```

结果（`run/final_eval/eval_seed7.json`）：

- **`natural_end_rate = 1.0`**（50/50 自然结束，≥ 0.9 达标，无 MAX_STEPS 强停）
- 胜率 0.50 / 0.50，**两者之和 = 1.0**，不一边倒
- 双方均为贪心（`--epsilon` 缺省 0.0）
- 动作分布：主 `{bet_20: 0.005, bet_100: 0.9863, compare: 0.0086}`；
  对手 `{bet_10: 0.0014, bet_50: 0.0021, bet_100: 0.9693, compare: 0.0271}`

## 7. 可加载性

`DQNAgent.from_checkpoint('run/final/dqn_sp_ep100_seed7.pth')` 加载无报错，
网络形状（实测 state_dict）：

- `fc1.weight = (128, 4)`（input_dim=4 → 128）
- `fc2.weight = (64, 128)`
- `fc3.weight = (6, 64)`（64 → action_dim=6）

隐藏层 = 默认 **(128, 64)**，UI 侧可直接加载。

## 8. 可复现性证据

同一命令同 seed 连跑两次（`run/final` 与 `run/repro2`），checkpoint 字节完全一致：

| 文件 | sha256（两次运行） |
|---|---|
| dqn_sp_ep100_seed7.pth | `52144d10ec7061362b23678033c5066018eb184bed3f9d3acce4ae677c437b22`（一致） |
| dqn_sp_opp_ep100_seed7.pth | `528a3c641856cf493debff214908e55faaa354b0025fc18699e924a239058de7`（一致） |

## 9. 产物绝对路径

> **唯一权威产物**（UI/下游应且只能加载这两个文件，隐藏层均为默认 (128,64)）：
>
> - 主策略：`run/final/dqn_sp_ep100_seed7.pth`
> - 对手策略：`run/final/dqn_sp_opp_ep100_seed7.pth`
>
> **注意**：`run/` 根目录下若有同名旧文件（如 `run/dqn_sp_ep100_seed7.pth`，约 6 KB），
> 则是历史遗留、隐藏层宽度不同（(32,16)）、不可使用 —— 用默认 config 的
> `DQNAgent.from_checkpoint` 加载会报 `size mismatch for fc1.weight`。R-2569c185 返工
> （2026-11-02）已删除本 worktree `run/` 下（除 `run/final/` 外）的全部陈旧 `.pth`，
> 见 §13。

- 主策略：`/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100/run/final/dqn_sp_ep100_seed7.pth`
- 对手策略：`/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100/run/final/dqn_sp_opp_ep100_seed7.pth`
- 训练 summary：`.../run/final/summary_seed7.json`
- 对抗评估 summary：`.../run/final_eval/eval_seed7.json`

（`run/` 与 `*.pth` 被 `.gitignore` 覆盖，不进版本库；一条命令即可再生。）

## 10. 回归与测试

- `python -m pytest tests/`：**8 failed, 129 passed**。
  8 个失败全部为既有环境问题（缺被 `.gitignore` 忽略的 `dqn_model_1.pth`，
  与基线 `tests/test_agents.py::TestCheckpointDims` 等 8 例完全相同），
  **无新增失败**（基线 125 passed + 本次新增 4 passed）。
- `python -m ruff check .`：**All checks passed**。
- 新增测试 `tests/test_selfplay_preset.py`（4 例）：
  1. `--preset selfplay-v1` 超参 = 验收配方（k=50、默认 hidden、lr/batch/decay）；
  2. preset 一条命令跑通并产出双 checkpoint（hidden=(128,64)）；
  3. CLI 不带 preset 的 self 模式不再 KeyError（3.1(a) 回归）；
  4. 塑形开启（k=50）时 `_settle_rewards` 零和性仍成立（每步
     `agent_reward + opponent_reward == 0`，终局 ±all_bet 且符号与赢家一致）。

## 11. 与参考值的偏差说明（如实汇报）

- seed=7 实测训练胜率 **56/44**（参考值 42/58）：不同实现细节下的小幅差异，
  同样满足「不一边倒」。
- 贪心强牌大注占比实测 **1.000**（参考值 ≈0.40）：分化更彻底，
  弱牌 ≈0.000 与参考值 ≈0.01 一致；「动作随手牌强度变化」的验收方向与量级
  （+1.0 差值）均满足。未做 seed 挑选或口径改动。

## 12. 验收清单

| # | 验收项 | 结果 | 证据 |
|---|---|---|---|
| 1 | 5 局测速记录墙钟 | ✅ | 墙钟 3.011 s / 纯训练 0.164 s |
| 2 | 产出双 .pth | ✅ | §9 绝对路径 |
| 3 | summary 含胜率/动作分布/耗时/局数 | ✅ | §4 全文 |
| 4 | 训练期无塌缩 | ✅ | 56/44；双方各 6 种动作 |
| 5 | 贪心策略不单一且随手牌强度变化 | ✅ | §5：2 动作、max 0.608<0.95、强−弱 +1.0 |
| 6 | natural_end_rate ≥ 0.9 且胜率之和 ≈1 | ✅ | 1.0；0.50+0.50 |
| 7 | from_checkpoint 可加载，hidden (128,64) | ✅ | §7 |
| 8 | 同 seed 可复现 | ✅ | §8 sha256 一致 |
| 9 | 配置固化 + 报告 | ✅ | §3 preset + 本报告 |

## 13. 附录：复核返工（R-2569c185，2026-11-02）——补测试覆盖 + 清理陈旧产物

独立 reviewer 复核 `ea2f024` 确认 9 条验收全部通过后，指出一个测试覆盖缺口与一个
产物路径歧义，本次返工处理如下（commit 见分支历史）：

1. **新增逐步零和测试**（覆盖缺口）：
   `tests/test_selfplay_preset.py::TestStepwiseZeroSumWithShaping::test_every_step_exactly_zero_sum_including_nonzero_bet_shaping`。
   既有零和测试只断言最后一步（恰为 fold、塑形增量 0），未锁住真正产生非零塑形增量
   的押注步。新测试用 preset 值 `strength_shaping=50.0`、3 seeds（7/11/20261021）× 20 局
   （420 个环境步）逐步精确断言 `agent_reward + opponent_reward == 0.0`，并断言确实
   覆盖到非零塑形增量的押注步（实测 360/360 押注步塑形增量均非零）、对手跟注步
   （360）、fold 步（60）、终局步（60）；实测最大残差 = 0.0（全部精确零和）。
2. **新增 checkpoint 可加载性回归测试**：
   `tests/test_selfplay_preset.py::TestSelfplayV1Preset::test_preset_checkpoint_loadable_with_default_config`。
   真实跑 `--preset selfplay-v1 --episodes 100 --seed 7` 后，`DQNAgent.from_checkpoint`
   用**默认 config（不传 hidden）**无异常加载，断言 fc1=(4→128)、fc2=(128→64)、
   fc3=(64→6)、`epsilon == 0.0`（主/对手两个产物均断言）。
3. **陈旧产物清理**（路径歧义）：删除 `run/` 下（除 `run/final/` 外）全部陈旧 `.pth`，
   共 45 个：其中 30 个隐藏层为 (32,16)（约 6 KB，含 `run/` 根目录 3 个同名文件
   及 `k1/ k2a/ k2b/ probe_v1/ repro/ robust_1..3/ robust_7/`），15 个为 (128,64) 的
   历史实验副本（`base100/ clireg/ repro2/ sped5/ speed5/`，其中 `repro2/` 与
   `run/final/` 逐字节一致、即 §8 的复现证据，sha256 已记录于 §8，文件本体已清理）。
   `run/` 下现仅存 `run/final/` 三个 `.pth`（§9 唯一权威产物，sha256 与 §8 一致）；
   各实验目录的 summary/eval JSON 证据文件保留未动。被删文件均被 `.gitignore` 覆盖，
   不产生 git 变更。
4. **测试与 lint 结果**：`python -m pytest tests/ -q` = **8 failed, 131 passed**
   （8 个失败与基线 `6bd6253` 完全相同：缺被 `.gitignore` 忽略的 `dqn_model_1.pth`，
   失败集合逐条一致，无新增失败；2 passed 为本次新增）。
   `python -m ruff check .` = All checks passed。
