# 调查报告 C2：测试体系与质量守护

## 调查目标
只读调查 game_rendering 的 tests/（含 baseline/）、pyproject.toml、.github/workflows/ci.yml、README.md 一致性，及 src/ 资源规模，产出带 file:line 证据的结构化报告。

## 涉及文件（含行数）
| 文件 | 行数 |
|---|---|
| tests/test_rules.py | 154 |
| tests/test_dealing.py | 101 |
| tests/test_ui.py | 303 |
| tests/test_strength.py | 80 |
| tests/test_evaluator.py | 112 |
| tests/test_agents.py | 219 |
| tests/test_scripts.py | 124 |
| tests/test_purity.py | 63 |
| tests/baseline/common.py | ~60 |
| tests/baseline/repro_d1_showcards.py | 40 |
| tests/baseline/repro_d2_rest_option.py | ~63 |
| tests/baseline/repro_d4_lagging_done.py | 44 |
| tests/baseline/repro_d5_wiring.py | 47 |
| tests/baseline/repro_d6_dealing.py | 58 |
| tests/baseline/repro_d7_timing.py | 110 |
| pyproject.toml | 49 |
| .github/workflows/ci.yml | 95（唯一 workflow） |
| README.md | 116 |
| const.py（仅核路径引用） | 82 |
| ui/theme.py（仅核路径引用） | ~176 |

无 conftest.py（find 全仓无结果）。

## 被测试锁定的行为清单（测试文件 → 守护约束 → file:line）

**tests/test_rules.py（D1/D2/D4 + 回合/命名）**
- D1 看牌结算方向：4 参数化用例（whose_turn×强弱手）必须「比输者输」，`test_rules.py:28-40`（assert 39-40）
- 看牌收费=当前最低注：`:42-48`；加注后按加注档收费（BET_100→BET_OPTIONS[3]）：`:50-58`
- 平局判非行动方胜：`:60-64`
- D2 rest_option 单调：BET_100 后 rest_option==3，降档 BET_10 抛 IllegalAction 且 rest_option 不回退：`:68-78`
- 合法动作集=高挡位∪弃牌∪看牌，低档被剔除：`:80-85`
- 押注更新底池/个人注/金币（开局各押 5：all_bet=10+20）：`:87-92`
- D4 结束后拒绝行动：finish 后 apply 抛 IllegalAction、legal_actions()==()：`:96-103`
- FOLD 判对方胜、底池全归对方、金币守恒 40000：`:105-121`
- 回合交替：`:125-131`；own_hand/opponent_hand 具名访问器（D5）：`:133-139`；snapshot 只读视图字段相等：`:141-146`；接受 legacy dict 手牌：`:148-154`

**tests/test_dealing.py（D6 发牌）**
- 均匀发牌 3 张不重复：`:43-47`；牌堆不足抛 EmptyDeckError：`:50-52`
- 400 手均匀样本强度分位均值 ∈(0.44,0.56)（基线 0.489）：`:56-59`
- 最强档（>0.95）占比 <0.08（理论 5%，基线实测 0.013）：`:62-66`
- 偏置路径（三抽一）均值须比均匀高 >0.15（基线 0.766 vs 0.489）：`:69-74`
- 偏置路径每发 1 手丢弃 9 张不回堆：`:78-83`
- 默认均匀路径不触发 22100 手建表（lru_cache 命中为 0）：`:86-95`
- 全牌堆 52 张唯一：`:98-101`

**tests/test_ui.py（时序/一致性/贴图/性能/入口）**
- Ticker IMMEDIATE 不等待（<50ms）：`:40-45`；FIXED 虚拟时钟推进 ≥dt：`:47-53`；deadline/due：`:55-61`
- 零 sleep 守护（仅扫 ui/）：`:63-65`
- D7-b QUIT 在等待期间被响应：post QUIT 后 step_frame → running is False：`:69-77`（assert 77）
- QUIT 在 AI 思考（think_seconds=5.0, TickPolicy.REAL）期间被响应：`:80-91`（assert 91）
- 无人输入帧持续推进（10 帧→frames==10）：`:94-100`
- 零等待 400 帧内整局跑完：`:102-108`
- 按 R 重开新局：`:110-119`
- UI 不记账：view() 与 room.snapshot() 五字段逐字段相等（money/bets/all_bet/finish/winner）：`:124-134`
- min_bet 来自 core（BET_100 后 view["min_bet"]==100）：`:137-140`；合法动作仅在人类回合非空：`:142-148`
- 性能：core 单步 <5ms（基线 1530.8ms）：`:152-165`（assert 165）；UI 路由+控制单帧 <50ms：`:167-173`（assert 173）
- 入口薄化：draw_me_vs_DQN_Plus.py 无星号导入/sleep/load_state_dict，import 期无 pygame.init()：`:177-183`
- const 可无 pygame 导入、路径绝对且不含 myclient：`:185-189`
- dummy 驱动下 Renderer 可绘制：`:191-202`；asset_paths 必含 5 键：`:204-208`
- 原始贴图：6 个动作按钮贴图存在且 2:1 比例：`:214-230`；头像 human/ai 存在、AVATAR_LIBRARY 四元神：`:232-241`；variant 生效（cat_spirit→喵喵.png）：`:243-249`；金币贴图尺寸=layout.coin_size：`:251-258`
- 贴图缺失回退文本绘制不崩溃（monkeypatch 指向不存在目录）：`:260-280`
- 布局不重叠（手牌≤按钮 y、信息栏不侵入、暗牌不压底池、按钮不出界）：`:282-293`；窗口 4:3：`:295-298`；missing_assets()==[]：`:300-303`

**tests/test_strength.py（精确强度表）**
- 表规模恰 22100（C(52,3)）：`:19-20`
- 确定性：同一手 50 次调用值唯一：`:23-27`
- 边界：概率∈[0,1)、最强手(三条A)胜率 >0.9998 且 <1.0：`:30-35`
- 单调：弱<中<强：`:38-42`；牌型键大者胜率不更小（200 次抽样成对校验）：`:45-53`
- strength_bin ∈{1..6}（500 抽样）：`:56-61`
- 单次查询 <100µs（基线蒙特卡洛 30.8ms）：`:64-72`（assert 72）
- 建表一次性（lru_cache，二次查询 <10ms）：`:75-80`

**tests/test_evaluator.py（牌型判定）**
- 六类牌型判定：`:18-35`
- 边界：A-K-Q 是顺子、A-2-3 不是（HIGH_CARD）、同点三张=TRIPS：`:38-47`；非 3 张抛 ValueError：`:50-53`；rank 越界(15/1)抛 ValueError：`:54-58`
- 排序：单张<对子<顺子<金花<顺金<三张（两两 compare ±1）：`:62-74`；对子点>踢脚、同对踢脚决胜、顺子比最大、金花比最大：`:76-95`
- 花色决胜：同点黑桃胜；完全相同=0；反对称：`:98-112`

**tests/test_agents.py（D8/D9/契约）**
- D8 维度自适应：KEEPER_CKPT=dqn_model_1.pth 实际维度 (4,6)：`:27-30`；from_checkpoint 构建 agent.input_dim==4、action_dim==6、model.fc1.in_features==4：`:32-37`；硬编码 DQN(9,6) 加载 4 维权重必须 RuntimeError：`:39-46`；缺文件 FileNotFoundError：`:48-50`
- D9 真正加载权重：加载后 epsilon==0.0（贪心）：`:54-56`；同状态 20 次 act 输出唯一：`:58-63`；与 epsilon=1.0 随机策略动作分布 L1 距离 >0.5：`:65-84`（assert 84）
- 契约：act 只返回合法动作（30 次×3 组）：`:88-93`；空合法集抛 ValueError：`:95-98`；同种子同序列：`:100-105`；save/load 往返动作一致：`:108-114`；replay 返回非负 loss 且 epsilon 按 decay 降至 0.5：`:116-125`
- Robot：act 合法、强牌 win_rate>弱牌、预设差异、robot.py 无星号导入（显式 import numpy）、强牌加注占比>弱牌（400 次统计）：`:141-180`
- 分层：agents/ 无 pygame（正则扫描）：`:184-191`；load_state_dict 不得在模块顶层：`:193-199`；import agents 子进程拦截 open/torch.load 证明不触盘：`:201-219`

**tests/test_scripts.py（训练/评估入口）**
- env 观测 4 维：`:18-21`；合法动作非空：`:23-26`
- D4 环境层防护：done 后再 step 抛 IllegalAction：`:28-43`
- 奖励仅终局非零：`:45-58`
- train 冒烟：episodes/win_rate/checkpoint 存在/summary_seed11.json：`:62-67`
- 可复现性：同种子(2026)两次 train，`weights_hash` 与 `avg_reward` 严格相等：`:69-74`；异种子 hash 不等：`:76-79`；5 回合 <60s：`:81-84`
- evaluate 冒烟（默认 ckpt=dqn_model_1.pth）：`:88-93`；D9 旁证：动作分布最大占比 >0.4：`:95-100`
- 分层：scripts/ 无 pygame：`:104-110`；torch.load 不得在模块顶层：`:112-116`；Transition 4 维：`:118-124`

**tests/test_purity.py（分层纯度）**
- core/ 有源文件：`:15-16`；core/ 不 import pygame（正则）：`:19-25`；摘除 pygame 后 core 六模块仍可导入：`:28-52`；core/ 不依赖 numpy/scipy/torch/matplotlib/pygame：`:55-63`

## 关键代码位置（file:line + 该处代码在做什么）
- `tests/test_purity.py:8` — `PYGAME_IMPORT = re.compile(r"^\s*(?:import\s+pygame|from\s+pygame[\s.])", re.MULTILINE)`：pygame 导入正则（行首、允许可变缩进）
- `tests/test_purity.py:11-12` — `_core_sources()`：`CORE_DIR.rglob("*.py")` 递归扫描 core/ 全部 .py（排除 __pycache__）
- `tests/test_purity.py:21-24` — 逐文件 `read_text` + `PYGAME_IMPORT.search`，违规收集 offenders；`:25` 断言 offenders 为空
- `tests/test_purity.py:43-49` — meta_path 注入 `_Blocker`（find_module 对 pygame* 抛 ImportError）+ 从 sys.modules 删除 pygame（:33-35），再 `importlib.import_module` core/core.cards/core.evaluator/core.strength/core.dealing/core.rules
- `tests/test_purity.py:60-63` — 对每个 core 文件对 (numpy,scipy,torch,matplotlib,pygame) 逐一 `re.search(rf"^\s*(?:import\s+{name}|from\s+{name}[\s.])")`，`:63` 断言 heavy 为空
- `tests/baseline/common.py:11-13` — 注入 REPO_ROOT 到 sys.path；`:35-37` check() 打印 PASS/FAIL；`:40-46` summary() 打印 `BASELINE_RESULT {code}: passed=N failed=M`
- `tests/baseline/common.py:4-5` — 自述：现断言「修复后的正确行为（绿）」，红证据在 docs/BASELINE-REPORT.md 与提交 97a2737
- `tests/baseline/repro_d1_showcards.py:21-34` — 4 用例循环，check 在 :34，summary :36
- `tests/baseline/repro_d2_rest_option.py:20-34` — rest_option 单调；`:37-46` D2b const 路径无 myclient/`..` 前缀且解析进仓库；`:48-57` D2c AST 解析 const.py 导入集合不含 pygame
- `tests/baseline/repro_d4_lagging_done.py:18-39` — FOLD 后 finish/合法动作为空/再行动抛异常/金币守恒 40000
- `tests/baseline/repro_d5_wiring.py:22-41` — own_hand/opponent_hand 四向校验 + StateEncoder 编码 state[3]==beats_probability(本人手牌)（无信息泄漏）
- `tests/baseline/repro_d6_dealing.py:28-53` — 均匀/偏置 300 手分位均值对比；`:47-53