## 调查目标

只读调查 game_rendering 训练侧（scripts/train.py、scripts/env.py、scripts/evaluate.py、agents/dqn.py、agents/base.py），回答 DQN-vs-DQN 自博弈可行性，产出带 file:line 证据的结论。Git 状态：本会话无 bash 工具无法跑 `git status`；依据 `.git/logs/HEAD:1-11`（最后一条为 merge 提交 7109e29，无后续改动记录）+ HANDOFF.md「未提交文件：无」判定工作区干净；本调查全程零写入。

## 涉及文件（含行数）

| 文件 | 行数 | 角色 |
|---|---|---|
| scripts/env.py | 158 | 对局环境封装（DQN vs Robot） |
| scripts/train.py | 123 | 无头训练入口 |
| scripts/evaluate.py | 107 | 无头评估入口 |
| agents/dqn.py | 223 | DQN 网络/智能体/状态编码 |
| agents/base.py | 57 | 智能体统一接口 |
| agents/robot.py | 256 | 内置对手（接口证据，非主责） |
| core/rules.py | ~175 | 规则状态机（对手/对称性证据） |
| tests/test_scripts.py | ~123 | 训练侧测试（成本/冒烟证据） |
| .github/workflows/ci.yml | ~97 | CI 冒烟（成本证据） |

## 关键代码位置（file:line + 该处做什么）

**scripts/env.py**
- env.py:31-41 `CardGameEnv` 定义与 `__init__(seed, opponent: Robot|None, agent_player=0)`；env.py:38 对手缺省 `Robot("1", seed=seed)`（内置，可注入）；env.py:39 持有 `StateEncoder`。
- env.py:44-55 `reset()`：env.py:45-46 `new_deck`+两次 `deal_uniform` 发牌；env.py:47 `GameRoom.new(hands)`（座位 0/1 顺序固定）；env.py:51-52 `opponent.reset()` + `opponent.init_dick(["1","0"], hands[opponent_seat])`（只给对手自己的手牌）；env.py:54 若对手先手则代打至 agent 回合。
- env.py:64-94 `step()`：agent 落子（env.py:69-70 `room.apply`，env.py:71-72 结束后再行动抛 `IllegalAction`）；env.py:76-77 奖励 0、done=`room.finish`；env.py:80-84 未结束则 `_advance_opponent_until_agent_turn()` 代打对手一步再查 done；env.py:85-86 超 `MAX_STEPS` 强制 done；env.py:88-94 返回 `StepResult(observation, reward, done, legal_actions, info)`（info 含 winner/steps/pot）。
- env.py:97-100 `_observation()`：`StateEncoder.encode(snapshot, self.agent_player, room.own_hand(self.agent_player))` —— 仅自己视角、仅自己的手牌。
- env.py:102-106 `_settle_reward()`：赢 `+room.all_bet`（env.py:105），输 `-玩家已押注`（env.py:106）。
- env.py:108-118 `_advance_opponent_until_agent_turn()`：env.py:113 取 `_opponent_snapshot()`，env.py:114 `opponent.act(snapshot, legal)`，env.py:116 应用，env.py:118 `_notify_opponent`。
- env.py:120-124 `_opponent_snapshot()`：`room.snapshot()` 后注入 `snapshot["hand"] = room.own_hand(1-agent)` —— Robot 专用 dict 通道。
- env.py:126-145 `_notify_opponent()`：拼 legacy json（含双方 bet、whose_turn、option、battle_win），env.py:143 `opponent.update_dick(payload)`，env.py:144-145 异常静默吞掉。
- env.py:19 `MAX_STEPS = 200`；env.py:148-155 `to_transition()` 把 StepResult 转成 Transition。

**scripts/train.py**
- train.py:27 `DEFAULT_OUT = REPO/"run"`；train.py:38-46 `train(episodes=20, seed=20261021, device="cpu", out_dir, config, min_episodes_before_save=1, verbose)`。
- train.py:52 `agent = DQNAgent(input_dim=4, action_dim=6, config, seed)`；train.py:53 `env = CardGameEnv(seed=seed)`（对手=Robot 缺省）。
- train.py:59-75 训练循环：每步 `legal_actions()`（train.py:65）→ `agent.act`（train.py:68）→ `env.step`（train.py:69）→ `agent.observe(to_transition(...))`（train.py:70）→ `agent.replay()`（train.py:71，每步一次）。
- train.py:78-79 胜率=`total_reward>0` 计数；train.py:85-96 summary（含 `weights_hash`、`elapsed_sec`、epsilon_final）；train.py:99-102 checkpoint 保存：train.py:100 文件名 `f"dqn_ep{episodes}_seed{seed}.pth"`，train.py:101 `agent.save(ckpt)`；train.py:104 `summary_seed{seed}.json`。
- train.py:112-119 `main()`：`--episodes`(114)、`--seed`(115)、`--device`(116)、`--out`(117)。**无「单局回合数」参数**（由 env.py:19 的 200 步上限兜底）。

**scripts/evaluate.py**
- evaluate.py:23 `DEFAULT_CKPT = REPO/"dqn_model_1.pth"`（该文件不在工作区，见「发现的问题」）；evaluate.py:35-36 `DQNAgent.from_checkpoint` + `CardGameEnv(seed=seed)`（单 agent vs Robot）；evaluate.py:52-57 逐动作计数/回合循环；evaluate.py:62-68 动作分布统计；evaluate.py:94-100 CLI（`--rounds/--seed/--checkpoint/--out/--epsilon`）。

**agents/dqn.py**
- dqn.py:29-32 状态/动作维度常量：`DEFAULT_STATE_DIM=4`（3 盘面+1 手牌强度）、`DEFAULT_ACTION_DIM=6`。
- dqn.py:36-46 `DQNConfig`：hidden=(128,64)、lr=1e-3、gamma=0.95、batch=32、buffer=5000、epsilon 1.0→0.01（decay 0.995/步）、target_sync_every=1。
- dqn.py:49-59 `DQN` 网络：fc1(input→128)→fc2(128→64)→fc3(64→output)，ReLU。
- dqn.py:62-67 `checkpoint_dims()`：从 `fc1.weight/fc3.weight` 形状推断 (input_dim, output_dim)。
- dqn.py:70-93 `StateEncoder.encode(snapshot, player, hand)`：`[circle/10, bets[player]/1000, bets[1-player]/1000, beats_probability(hand)]`（dqn.py:85-92）——**相对 player 座位**的 4 维；encoder 无状态（dqn.py:78-79）。
- dqn.py:96-120 `DQNAgent.__init__(input_dim=4, action_dim=6, config, seed, epsilon)`：双网络（model/target，dqn.py:114-115）、Adam（dqn.py:116）、deque buffer（dqn.py:117）、epsilon 初始化（dqn.py:118）、target 同步（dqn.py:120）。
- dqn.py:124-145 `from_checkpoint(path, config, seed, epsilon=0.0, device)`：维度自适应（dqn.py:136）+ 缺文件抛 `FileNotFoundError`（dqn.py:134）+ eval 模式（dqn.py:143）。
- dqn.py:148-162 推理：`q_values`（dqn.py:148-151）；`act(observation, legal_actions)`：epsilon 随机合法动作（dqn.py:157）或 legal-mask argmax（dqn.py:160-162）。
- dqn.py:165-195 学习：`observe`（dqn.py:165-166）、`replay`（dqn.py:168-195：batch 采样 dqn.py:171、目标 Q dqn.py:182-183、MSE dqn.py:184、epsilon 衰减 dqn.py:191-192、target 同步 dqn.py:193-194）。
- dqn.py:197-198 `update_target`；dqn.py:200-201 `reset()` 空操作；dqn.py:204-207 `save(path)`（torch.save state_dict，自动建目录）；dqn.py:209-212 `load(path)`（load_state_dict + 同步 target）；dqn.py:215-223 `weights_hash`。

**agents/base.py**
- base.py:20-25 `Transition(state, action, reward, next_state, done)`；base.py:28-57 `BaseAgent`：`act(observation, legal_actions)` 抽象（base.py:34-35），`observe/reset/save/load` 默认实现（base.py:37-48），`_pick_legal` 兜底（base.py:50-57）。

**core/rules.py（对称性/公平性证据）**
- rules.py:57-66 `GameRoom`：rules.py:60 `whose_turn: int = 0` 缺省；rules.py:70-87 `GameRoom.new()` **无 first_player 参数** → 玩家 0 恒先手。
- rules.py:92-97 `own_hand/opponent_hand` 具名访问器；rules.py:99-102 `legal_actions()`：`range(rest_option,4)+FOLD+COMPARE`，座位无关。
- rules.py:107-120 `snapshot()`：仅 whose_turn/rest_option/circle/all_bet/bets/money/folded/finish/winner/legal_actions，**不含任何手牌**。
- rules.py:123-142 `apply()`：行动后换边（rules.py:140），轮到 0 时 circle+1（rules.py:141-142）。
- rules.py:156-170 `_fold/_compare`：rules.py:168-170 比牌，平局看牌方输（rules.py:169 注释+170 `winner = actor if outcome>0 else 1-actor`）；rules.py:172-175 `_finish` 赢家吃池。

## 当前训练流程（对手选择 / 状态编码 / 奖励 / 回合结束 / checkpoint）

1. **对手选择**：`train.py:53` 建 `CardGameEnv(seed=seed)` → env.py:38 缺省对手为内置 `Robot("1")`（启发式概率采样，非随机：cal_value 带噪声 robot.py:155，按 v^1.2 归一采样 robot.py:178-179，动作合法性兜底 robot.py:198）。仓库无 epsilon-greedy 对手；对手可注入（env.py:34 参数）但注入协议绑定 Robot 专属方法 `init_dick`（env.py:52）/`update_dick`（env.py:143）。
2. **状态编码**：`StateEncoder`（dqn.py:70-93）4 维 float32，相对 agent 座位（env.py:100）；测试断言 shape==(4,)（tests/test_scripts.py:18-21）。
3. **奖励**：过程 0，终局一次性（env.py:75-79）：赢 +全池（env.py:105），输 -自己已押（env.py:106）；test 佐证（tests/test_scripts.py:45-58）。
4. **回合结束**：agent 每调一次 `step`，env 内部代打对手一步回到 agent 回合（env.py:80-84）；done=`room.finish`（env.py:77/82）或 200 步硬停（env.py:85-86）；结束后再 step 抛 `IllegalAction`（env.py:71-72）。
5. **checkpoint**：`run/dqn_ep{episodes}_seed{seed}.pth`（train.py:27,100-101，dqn.py:204-207）+ `run/summary_seed{seed}.json`（train.py:104）；run/ 被 gitignore（.gitignore:21）。

## 权重文件清单与维度表

**工作区内 *.pth / *.pt 文件：0 个。** 证据：仓库根目录 `ls` 无任何 .pth（且 agents/scripts/ui/mymath/tests/src/docs 目录逐一 ls 无 .pth）；`run/` 目录不存在（ls 报 Path not found）；`find *.pth`、`find *.pt` 无结果；docs/ARCHITECTURE.md:114 明载「该 .pth 仓库内不存在（find 无结果）」；docs/FINAL-REPORT.md:18 版本库跟踪 `*.pth` 数=0。（注意 .gitignore:17-18 忽略 *.pth/*.pt，find 对未跟踪文件无效，故已用 ls 逐目录复核。）

| 路径 | 大小 | input_dim | action_dim |
|---|---|---|---|
| （无） | — | — | — |

本会话工具集只有 read/grep/find/ls，**无 bash/python3**，无法执行 `python3 -c "import torch; ..."` 读维度；因文件本身不存在，维度表为空是确定结论。供父级留档的历史维度（docs/BASELINE-REPORT.md:145-148，文件已不在）：`dqn_model_0.pth` (4,6)、`dqn_model_1.pth` (4,6)、`dqn_final.pth`/`dqn_model_ep50/150/200/250.pth` (9,6)、`pytorch_dqn.pth` 非 DQN state_dict。**结论：没有任何现成权重可直接用于 DQN-vs-DQN，全部需新训。**

## DQN-vs-DQN 自博弈可行性分析

**a. 对称性：可行。** 状态是「相对某一方」的 4 维：`[circle/10, 己方押注/1000, 对方押注/1000, 己方手牌击败随机手牌概率]`（env.py:99-100 + dqn.py:85-92），编码函数以 `player` 为参数、无状态（dqn.py:78-93），两个 DQN 可共用同一个 `StateEncoder`，各自 `encode(snapshot, 己方座位, 己方手牌)` 即得同构观测。动作空间座位无关（rules.py:99-102，同为 0-5 六动作 + legal mask），`act(observation, legal_actions)` 接口两边一致（dqn.py:153-162 / base.py:34）。**唯一不对称**：玩家 0 恒先手（rules.py:60；rules.py:70-87 `new()` 无先手参数；env.py:45-47 发牌顺序固定）→ 自博弈需每局交换座位或给 `GameRoom.new` 加 `first_player`，否则 seat-0 方有先手优势。

**b. 信息泄漏：无。** `GameRoom.snapshot()` 不含手牌（rules.py:107-120 全字段枚举）；agent 观测仅混入自己的手牌（env.py:100 `room.own_hand(self.agent_player)`）；对手 Robot 也只收到自己的手牌（env.py:52 `hands[opponent_seat]`、env.py:123 `own_hand(1-agent)`）。`bets/money` 属公开信息。对手真手牌从未进入任何一方的状态。

**c. 对手改用 DQN 需要的改动**
- **实例创建**：在线学习型 `DQNAgent(input_dim=4, action_dim=6, config=..., seed=...)`（dqn.py:99-120）；固定快照型 `DQNAgent.from_checkpoint(path, epsilon=0.0)`（dqn.py:124-145，维度自适应 dqn.py:136）。
- **env 协议改造**：`opponent: Robot|None` 放宽为 `BaseAgent|None`（env.py:34,38）；`reset()` 按类型分支——Robot 走 `init_dick`（env.py:52），DQN 只需 `reset()`（dqn.py:200，空操作）；`_opponent_snapshot`（env.py:120-124）对 DQN 对手须改为返回己视角 4 维编码（而非带 "hand" 的 dict）；`_notify_opponent`（env.py:126-145）的 json 协议对 DQN 无意义，改为构造对手视角 Transition 并调 `opponent.observe()/replay()`。
- **对手侧奖励**：现 `_settle_reward` 只算 agent 视角（env.py:102-106）；对手镜像奖励=赢 +all_bet / 输 -对手已押（零和，但注意现有奖励本身非严格反对称，见「发现的问题」3）。
- **对手更新（在线 vs 快照）**：快照型每 K 局用 `opponent.load(best_path)`（dqn.py:209-212，自动同步 target）或 `load_state_dict`+`update_target`（dqn.py:197-198,207）；在线型两边同频 `observe/replay`（buffer 各自独立 deque，dqn.py:117，互不污染，因为过渡以各自视角编码）。
- **探索**：epsilon 只在 `replay()` 内衰减（dqn.py:191-192）。建议对手 epsilon 取小常数（如 0.05）或降低其 replay 频率（如每 k 步一次）控制衰减速度，避免双方探索同步消失。
- **防 self-play collapse**：周期性用「当前最佳 checkpoint」重置对手（交替自博弈/快照回滚）；每局记录双方胜率与动作分布（参照 evaluate.py:52-68 的 action_counter 模式）做退化监测；座位交换消除先手偏置；必要时对手 target 网络降频同步。

**d. 最小可行改造方案**
- **scripts/env.py（主改）**
  - `__init__` env.py:34-38：`opponent: BaseAgent | None`；保留 `opponent_seat`（env.py:50 已有局部变量，提升为属性）。
  - `reset()` env.py:44-55：按 `isinstance(opponent, Robot)` 分支，DQN 对手跳过 `init_dick`（env.py:52）。
  - **新增** `_opponent_observation()`：`self.encoder.encode(snapshot, opp_seat, room.own_hand(opp_seat))`（env.py:120 附近）。
  - **新增/改** `_settle_rewards()` 返回 (agent_reward, opponent_reward)（现 env.py:102-106 单值改双值）。
  - `_advance_opponent_until_agent_turn` env.py:108-118：对手每次行动后记录其视角 transition 并 `opponent.observe/replay`（可加频率节流）；对 Robot 仍走 `_notify_opponent`（env.py:126-145 保留）。
- **scripts/train.py**
  - `train()` train.py:38-45 增参：`opponent_mode: "robot"|"self"|"snapshot"`、`opponent_ckpt`、`opponent_sync_every`。
  - train.py:53 改 `env = CardGameEnv(seed=seed, opponent=opp_agent)`。
  - 循环 train.py:59-82：self 模式统计对手胜率；每 `opponent_sync_every` 局把 agent 权重快照给对手（`agent.save(tmp)`+`opponent.load(tmp)`，dqn.py:204-212）。
  - checkpoint train.py:100：自博弈命名如 `dqn_sp_ep{N}_seed{S}.pth`（主）+ `dqn_sp_opp_ep{N}_seed{S}.pth`（对手快照）；summary train.py:86-96 增 opponent 字段。
  - `main()` train.py:112-119 增 `--opponent/--opponent-ckpt/--opponent-sync-every`。
- **agents/dqn.py：无需改动**（act/observe/replay/save/load/from_checkpoint 已够用，dqn.py:124-212）。
- **core/rules.py（可选公平性）**：`GameRoom.new` 增 `first_player`（rules.py:70）；或在 env.py:45-47 按局奇偶交换发牌顺序（不动 core）。
- **scripts/evaluate.py（可选）**：新增双 checkpoint 对战模式（现仅单 agent vs Robot，evaluate.py:35-36）。

## 训练成本

- 「一轮」=1 episode=1 整局（train.py:59-82）；局内步数上限 200（env.py:19,85-86），实际折牌/看牌即终局（rules.py:156-170），远小于上限。
- 参数：`--episodes`（train.py:39,114，默认 20）、`--seed`（train.py:40,115）、`--device`（train.py:116）、`--out`（train.py:117）；**无局内回合数参数**。
- 耗时：仓库无 20 局实测数字（UNKNOWN，见下）；已知上界：tests/test_scripts.py:81-84「5 episodes CPU < 60s」断言；CI 冒烟跑 2 局训练（ci.yml:63）与 3 局×2 可复现性训练（ci.yml:86-87）均在常规 CI 预算内。summary 自带 `elapsed_sec`（train.py:85,95），实跑一次即得。
- 现成产物目录：**无** `run/`（ls 确认不存在；.gitignore:21 忽略之）；产物写入 `run/`（train.py:27）。

## 发现的问题

1. **`dqn_model_1.pth` 在工作区不存在**：evaluate.py:23 默认 checkpoint 指向它；缺失时 `from_checkpoint` 抛 `FileNotFoundError`（dqn.py:133-134）→ `scripts.evaluate` 默认路径直接崩，且 tests/test_scripts.py:88-93、95-100 两个评估测试在无该文件的工作区（如干净 clone/CI 检出）会失败。UI 侧同样走未训练回退（docs/ARCHITECTURE.md:114）。
2. **玩家 0 恒先手**（rules.py:60；rules.py:70-87 无先手参数）：自博弈下构成结构性偏置，必须交换座位或加 `first_player`。
3. **奖励非严格反对称**：赢 +全池（env.py:105）而输 -己方已押（env.py:106），双方奖励量纲不对称（赢家奖励含自己已投入部分）；双 DQN 训练时对手镜像奖励需按同一口径显式定义，否则两侧 Q 值基线不一致。
4. **env 与 Robot 协议强耦合**：`init_dick`（env.py:52）、dict+"hand" 快照（env.py:120-124）、json `update_dick`（env.py:126-145）均为 Robot 专属；`_notify_opponent` 吞一切异常（env.py:144-145），改造时 DQN 对手的错误也会被静默吞掉。
5. **target_sync_every=1 + 每步一次 replay**（dqn.py:45；train.py:71）：对手若同频学习则 epsilon 同步衰减至 0.01（dqn.py:191-192），探索同步消失、塌缩风险高，建议对手降频。
6. `circle` 是全局轮数（rules.py:141-142 轮到 0 才 +1），作为双方共享状态特征无语义问题（dqn.py:86），但注意它是「已过轮数」而非各自视角步数。

## UNKNOWN 清单

1. 20 局训练的准确墙钟耗时——本会话无 bash/python3 工具，无法实跑；仅有 test_scripts.py:84 的 <60s/5ep 上界。
2. `git status` 逐字输出——无 bash 工具；以 .git/logs/HEAD:1-11 干净记录 + HANDOFF「未提交文件：无」替代，且本调查零写入。
3. `core/evaluator.py::compare` 的返回值域（+1/0/-1）未读源文件，从 rules.py:168-170 用法推断（outcome>0=看牌方赢，=0 平局判输）。
4. CI 在缺失 dqn_model_1.pth 的检出环境是否失败——推断 ci.yml:64 的 evaluate 冒烟会失败，未实跑验证。