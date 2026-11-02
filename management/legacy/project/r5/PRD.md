# PRD：game_exercise 架构优化（r5，单一策略版）

## 1. 背景与本次变更
game_exercise 是 Python + pygame 的「炸金花」三张牌博弈游戏 + DQN 训练实验仓库。原形态：根目录 20 个脚本互相复制 `Game_room`/`DQN`/`DQNAgent`（实测 `class DQN` **21 份**、`class Game_room` **11 份**），另有整份旧代码副本 `备份/`（37 项）与失配的模型产物。

**人工决策（r5）**：只保留**一种**策略实现，其余全部清理。保留对象为：
- `draw_me_vs_DQN_Plus.py` —— 人类对战 DQN 的交互式策略，也是**唯一维度自洽且可启动**的脚本（`DQN(4,6)` + 3 个盘面特征 + 1 个 `card_prob` = 4 维，匹配 `dqn_model_1.pth`）
- `mymath/robot2.py` —— 唯一对手策略实现

删除 15 个策略脚本、`mymath/robot.py` 与整个 `备份/` 目录（清单见契约 inScope，全部可从 git 历史恢复）。

## 2. 基线实测结论（见 `docs/BASELINE-REPORT.md`）

环境在基线下**完全无法运行**：`mymath.robot` → `matplotlib 3.8.0` 在 numpy 2.3.5 下 ABI 崩溃 → `import game_room_deepseek_cp` 失败 → 所有训练脚本与 `draw.py` 无法启动；pygame 亦未安装。恢复后全链路通过。

### D1 看牌结算：比较方向整体反转 + 忽略 whose_turn（严重）
```python
if self.cards1_value < self.cards2_value:
    self.winner = 0        # 牌小者获胜
```
实测 4/4 用例判胜与规则相反。**订正 r3**：不止"忽略 whose_turn 导致看牌方输局反转"，而是比较方向整体反了。正确语义（契约 D-R2）：看牌方比输即输，`winner = whose_turn if 自己手牌较大 else 1 - whose_turn`。

### D2 rest_option：`draw.py` 用 `min()`（真 bug）
基线实测：押注 100（索引 3）后 `rest_option` 仍为 0，门槛不升、允许继续小额下注。`draw_me_vs_DQN.py` 用 `max()` 正确。
（注：`draw.py` 在 r5 删除清单内，但该语义已判据纳入 core 契约测试。）

### D4 滞后 done 标志：仅 `game_room_deepseek_cp.py::main`
基线实测：滞后版本结束后仍多调 1 次 `get_choice`；`room.finish` 守卫版本为 0 次。

### D5 接线：无信息泄漏（订正 r2）
实测机器人持 `cards2`、玩家0 的 `get_state` 读 `cards1` → 各自读自己的牌。真实问题仅为 `__init__` 与 `show_inform` 的手牌标签自相矛盾（可读性）。

### D6 发牌偏置：量化确认
穷举 22100 手的精确分位：均匀路径均值 0.489、最强档占比 0.013；`draw_cards_plus` 均值 **0.766**、最强档 **0.147**（11 倍）。决策（D-R1）：默认均匀发牌，偏置逻辑保留为可选开关。

### D7 时序与并发（人工提出）
- **D7-a** 单步墙钟 ≈1530.8ms，其中 `sleep(1.5)` 占 **98.0%**，计算占 2.0%（单次 `get_state` 30.8ms、`draw_cards_plus` 99.3ms）
- **D7-b** `check_button_click` 为 `while not signal` 忙等且**完全不处理 `pygame.QUIT`** → 等待期间窗口无法关闭、无法重绘
- **D7-c 订正 r3**：`stop()` 未 start 抛 `AttributeError` ✅；但**"回调异常静默断链"不成立**（`_run` 先 `start()` 再回调，实测 10/10 次全部触发），真实后果是每次向 stderr 抛未捕获堆栈；🆕 `threading.Timer` 为**非 daemon**，未 `stop()` 会阻止进程退出
- **D7-d** import 期 `load_state_dict` 使启动与权重文件硬耦合（实测直接导致 4 个脚本 import 崩溃）

### D8 权重维度失配（新增，阻断级）
`dqn_model_0.pth`/`dqn_model_1.pth` 为 **4 维**输入；`dqn_final.pth`/`dqn_model_ep*.pth` 为 **9 维**；`pytorch_dqn.pth` 非 DQN 结构。而 8 处脚本声明 `DQN(9,6)` 去加载 4 维权重 → `draw_me_vs_DQN.py`、`draw_PRO_vs_DQN.py`、`nodraw_DQN_vs_QN.py`、`nodraw_cmp_DQN_PRO.py` **import 即 RuntimeError**；`use_model.py` 加载不存在的 `dqn_model_ep100.pth`。

### D9 保留策略实际未使用训练权重（新增）
`draw_me_vs_DQN_Plus.py::__main__` 用 `DQNAgent()`（默认 `state_dim=9`、`epsilon=1.0`）→ 恒走随机分支，从不加载 checkpoint；同文件级的 `model = DQN(4,6)` + `dqn_model_1.pth` + `select_action()` 是**死代码**。⇒ 现状是"能启动，但 AI 是乱下注的"。

## 3. 已核实的工程问题
1. **性能**：`Cards_Probability` 每次调用 2000 轮蒙特卡洛（实测 30.8ms/次）；`get_state` 与 `get_probability` 代码完全重复。穷举 22100 手建表后全部 O(1)。
2. **模块级副作用**：`card_deck.py` import 期执行演示并 print；`const.py` 类体定义期调 `pygame.Rect`（使 `import const` 依赖 `pygame.init`）。
3. **隐式依赖**：`mymath/robot*.py` 用 `np` 未显式 import，靠星号导入泄漏。
4. **重复实现**：Robot 与 Robot2 约 130 行近乎逐行相同（r5 起只保留 Robot2）。
5. **UI 与逻辑耦合**：`Draw_Pic` 自维护 `rest_option/turn/all_bet/bets/player_money` 并自行复算押注（D2 的温床），与 `Game_room` 形成两个事实来源。
6. **坏路径**：`const.py` 硬编码 `'../game_exercise/src/...'` 与 `'../myclient/src/BGM/...'`（后者指向仓库外，必然失效）。
7. **误依赖**：12 处 `from sympy import false`，未使用。
8. **废弃 API**：`np.trapz`（numpy 2.x 废弃，实测仍存在但已弃用）。
9. **死代码**：`conv_func.arr_100` 从未被读取。
10. **工程卫生**：`.gitignore`/`requirements.txt`/`pyproject.toml` 全缺；**零测试**；仓库 284MB（`.git` 176MB、`src` 105MB）；跟踪 `__pycache__` 15 项、`*.pth` 14 个。

## 4. 用户与需求
仓库所有者本人，学习/实验用途。核心诉求：
- 只保留一种策略，其余清理干净，**仓库要能看懂**
- 保留的策略要**能顺利启动、能正常玩**
- 换机器能一键装好跑通
- 界面不能卡死、不能靠 sleep 撑节奏

## 5. 目标
- **单一事实来源**：规则、牌型判定、DQN 网络各只有一份。
- **确定性**：同种子训练逐位可复现；胜率是精确值。
- **可测试**：核心规则全覆盖单测；每个真 bug 修复都有先红后绿回归（基线快照已就绪）。
- **可分层**：core/ 与 agents/ 不依赖 pygame，无头可跑。
- **零阻塞**：UI 事件驱动，节奏可注入，headless 零等待。
- **可启动**：保留策略在真实显示下完整走完一局，AI 真正加载已训练权重（D9）。

## 6. 非目标
见契约 outOfScope：不加功能、不重训、不改 git 历史、不动资产内容、不打包发布、不动治理目录、不调 conv_func 公式、不重命名中文资源、不引入 asyncio、不为被删策略保留兼容层。

## 7. 风险
- **R1（已接受）**：默认均匀发牌改变对局分布；旧 9 维 `.pth` 在新状态口径下无意义，仅归档不删除。
- **R2（已接受）**：D1 修复改变历史对局判定结果。
- **R3（已关闭）**：D5 接线经实测确认无泄漏。
- **R5（已接受）**：保留策略依赖 4 维 `dqn_model_1.pth`，其余权重归档。
- **R6**：删除 15 个脚本不可逆地改变仓库形态（可经 git 恢复），需在本契约批准后执行。
- **R7**：P5 是工作量最大阶段，需与 P4 串行以避免同工作区写冲突。

## 8. 验收
见契约 successCriteria，逐条可机器验证（grep 断言、pytest、headless 耗时与 QUIT 响应测试、发牌均匀性检验、策略加载后的动作差异检验）。

## 9. 决策记录
| 编号 | 内容 | 状态 |
|---|---|---|
| D-R1 | D6：默认均匀发牌 + 保留 `draw_strength_biased()` 默认关闭 | 已确认 |
| D-R2 | D1：比输者输，`winner = whose_turn if 自己较大 else 1 - whose_turn` | 已确认 |
| D-R3 | D5 信息泄漏证伪，仅修标签与具名属性 | 已确认 |
| D-R4 | D3 降级为 API 契约（IllegalAction） | 已确认 |
| D-R5 | 只保留一种策略：`draw_me_vs_DQN_Plus.py` + `mymath/robot2.py`，其余 15 脚本 + `robot.py` + `备份/` 删除 | r5 待批准 |
| D-R6 | D7-c 订正：回调异常不断链；真实风险为非 daemon 线程阻止退出 | r5 待批准 |
