# PRD：game_exercise 架构优化（r4）

## 1. 背景
game_exercise 是 Python + pygame 的「炸金花」三张牌博弈游戏与 DQN 训练实验仓库。现状：根目录平铺约 15 个脚本，`draw_*`/`nodraw_*` 互相复制粘贴 `Game_room`/`DQN`/`DQNAgent`；`mymath/` 为 AI 策略包；`src/` 为美术与音频资产。

**证据获取限制**：r1–r3 分析在基线 DRAFT 下进行，bash/grep/目录枚举被治理层拦截，只能定向读文件取证。文件数量类统计标注「未核实」，必须在 Phase 0 用 bash 落定后才可排期。

## 2. 已核实规则与数据缺陷

### D1 看牌结算忽略 whose_turn（严重，确认，语义已由人确认）
`game_room_deepseek_cp.py::Game_room.get_choice`，action==5 分支只比较 `cards1_value < cards2_value` 就定 winner，完全无视 `self.whose_turn`。代码自己的注释已写明正确语义：「玩家0看牌 如果玩家0小 winner = 1 / 玩家1看牌 如果玩家1小 winner = 0」。
**已确认修复语义（D-R2）**：看牌方支付当前单注费用后与对手比大小，比输者输掉本局 → 当 `whose_turn` 手牌较小时 `winner = 1 - whose_turn`。与 `show_help_font` 规则文本一致。

### D2 rest_option 语义不一致（确认，范围收窄）
- **规则文本**（`algorithm.py::show_help_font`）：「每轮玩家可以押注大小的最小选项是当前所有玩家押注选项的最大值」。
- `Game_room.get_choice`：`self.rest_option = action`。在「动作合法」不变量下（`legal_actions = range(rest_option, 6)` 已限制下限）**等价于运行最大值 → 本就正确，不得改动语义**。
- `draw.py::Draw_Pic.update_inform`：`self.rest_option = min(self.rest_option, self.option)` → **真 bug**（门槛只会降低）。且 `__init__` 里 `rest_option = 0` 是 int，被后续分支当索引用，两种含义混用同一字段。
- 旁证：同仓库 `draw_me_vs_DQN.py::update_inform` 写的是 `max(self.rest_option, self.option)` —— 同一项目内已存在正确版本，说明这是复制分叉造成的漂移。

### D4 训练循环滞后 done 标志（确认，仅一处）
`game_room_deepseek_cp.py::main`：`while not room.finish:` 内用 `if not done:` 守卫对手行动，而 `done` 只在其后才置 True → 玩家动作已结束对局时，对手仍在已结束的房间上行动，污染经验回放。
**订正 r2**：`draw.py::__main__` 用的是 `if not room.finish:`，**没有此问题**，r2 声称「两者均为 if not done」举证错误。

### D6 发牌非均匀（确认，已决策修复 D-R1）
`card_deck.py::Cards.draw_cards_plus`：抽 3 组候选、各算胜率、只留最高的一组，其余 6 张弃置不回堆。双方手牌来自「3 次抽样取最大」的有偏分布 ⇒ 穷举精确胜率与真实发牌分布**不匹配**，`Cards_Probability` 只能当「相对强度」。
**已确认修复方式（D-R1）**：默认发牌改为均匀（每名玩家直接从洗好的牌堆取 3 张）；旧「三抽一取最优」逻辑保留为显式可选 `core.dealing.draw_strength_biased()`，默认关闭，仅供复现旧实验；旧 `dqn_*.pth` 归档不删除。
代价（已接受）：默认对局公平性改变，旧模型在新默认发牌下失效。

### D5 已撤销（r2 结论错误，须记录以免重犯）
r2 断言 `get_state(room, 0)` 读到对手手牌、构成信息泄漏。**经核实该结论不成立**：
- `show_inform()`：`玩家0的手牌是 cards1` / `玩家1的手牌是 cards2`；
- `opponent_robot.init_dick(['1','0'], room.cards2)`：机器人 id `'1'` 持 **cards2** → 机器人是玩家1；
- 训练循环：`reward = all_bet if room.winner == 0 else -player_bet[0]` → DQN 是玩家0。
⇒ DQN 的 `get_state` 读 `cards1` 读的是**自己的牌**，逻辑自洽、无泄漏。
真实遗留问题是 `__init__` 里 `print("机器人的手牌是", self.cards1)` 与 `show_inform` 的标签**自相矛盾**（前者说 cards1 属机器人，后者说 cards1 属玩家0）。处理：修正标签 + core 中用 `own_hand`/`opponent_hand` 具名属性消除歧义，**不改状态空间语义、不使旧模型失效**。Phase 0 仍需实测复核一次。

### D3 降级为 API 健壮性要求（r2 定性不准）
- 「action=5 不看 rest_option 门槛」不成立：看牌费用固定为 `options[rest_option]`，规则就是按当前单注自动收费，无可校验门槛。
- 「弃牌后仍推进 whose_turn/circle」代码确实执行，但 `finish=True` 后外层 `while not room.finish` 立即退出，**无可观测行为差异**，写不出失败测试。
- 唯一实质点（已并入 D4 相关）：对已 finish 的房间继续调 `get_choice` 会改写 `winner`。
⇒ core 侧把非法动作做成显式 `IllegalAction` 异常作为**契约测试**，不列入「先红后绿」bug 清单。

## 3. 已核实时序与并发缺陷（D7，人工提出）

### D7-a time.sleep 散落在步进与渲染之间
`draw.py`：每步 `time.sleep(3)`；`draw_me_vs_DQN.py`：DQN 回合与人类回合各 `time.sleep(1.5)`，外加每局开始 `time.sleep(1.5)`。一局 N 步即 N×1.5~3 秒的硬阻塞。sleep 还隐式承担了「让画面停留可读」的唯一职责 —— 因此不能简单删除，必须重构为可注入的节奏器（真实时间 / 固定步长 / 立即三档，测试用「立即」）。

### D7-b 阻塞式事件泵劫持事件循环
`draw_me_vs_DQN.py::Draw_Pic.check_button_click`：
```
signal = False
while not signal:
    for event in pygame.event.get(): ...
```
人类回合期间独占事件队列并在 Python 层忙等：等待期间 `SDL_QUIT` 无法被响应（窗口无法关闭）、无法重绘、`clock.tick(20)` 完全失效 → 表现为 UI 冻死。这是「事件循环被业务逻辑劫持」，不是渲染性能问题。

### D7-c RepeatedTimer 线程不安全
`algorithm.py::RepeatedTimer`：`is_running` 为裸 bool 无锁保护（start/stop 竞态）；`stop()` 在未 `start()` 时 `self._timer is None` → `AttributeError`；`next_call` 逐次累加导致漂移；`_run` 内无 try，回调异常会静默掐断定时器链。与 pygame 事件循环共存时是卡顿与偶发崩溃来源。

### D7-d import 期副作用耦合启动路径
`draw_me_vs_DQN.py` 在**文件级**执行 `model = DQN(9,6)` + `model.load_state_dict(torch.load('dqn_model_0.pth'))` + `model.eval()`。⇒ import 该模块即读权重文件，文件缺失/不匹配则整个模块导入失败，UI 启动与权重可用性硬耦合。与 `card_deck.py` 的模块级 print、`const.py` 类定义期 `pygame.Rect` 同属一类反模式。

### 根因归纳
单步延迟 = Monte Carlo（数千次牌型计算）+ sleep(1.5s) + 阻塞事件泵，三者叠加，被误判为「渲染慢」。修复必须同时处理：计算（穷举查表）、时序（节奏器）、事件（非阻塞状态机）。

## 4. 已核实的其他工程问题
1. **性能**：`Cards_Probability.get_probability/get_state` 每次 2000 轮 `reset_deck+shuffle+Get_Value`；`draw_cards_plus` 每手调 3 次、`Robot.init_dick` 再调 1 次 → 单局上万次牌型计算；`get_state` 与 `get_probability` 代码完全重复。C(52,3)=22100 可一次枚举成表，之后 O(1)。
2. **模块级副作用**：`card_deck.py` 底部 import 期执行 `Cards_Probability(cards1).get_probability()` 并 print；同文件有大段注释掉的 1000000 次实验代码。
3. **隐式依赖**：`mymath/robot.py`/`robot2.py` 用 `np.random.choice` 但无 `import numpy as np`，靠 `from .probability_func import *` 星号导入泄漏；被 ruff 清理即崩。
4. **重复实现**：Robot 与 Robot2 约 130 行近乎逐行相同，差异仅 `cal_value` 系数与 `cal_final_option` 弃牌保护 → 应参数化。
5. **UI 与逻辑耦合**：`Draw_Pic` 自维护 `rest_option/turn/option/all_bet/bets/player_money` 并自行复算押注，与 `Game_room` 形成两个事实来源（D2 的温床）；`draw.py::__main__` 复制整份训练循环。
6. **坏路径与类定义期副作用**：`const.py` 硬编码 `'../game_exercise/src/...'` 与 `'../myclient/src/BGM/...'`（后者指向仓库外，必然失效）；`Mouce`/`button_spirit` 类体定义期调 `pygame.Rect(...)`，导致 `import const` 必须已 `pygame.init` —— 这是 core 无法脱离 pygame 的根因。
7. **误依赖**：多个 `draw*.py` 顶部 `from sympy import false`，全文件未使用，白拖 sympy 进依赖树。
8. **废弃 API**：`probability_func.py` 的 `np.trapz` 在 numpy 2.x 废弃，应改 `np.trapezoid`。
9. **死代码**：`func_const.py::conv_func.arr_100` 从未被读取。
10. **工程卫生（部分未核实）**：`__pycache__`、`*.pth`、`remember.txt`、统计 png 是否被 git 跟踪，是否存在 `requirements.txt`/`.gitignore`/`备份/`，根目录副本确切数量 —— 需 Phase 0 用 bash 核定。

## 5. 用户
仓库所有者本人，学习/实验用途。核心诉求：换机器一键装好跑通；能读懂架构；改规则时不怕碰坏别的脚本；**游戏界面不能卡死、不能靠 sleep 撑节奏**。

## 6. 目标
- **单一事实来源**：规则、牌型判定、DQN 网络各只有一份。
- **确定性**：同种子训练逐位可复现；胜率是精确值不是抽样值。
- **可测试**：核心规则全覆盖单测；每个真 bug 修复都有先红后绿回归。
- **可分层**：core/ 与 agents/ 不依赖 pygame，无头可跑。
- **零阻塞**：UI 事件驱动，任何分支不阻塞；节奏控制可注入；headless 可零等待跑完整局。

## 7. 非目标
见契约 outOfScope。特别说明：不动 `conv_func` 概率密度公式（属策略调参，非架构问题）；不引入 asyncio（避免在 pygame 上叠加第二套调度模型）；不删除旧偏置发牌能力（仅默认关闭）。

## 8. 关键风险与待决问题
- **R1（已决策 → D-R1）**：D6 修复为默认均匀发牌 + 保留可选偏置开关。风险余项：旧 `.pth` 在新默认分布下失效（已接受，只归档不删除）。
- **R2（已决策 → D-R2）**：D1 语义定为「比输者输，winner = 1 - whose_turn」。风险余项：修复会改变现有对局结果，旧训练数据语义改变（已接受）。
- **R3**：D5 已撤销，Phase 0 须实测再确认一次接线；若推翻则立即挂起请示。
- **R4**：环境未知（python/torch/pygame 版本）。Phase 0 建 venv 记录基线。
- **R5**：中文文件名重命名牵连大量资产引用，已移出本轮。
- **R6**：UI 时序重构涉及 `draw_*` 多份副本的收敛，Phase 5 工作量最大，需与 P4 串行以避免同工作区写冲突。

## 9. 验收
见契约 successCriteria，逐条可机器验证（grep 断言、pytest、headless 耗时与 QUIT 响应测试、发牌均匀性检验）。

## 10. 决策记录
| 编号 | 内容 | 状态 |
|---|---|---|
| D-R1 | D6 发牌：默认均匀 + 保留 `draw_strength_biased()` 可选开关（默认关） | 已确认（r4） |
| D-R2 | D1 看牌结算：比输者输，`winner = 1 - whose_turn` | 已确认（r4） |
| D-R3 | D5 信息泄漏说法证伪，仅修标签与具名属性 | 已确认（r3） |
| D-R4 | D3 降级为 API 契约（IllegalAction），不作 bug 修复 | 已确认（r3） |
