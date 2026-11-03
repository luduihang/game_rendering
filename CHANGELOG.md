# CHANGELOG

本文件记录仓库形态的重大变更。所有删除都可通过 git 历史恢复。

## [0.2.0] — 单一策略清理（P1）

人工决策 D-R5：**只保留一种策略实现**，清理历史实验脚本。
保留对象：`draw_me_vs_DQN_Plus.py`（人类 vs DQN 交互策略）+ `mymath/robot2.py`（唯一对手策略）。

### 删除：冗余策略脚本（15 个）

| 文件 | 原用途 | 删除理由 |
|---|---|---|
| `draw.py` | 早期 UI demo（`rest_option` 用 `min()`，D2 bug） | 被 `draw_me_vs_DQN_Plus.py` 取代 |
| `draw_me_vs_DQN.py` | 人类 vs DQN（9 维声明 + 4 维权重，D8 崩溃） | 维度失配，无法启动 |
| `draw_me_vs_DQN_Plus.py` 之外的 `draw_*` | 见下 | — |
| `draw_PRO_vs_DQN.py` | PRO vs DQN（D8 崩溃） | 维度失配，无法启动 |
| `draw_me_train_DQN.py` | 人类 vs 训练中的 DQN | 训练入口由 `scripts/` 取代（P4） |
| `draw_me_train_QN.py` | 人类 vs 训练中的 Q-Network | Q 表策略不再保留 |
| `game_room_random.py` | 随机对手对局 | 被 core 单测取代（P2） |
| `use_model.py` | 单步推理 demo（加载不存在的 `dqn_model_ep100.pth`） | 本身已损坏，由 `agents/` 取代（P3） |
| `nodraw_DQN_train_DQN.py` | 无头 DQN 训练 DQN | 由 `scripts/` 取代（P4） |
| `nodraw_DQN_train_DQN_Plus.py` | 无头 DQN 训练（4 维变体） | 由 `scripts/` 取代（P4） |
| `nodraw_DQN_vs_QN.py` | DQN vs Q-Network（D8 崩溃） | 维度失配 + Q 表策略不保留 |
| `nodraw_DQN_vs_QN_Plus.py` | DQN vs Q-Network（4 维变体） | Q 表策略不保留 |
| `nodraw_PRO_train_QN.py` | PRO 策略训练 Q 表 | Q 表策略不保留 |
| `nodraw_QN_train_QN.py` | Q 表自博弈 | Q 表策略不保留 |
| `nodraw_cmp_DQN_PRO.py` | DQN vs PRO 对比（D8 崩溃） | 维度失配 |
| `nodraw_cmp_QN_PRO.py` | Q 表 vs PRO 对比 | Q 表策略不保留 |

> 说明：上表首两行标「见下」为笔误一致性说明，实际删除清单以「恢复方式」一节的命令为准。

### 删除：重复策略模块（1 个）

| 文件 | 理由 |
|---|---|
| `mymath/robot.py` | 与 `mymath/robot2.py` 约 130 行近乎逐行相同，仅系数不同；`robot2` 为其超集（含弃牌保护与非线性概率分布），保留 `robot2` |

### 删除：旧代码副本（1 个目录）

| 目录 | 内容 | 理由 |
|---|---|---|
| `备份/` | 37 项（12 个 `.py` + 模型 + 统计图） | 整份旧版本代码副本，已完全被当前代码与 git 历史覆盖 |

### 归档：模型与统计产物

保留在工作区：`dqn_model_1.pth`（保留策略使用，4 维输入）。
其余已从 git 索引移除（`.gitignore` 覆盖），并移动到仓库外的归档目录：

- `dqn_model_0.pth`、`dqn_final.pth`、`dqn_model_ep50/150/200/250.pth`、`pytorch_dqn.pth`
- `q_table.txt`、`q_table1.txt`、`q_table2.txt`、`q_table_dinamic.txt`、`remember.txt`
- `dqn_vs_dqn_stats.png`、`dqn_vs_opponent_stats.png`、`game_stats.png`、`me_vs_qn_stats.png`

### 随之修改

- `game_room_deepseek_cp.py`：移除 `from mymath.robot import Robot`，`main()` 改用 `Robot2`
- `tests/baseline/repro_d5_wiring.py`：改用 `Robot2`（语义等价，仍验证手牌接线）

### 恢复方式

```bash
# 查看某次删除前的状态
git show <删除提交的父提交>:draw.py

# 恢复单个文件到工作区
git checkout <删除提交的父提交> -- draw.py

# 恢复整个备份目录
git checkout <删除提交的父提交> -- 备份/
```

## [0.2.0] — 架构重构（P2–P6）

### 新增分层
- `core/`：`cards` · `evaluator` · `strength` · `dealing` · `rules`（纯逻辑，无 pygame/numpy/scipy/torch）
- `agents/`：`base`（BaseAgent 接口）· `dqn`（含 `from_checkpoint` 维度自适应）· `robot`（Robot2 迁入）
- `ui/`：`app`（事件驱动主循环）· `clock`（可注入节奏器）· `render`（薄渲染）· `theme`
- `scripts/`：`env` · `train` · `evaluate`（无头、同种子逐位可复现）

### 追加删除（P5 消除遗留链路，已由新分层取代）
| 文件 | 取代者 |
|---|---|
| `game_room_deepseek_cp.py` | `core.rules.GameRoom` + `agents.dqn` |
| `card_deck.py` | `core.cards` / `core.evaluator` / `core.strength` / `core.dealing` |
| `mymath/robot2.py` | `agents.robot.Robot`（行为等价留证 L1=0.076） |

### 重写
- `algorithm.py`：收敛为「规则文案 + 已加固 RepeatedTimer」（移除与已删 UI 的耦合）
- `const.py`：路径改 `pathlib` 包根相对；不再 import pygame；`pygame.Rect` 移出类体
- `draw_me_vs_DQN_Plus.py`：20 个脚本中唯一的入口，重构为 6 行薄入口

### 修复
- D1 看牌结算（比较方向 + `whose_turn`）· D2 `rest_option` 单调 · D4 结束后拒绝行动
- D5 手牌归属具名化 · D6 默认均匀发牌 · D7-a/b/c/d 时序与事件循环
- D8 权重维度自适应 · D9 加载真实权重（`epsilon=0.0`）
- `mymath/func_const.py::sum_circle_turn` 陈旧缓存（`circle_turn` 变化后仍返回旧值）

### 质量
- 104 项 pytest、6 个缺陷回归脚本、`ruff` 682 → 0
- CI：`.github/workflows/ci.yml`（ruff + pytest + 回归 + 无头冒烟 + 可复现性）
- 文档：`docs/BASELINE-REPORT.md`（基线实测）、`docs/FINAL-REPORT.md`（验收）

## [0.1.x] — 基线与卫生（P0 / P1 部分）

- 修复运行环境：安装 pygame 2.6.1、matplotlib 3.8.0 → 3.11.2（numpy 2.x ABI 崩溃）、ruff 0.17.1
- 新增 `docs/BASELINE-REPORT.md` 与 `tests/baseline/`（D1/D2/D4/D5/D6/D7 复现脚本）
- 新增 `.gitignore`、`pyproject.toml`；35 个产物移出 git 索引
- 移除 `from sympy import false` 误依赖；`np.trapz` → `np.trapezoid`
- 重写 `README.md`

## [0.2.1] — S/M 级重构清理与 README 修正（零行为风险）

### 代码清理
- `ui/app.py`：键码差值映射（`Action(key - pygame.K_1)`）改为显式映射表 `key_to_action_map()`（K_1..K_4 → BET_10/20/50/100，K_f → FOLD，K_c → COMPARE），避免小键盘/非标准布局下错位
- `ui/app.py`：启动资源自检改用 `ui.theme.missing_assets()`（新增 `check_assets()`），缺失时打印具体缺失资源名
- `ui/app.py`：`Controller.last_now` 由类级属性移入 `__init__`
- `ui/theme.py`：`button_rects` 返回注解由 `dict[int, "object"]` 改为 `dict[int, pygame.Rect]`
- `core/__init__.py`：`__all__` 补齐 `strength_ordinal`、`strongest_hand` 与 dealing 符号（`new_deck` / `deal_uniform` / `deal_strength_biased` / `verify_uniformity` / `EmptyDeckError`）；惰性建表不变（import core 不触发 22100 手建表）

### 文档与配置
- `README.md`：入口行数 (6 行) → (14 行)；架构图改为入口层置顶（`draw_me_vs_DQN_Plus.py` 与 `scripts/` 并排），箭头由入口向下指向 ui/core/agents，与实际 import 方向一致；`time.sleep` 守护声明拆为两行（`ui/` 由 pytest 守护、`scripts/` 由 `tests/baseline/repro_d7_timing.py` 守护，非 pytest）；`src/` 目录说明同步实际内容（注明 `card_pic备用/`、`login/` 等未被引用的残留目录）
- `pyproject.toml`：ruff `extend-exclude` 移除已不存在的 `备份/` 目录

### 测试
- 新增 `tests/test_ui.py::TestKeyMapping::test_key_map_covers_all_actions_with_unique_keys`（映射表与 Action 一一对应）
- 新增 `tests/test_ui.py::TestEntryAndAssets::test_startup_asset_check_reports_specific_missing`（缺失资源场景报出具体资源名）
- 新增 `tests/test_ui.py::TestOriginalTextures::test_button_rects_return_pygame_rects`（运行时类型为 pygame.Rect）
- 新增 `tests/test_purity.py::test_import_core_does_not_build_strength_table`（全新解释器验证惰性建表）

## [0.3.0] — 自博弈训练与 UI 机器对手接线

### 自博弈训练（scripts/env.py · scripts/train.py · scripts/evaluate.py）
- `CardGameEnv` 支持 DQN 对手：`self`（自博弈）/ `snapshot`（固定 checkpoint）两种新对手模式；对手走自己的观测、transition、replay 路径（`_opponent_observation` 对手视角 4 维观测，与 agent 视角互为镜像），逐局座位交换使先手优势在两策略间交替（座位 0 恒先手，core 规则不变）
- 严格零和：`agent_reward + opponent_reward == 0` 逐局恒成立（终局结算口径未改：赢方 +all_bet / 输方 -all_bet，`_settle_rewards`）
- 新增稠密奖励塑形 `strength_shaping`：`k·(p−0.5)·押注额`（p=beats_probability），按**押注额**（而非底池，避免自增强死循环）计酬；修复「终局奖励 ±all_bet 量级随押注额线性增长 → Q 单调偏好最大押注 → 贪心恒 bet_100、动作分布退化、对局永不自然结束（撞 MAX_STEPS=200 强停、底池涨到 20060）」的塌缩；k=50.0 实测大注占比随牌力单调递增（弱牌 0.008~0.149 / 中牌 0.84~0.97 / 强牌 1.000）、natural_end_rate=1.0
- `scripts/train.py` 新增 `--opponent-mode {robot,self,snapshot}`（robot 为旧行为、产物命名不变）与 `--preset selfplay-v1`（固化验收配方：strength_shaping=50.0 / lr=3e-2 / gamma=0.95 / batch_size=4 / epsilon_start=0.5 / epsilon_decay=0.99 / opponent_replay_every=1 / hidden 缺省 (128,64)）；同 seed 产出 checkpoint sha256 逐字节一致（依赖 `set_global_seed`；注意 `from_checkpoint` 不推断隐藏层宽度，自定义 hidden 会 size mismatch）
- `scripts/evaluate.py` 新增 `--opponent-checkpoint` 双 checkpoint 对战（双方胜率 + 对手动作分布），summary 新增 `natural_end_rate`（区分自然终局与 MAX_STEPS 强停）；隐藏层宽度在 evaluate.py 侧读 state_dict 形状自适应（不改 agents/dqn.py）
- 复现：`python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out run/final` → `run/final/dqn_sp_ep100_seed7.pth`（主策略）+ `run/final/dqn_sp_opp_ep100_seed7.pth`（对手）；实测训练数据见 `docs/selfplay_train_report.md`

### UI 机器对手接线（ui/app.py）
- 新增 `resolve_checkpoint`：路径优先级 CLI `--checkpoint` > 环境变量 `DQN_CHECKPOINT` > 默认仓库根 `dqn_model_1.pth`，相对路径按仓库根解析；`main()` 新增 `--checkpoint`（入口 draw_me_vs_DQN_Plus.py 无需改动）
- `Controller.trained` / `Controller.policy_source` 提供可观测的「是否在用训练策略」标志；加载成功为 ε=0.0 贪心训练策略；缺失或损坏权重三行醒目告警（明写「当前机器方为未训练随机策略（epsilon=0.15），不是训练出的策略」）+ 修复指引，保留回退不崩溃
- 把训练产物复制为 `dqn_model_1.pth` 后，8 个既有基线失败测试全部转绿，全套件 **160 passed / 0 failed**
- 权重不入版本库（`.gitignore` 的 `*.pth` 与 `run/` 规则）；新环境需重训（命令见上）或拷贝权重（详见 docs/ARCHITECTURE.md 4.7/4.8）

### 测试（新增 3 份文件，共 36 用例）
- 新增 `tests/test_selfplay.py`（15 用例）：DQN 对手注入、对手视角对称、座位交换、零和奖励、冻结对手、训练冒烟与同 seed 可复现性、snapshot 模式、双 checkpoint 评估
- 新增 `tests/test_selfplay_preset.py`（6 用例）：preset 超参防回归、CLI 端到端、checkpoint 默认 config 可加载、self 模式不 KeyError、终局与逐步严格零和（含非零塑形押注步）
- 新增 `tests/test_trained_ui.py`（15 用例）：headless 端到端、动作与 checkpoint argmax 比对、路径优先级（CLI > 环境变量 > 默认）、缺失/损坏权重告警

### 文档
- `docs/ARCHITECTURE.md`：新增 4.4~4.8（自博弈环境、根因与 strength_shaping 解法、训练/评估入口、机器对手接线、权重获取与存放）与 6.10~6.12（3 份新测试文件断言清单）；7.6/7.7 条目逐条标注处置结果（已处置/升级/保留）；修正 6 处措辞过期（evaluate.py:23 import 归属、extend-exclude「备份」条目、missing_assets 使用情况、button_rects 注解、键码映射、last_now 属性位置）
- S/M 级重构清理与 README 三处修正已记录于 [0.2.1]
