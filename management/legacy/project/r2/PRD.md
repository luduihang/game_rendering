# PRD：game_exercise 架构优化

## 1. 背景
game_exercise 是一个 Python + pygame 的「炸金花」三张牌博弈游戏与 DQN 训练实验仓库。当前形态是根目录平铺脚本 + 互相复制粘贴的逻辑；mymath/ 为 AI 策略包，src/ 为美术与音频资产。

**证据获取限制（重要）**：本轮分析在项目基线为 DRAFT 状态下进行，bash/grep/目录枚举被治理层拦截，只能通过定向读取文件取证。因此下文所有结论均来自实际读到的源码；文件数量类统计标注为「未核实」，必须在 Phase 0 用 grep/ls 核实后才能用于排期。

## 2. 已核实缺陷（全部有源码证据）

### D1 规则 bug：看牌结算忽略 whose_turn（严重）
`game_room_deepseek_cp.py::Game_room.get_choice`，action==5 分支：
```
if self.cards1_value < self.cards2_value:
    self.winner = 0
```
判定只看牌面大小，完全不看 `self.whose_turn`。任何一方看牌时，「牌面大者获胜」与「看牌方获胜」被混为一谈，看牌方输局会反被判胜。这是本仓库最严重的逻辑错误。

### D2 rest_option 语义不一致（严重）
- `Game_room.get_choice`：`self.rest_option = action` —— 覆盖式赋值，允许下一轮降到更小档位（rest_option 变小 = 门槛变低）。
- `draw.py::Draw_Pic.update_inform`：`self.rest_option = min(self.rest_option, self.option)` —— 取最小值。
- `Robot.cal_value`：`threaten_rate = int(all_option[i]) / int(all_option[self.desk_dict["rest_option"]])` —— 假定 rest_option 是「当前最低可押档」。
三处语义互不兼容。且 `Draw_Pic.__init__` 里 `self.rest_option = 0` 是 int，而 `update_inform` 在 action==5 分支用 `int(all_option[self.rest_option])` 把它当索引，两种含义混用同一个字段。

### D3 get_choice 不校验动作合法性
action==5（看牌/比牌）分支不检查 `rest_option` 门槛，也不检查该玩家是否已弃牌；action==4（弃牌）后仍然执行 `self.whose_turn += 1` 与 `circle` 递增，已结束的局仍在推进轮次。

### D4 训练循环使用滞后标志
`game_room_deepseek_cp.py::main` 与 `draw.py::__main__` 均为：
```
if not done:
    opponent_action = opponent_robot.cal_final_option()
    room.get_choice(opponent_action['option'])
```
而 `done` 只在其后的 `if room.finish:` 里才被置为 True。因此当玩家 0 的动作已经结束对局时，对手仍会在已结束的房间上再行动一次，污染经验回放数据。

### D5 DQN 状态读取对手手牌（数据正确性）
`Game_room.__init__` 明确约定 `self.cards1` 是机器人手牌、`self.cards2` 是玩家手牌（`print("机器人的手牌是", self.cards1)` / `print("玩家的手牌是", self.cards2)`）。但 `DQNAgent.get_state(room, player_id)` 写的是：
```
card_value = Cards_Probability(game_room.cards1 if player_id == 0 else game_room.cards2).get_state()
```
即玩家 0 读到的是**对手**的手牌，构成信息泄漏，状态特征语义错误。

同时 `draw.py::__main__` 里 `cards.append(room.cards1); cards.append(room.cards2)`，而 `Draw_Pic.render_player_text_info` 把 `self.cards[0]` 渲染为「这是自己的手牌」——同样把机器人手牌当成了玩家手牌。两处引用的是同一个错位。

### D6 发牌非均匀（数据正确性）
`card_deck.py::Cards.draw_cards_plus`：抽 3 组候选各 3 张、用 `Cards_Probability` 计算每组胜率、只保留胜率最高的一组，其余 6 张直接丢弃（不回牌堆）。这使双方手牌都不是来自均匀 52 张的 `C(52,3)` 分布，而是「3 次抽样取最大」的有偏分布。PRD 原稿把「穷举胜率」当作纯性能优化，实际上发牌本身有偏，穷举胜率会与真实发牌分布对不上——这是必须先决策的语义问题。

## 3. 已核实的工程问题
1. **性能**：`Cards_Probability.get_probability/get_state` 每次调用做 2000 轮 `reset_deck + shuffle + Get_Value`。而 `draw_cards_plus` 每手牌调用 3 次、`Robot.init_dick` 每局每人再调用 1 次——单局可触发上万次牌型计算；`get_state` 与 `get_probability` 代码完全重复。C(52,3)=22100 可一次枚举成表，之后全部变 O(1) 查表。
2. **模块级副作用**：`card_deck.py` 底部在 import 时执行 `Cards_Probability(cards1).get_probability()` 并 print；同文件还有大段被注释掉的 1000000 次实验代码。
3. **隐式依赖**：`mymath/robot.py` 与 `robot2.py` 使用 `np.random.choice` 但没有 `import numpy as np`，靠 `from .probability_func import *` 的星号导入泄漏；这种写法一旦被 ruff 清理就会立刻崩。
4. **重复实现**：`mymath/robot.py::Robot` 与 `mymath/robot2.py::Robot2` 约 130 行几乎逐行相同，差异集中在 `cal_value` 的系数与 `cal_final_option` 的弃牌保护——应当参数化而非复制。
5. **UI 与逻辑耦合**：`draw.py::Draw_Pic` 内部维护 `rest_option/turn/option/all_bet/bets/player_money` 并自行复算押注（`self.player_money[self.turn] -= int(all_option[self.option])`），与 `Game_room` 成为两个事实来源；`draw.py::__main__` 里复制了一份完整训练循环。
6. **坏路径与类定义期副作用**：`const.py` 硬编码 `'../game_exercise/src/...'` 与 `'../myclient/src/BGM/...'`（后者指向仓库外的目录，必然失效）；`Mouce`/`button_spirit` 在类体定义期调用 `pygame.Rect(...)`，导致 `import const` 必须已 `pygame.init`——这是 `core/` 无法脱离 pygame 的根因。
7. **误依赖**：`draw.py` 顶部 `from sympy import false`，全文件未使用 `false`，却把 sympy 拖进依赖树。
8. **废弃 API**：`mymath/probability_func.py` 中 `np.trapz` 在 numpy 2.x 已废弃，应改 `np.trapezoid`。
9. **死代码**：`func_const.py::conv_func.arr_100` 从未被读取（`f100` 不索引它）。
10. **工程卫生（部分未核实）**：README 仅一行「你好」；已确认无 `mymath` 包导出约束；`__pycache__`、`*.pth`、`remember.txt`、统计 png 是否被 git 跟踪、是否存在 `requirements.txt`/`.gitignore`/`备份/` 目录、根目录究竟有多少个 draw_*/nodraw_* 副本 —— **均需 Phase 0 用 bash 核实**。

## 4. 用户
仓库所有者本人，学习/实验用途。核心诉求：换机器能一键装好跑通、能读懂架构、改规则时不怕碰坏别的脚本。

## 5. 目标
- **单一事实来源**：规则、牌型判定、DQN 网络各只有一份。
- **确定性**：同种子训练逐位可复现；胜率是精确值不是抽样值。
- **可测试**：核心规则全覆盖单测；每项 bug 修复都有先红后绿的回归测试。
- **可分层**：core/ 与 agents/ 不依赖 pygame，无头可跑。

## 6. 非目标
见契约 outOfScope。特别说明：本轮**不动** `conv_func` 的概率密度启发式公式（那是策略调参，不是架构问题），只做 `np.trapz` 替换与显式 import。

## 7. 关键风险与待决问题
- **R1（阻塞）**: D6 发牌非均匀要不要修？修 = 对局公平性改变 + 旧 `.pth` 失效；不修 = 穷举胜率表与实际发牌分布不匹配，`Cards_Probability` 只能保留为「相对强度」而非真实胜率。**这是 PRD 层必须先由人决策的分叉点。**
- **R2**: D5 修掉信息泄漏后，旧模型失效；默认只归档旧 `.pth`，不删除。
- **R3**: D1/D2 修复会改变现有对局结果；需人工确认「正确规则」的定义（尤其看牌后谁赢的语义）。
- **R4**: 环境未知（python/torch/pygame 版本）。Phase 0 先建 venv 记录基线。
- **R5**: 中文文件名重命名牵连大量资产引用，已移出本轮范围。

## 8. 验收
见契约 successCriteria，逐条可机器验证。
