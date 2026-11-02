# PLAN —— 重构 + DQN 对抗 DQN 策略（基线 r2）

## 角色分工（基线硬约束）

**Main Agent**：只做调度与编排。不亲自读业务代码、不亲自写实现、不亲自跑训练。
只负责：切分任务、派发子 Agent、审阅交付、维持基线与文档。

**Child Agent**：唯一执行者。实现代码、写测试、跑训练、做审核。

## Task 拆分与依赖

预算上限受组织策略约束（单 Task < 2,000,000 token），故拆成 5 个 Task，项目总预算 40,000,000。

| Task | 目标 | 依赖 | 预算 | 并行组 |
|---|---|---|---|---|
| T1 `selfplay-engine` | `scripts/env.py` + `scripts/train.py` 支持 DQN 对抗 DQN 自博弈 | — | 1,800,000 | A |
| T2 `core-and-docs-cleanup` | 知识库 7.7 的 S 级项 + `core/__all__` + README 三处不一致 | — | 1,800,000 | A |
| T3 `ui-wiring` | `ui/` 接线：checkpoint 可配置、启动校验、资源自检接入、键码映射、last_now | T1（需确定权重命名契约） | 1,800,000 | B |
| T4 `train-and-evaluate` | 跑自博弈训练产出真实权重 + 双 DQN 评估 + CI/权重获取说明 | T1, T3 | 1,800,000 | C |
| T5 `final-audit` | reviewer 逐条核对 9 条验收标准 + 更新 `docs/ARCHITECTURE.md` | T2, T4 | 1,800,000 | — |

A 组并行（T1 ∥ T2，文件不重叠）；B、C 顺序推进。`maxConcurrent = 3`。

## Phase 0 — 基线与任务（Main）
1. `governance_project_draft` 记录 r2（PRD + contract + plan），人工 `project approve 2`。
2. 逐个 `governance_task_create` 建立 T1–T5（internal，auto-approved by baseline-subset）。
3. 激活当前 Task。

## Phase 1 — T1 自博弈训练引擎（worker，group A）
**改 `scripts/env.py`**：
- `opponent` 参数类型 `Robot | None` → `BaseAgent | None`（env.py:34,38）。
- `reset()` 按对手类型分支：DQN 对手跳过 Robot 专属的 `init_dick`（env.py:52）。
- 新增 `_opponent_observation()`：以对手座位为视角做 4 维编码（`encoder.encode(snapshot, opp_seat, room.own_hand(opp_seat))`）。
- `_settle_reward()`（env.py:102-106）扩为返回 `(agent_reward, opponent_reward)` 双值，零和口径对齐。
- `_advance_opponent_until_agent_turn()`（env.py:108-118）：DQN 对手记录其视角 transition 并调 `observe/replay`；
  Robot 仍走 `_notify_opponent`（env.py:126-145）。
- **座位交换**：每局按奇偶交换发牌顺序，消除先手偏置（在 env 层实现，不改 `core/rules.py`）。

**改 `scripts/train.py`**：
- 增参 `opponent_mode`（`robot|self|snapshot`）、`opponent_ckpt`、`opponent_sync_every`、`opponent_replay_every`。
- 自博弈模式：对手为在线 DQN，**降频 replay**（默认每 k 步一次）避免探索同步消失。
- 周期性用主策略快照重置对手（`agent.save(tmp)` + `opponent.load(tmp)`，agents/dqn.py:204-212）。
- checkpoint 命名：主 `dqn_sp_ep{N}_seed{S}.pth`，对手 `dqn_sp_opp_ep{N}_seed{S}.pth`；summary 增
  `opponent_mode`、双方胜率、双方动作分布、训练耗时。
- `main()` 增对应 CLI 参数。

**约束**：`agents/dqn.py` 原则上不改（`act/observe/replay/save/load/from_checkpoint` 已够用）；
若确需改，只允许加不改既有语义，并说明理由。`core/` 原则上不改。

**测试**：新增 `tests/test_selfplay.py`（或并入 `tests/test_scripts.py`）覆盖：
- DQN 对手可注入 env 并完成整局；对手视角观测维度为 4 且与 agent 视角编码对称。
- 座位交换生效（连续两局的先手方不同）。
- 双方奖励零和（agent_reward + opponent_reward == 0）。
- 自博弈训练冒烟：少量局数能跑完、产出两个 checkpoint、summary 含新增字段。
- 同种子两次训练可复现（同 seed → summary 的关键字段一致）。

## Phase 2 — T2 清理与文档修正（worker，group A，与 T1 并行）
按调研 F 的清单逐条做，全部 S/M 级：
- `ui/app.py:211-212` 键码差值映射 → 显式映射表（`1/2/3/4` → Action）。
- `ui/app.py:269-271` 资源自检 → 改用 `ui/theme.py:77-90` 的 `missing_assets()`。
- `ui/theme.py:130` `button_rects` 返回注解 → `dict[int, pygame.Rect]`。
- `ui/app.py:141,143-144` `last_now` 类属性 → 移入 `__init__`。
- `core/__init__.py:16-31` `__all__` → 补 `strength_ordinal` / `strongest_hand` / dealing 相关符号（保持惰性导入不变）。
- `README.md:28` 「6 行」→ 实际行数；`README.md:44-48` 架构图箭头方向改正（scripts/ 上移为入口层）；
  `README.md:63` time.sleep 声明改为不 overclaim 的两行表述（pytest 只扫 ui/，scripts/ 由
  `tests/baseline/repro_d7_timing.py` 守护）。
- `pyproject.toml:42` 残留的「备份」字样；`README.md:73` 目录说明补 `card_pic备用/`、`login/` 残留。

**约束**：不碰 `core/rules.py`、`core/strength.py`、`core/dealing.py` 的机制；不碰 `agents/dqn.py`。
改动前后各跑一次 `pytest`，对比**没有既有测试被打红**。

## Phase 3 — T3 交互侧接线（worker，group B，依赖 T1）
- `ui/app.py:25` `DEFAULT_CHECKPOINT` 指向自博弈产出的权重文件名（命名契约由 T1 定）。
- checkpoint 路径做成可配置（CLI 参数或环境变量），启动时校验存在性；**缺失时给出明确警告**
  而不是静默回退（保留回退但必须可见）。
- 机器推理路径改为加载自博弈权重后 `epsilon == 0.0`（贪心），并新增断言测试。
- 若 T2 已改键码映射与资源自检，本 Task 不重复改（按依赖顺序，T3 只做接线相关部分）。

**测试**：新增/扩展 `tests/test_ui.py`：checkpoint 缺失时启动有可见告警；加载成功时
`agent.epsilon == 0.0`；自博弈权重可被 `from_checkpoint` 直接加载（4×6）。

## Phase 4 — T4 训练与评估（worker，group C，依赖 T1/T3）
1. **先测速**：跑 5 局，测墙钟耗时（参考 `tests/test_scripts.py:81-84` 的 <60s 上界）。
2. **定局数**：按测速结果选一个能在 **≤30 分钟**内完成的局数，写进 summary 与文档。
3. **正式训练**：产出主策略与对手策略两个 checkpoint；记录双方胜率曲线与动作分布，
   确认**无塌缩**（双方胜率不悬殊到一边倒、动作分布不退化为单一动作）。
4. **双 DQN 评估**：`scripts/evaluate.py` 增加双 checkpoint 对战模式，输出双方胜率。
5. **权重落地**：权重按 `.gitignore` 规则不进版本库；提供明确的获取方式（训练命令 + 输出路径）
   写入 README 与 `docs/ARCHITECTURE.md`；CI 步骤里补上生成权重或在缺权重时显式 skip。

**约束**：训练必须固定种子可复现；单次训练 ≤ 30 分钟；不删除仓库既有文件。

## Phase 5 — T5 终审与文档同步（reviewer + worker，依赖 T2/T4）
1. **reviewer 逐条核对 9 条验收标准**，重点：
   - 「不可碰」清单（7.1 状态契约 / 7.3 惰性建表 / 7.4 维度自适应 / 7.5 均匀发牌）是否被改动；
   - D1-D9 回归测试是否仍全绿；
   - 自博弈训练是否真的产生了**两个** checkpoint 且对称性/零和/座位交换生效；
   - 机器对手加载后 `epsilon == 0.0`，不是回退的 0.15；
   - README 三处是否已修正。
2. **worker 更新 `docs/ARCHITECTURE.md`**：新增「自博弈训练」章节、机器对手接线变化、
   权重获取与存放说明、7.6/7.7 条目的处置结果、重构后行号校正。
3. 独立验证：跑 `pytest` + `ruff`，与重构前基线对比测试结果。

## 验收门

| 门 | 判据 |
|---|---|
| G1 自博弈引擎 | `scripts/train.py --opponent-mode self` 可跑；产出 2 个 checkpoint；summary 含双方胜率 |
| G2 对称与零和 | 座位每局交换；双方奖励和为 0；测试覆盖 |
| G3 真实权重 | 仓库工作区存在自博弈权重；UI 加载后 `epsilon == 0.0`；动作分布异于随机 |
| G4 交互模式 | 人类 vs 机器仍可完整走完一局 |
| G5 评估 | `scripts/evaluate.py` 双 DQN 对战可输出胜率 |
| G6 重构完成 | 7.7 的 S/M 级条目 + 7.6 README 三处全部完成 |
| G7 测试 | pytest + ruff 全绿；既有测试零打红 |
| G8 文档 | `docs/ARCHITECTURE.md` 已同步，含自博弈章节与权重获取说明 |
| G9 不可碰 | 「不可碰」清单零改动，由 reviewer 逐条核对 diff |

## 回滚

- 每个 Task 在独立 worktree 分支（`governance/<task-id>`）上完成，可按 Task 单独回滚。
- 未合并到 main；合并由人工执行。

