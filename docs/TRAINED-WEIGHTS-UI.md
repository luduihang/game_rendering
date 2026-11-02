# 用训练产出的权重启动 UI（人类 vs 机器）

> 对应治理任务 `human-vs-machine`（T3）：UI 的机器对手真正使用自博弈训练产出的 DQN 策略
> （`epsilon=0.0` 贪心），而不是未训练的随机策略。

## 权重从哪来

- 训练入口：`python -m scripts.train --preset selfplay_v1`（100 局自博弈，配方见
  `docs/selfplay_train_report.md` 与 `scripts/train.py` 的 `SELFPLAY_V1`）。
- 训练产物：`run/final/dqn_sp_ep100_seed7.pth`（自博弈主策略）、
  `run/final/dqn_sp_opp_ep100_seed7.pth`（对手镜像策略）。
- **部署副本**：仓库根的 `dqn_model_1.pth`（= `run/final/dqn_sp_ep100_seed7.pth`）。
  UI 默认加载它（`ui/app.py` 的 `DEFAULT_CHECKPOINT`，见 `ui/app.py:27`）。
- 权重文件被 `.gitignore` 忽略（`*.pth`、`run/`），**不进版本库**。
  新环境里跑过自博弈训练（或从有产物的环境拷贝这两个文件）即可。

## 启动方式

```bash
# 默认：加载仓库根 dqn_model_1.pth（训练策略，epsilon=0.0）
python draw_me_vs_DQN_Plus.py

# 指定权重文件（绝对路径，或相对仓库根目录的路径）
python draw_me_vs_DQN_Plus.py --checkpoint run/final/dqn_sp_opp_ep100_seed7.pth
python draw_me_vs_DQN_Plus.py --checkpoint /path/to/my_model.pth

# 或环境变量（CLI 参数优先于环境变量）
DQN_CHECKPOINT=run/final/dqn_sp_opp_ep100_seed7.pth python draw_me_vs_DQN_Plus.py
```

无显示环境（CI / 容器）：`SDL_VIDEODRIVER=dummy python draw_me_vs_DQN_Plus.py`。

### 路径优先级

`CLI --checkpoint` > 环境变量 `DQN_CHECKPOINT` > 默认 `REPO/dqn_model_1.pth`。
相对路径一律按**仓库根目录**解析，与当前工作目录无关
（解析函数：`ui/app.py::resolve_checkpoint`，`ui/app.py:31`）。

## 加载成功 / 缺失时的行为

- **加载成功**：启动时打印一行
  `[信息] 已加载训练权重 <路径>（epsilon=0.0 贪心策略）`；
  程序上可通过 `Controller.trained == True`、`Controller.agent.epsilon == 0.0`、
  `Controller.policy_source == <路径>` 判断（`ui/app.py:83-84`）。
- **权重缺失或损坏**：不崩溃，回退为**未训练随机策略（epsilon=0.15）**，
  但启动时会打印醒目的三行 `[警告]`，明确说明
  「当前机器方为未训练随机策略（epsilon=0.15），不是训练出的策略」，
  并提示把权重放到默认位置或用 `--checkpoint` / `DQN_CHECKPOINT` 指定。
  程序上 `Controller.trained == False`、`Controller.policy_source == "untrained-random(epsilon=0.15)"`。

## 验证

```bash
python -m pytest tests/test_trained_ui.py -v   # headless 端到端 + 动作溯源 + 路径优先级
python -m ruff check .
```

`tests/test_trained_ui.py` 覆盖：

| 用例组 | 断言 |
|---|---|
| `TestCheckpointResolution` | 路径优先级 CLI > env > 默认；相对路径按 REPO 解析 |
| `TestTrainedFlagAndWarnings` | 加载成功 → `trained=True`、`epsilon==0.0`；缺失/损坏 → 醒目告警 + `trained=False` |
| `TestHeadlessEndToEnd` | 无显示环境完整一局：人类 `human_action` 输入 → 机器应招 → 回合交替 → 看牌结算、赢家拿底池 |
| `TestActionsComeFromTrainedWeights` | 机器每回合动作 == 独立参考 agent（同一权重）的 argmax；与 epsilon=1.0 随机策略分布显著不同 |
