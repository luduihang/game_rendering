T3 完成，已提交 `4e6570a` 到 `governance/human-vs-machine`。

## 改动摘要

**任务 1 — checkpoint 路径可配置**（`ui/app.py`）
- 新增 `resolve_checkpoint(arg=None, env=None) -> Path`（`ui/app.py:33`）：优先级 **CLI 参数 > 环境变量 `DQN_CHECKPOINT` > 默认 `REPO/dqn_model_1.pth`**；相对路径一律按仓库根解析（与 CWD 无关）；`env` 参数可注入映射，便于测试。
- `main()` 新增 `--checkpoint` argparse 参数（`ui/app.py:296`），传入 `Controller(checkpoint=...)`（`ui/app.py:307`）。`Controller.__init__` 的 `checkpoint` 默认改为 `None` 并在内部解析（`ui/app.py:56,71`）。入口 `draw_me_vs_DQN_Plus.py` 无需改动（不在授权路径内，未动）：`main(argv=None)` 的 argparse 自动读 `sys.argv`，`python draw_me_vs_DQN_Plus.py --checkpoint x` 直接可用（已实测 `--help` 与真实启动）。
- 验收 1：`DEFAULT_CHECKPOINT = REPO / "dqn_model_1.pth"`（`ui/app.py:29`），md5 实测与 `run/final/dqn_sp_ep100_seed7.pth` **逐位一致**（`6fbb71e0…`），即自博弈训练产出。

**任务 2 — 缺失时可见告警 + 训练标志**（`ui/app.py`）
- `_load_agent`（`ui/app.py:81`）：缺失/损坏时打印三行醒目 `[警告]`（`ui/app.py:86-89`），明确「当前机器方为**未训练随机策略（epsilon=0.15）**，不是训练出的策略」+ 默认位置与 `--checkpoint`/`DQN_CHECKPOINT` 修复指引；保留回退不崩溃。加载成功打印 `[信息] 已加载训练权重 <路径>（epsilon=0.0 贪心策略）`（`ui/app.py:91`）。
- **训练标志（任务 5/6 测试钩子）**：`Controller.trained: bool`（`ui/app.py:72`），另有 `Controller.policy_source: str`（加载时=权重路径，回退时=`"untrained-random(epsilon=0.15)"`，`ui/app.py:73`）与 `Controller.checkpoint: Path`（`ui/app.py:71`）。
- 顺手修了一个真实健壮性缺口（在授权路径内）：损坏权重会让 `torch.load` 抛 `pickle.UnpicklingError`（非 ValueError/RuntimeError），原 except 接不住 → 启动直接崩。except 元组补了 `pickle.PickleError`（`ui/app.py:85`）。

**任务 3 — headless 端到端测试**（`tests/test_trained_ui.py:114` `TestHeadlessEndToEnd`，无 pygame、无窗口）
- 驱动方式：`Controller(seed=20260102, checkpoint=CKPT, think_seconds=0, settle_seconds=0)`；人类前 5 手经公开入口 `controller.human_action(最低可押档)`，第 6 手 `human_action(Action.COMPARE)` 看牌结算；机器回合由 `controller.update(now)` 走内部 AI 分支。**每回合先算独立参考 agent（同一权重、不同 seed）的 argmax，再断言 `room.history[-1] == (AI, expected)`**。
- 实测输出（seed=20260102）：`步数=11 winner=1 all_bet=1020 finish=True`，`money=(19485, 20515)`，history `[(0,0),(1,3),(0,3),(1,3),(0,3),(1,3),(0,3),(1,3),(0,3),(1,3),(0,5)]` —— 人机严格交替（10 次应招+人类 6 手），机器 10 次动作全部等于参考 argmax，人类看牌后机器（winner=1）赢走底池。
- 断言：`room.finish is True` 且 `winner is not None`；相邻 actor 全不同且双方各 ≥2 次；`all_bet > 0`；赢家资金 > 20000、输家 < 20000、两人资金守恒 == 40000（`core/rules.py:172-175` 结算语义）。

**任务 4 — 动作溯源（验收 6）**（`tests/test_trained_ui.py:197` `TestActionsComeFromTrainedWeights`）
- 用 `new_deck + deal_uniform` 发真手牌构造 3 个已知状态（`tests/test_trained_ui.py:187`），`StateEncoder.encode` 编码（含 `beats_probability` 强度维）。
- 断言：① Controller 加载的 agent 与独立参考 `from_checkpoint` agent 同状态动作**完全一致**；② 加载权重 agent 同状态 21 次调用**恒定**（top1 频率=1.0）；③ 未加载权重 `epsilon=1.0` 随机 agent 同状态 200 次采样：≥2 种动作且 top1 频率 < 1.0，**训练分布明显更集中**（top1 1.0 > 随机 top1）。
- 更强做法已做：`test_controller_ai_move_equals_checkpoint_argmax_in_live_game` —— 对局中 Controller **实际执行**的机器动作逐回合等于独立参考 agent 对同一状态的 argmax（≥3 次核对）。

**任务 5 — 其他测试**：路径优先级 7 例（`tests/test_trained_ui.py:41`，含真实 `os.environ` monkeypatch 与显式 env 映射）；缺失/损坏权重可见告警 2 例（`tests/test_trained_ui.py:93-109`，capsys 断言「未训练随机策略」「0.15」「不是训练出的策略」及修复指引）；加载成功 `epsilon==0.0` + `trained is True`（`tests/test_trained_ui.py:83`）。

**任务 6 — 文档**：新增 `docs/TRAINED-WEIGHTS-UI.md`（权重来源=SELFPLAY_V1 自博弈 100 局 seed=7、启动/自定义路径/优先级/缺失行为/验证）；`README.md` 快速开始加 `--checkpoint`/环境变量示例与缺失行为说明、入口产物段注明部署权重即 `dqn_model_1.pth`、分层约束表加 `tests/test_trained_ui.py` 守护行、目录说明同步。

## 验证方式与结果
- `python -m pytest tests/ --tb=short` → **156 passed**（139 既有 + 17 新增；基线 8 个失败因 worktree 里已有 `dqn_model_1.pth` 全部转绿，与任务预期 139/0 一致，新增后 156/0）
- `python -m ruff check .` → **All checks passed**（修了 1 处 import 排序）
- CLI 实测：`--help` 正常；`--checkpoint run/final/dqn_sp_opp_ep100_seed7.pth` 启动打印 `[信息]` 加载行；`--checkpoint /nonexistent/model.pth` 打印三行 `[警告]` 后正常运行
- 未提交 `.agent/*`、`.pi/*`、`PROGRESS.md` 的环境遥测改动（非我产生，超出授权路径）；权重 `.pth` 保持 gitignore

## 风险项
- 训练策略经状态网格探测**中局几乎只押注、不主动弃牌/看牌**（全 6 动作合法时贪心分布只含 bet_20/bet_100，见训练报告已知的 Q 值饱和问题）——端到端「自然结束」由人类一方看牌/弃牌触发，这是规则允许的合法结算路径，但意味着真实玩家若一直跟注，机器可能长期不下注不摊牌（策略质量问题，属训练侧，超出本任务范围，UNKNOWN 是否需后续训练任务跟进）。