# Phase 0 基线报告（game_exercise 架构优化）

> 任务：`p0-baseline`　分支：`refactor/arch-v2`　依据契约：r3（已批准）/ r4（草稿，决策记录）
> 生成方式：全部数字来自 `bash` 与 `tests/baseline/*.py` 实跑，不含未核实估计。

## 1. 运行环境基线（T0.1）

| 组件 | 初始状态 | 当前状态 |
|---|---|---|
| python | 3.11.7 (conda base) | 3.11.7 |
| pygame | **缺失** | 2.6.1 (SDL 2.28.4) |
| numpy | 2.3.5 | 2.3.5 |
| matplotlib | **3.8.0，在 numpy 2.x 下 ABI 崩溃** | 3.11.2 |
| torch | 2.13.0+cu130 | 2.13.0+cu130 |
| scipy | 1.17.1 | 1.17.1 |
| sympy | 1.14.0（误依赖） | 1.14.0（待 P1 移除） |
| ruff | **缺失** | 0.17.1 |
| pytest | 9.1.1 | 9.1.1 |

**关键结论**：基线状态下 `import mymath.robot` → `matplotlib` ABI 崩溃 → `import game_room_deepseek_cp` 失败
→ **所有训练脚本与 draw.py 在该环境下完全无法启动**。修复后（pygame 安装 + matplotlib 升级到支持 numpy 2.x）
项目模块 import 链全部打通。

无头渲染已验证：`SDL_VIDEODRIVER=dummy` 下 `pygame.display.set_mode` + `flip` 正常。

## 2. 仓库清单（T0.2，已消除全部「未核实」）

| 指标 | 实测 |
|---|---|
| git 跟踪文件 | 326 |
| `.py` 文件 | 37（根目录 20 / `备份` 12 / `mymath` 5） |
| `class Game_room` 定义 | **11** |
| `class DQN(torch.nn.Module)` 定义 | **21** |
| `class DQNAgent` 定义 | 3 |
| `Cards_Probability` 引用 | 48 |
| `time.sleep(` 实际调用 | **21**（12×1.5s、6×3s、5×1s）+ 6 处注释掉的 2s |
| `threading.Timer` | 2 |
| `load_state_dict` | 19 |
| `from sympy` | 12 |
| 仓库体积 | 总 284MB（`.git` 176MB、`src` 105MB、`备份` 1.9MB） |
| 版本库跟踪的产物 | `__pycache__` 15 项、`*.pth` 14 个、q_table/remember 6 个 |
| `.gitignore` / `requirements.txt` / `pyproject.toml` | **全部缺失** |
| 测试文件 | **0** |

## 3. 缺陷实测复核（T0.3）

### D1 看牌结算 —— 比 PRD 描述更严重（4/4 全错）

`Game_room.get_choice`，action==5：

```python
if self.cards1_value < self.cards2_value:
    self.winner = 0
```

实测 4 个用例：

| whose_turn | cards1 较小 | 期望 winner | 实际 winner |
|---|---|---|---|
| 0 | 是 | 1 | **0** |
| 0 | 否 | 0 | **1** |
| 1 | 是（玩家1牌大） | 1 | **0** |
| 1 | 否（玩家1牌小） | 0 | **1** |

**新结论**：不只是"忽略 whose_turn 导致看牌方输局反转"，而是**比较方向整体反了**——
`cards1 < cards2` 时判玩家0胜，即**牌小的一方永远获胜**。PRD 的 D1 描述需升级为
「比较方向反转 + 忽略 whose_turn」双重缺陷。

复现：`python tests/baseline/repro_d1_showcards.py`

### D2 rest_option 语义 —— 确认，范围如 r3 所述

`draw.py::Draw_Pic.update_inform` 押注 100（索引3）后 `rest_option` 仍为 **0**（门槛未提升），
允许继续小额下注。`draw_me_vs_DQN.py` 用 `max(...)` 正确（静态核对，因其 import 会崩，见 D7-d）。

复现：`python tests/baseline/repro_d2_rest_option.py`

### D4 滞后 done 标志 —— 确认，仅一处

滞后版本：`get_choice` 总调用 2 次，其中 **1 次发生在对局已结束后**。
`room.finish` 守卫版本：结束后调用 0 次。**证实 r3 订正**（draw.py 无此问题）。

复现：`python tests/baseline/repro_d4_lagging_done.py`

### D5 接线复核 —— 证实 r3 判定，r2 的"信息泄漏"不成立

实测：`Robot('1').init_dick(['1','0'], room.cards2)` 后机器人持有 `cards2`；
玩家0 的 `get_state` 档位来自 `cards1`。⇒ 各自读自己的牌，**无泄漏**。

但 `__init__` 打印「机器人的手牌是 cards1」与 `show_inform` 打印「玩家0的手牌是 cards1」
**同时把 cards1 描述为不同归属** —— 遗留脏标签确认为真实问题（仅可读性）。

复现：`python tests/baseline/repro_d5_wiring.py`

### D6 发牌偏置 —— 量化完成

用穷举 C(52,3)=22100 手的精确强度表，把任一手牌映射为分位（击败比例）：

| 路径 | 均值 | 中位 | p25 | p75 | 最强档(>0.95)占比 |
|---|---|---|---|---|---|
| 均匀 `draw_cards(3)` | 0.489 | 0.471 | 0.241 | 0.756 | 0.013 |
| `draw_cards_plus(3)` | **0.766** | 0.797 | 0.653 | 0.908 | **0.147**（11.3 倍） |

⇒ 偏置路径让手牌强度整体上移 0.277，顶级手牌出现率放大 11 倍。均匀路径分位均值 0.489 ≈ 0.5，验证表本身正确。

复现：`python tests/baseline/repro_d6_dealing.py`

### D7 时序与并发 —— 四项全部实测确认

**D7-a 单步耗时分解**（`draw_me_vs_DQN.py` 口径）：

| 组成 | 耗时 |
|---|---|
| `Cards_Probability.get_state()`（2000 轮蒙特卡洛） | 30.8 ms |
| `draw_cards_plus(3)`（3×2000 轮） | 99.3 ms |
| 固定 `time.sleep(1.5)` | 1500 ms |
| **单步墙钟** | **≈1530.8 ms（sleep 占 98.0%，计算占 2.0%）** |

⇒ 卡顿主因是 sleep 而非计算。但计算侧同样有问题：单局多次 `get_state` 会让 30.8ms 累积成秒级。

**D7-b 忙等事件泵**：`check_button_click` 含 `while not signal` 忙等，
且**完全不处理 `pygame.QUIT`** → 等待人类点击期间窗口无法关闭、无法重绘。静态证据确凿。

**D7-c RepeatedTimer —— r3 的一项判断需订正**：

| r3 声称 | 实测 |
|---|---|
| `stop()` 未 start 时抛 `AttributeError` | ✅ 确认：`'NoneType' object has no attribute 'cancel'` |
| 无锁竞态 | 代码确无锁（未构造出稳定复现，保留为代码审查结论） |
| `next_call` 累积漂移 | 代码成立 |
| **回调异常静默断链** | ❌ **不成立**：`_run()` 先 `start()` 再调回调，测得 0.52s/0.05s 窗口内 10/10 次全部触发，未断链 |
| （r3 未提） | 🆕 `threading.Timer` 为**非 daemon**（`daemon=False`）→ 未 `stop()` 会阻止进程退出 |

异常的真实后果是：每次向 stderr 抛未捕获堆栈（刷屏），而非断链。

**D7-d import 期加载权重 —— 实测直接崩溃**：见下节 D8。

## 4. 新发现：D8 模型权重与模型声明不匹配（阻断级）

`draw_me_vs_DQN.py` 等脚本在**文件级**执行 `model = DQN(9,6)` + `load_state_dict('dqn_model_0.pth')`，
而各权重实际输入维度：

| 权重文件 | fc1 形状 | input_dim | output_dim |
|---|---|---|---|
| `dqn_model_0.pth` | (128, **4**) | 4 | 6 |
| `dqn_model_1.pth` | (128, **4**) | 4 | 6 |
| `dqn_final.pth` / `ep50/150/200/250` | (128, **9**) | 9 | 6 |
| `pytorch_dqn.pth` | 非 DQN state_dict（4 键） | — | — |

⇒ 声明 `DQN(9,6)` 却加载 4 维权重的脚本**在 import 阶段即抛 RuntimeError**：

- `draw_me_vs_DQN.py` ❌ 崩溃
- `draw_PRO_vs_DQN.py` ❌ 崩溃
- `nodraw_DQN_vs_QN.py`、`nodraw_cmp_DQN_PRO.py` ❌ 崩溃
- `use_model.py` ❌ 加载不存在的 `dqn_model_ep100.pth`
- `draw_me_vs_DQN_Plus.py` ✅ 唯一维度自洽（`DQN(4,6)` + 3 盘面特征 + 1 个 card_prob = 4 维）
- `draw.py` / `draw_me_train_DQN.py` ✅ 可 import

## 5. 结论与对后续阶段的影响

1. **P0 阻塞项全部落定**，PRD 中「未核实」标注已可消除。
2. **D1 需升级描述**（比较方向反转，非仅忽略 whose_turn）——建议 r5 订正。
3. **D7-c 需订正**（回调异常不断链；新增非 daemon 风险）——建议 r5 订正。
4. **新增 D8**（权重/声明维度不匹配）——不在 r3 范围内，需并入计划（P3 的 checkpoint 工厂可覆盖）。
5. 环境已恢复可运行（pygame + matplotlib 修复），基线脚本可一键重跑。

## 6. 复现方式

```bash
cd /home/kipley/Documents/code/learning/game_exercise
python tests/baseline/repro_d1_showcards.py
python tests/baseline/repro_d2_rest_option.py
python tests/baseline/repro_d4_lagging_done.py
python tests/baseline/repro_d5_wiring.py
python tests/baseline/repro_d6_dealing.py
SDL_VIDEODRIVER=dummy python tests/baseline/repro_d7_timing.py
```
