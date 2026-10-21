# game_exercise —— 炸金花（三张牌）博弈 + DQN 人机对战

Python + pygame 实现的「炸金花」三张牌游戏，对手是一个 DQN 智能体。
**只保留一种策略实现**（人类 vs DQN），历史实验脚本已清理。

[![CI](https://github.com/luduihang/game_rendering/actions/workflows/ci.yml/badge.svg)](https://github.com/luduihang/game_rendering/actions/workflows/ci.yml)

## 快速开始

```bash
pip install -e ".[dev]"          # 安装依赖（建议在 conda env / venv 中）
python draw_me_vs_DQN_Plus.py    # 开始游戏
```

需要特定 CUDA 版本时先单独安装 torch：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu130
pip install -e ".[dev]"
```

**操作**：鼠标点按钮，或键盘 `1/2/3/4` 押 10/20/50/100、`F` 弃牌、`C` 看牌、`R` 重开一局、`Esc` 退出。

## 架构

```
                    ┌──────────────────────────────┐
   入口             │  draw_me_vs_DQN_Plus.py (6 行)│
                    └───────────────┬──────────────┘
                                    │
                    ┌───────────────▼──────────────┐
   表现层           │  ui/                          │
                    │   app.py    事件驱动主循环     │
                    │   clock.py  可注入节奏器       │
                    │   render.py 薄渲染（无规则）   │
                    │   theme.py  布局 / 资源路径    │
                    └───────┬───────────────┬──────┘
                            │               │
            ┌───────────────▼──────┐  ┌─────▼──────────────┐
   领域层   │  core/                │  │  agents/            │
            │   cards.py    牌      │  │   base.py  BaseAgent│
            │   evaluator.py 牌型   │  │   dqn.py   DQN      │
            │   strength.py 精确表  │  │   robot.py Robot    │
            │   dealing.py  发牌    │  └─────┬──────────────┘
            │   rules.py    状态机   │        │
            └───────────┬───────────┘        │
                        │                    │
            ┌───────────▼────────────────────▼──────────┐
   入口层   │  scripts/  env.py · train.py · evaluate.py │
            └────────────────────────────────────────────┘

  依赖方向严格单向：ui → core/agents，scripts → core/agents。
  core/ 与 agents/ 不依赖 pygame，可无头运行（CI 用 SDL dummy 驱动验证）。
```

### 分层约束（有测试守护）

| 约束 | 守护测试 |
|---|---|
| `core/` 不 import pygame / numpy / scipy / torch | `tests/test_purity.py` |
| `agents/`、`scripts/` 不 import pygame | `tests/test_agents.py`、`tests/test_scripts.py` |
| 无模块在 import 期加载权重 | `tests/test_agents.py::TestLayeringAndImportPurity` |
| `ui/`、`scripts/` 无 `time.sleep` | `tests/test_ui.py::TestTicker::test_no_sleep_in_source` |
| UI 不自行记账（渲染值 = core 快照） | `tests/test_ui.py::TestUICoreConsistency` |

## 目录

```
core/      cards·evaluator·strength·dealing·rules   纯规则，无重依赖
agents/    base·dqn·robot                            策略实现
ui/        app·clock·render·theme                    渲染与事件循环
scripts/   env·train·evaluate                        训练/评估入口
mymath/    func_const·probability_func               概率密度工具（Robot 依赖）
tests/     单元测试 + baseline 缺陷回归脚本
src/       美术与音频资源
```

## 四个入口

| 用途 | 命令 |
|---|---|
| 游玩 | `python draw_me_vs_DQN_Plus.py` |
| 训练 | `python -m scripts.train --episodes 200 --seed 7 --device cpu --out run/exp1` |
| 评估 | `python -m scripts.evaluate --rounds 500 --seed 7 --checkpoint dqn_model_1.pth` |
| 测试 | `pytest -q` / `ruff check .` |

产物统一写入 `run/`（已被 `.gitignore` 覆盖）。同种子两次训练产出**逐位一致**的权重。

## 规则（摘要）

- 每人 3 张牌：单张 < 对子 < 顺子 < 金花 < 顺金 < 三张
- 开局自动押 5，之后轮流押 10/20/50/100、弃牌或看牌
- **最低可押档 = 已出现的最高押注档**（单调不减）
- 看牌需支付当前单注，与对手比大小，**比输者输掉本局**
- 最后留在场上的玩家赢得全部底池

## 已修复的缺陷

| 编号 | 问题 | 证据 |
|---|---|---|
| D1 | 看牌结算比较方向反转（牌小者获胜） | `tests/baseline/repro_d1_showcards.py` |
| D2 | UI 侧 `rest_option` 用 `min()`，押注门槛不升 | `repro_d2_rest_option.py` |
| D4 | 训练循环滞后 `done` 标志，结束后多走一步 | `repro_d4_lagging_done.py` |
| D5 | 手牌归属标签自相矛盾 | `repro_d5_wiring.py` |
| D6 | 发牌三抽一取最优，分布有偏 | `repro_d6_dealing.py` |
| D7 | `time.sleep` 占单步 98%；忙等事件泵吞掉 QUIT | `repro_d7_timing.py` |
| D8 | 权重维度与模型声明不匹配，import 即崩 | `tests/test_agents.py` |
| D9 | 保留策略未加载训练权重，实际随机 | `tests/test_agents.py::TestD9LoadedPolicyInEffect` |

修复前后的量化对比见 [`docs/BASELINE-REPORT.md`](docs/BASELINE-REPORT.md)，
逐条验收结论见 [`docs/FINAL-REPORT.md`](docs/FINAL-REPORT.md)。

## 环境要求

Python ≥ 3.11；pygame 2.6.1；numpy 2.3.x；scipy 1.17.x；matplotlib 3.11.x；torch 2.13.x。
版本范围见 `pyproject.toml`。
