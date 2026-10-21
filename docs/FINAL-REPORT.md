# 收尾报告：game_exercise 架构优化（r5 基线验收）

> 分支：`refactor/arch-v2`　依据契约：**r5（已批准）**
> 验收时间：本次会话末　验收方式：全部结论由命令实测产出，可重跑复现

## 一、总体结果

| 维度 | 优化前 | 优化后 |
|---|---|---|
| 代码形态 | 根目录 20 个平铺脚本，逻辑复制粘贴 | `core/` `agents/` `ui/` `scripts/` 四层 + 6 行薄入口 |
| `class DQN` 定义 | 21 处 | **1 处** |
| `class Game_room` 定义 | 11 处 | **0 处**（收敛为 `core.GameRoom` 1 处） |
| `time.sleep` | 21 处实际调用 | **0 处** |
| 手牌强度计算 | 2000 次蒙特卡洛 / 30.8 ms | 穷举 22100 手查表 / **0.025 ms（1230×）** |
| 单步墙钟 | ≈1530.8 ms（sleep 占 98.0%） | **0 ms 等待**（节奏器可注入） |
| 测试 | 0 | **104 项 pytest + 6 个缺陷回归脚本** |
| ruff | 682 errors | **0（All checks passed）** |
| 版本库跟踪产物 | `__pycache__` 15 / `*.pth` 14 / q_table·remember 6 | **0 / 0 / 0** |
| 仓库体积 | 284 MB（`.git` 176 + `src` 105 + `备份` 1.9） | **106 MB**（删除 `备份/` 与冗余脚本） |
| Python 代码量 | — | 4001 行（含测试） |

## 二、successCriteria 逐条验收

### 1. 单一策略落地 ✅
```
class DQN(     → 1     class GameRoom:  → 1     class DQNAgent: → 1
class Game_room → 0    nodraw_* 脚本   → 0     draw_* 脚本    → draw_me_vs_DQN_Plus.py（唯一入口）
```
证据：`grep -rn '^class DQN(' --include=*.py .` 等。

### 2. 删除清单完成且可追溯 ✅
删除 15 个策略脚本 + `mymath/robot.py` + `备份/`（37 项），commit `b3272e8`；
**追加清理**（P5 消除遗留链路）：`game_room_deepseek_cp.py`、`card_deck.py`、`mymath/robot2.py`，commit `e0263e1`。
`CHANGELOG.md` 逐项记录去向与恢复命令。

### 3. 保留策略可稳定启动 ✅
- 真实显示：`python draw_me_vs_DQN_Plus.py` 连续运行无未捕获异常（仅 libpng iCCP 素材告警，见「已知残留」）
- headless：连跑 **20 局**人类 vs DQN 全部完成
- 等待输入期间持续重绘、`SDL_QUIT` 立即响应（`tests/test_ui.py::TestEventLoop`）

### 4. D9 修复：AI 真正加载训练权重 ✅
```
AI 策略 epsilon = 0.0        （原实现恒为 1.0，等于随机）
AI 权重 input_dim = 4        （匹配 dqn_model_1.pth）
```
动作分布与随机策略的 L1 距离 > 0.5（`TestD9LoadedPolicyInEffect`）。

### 5. D8 修复：维度自适应 ✅
`DQNAgent.from_checkpoint()` 由 checkpoint 的 `fc1.weight`/`fc3.weight` 推断维度；
全仓无「硬编码 `DQN(9,6)` 加载 4 维权重」的组合（grep 仅命中文档说明）。

### 6. 缺陷回归：先红后绿 ✅
| 缺陷 | P0 基线（修复前） | 现在 |
|---|---|---|
| D1 看牌结算 | `bug=4`（牌小者获胜） | **`passed=4`** |
| D2 rest_option | 押 100 后仍为 0 | **`passed=5`** |
| D4 滞后 done | 结束后多走 1 步 | **`passed=4`** |
| D5 手牌归属 | 标签自相矛盾 | **`passed=5`** |
| D6 发牌偏置 | 均值 0.766 | **`passed=3`** |
| D7 时序 | sleep 占 98% | **`passed=8`** |

红证据：`docs/BASELINE-REPORT.md` + commit `97a2737`（当时脚本记录错误行为）。

### 7. 发牌均匀性可机器验证 ✅
均匀路径分位均值 **0.489**（≈0.5）；偏置路径 **0.766**，最强档占比 0.147 vs 0.013。
默认路径为 `deal_uniform`；`deal_strength_biased` 保留但**默认不被任何路径调用**（脚本断言）。

### 8. D7 时序缺陷全部消除 ✅
- (a) `ui/`、`scripts/` 中 `time.sleep` = **0**
- (b) 等待/思考期间 `SDL_QUIT` 被及时响应（含 AI 5 秒思考期用例）
- (c) core step < 5 ms；单帧 < 50 ms（实测整局 20 步 ≈ 76–104 ms）
- (d) 节奏器 `IMMEDIATE` 档整局**零等待**跑完

### 9. RepeatedTimer 加固 ✅
`safe stop()`（未启动不抛异常）、`daemon=True`、回调异常隔离到 `last_error`、
`is_running` 由锁保护。对应 `repro_d7_timing.py` 三项 PASS。

### 10. 穷举精确表 ✅
22100 手全枚举 + `lru_cache`；同一手牌任意次调用结果完全一致；查询 0.025 ms。

### 11. 牌型判定六类全覆盖 ✅
`tests/test_evaluator.py` 19 项：六类 + A 高顺边界 + A/2/3 非顺 + 平局 + 花色决胜 + 反对称性。

### 12. `core/` 与 `agents/` 无 pygame ✅
`tests/test_purity.py`（源码级 + 禁用 pygame 的 import 测试）+ `tests/test_agents.py` 静态检查。

### 13. UI↔core 状态一致性 ✅
`tests/test_ui.py::TestUICoreConsistency` 逐字段比对 `view()` 与 `room.snapshot()`；UI 不再自行记账。

### 14. 同种子逐位可复现 ✅
```
weights_hash 一致: True (57d93023675cf48d…)
```
限定 ≤20 回合、CPU-only（实测 3 回合约 1 秒）。

### 15. 干净环境安装可跑通 ✅
`python -m venv --system-site-packages /tmp/venv_verify` → `pip install -e .` →
从 `/tmp` 导入 `core/agents/ui/scripts/const/algorithm` 全部 OK →
训练、评估、UI 冒烟三入口全部跑通。

### 16. 产物不再跟踪 + ruff 通过 + README 可用 ✅
`__pycache__`/`*.pth`/remember/q_table 跟踪数均为 **0**；`ruff check .` → **All checks passed**；
README 含架构图、四入口、规则、缺陷表、CI 徽章。

## 三、测试与 CI

| 文件 | 用例数 | 覆盖内容 |
|---|---|---|
| `test_evaluator.py` | 19 | 牌型六类、边界、平局、花色决胜 |
| `test_rules.py` | 14 | D1/D2/D4、结算守恒、具名访问器 |
| `test_strength.py` | 8 | 精确表确定性、单调性、性能 |
| `test_dealing.py` | 8 | 均匀性、偏置路径、牌堆耗尽 |
| `test_agents.py` | 20 | D8/D9、接口契约、确定性、分层纯度 |
| `test_scripts.py` | 13 | 环境、可复现性、D4 防护 |
| `test_ui.py` | 18 | 时序契约、QUIT 响应、UI↔core 一致、性能 |
| `test_purity.py` | 4 | core 零重依赖 |
| **合计** | **104** | |

CI：`.github/workflows/ci.yml`（GitHub Actions，py3.11/3.12，ruff + pytest + 缺陷回归 + 无头冒烟 + 可复现性）。

## 四、已知残留（不影响验收，已记录）

1. **libpng `iCCP` 告警**：素材 PNG 的 sRGB profile 不规范。属「不重做美术资源」范围外，修法为用图像工具重存。不影响运行与渲染结果。
2. **共享 conda base 环境的既有依赖冲突**：`pandas 2.1.4`/`astropy`/`pywavelets` 要求 `numpy<2`，而项目需要 numpy 2.3.x；本轮未改动它们（项目已可通过独立 venv 隔离）。
3. **`mymath/probability_func.py` 的 `mean_func`/`integral_func`** 目前无调用方（Robot 迁移后仅 `mapping_dict`/`switch_func` 在用），保留以备后续策略使用。
4. **模型质量未提升**：`dqn_model_1.pth` 为历史产物（在旧规则下训练），本轮只保证其被正确加载、不再被闲置；重训属独立决策。

## 五、提交记录

```
e0263e1  P5: ui/ 时序与事件循环重构（D7 全部修复）
414b3ad  P4: scripts/ 训练与评估入口（无头、可复现）
b869030  P3: agents/ 智能体层（D8 维度自适应 + D9 加载真实权重）
4696aa8  P2: core 核心包 + D1/D2/D4/D6 修复（TDD）
b3272e8  P1: 单一策略清理（D-R5）
38c427d  P1(partial): 仓库卫生与依赖锁定
97a2737  P0: 基线核实与缺陷复现脚本
```

合并到 `main` 需人工执行（`integrateBranch` 未授予 agent）。
