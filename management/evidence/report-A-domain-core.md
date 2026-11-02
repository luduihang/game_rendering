调查完成，证据齐备。以下为领域层（范围 A）只读调查报告。

## 调查目标

只读调查 game_rendering 仓库领域层：`core/` 全部 6 文件 + `algorithm.py` + `const.py`，回答任务书 10 个问题，产出带 file:line 证据的结构化报告，供 Main Agent 汇总进 docs/ARCHITECTURE.md。

Git 状态说明：本次 Run 未做任何写操作（只读角色，无写工具）。无 bash 工具，无法运行 `git status` 实时核验工作区，活体 git 状态标 UNKNOWN（见 UNKNOWN 清单）。

## 涉及文件（含行数）

| 文件 | 行数 | 层 |
|---|---|---|
| `core/__init__.py` | 31 | core 包公开 API 重导出 |
| `core/cards.py` | 74 | 牌与牌堆数据模型 |
| `core/evaluator.py` | 89 | 牌型判定与比大小 |
| `core/strength.py` | 58 | 穷举精确强度表 |
| `core/dealing.py` | 68 | 发牌 |
| `core/rules.py` | 176 | 对局状态机与结算 |
| `algorithm.py` | 120 | 根目录 UI 辅助（字体绘制 + RepeatedTimer + 规则文案） |
| `const.py` | 82 | 资源路径/颜色/布局常量 |

## 关键代码位置（file:line + 该处代码在做什么）

**Q1 模块职责与公开符号**

- `core/cards.py`：`Suit`（cards.py:13，IntEnum：SPADE=0/HEART=1/DIAMOND=2/CLUB=3，cards.py:14-17；`cn` 属性 cards.py:19-21）、`SUIT_CN`（cards.py:24-29）、`SUIT_FROM_CN`（cards.py:31）、`MIN_RANK=2`/`MAX_RANK=14`（cards.py:33-34）、`Card`（cards.py:37-38，frozen dataclass，字段 `suit: Suit` cards.py:39、`rank: int` cards.py:40）、`Card.name`（cards.py:48-50）、`Card.from_legacy`（cards.py:55-58）、`Card.to_legacy`（cards.py:60-61）、`full_deck()`（cards.py:64-66）、`hand_from_legacy`（cards.py:69-70）、`hand_to_legacy`（cards.py:73-74）。
- `core/evaluator.py`：`HandType`（evaluator.py:18-24）、`HAND_TYPE_NAMES`（evaluator.py:27）、`HandRank`（evaluator.py:30-34）、`HandRank.type_name`（evaluator.py:36-38）、`HandRank.key()`（evaluator.py:40-42）、`HandRank.__str__`（evaluator.py:44-45）、`_is_consecutive`（私有，evaluator.py:48-50）、`evaluate()`（evaluator.py:53-83）、`compare()`（evaluator.py:86-89）。
- `core/strength.py`：`BIN_THRESHOLDS`（strength.py:21）、`_ranked_keys()`（私有，strength.py:24-27）、`table_size()`（strength.py:30-31）、`beats_probability()`（strength.py:34-37）、`strength_ordinal()`（strength.py:40-45）、`strength_bin()`（strength.py:48-54）、`strongest_hand()`（strength.py:57-58）。
- `core/dealing.py`：`DEFAULT_CANDIDATES=3`（dealing.py:20）、`EmptyDeckError`（dealing.py:23-24）、`new_deck()`（dealing.py:27-31）、`deal_uniform()`（dealing.py:34-38）、`deal_strength_biased()`（dealing.py:41-61）、`verify_uniformity()`（dealing.py:64-68）。
- `core/rules.py`：`BET_OPTIONS=(10,20,50,100)`（rules.py:26）、`DEFAULT_ANTE=5`（rules.py:27）、`DEFAULT_MONEY=20000`（rules.py:28）、`Action`（rules.py:31-39，`is_bet` rules.py:40-41）、`IllegalAction`（rules.py:44-45）、`Player`（rules.py:48-53）、`GameRoom`（rules.py:56-175）及方法 `new`（rules.py:69-86）、`hand`（rules.py:89-90）、`own_hand`（rules.py:92-94）、`opponent_hand`（rules.py:96-97）、`legal_actions`（rules.py:99-102）、`rank_of`（rules.py:104-105）、`snapshot`（rules.py:107-121）、`apply`（rules.py:123-142）、`_bet`（rules.py:144-154）、`_fold`（rules.py:156-158）、`_compare`（rules.py:160-170）、`_finish`（rules.py:172-175）。
- `core/__init__.py`：重导出 cards/evaluator/rules/strength 的符号（__init__.py:11-14），`__all__` 白名单（__init__.py:16-30）。注意 `strength_ordinal`、`strongest_hand`、dealing 全部符号**不在** `__all__` 中（__init__.py:16-30）。
- `algorithm.py`：`RepeatedTimer`（algorithm.py:20-86）、`show_font()`（algorithm.py:89-97）、`RULES_LINES`（algorithm.py:100-111）、`show_help_font()`（algorithm.py:114-120）。
- `const.py`：`ROOT`/`SRC`（const.py:15-16）、资源目录（const.py:19-24）、`background_directory` 别名（const.py:27）、`Background`/`Card_Back`（const.py:30-31）、`FONT_MAIN`/`FONT_UI`（const.py:33-34）、窗口尺寸（const.py:38-41）、`CARD_SIZE`/`CARD_SIZE_SMALL`（const.py:43-44）、`card_type_arr`（const.py:47）、`select_option`（const.py:48）、`Color`（const.py:51-63）、`BG_MUSIC`（const.py:67-78）、`asset_exists()`（const.py:81-82）。

**Q2 数据模型与不变式**

- `Card`：frozen dataclass（cards.py:37-40）。不变式：`rank` 必须是 int，否则 TypeError（cards.py:43-44）；`2 <= rank <= 14`，否则 ValueError（cards.py:45-46，边界 MIN_RANK/MAX_RANK cards.py:33-34）。`suit` 被 IntEnum 域限定（cards.py:13-17）。A 为最大牌=14（cards.py:4 文档 + cards.py:34）。
- `Suit` 强度序：黑桃>红心>方块>梅花（cards.py:3 文档），数值越小越强；比较时取 `-int(suit)`（evaluator.py:42）。
- `HandRank`：frozen（evaluator.py:30），字段 `hand_type`（evaluator.py:32）、`values` 长度恒为 3 且降序（evaluator.py:33、evaluator.py:62-63）、`suit`（evaluator.py:34）。决胜花色=最大牌的花色，三张同点取最强花色（evaluator.py:67-68）。
- 手牌级不变式：必须恰好 3 张且元素为 Card（evaluator.py:55-60：非 3 张 ValueError、非 Card TypeError）；对局级：2 名玩家、每人 3 张（rules.py:80-81 ValueError）。
- `full_deck()` 生成 52 张不重复牌（cards.py:64-66）。
- `Player`：name/money/bet/folded（rules.py:50-53），可变 dataclass（rules.py:48 非 frozen）。

**Q3 牌型判定六类、判定顺序、比大小与平局**

- 六类定义：`HandType` HIGH_CARD=0 / PAIR=1 / STRAIGHT=2 / FLUSH=3 / STRAIGHT_FLUSH=4 / TRIPS=5（evaluator.py:18-24），中文名映射 evaluator.py:27。
- 判定全部在 `evaluate()` 内，顺序为（evaluator.py:70-83）：三张 TRIPS（70-71）→ 顺金 STRAIGHT_FLUSH（72-73）→ 金花 FLUSH（74-75）→ 顺子 STRAIGHT（76-77）→ 对子 PAIR（78-82，pair_rank/kicker 计算 80-81，values 置为 `(pair_rank, pair_rank, kicker)` 82）→ 兜底单张 HIGH_CARD（83）。分支互斥（按 distinct==1/2/3），唯二的硬顺序约束是顺金先于金花、金花先于顺子。
- 比大小：`compare()`（evaluator.py:86-89）比较 `key()` 元组 `(int(hand_type), values, -int(suit))`（evaluator.py:40-42），返回 1/0/-1。花色仅作最终决胜。
- 平局处理：在 `rules._compare` 中，`outcome = compare(...)`（rules.py:168），`winner = actor if outcome > 0 else 1 - actor`（rules.py:170）——**完全相等（0）时看牌方输**，rules.py:169 注释明确此约定。

**Q4 strength.py 精确表（重点）**

- 表 = `_ranked_keys()`：`@lru_cache(maxsize=1)` 装饰（strength.py:24），函数体 `tuple(sorted(evaluate(hand).key() for hand in combinations(full_deck(), 3)))`（strength.py:27）——对 C(52,3)=22100 手（52×51×50/6=22100，算术验证）求比较键并升序排序。
- **生成时机：惰性（lazy），首次查询期生成，不是 import 期。** 模块级（strength.py:11-21）只有 import 与 `BIN_THRESHOLDS` 常量（strength.py:21），没有任何模块级代码调用 `combinations`/`evaluate`/`_ranked_keys`。首次调用 `table_size`（strength.py:31）/ `beats_probability`（strength.py:36）/ `strength_ordinal`（strength.py:45）/ `strength_bin`（经 strength.py:50）之一时才触发全量枚举与排序；之后命中 lru_cache。注释自述"首次调用约数十毫秒，之后命中缓存"（strength.py:26）。
- **查询方式：二分查找。** `beats_probability = bisect_left(keys, evaluate(hand).key()) / len(keys)`（strength.py:36-37，取值 [0,1)）；`strength_ordinal` 同样 `bisect_left`（strength.py:45）。`strength_bin` 按 `BIN_THRESHOLDS=(0.4,0.7,0.9,0.96,0.99)`（strength.py:21）把胜率映射为 1..6 档（strength.py:50-54）。`strongest_hand()` 不走缓存，直接 `max(combinations(...))`（strength.py:58）。
- 表只存在于进程内存，无任何磁盘持久化（全文无文件 IO 证据）。

**Q5 dealing.py 发牌**

- **默认路径是均匀发牌**：`new_deck()` 洗牌（dealing.py:27-31，`(rng or random).shuffle` dealing.py:30，可注入 rng），`deal_uniform(deck, n=3)` 从牌堆 `pop` n 张（dealing.py:34-38）。模块 docstring 明确"默认 `deal_uniform`…`deal_strength_biased` 默认不启用，仅供复现历史实验（契约 D-R1）"（dealing.py:3-5）。
- **任务书所问的 `draw_strength_biased()` 开关：代码中不存在该名。** 全仓 `.py` grep `draw_strength_biased` 零匹配（仅 legacy 管理文档 r4 plan 中用此名）。实际函数名是 **`deal_strength_biased`**（dealing.py:41-61）。
- `deal_strength_biased` 行为：抽 `candidates`（默认 `DEFAULT_CANDIDATES=3`，dealing.py:20）组各 n 张候选（dealing.py:55-56），逐组用 `beats_probability` 打分（dealing.py:57），保留最强一组（dealing.py:58-59），其余弃置不回堆（dealing.py:46 注释）；牌堆不足 `n*candidates` 抛 `EmptyDeckError`（dealing.py:50-52）；`assert best is not None`（dealing.py:60）。
- `verify_uniformity`（dealing.py:64-68）：样本平均强度分位，均匀发牌应趋近 0.5，供测试/验收。

**Q6 rules.py 状态机**

- 无显式 State 枚举；"状态"= `GameRoom` 字段集合：`hands`（rules.py:58）、`players`（rules.py:59）、`whose_turn: int = 0`（rules.py:60）、`rest_option: int = 0`（rules.py:61）、`circle: int = 1`（rules.py:62）、`all_bet: int = 10`（rules.py:63）、`finish: bool = False`（rules.py:64）、`winner: int | None = None`（rules.py:65）、`history`（rules.py:66），叠加每玩家 `money/bet/folded`（rules.py:50-53）。宏观两态：进行中（`finish=False`，rules.py:100/124 判断）与已结束（`finish=True`，rules.py:173 置位）；弃牌以 `folded` 标记（rules.py:157）。
- **权威状态由 `GameRoom` 单点持有**；UI 只能经 `snapshot()` 取只读快照，docstring 明示"UI 不得自行记账"（rules.py:107-121，尤其 rules.py:108）。
- 底注：`new()` 构造时从双方 money 扣除 ante（rules.py:82-85：`Player(names[0], money[0] - ante, ante)` rules.py:83-84），`all_bet=ante*2`（rules.py:86）；ante 默认 `DEFAULT_ANTE=5`（rules.py:27、75）。
- 押注规则：`_bet` rules.py:144-154——低于 `rest_option` 的降档押注抛 `IllegalAction`（rules.py:145-148）；金额=`BET_OPTIONS[action]`（rules.py:149）；记账 `bet+=`/`money-=`/`all_bet+=`（rules.py:151-153）；`rest_option = max(rest_option, action)` 单调不减（rules.py:154）。
- 弃牌：`_fold` rules.py:156-158（置 folded、对手赢）。
- 看牌/结算：`_compare` rules.py:160-170——费用=`BET_OPTIONS[rest_option]`（rules.py:162），仅看牌方付款（rules.py:164-166），`compare` 比大小（rules.py:168），平局看牌方输（rules.py:169-170）。
- 终局：`_finish` rules.py:172-175——`finish=True`（173）、`winner` 记录（174）、赢家拿走全部押注池 `money += all_bet`（175）。
- 行动入口：`apply()` rules.py:123-142——结束后任何行动抛 `IllegalAction`（rules.py:124-125）、未知动作（rules.py:126-129）、分发 bet/fold/compare（rules.py:132-137）、记 history（rules.py:138）、未结束时换手 `whose_turn = 1 - actor`（rules.py:140）、回到玩家 0 时 `circle += 1`（rules.py:141-142）。合法动作查询 `legal_actions()`（rules.py:99-102：结束后返回空，否则 rest_option 起的押注档 + FOLD + COMPARE）。

**Q7 evaluator.py 职责与对外接口**

- 职责：三张牌的牌型判定（`evaluate` evaluator.py:53-83）与两副手牌比较（`compare` evaluator.py:86-89）；生成可排序比较键（`key` evaluator.py:40-42）。
- 对外接口：`evaluate(hand) -> HandRank`（evaluator.py:53）、`compare(left, right) -> int` 返回 1/0/-1（evaluator.py:86-89）、类型 `HandType`/`HandRank`/`HAND_TYPE_NAMES`（evaluator.py:18/31/27）。`_is_consecutive` 为私有（evaluator.py:48）。入口参数校验：3 张 + Card 类型（evaluator.py:55-60）。

**Q8 algorithm.py RepeatedTimer**

- **仍然存在**：`class RepeatedTimer`（algorithm.py:20-86）。
- 调度语义：每次 `_run` 先（持锁）重置 `is_running`、检查 `_stopped`、**先排下一次** `threading.Timer` 再执行回调（algorithm.py:45-54）；下次延迟 = `max(0.0, next_call - time.time())`（algorithm.py:58），`next_call` 按 interval 累加（algorithm.py:57）即网格锚定、迟到钳零（catch-up 钳制）；`start()` 重置 `next_call = time.time()` 且运行中再 start 直接返回（algorithm.py:63-69）。
- **daemon：是**，`self._timer.daemon = True`（algorithm.py:59）。
- **stop() 幂等：是**（algorithm.py:71-78）——持锁置 `_stopped=True`/`is_running=False`、取走 `_timer` 并置 None（algorithm.py:72-76），仅当非 None 才 `cancel()`（algorithm.py:77-78）；重复 stop 无副作用；`_run` 中 `_stopped` 检查（algorithm.py:47-49）保证已排未触发的定时器不再续链。
- 附加加固：回调异常隔离存入 `last_error` 不外抛（algorithm.py:51-54）；`threading.Lock` 保护全部共享状态（algorithm.py:34、46、64、72）；上下文管理器 `__enter__/__exit__`（algorithm.py:80-86）。
- 生产调用方：无。全仓仅基线复现脚本 `tests/baseline/repro_d7_timing.py:76-91` 使用；模块 docstring 自述新版 UI 已改用 `ui.clock.Ticker` 帧驱动、本类保留供脚本/旧接口（algorithm.py:29-30）。

**Q9 const.py 常量**

- 路径根：`ROOT`（const.py:15）、`SRC=ROOT/"src"`（const.py:16）；资源目录 item_pic/card_pic/button/Font/character/BGM（const.py:19-24）；`background_directory` 历史别名（const.py:27）；`Background`/`Card_Back`（const.py:30-31）；`FONT_MAIN`/`FONT_UI`（const.py:33-34）；窗口 1000×750（const.py:38-41）；卡牌尺寸（const.py:43-44）；`card_type_arr`（const.py:47，与 evaluator.py:27 重复）；`select_option`（const.py:48）；`Color` 类 12 个 RGB 元组（const.py:51-63）；`BG_MUSIC` 10 个音频路径（const.py:67-78）；`asset_exists()`（const.py:81-82）。

**Q10 依赖禁令核查（逐文件 import 清单）**

| 文件 | import（行号） | pygame/numpy/scipy/torch |
|---|---|---|
| core/cards.py | `__future__`(7)、dataclasses(9)、enum(10) | 无 |
| core/evaluator.py | `__future__`(10)、dataclasses(12)、enum(13)、core.cards(15) | 无 |
| core/strength.py | `__future__`(11)、bisect(13)、functools(14)、itertools(15)、core.cards(17)、core.evaluator(18) | 无 |
| core/dealing.py | `__future__`(12)、random(14)、collections.abc(15)、core.cards(17)、core.strength(18) | 无 |
| core/rules.py | `__future__`(17)、dataclasses(19)、enum(20)、typing(21)、core.cards(23)、core.evaluator(24) | 无 |
| core/__init__.py | core.cards(11)、core.evaluator(12)、core.rules(13)、core.strength(14) | 无 |
| const.py | `__future__`(11)、pathlib(13) | 无（docstring 声明不依赖 pygame.init()，const.py:6-7，与代码一致） |
| algorithm.py | `__future__`(10)、threading(12)、time(13)、**pygame(15)**、const(17) | **pygame 存在**（行 15） |

结论：`core/` 全目录零 pygame/numpy/scipy/torch import，分层禁令满足；`algorithm.py` 属根目录 UI 辅助（非 core/），import pygame 符合其 UI 辅助定位，不构成分层违例，但注意任务书将其划入"领域层"调查范围是范围切分口径，该文件本身是 UI 耦合件。

## 调用关系（谁调用谁）

域内依赖（core/ 内部，全部为同层合法依赖）：
- `core/__init__.py` → cards(11)、evaluator(12)、rules(13)、strength(14)。
- `rules.py` → `cards.Card`（rules.py:23，`new` 中 `Card.from_legacy` rules.py:78）；→ `evaluator.compare/evaluate`（rules.py:24，`_compare` 调 compare rules.py:168，`rank_of` 调 evaluate rules.py:105）。
- `strength.py` → `cards.full_deck`（strength.py:17，用于 27、58）；→ `evaluator.evaluate`（strength.py:18，用于 27、37、45、58）。
- `dealing.py` → `cards.Card/full_deck`（dealing.py:17，new_deck dealing.py:29）；→ `strength.beats_probability`（dealing.py:18，dealing.py:57、68）。
- `evaluator.py` → `cards.Card/Suit`（evaluator.py:15）。
- `cards.py` → 仅标准库（无 core 内依赖，是域内依赖图的叶子）。
- 域内方法链：`GameRoom.apply`（rules.py:123）→ `_bet`/`_fold`/`_compare`（rules.py:132-137）→ `_finish`（rules.py:158/170/172）；`_compare` → `compare` → `evaluate`（evaluator.py:88 → 53）。

跨层调用方（域外，仅作调用链证据，未深入其内部）：
- `ui/app.py:18-21` → dealing(deal_uniform/new_deck)、evaluator(evaluate)、rules(BET_OPTIONS/Action/GameRoom/IllegalAction)、strength(beats_probability)。
- `ui/render.py:16`、`ui/theme.py:16` → const；`algorithm.py:17` → const。
- `agents/robot.py:18-19` → cards(Card)、strength(beats_probability)。
- `scripts/env.py:16-17` → dealing、rules；`scripts/evaluate.py:19` → rules.Action。
- 入口 `draw_me_vs_DQN_Plus.py:11` → `ui.app.main`（其函数体未在本次范围内核实）。
- 测试：`tests/test_evaluator.py:5-6`、`