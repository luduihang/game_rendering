# game_exercise —— 炸金花（三张牌）博弈 + DQN 人机对战

Python + pygame 实现的「炸金花」三张牌游戏，带一个 DQN 智能体作为对手。
**当前只保留一种策略实现**（人机对战），历史实验脚本已清理。

> ⚠️ 本仓库正在进行架构重构（分支 `refactor/arch-v2`）。
> 阶段进度与缺陷清单见 `docs/BASELINE-REPORT.md`；契约见 `management/PROJECT.md`。

## 快速开始

```bash
# 1. 安装依赖（建议在 conda env 或 venv 中）
pip install -e ".[dev]"

# 2. 启动游戏（人类对战 DQN）
python draw_me_vs_DQN_Plus.py
```

若使用 CPU 版 torch 或需要特定 CUDA 版本，请先单独安装对应 torch 轮子：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu130
pip install -e ".[dev]"
```

### 无头运行（CI / 无显示器环境）

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python draw_me_vs_DQN_Plus.py
```

## 目录结构

```
game_exercise/
├── draw_me_vs_DQN_Plus.py   # 唯一策略入口：人类 vs DQN 交互对局
├── card_deck.py             # 牌堆、牌型判定、手牌强度（含 2000 次蒙特卡洛胜率）
├── const.py                 # 资源路径、UI 坐标、按钮区域、颜色、BGM 清单
├── algorithm.py             # 文字渲染、消息高亮、RepeatedTimer、规则帮助文案
├── game_room_deepseek_cp.py # Game_room(对局状态) + DQN 网络 + DQNAgent
├── mymath/                  # 对手策略（Robot2）与卷积概率密度工具
│   ├── robot2.py            # 唯一的对手策略实现
│   ├── robot.py             # （待清理：与 robot2 重复）
│   ├── func_const.py        # 分段概率密度函数 f10/f20/f50/f100
│   └── probability_func.py  # 函数卷积、积分、ID 映射
├── src/                     # 美术与音频资源（卡牌、角色、按钮、字体、BGM）
├── tests/baseline/          # Phase 0 缺陷复现脚本（可重跑）
└── docs/BASELINE-REPORT.md  # 基线实测报告
```

## 游戏规则（摘要）

- 每人 3 张牌，牌型大小：单张 < 对子 < 顺子 < 金花 < 顺金 < 三张
- 开局自动押注 5，随后轮流押注 10/20/50/100，或弃牌、看牌
- **最低可押档 = 已出现的最高押注档**（单调不减）
- 看牌需支付当前单注费用，与对手比大小，**比输者输掉本局**
- 最后留在场上的玩家赢得押注池

完整规则见游戏内「帮助」界面（`algorithm.py::show_help_font`）。

## 已知问题

`docs/BASELINE-REPORT.md` 有完整实测证据，简要列出：

| 编号 | 问题 | 状态 |
|---|---|---|
| D1 | 看牌结算比较方向整体反转（牌小者获胜） | 待修（P2） |
| D2 | UI 侧 `rest_option` 使用 `min()`，押注门槛不升 | 待修（P2） |
| D4 | 训练循环使用滞后 `done` 标志，结束后仍多走一步 | 待修（P4） |
| D6 | 发牌三抽一取最优，分布有偏（均值 0.766 vs 均匀 0.489） | 待修（P2） |
| D7 | `time.sleep` 占单步墙钟 98%；忙等事件泵忽略 QUIT | 待修（P5） |
| D8 | 权重维度与模型声明不匹配，多个脚本 import 即崩 | 待修（P3） |
| D9 | 保留策略的 AI 未加载训练权重，实际为随机策略 | 待修（P3） |

## 测试

```bash
pytest                      # 单元测试（随重构阶段补齐）
ruff check .                # 静态检查

# 缺陷基线复现（记录当前错误行为，用于「先红后绿」）
python tests/baseline/repro_d1_showcards.py
python tests/baseline/repro_d2_rest_option.py
python tests/baseline/repro_d4_lagging_done.py
python tests/baseline/repro_d5_wiring.py
python tests/baseline/repro_d6_dealing.py
SDL_VIDEODRIVER=dummy python tests/baseline/repro_d7_timing.py
```

## 环境要求

Python ≥ 3.11；pygame 2.6.1；numpy 2.3.x；scipy 1.17.x；matplotlib 3.11.x；torch 2.13.x。
版本范围见 `pyproject.toml`。
