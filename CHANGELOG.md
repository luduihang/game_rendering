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

## [0.1.x] — 基线与卫生（P0 / P1 部分）

- 修复运行环境：安装 pygame 2.6.1、matplotlib 3.8.0 → 3.11.2（numpy 2.x ABI 崩溃）、ruff 0.17.1
- 新增 `docs/BASELINE-REPORT.md` 与 `tests/baseline/`（D1/D2/D4/D5/D6/D7 复现脚本）
- 新增 `.gitignore`、`pyproject.toml`；35 个产物移出 git 索引
- 移除 `from sympy import false` 误依赖；`np.trapz` → `np.trapezoid`
- 重写 `README.md`
