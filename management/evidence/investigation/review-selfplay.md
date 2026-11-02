All verification complete. Compiling the final review report.

# 独立核验报告：DQN 对抗 DQN 自博弈训练机制（commit cb813cf，基线 6bd6253）

## 逐条结论

**1. 交付物与报告一致 — 通过（实测）**
`git show --stat cb813cf`：恰好 4 个文件，stat 行数 163/71/136/252 与报告一致（numstat 细看：env 144+/19-、evaluate 50+/21-、train 130+/6-、test 252+/0-）。`git diff --name-only 6bd6253 cb813cf` 仅这 4 个文件；未动 core/ agents/ ui/ README.md。工作区 3 个未提交文件（.agent/*、PROGRESS.md）为 HANDOFF 已记载的接管前既有状态，不在 commit 内。

**2. agents/dqn.py 零改动 — 通过（实测）**
`git diff 6bd6253 cb813cf -- agents/ core/ ui/ README.md` 输出 0 行。

**3. 零和奖励 — 通过（实测），行为变更已确认且无打红隐患**
代码 env.py:188-194：`_settle_rewards()` 返回 `(total,-total)` / `(-total,total)`，严格反对称。实测 5 个 seed 跑整局：每步（含终局）`reward + opponent_reward == 0`，终局符号与 winner 一致，|reward|==pot，均为自然终局（如 seed=2：`(-270.0,+270.0) winner=1 pot=270`）。
与 core/rules.py 结算一致性（rules.py:175 `players[winner].money += all_bet`，赢家拿走全池含底注）：方向一致、零和、幅度=赢家所得全池。精确表述：输家净资金损失其实等于其自身投入（含底注），旧 robot 输局奖励 `-agent.bet` 恰好等于输家净损失，新 `-all_bet` 是对称零和口径、幅度更大。worker 已如实披露该变更。
既有测试依赖检查（自己 grep 基线 tests/）：仅 test_scripts.py:45-58 断言「非终局 reward==0、终局 !=0」，无数值幅度断言；无任何测试引用旧 `-bet` 数值。实测基线 vs 改动后失败集完全相同（同为 8 例，见第 6 条）→ **无打红隐患**。

**4. 座位交换 — 通过（实测），先手偏置确实被消除**
代码 env.py:100-111：`agent_player = (base + (episodes-1)) % 2`，DQN 对手自动启用、Robot 不交换（test_robot_mode_does_not_swap_seats 佐证）。实测 6 局：先手策略序列 `agent/opponent/agent/opponent/agent/opponent` 严格交替；对手坐座位 0 的局 `room.history[0] = (0, action)` 直接证明座位 0 先行动。
关键追问：座位 0 恒先手（core 未动），但**哪个策略坐在座位 0 每局翻转**——先手优势在两个策略间交替分配，是真实交换，不是只换 agent 视角。

**5. 对手视角编码对称性 — 通过（实测）**
env.py:182-186 + dqn.py:85-95（`[circle/10, bets[player]/1000, bets[1-player]/1000, strength(hand)]`）。构造非对称押注局面实测输出：agent `[0.1, 0.015, 0.005, 0.6882]`，opp `[0.1, 0.005, 0.015, 0.9235]`——a[0]==o[0]、a[1]==o[2]、a[2]==o[1]、手牌槽各用各的手（0.6882≠0.9235）。真镜像。

**6. 测试真实性 — 通过（实测）**
worktree 内 `python -m pytest tests/ --tb=short -q`：收集 133（20+8+21+4+17+13+15+8+27，test_selfplay=15 与声称一致），**8 failed / 125 passed**。基线临时 worktree `/tmp/baseline-check`（6bd6253，已 remove 清理）：**118 收集，同样 8 failed / 110 passed**。
8 个失败用例（两侧完全相同）：test_agents.py::TestCheckpointDims 3 例 + TestD9LoadedPolicyInEffect 3 例、test_scripts.py::TestEvaluate 2 例；逐个看 traceback 全部是 `FileNotFoundError: 找不到权重文件: .../dqn_model_1.pth`，该文件在 worktree 与主仓均不存在，属**既有环境问题**，非本次改动弄坏。
新测试质量：无 skip、无 mock、断言具体（镜像数值 0.015/0.005、先手交替精确序列 [T,F,T,F]、9 字段全等、pytest.raises 具体异常），无恒真断言。

**7. 可复现与 checkpoint 真实性 — 通过（实测）**
独立跑两次同 seed（424243）3 局 self 训练：15 个关键字段（含 weights_hash、opponent_weights_hash、双方动作分布、avg_reward）逐一对比 **全部一致**（hash 前缀 0726ae4b...）。
checkpoint 实测：fc1.weight=(128,4)、fc2=(64,128)、fc3=(6,64)，即输入 4/输出 6（worker 说的「(4,6)」指输入输出维）；`DQNAgent.from_checkpoint` 加载成功并可 act。
注：3 局 run 中双方 hash 相同是机制使然（sync_every=max(1,3//4)=1，第 2 局后对手重置为主策略快照，第 3 局对手 buffer 未达 batch 32 无更新），两次 run 间一致，非异常。

**8. 降频 replay 与防塌缩 — 通过（实测），1 个小问题**
默认值真实生效：train.py 签名 `opponent_replay_every: int = 4` + argparse default=4，self 模式原样传入 env；`opponent_sync_every` None → `max(1, episodes//4)`；`opponent_epsilon` None → self 模式 1.0（train.py:95-100）。
200 局实测（镜像 train() 含 sync）：ep200 时 agent.eps=0.3525（208 次 replay）vs opp.eps=0.9801（4 次成功 replay）——**对手衰减确实慢一个数量级**，防塌缩目标达成。
小问题：`_opp_actions` 在 reset() 清零（env.py:118），replay_every=4 实为「**单局内**每 4 次行动」，短局（对手每局 <4 次行动）时 replay 饥饿（200 局仅 4 次）。效果上强化防塌缩，但文档「每 k 次行动」表述不精确，建议注明或改累计计数。

**9. evaluate 双 checkpoint — 通过（有条件）**
真跑 20 轮（3 局 self 训练产出双 ckpt，默认 epsilon=0）：`win_rate=0.0, opponent_win_rate=0.0, sum=0.0`，动作分布 98.5% bet_50。复现排查：20/20 轮全部 MAX_STEPS=200 强停（finish=False、winner=None、pot≈10010-10260）——近随机贪心策略双方只加注不弃牌不看不。改 epsilon=0.7：`win_rate=0.3, opponent_win_rate=0.7, sum=1.0000`，双方动作分布合理。**机制正确输出双方胜率；「和≈1」仅在自然终局场景成立**，0/0 是未训练策略+强停的 artifact。

**10. 双路径兼容性 — 通过（实测+逐行 diff）**
Robot 分支：reset() 的 `init_dick(["1","0"], hands[1])`、`_advance_opponent_until_agent_turn` 的 snapshot→act→apply→notify 语义逐行等价；step() 的 `_notify_opponent` 调用不变；新增 action_counts 仅计数。Robot 决策行为未变；唯一行为差异即第 3 条已披露的输局奖励幅度。基线 vs 改动后失败集相同，无既有测试被打红。

**11. 边界与异常 — 通过（实测）**
非法 mode → `ValueError: 未知 opponent_mode: 'bogus'（可选 ('robot', 'self', 'snapshot')）`；snapshot 缺 ckpt → `ValueError: opponent_mode='snapshot' 必须提供 opponent_ckpt`；缺文件 → `FileNotFoundError: 找不到权重文件: ...`。均有测试覆盖（test_invalid_mode_rejected 等），信息可读。

**12. 判断：是真正的 DQN 对抗 DQN — 结论：是（实测确认）**
证据链完整闭环：对手动作真实进入房间（room.apply、计入 history、进入动作分布）；对手经验来源正确（opponent.memory 条数 == 对手行动数，state/next_state 均为 4 维对手视角）；奖励按双方各自视角零和传递、终局正确补给最后一条 transition；座位交换改变真实先手归属；两个 checkpoint 均产出、可加载、可互相对战。不存在「经验来源不对/状态不对称/奖励断裂」。防塌缩双机制（降频 replay + 周期快照重置）实测生效。

## 实测命令与关键输出（摘要）
- `git show --stat cb813cf`：4 文件 163/71/136/252；`git diff --name-only` 仅 4 文件；`git diff ... -- agents/ core/ ui/ README.md` = 0 行
- worktree pytest：133 收集 / 8 failed / 125 passed；基线 /tmp/baseline-check：118 / 8 / 110；8 失败全为 dqn_model_1.pth 缺失（FileNotFoundError）
- 零和：5 seeds 全步 `r+opp_r==0`，终局 `(+70,-70)/(-270,+270)/(-50,+50)/(+150,-150)/(-10,+10)` 与 winner 一致
- 座位：6 局先手 `agent,opponent,agent,opponent,agent,opponent`，history[0]=(0,a) 佐证
- 对称：agent `[0.1,0.015,0.005,0.6882]` vs opp `[0.1,0.005,0.015,0.9235]`
- 复现：两次同 seed 15 字段 diff = NONE，hash 相同；fc1=(128,4) fc3=(6,64)，from_checkpoint 可加载
- epsilon：200 局 agent=0.3525 vs opp=0.9801
- evaluate：eps=0 → 0.0/0.0（20 轮全 MAX_STEPS 强停）；eps=0.7 → 0.3/0.7，和=1.0000

## 必须返工的点
无。（无阻断项）

## 不影响验收的小问题
1. env.py:118 `_opp_actions` 每局清零 → replay_every 名义语义与实现有偏差（短局下对手 replay 饥饿），建议 docstring 注明「局内计数」或改跨局累计。
2. 零和幅度 ±all_bet 为全池而非输家净损失（输家净损失=自身投入）；口径合理且已披露，下游若把它当资金代理需注意。
3. 未训练双 ckpt 贪心 evaluate 会 0/0（MAX_STEPS 强停），建议在 evaluate 文档中提示解读方式。
4. worker 报告「权重 shape (4,6)」是输入/输出维的简写，非权重矩阵形状（实为 128×4 / 6×64），表述可更精确。

## UNKNOWN
无。所有清单项均实测核验。

**总体结论：通过。** 12 条清单全部达标；worker 报告与代码/实测相符，披露充分（robot 奖励变更主动说明），未发现夸大或隐瞒。基线 worktree 已清理，被核验 worktree 未被修改（git status 仅剩接管前既有未提交文件，缓存均 gitignore）。