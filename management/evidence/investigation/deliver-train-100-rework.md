All done and verified. Final delivery report:

## 交付报告（T2 收尾返工，≤2000 字）

**提交**：`fad9206` @ `governance/selfplay-train-100`（基线 `3b5226c`）。改动仅 `tests/test_selfplay_preset.py`（+155/-3）与 `docs/selfplay_train_report.md`（+41），另有 run/ 下 gitignore 产物删除（不产生 git 变更）。未触碰 pi 源码、未改 scripts/ 功能实现、未做超参搜索。

### 任务 1：逐步零和测试（核心）
- **位置**：`tests/test_selfplay_preset.py:154-155` `TestStepwiseZeroSumWithShaping.test_every_step_exactly_zero_sum_including_nonzero_bet_shaping`；辅助确定性对手 `_AlwaysCallOpponent`（恒最小合法押注=被动跟注，不弃牌）在 `tests/test_selfplay_preset.py:137`。
- **构造**：`CardGameEnv(strength_shaping=SELFPLAY_V1["strength_shaping"]=50.0, opponent_replay_every=1)`，agent 策略「前 6 个 agent 行动押最小合法注、之后 fold → 自然终局」；3 seeds（7/11/20261021）× 20 局 = **420 个环境步**。
- **断言**：每步 `float(result.reward) + float(result.info["opponent_reward"]) == 0.0` **精确相等**（断言失败消息会原样报出残差，无容差）。
- **实测残差**：420/420 步残差**全部精确为 0.0**（max|residual| = 0.0，非零残差 0 个）——IEEE-754 `fl(A+N)+fl(-A-N)` 精确零和成立，无需放宽。
- **覆盖计数证据**（按 `scripts/env.py:152-156,166-189` 同口径重算塑形增量）：押注步 **360**，其中非零塑形增量 **360/360**（`bet_steps_nonzero_shaping`，assert >0）；对手跟注（agent 被动跟注）步 **360**；fold 步 **60**；终局步 **60**。测试内对五类覆盖均 assert >0，且 assert `max_abs_residual == 0.0`，杜绝「碰巧没触发塑形」的空转测试。

### 任务 2：checkpoint 可加载性回归测试
- **位置**：`tests/test_selfplay_preset.py:71` `TestSelfplayV1Preset.test_preset_checkpoint_loadable_with_default_config`。
- **做法**：subprocess 真实跑 `python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out tmp_path`（约 3.5s）；然后 `DQNAgent.from_checkpoint(path)` **默认 config、不传 hidden**。
- **断言与结果**：无异常；`fc1.in_features==4`、`fc1.out_features==128`、`fc2.out_features==64`、`fc3.out_features==6`、`epsilon==0.0` —— 主/对手两个产物均断言，**通过**。

### 任务 3：陈旧产物清理
逐个 `torch.load` 检查 `fc1.weight` 形状后删除 `run/final/` 之外全部 45 个 `.pth`：
- **hidden=(32,16)（约 6KB，30 个）**：`run/` 根目录 `dqn_sp_ep100_seed7.pth`、`dqn_sp_opp_ep100_seed7.pth`、`_sync_tmp_seed7.pth`（任务点名的 3 个）+ `run/k1/`、`k2a/`、`k2b/`、`probe_v1/`、`repro/`、`robust_1/`、`robust_2/`、`robust_3/`、`robust_7/` 各 3 个（主/对手/sync）。
- **hidden=(128,64) 历史实验副本（15 个）**：`run/base100/`、`clireg/`、`repro2/`、`sped5/`、`speed5/` 各 3 个 —— 按「只保留 run/final/ 下当前正确的产物」的终态要求一并删除；其中 `repro2/` 与 `run/final/` **逐字节一致**（报告 §8 已记录的复现证据 sha256：`52144d10…`/`528a3c64…`），其余为早期冒烟/base 实验（base100 权重 hash `5b945c7d…` 与 final 不同，非权威产物）。
- **保留**：`run/final/` 3 个 `.pth`（sha256 与报告 §8 逐位核对一致）+ 所有 summary/eval JSON 证据文件。删除均被 `.gitignore` 覆盖，git 无变更。
- **文档**：`docs/selfplay_train_report.md:180-189`（§9）明确**唯一权威产物** = `run/final/dqn_sp_ep100_seed7.pth` 与 `run/final/dqn_sp_opp_ep100_seed7.pth`，并注明「`run/` 根目录下若有同名旧文件则是历史遗留、隐藏层宽度不同、不可使用」；`docs/selfplay_train_report.md:234` 起（§13）附录完整记录本次返工。

### 验证结果
- `python -m pytest tests/ -q`：**8 failed, 131 passed**（基线为 8 failed/129 passed；8 个失败与基线 `6bd6253` 逐条一致 —— 缺被 gitignore 的 `dqn_model_1.pth`，涉及 `tests/test_agents.py::TestCheckpointDims`×3、`TestD9LoadedPolicyInEffect`×3、`tests/test_scripts.py::TestEvaluate`×2，**无新增失败**；+2 passed 为本次新增）。
- `python -m ruff check .`：**All checks passed**（无 warning）。
- 耗时：全程约 12 分钟，远低于 20 分钟目标。

### 未完成 / UNKNOWN
- 无 UNKNOWN：残差、覆盖计数、产物 hash 均为实测值。
- 轻微越界说明（已在 §13 记录）：删除范围比字面「只删 hidden=(32,16)」多覆盖了 5 个 (128,64) 实验目录副本，依据是任务明确的终态要求「只保留 run/final/ 下当前正确的产物」；若 Main Agent 希望保留其中任何目录，可从训练命令一条命令再生（repro2 的权重与 run/final 逐位相同，无信息丢失）。
- 工作区遗留 `M .agent/telemetry*`、`M PROGRESS.md` 为任务前既有改动（非本 worker 产生），未纳入提交。