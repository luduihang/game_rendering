# PRD —— game_rendering 重构 + 机器对手改为 DQN 对抗 DQN 策略

## 背景

`game_rendering`（炸金花三张牌博弈）已完成 core/agents/ui/scripts 四层重构，并有 `docs/ARCHITECTURE.md`
（439 行，421 处 file:line 证据）作为架构知识库。本次任务按该知识库第 7 节的结论做实际重构，
并把交互界面的机器对手策略改成 **DQN 对抗 DQN**。

### 已核实的现状（verified，见 management/evidence/investigation/）

1. **仓库内没有任何 `.pth` 权重文件**（`find`/`ls`/git 索引三重复核均为 0）。`ui/app.py:25` 的
   `DEFAULT_CHECKPOINT = REPO / "dqn_model_1.pth"` 指向一个不存在的文件，`ui/app.py:57-62` 捕获
   `FileNotFoundError` 后**静默回退为未训练策略**（epsilon=0.15 随机）。也就是说，**当前交互界面里的
   机器根本不是训练过的 DQN，而是随机策略**。同样地 `scripts/evaluate.py:23` 的默认 checkpoint 也不存在。
2. **状态编码天然支持双 DQN**：`StateEncoder.encode(snapshot, player, own_hand)`（`agents/dqn.py:70-94`）
   以视角方为参数、无内部状态，产出 4 维输入（`agents/dqn.py:29-32`）；动作空间座位无关、6 个动作
   （`core/rules.py:99-102`）。UI 侧（`ui/app.py:147-148`）与训练侧（`scripts/env.py:97-100`）
   用的是同一个编码器与同一维度（调研 E 核对结论：一致）。
3. **无信息泄漏**：`GameRoom.snapshot()` 不含手牌（`core/rules.py:107-120`），每个智能体只拿到自己
   的手牌（`scripts/env.py:100`、`ui/app.py:147-148`）。
4. **唯一的结构性不对称**：玩家 0 恒先手（`core/rules.py:60`，`GameRoom.new` 无先手参数）。双 DQN
   自博弈下这构成先手优势，必须消除。
5. **`scripts/env.py` 与 Robot 协议强耦合**：`init_dick`（`scripts/env.py:52`）、带 `hand` 键的
   dict 快照（`:120-124`）、json `update_dick`（`:126-145`）都是 Robot 专属协议。
6. **自博弈塌缩风险**：当前 `target_sync_every=1` + 每步一次 replay（`agents/dqn.py:45`，
   `scripts/train.py:71`），两侧 epsilon 会同步衰减到 0.01（`agents/dqn.py:191-192`），探索同时消失。
7. **知识库第 7 节判定**：7.1（snapshot/view 契约）、7.3（22100 惰性建表）、7.4（from_checkpoint
   维度自适应）、7.5（均匀发牌默认）**不可碰**；7.2 的 D1-D9 路径**必须避开**；7.6（README 三处
   不一致）可安全做。7.7 的 10 个小问题分为 S(约 9 条) / M(3 条) / L(1 条)。

## 目标

1. 实现 **DQN 对抗 DQN（自博弈）训练**：机器对手由另一个 DQN 担任，两个 DQN 互相对弈学习。
2. 用自博弈训练产出**真实权重**，让交互界面的机器真正是一个训练过的策略（消除当前的静默随机回退）。
3. 保持**人类对抗机器**的交互模式不变（人仍按键/鼠标操作，机器自动出牌）。
4. 按 `docs/ARCHITECTURE.md` 第 7 节完成 **S/M 级重构**，修正 7.6 的 README 三处不一致。
5. 保持「改动不打红现有测试」，且新增测试锁定新行为。

## 非目标

- 不改核心牌局规则语义（`core/rules.py` 的比对方向、平局、花色决胜一律不动）。
- 不改 22100 精确表的惰性建表机制（不挪到 import 期、不去 lru_cache）。
- 不改 `from_checkpoint` 的维度自适应机制。
- 不改默认发牌（保持均匀发牌；`deal_strength_biased` 仅作可选开关）。
- 不改状态编码的 4 维定义与 6 维动作空间（否则新权重与 UI 不兼容）。
- 不做联网对战、不做新玩法、不做发布打包。
- 不重写 git 历史。

## 当前状态核实

已核实（verified）：

- 上述 7 条现状均由本次三份调研报告以 file:line 证据确认（`management/evidence/investigation/`）。
- `docs/ARCHITECTURE.md` 存在且已合并进 main（commit 7109e29）。
- 基线 r1 为 ACTIVE；本任务需要 r2（r1 的 `outOfScope` 明确禁止改业务代码）。

未核实（unverified，由执行阶段实测）：

- 自博弈训练在 CPU 上的实际墙钟耗时（只有 `tests/test_scripts.py:81-84` 的「5 局 < 60s」上界）。
- 自博弈训练能收敛到何种程度（胜率曲线、动作分布是否退化）。
- CI 在干净检出下的真实红绿状态（调研 F 推断 pytest 阶段会因权重缺失而红，未实测）。

## 约束

- **Main Agent 不亲自实现**。Main 只做：拆分任务、派发子 Agent、审阅交付、维护基线与文档。
  编码、测试、训练、审核全部由子 Agent 完成。
- 委派深度固定 1 层；子 Agent 模型统一 `vllm-local/Qwen3.8-27B`（qwen38）。
- **不得触碰**：`core/rules.py` 的规则语义、`core/strength.py` 的建表时机、`agents/dqn.py` 的
  `from_checkpoint` 机制、`core/dealing.py` 的默认均匀发牌。改动这些会让对应回归测试变红。
- 训练必须**可复现**（固定种子），且单次训练运行**不得超过 30 分钟**；超出需人工批准。
- 权重文件不进版本库（`.gitignore` 已忽略 `*.pth`），但需在文档与 CI 中说明其获取方式。
- 所有新增/修改行为必须有对应测试。

## 可验证验收标准

1. `scripts/train.py` 支持自博弈模式（如 `--opponent-mode self`），两个 DQN 互相对弈；
   训练产物含主策略与对手策略两个 checkpoint，并写入 summary。
2. 自博弈训练消除了先手偏置：两个 DQN 的座位在每局中交换，且训练 summary 记录双方胜率。
3. 仓库内**存在**由自博弈训练产出的真实权重文件；`ui/app.py` 默认加载该权重时
   `epsilon == 0.0`（不是回退的 0.15），且动作分布与随机策略显著不同。
4. 交互界面仍是「人类 vs 机器」模式：人类按键/鼠标操作，机器自动出牌，回合交替正常。
5. `scripts/evaluate.py` 能以自博弈权重做双 DQN 对战评估并输出胜率。
6. 知识库 7.7 的 S 级与 M 级条目全部完成（键码映射、资源自检接入、core `__all__` 补全、
   `last_now` 归位、`button_rects` 注解等），7.6 的 README 三处不一致全部修正。
7. `pytest` 与 `ruff` 全绿；**既有测试无一被打红**（对比重构前基线）。
8. `docs/ARCHITECTURE.md` 同步更新：新增自博弈训练章节、机器对手接线变化、
   权重获取与存放说明、重构后各章行号与结论的校正。
9. 本次改动**未触碰**「不可碰」清单中的任何文件机制（由 reviewer 逐条核对）。

## 风险与变更点

| 风险 | 影响 | 应对 |
|---|---|---|
| 自博弈塌缩（双方同步衰减探索、互相模仿） | 训练出的权重是废的 | 对手降频学习（每 k 步才 replay）、对手 epsilon 取小常数、周期性用最佳 checkpoint 重置对手、summary 记录双方胜率与动作分布做退化监测 |
| 先手偏置 | 训练偏向先手方，机器对人类不公平 | 每局交换座位（env 层实现，不改 `core/rules.py`） |
| 训练耗时超预期 | 任务超期 | 先跑 5 局测速，再定局数；单次训练硬上限 30 分钟，超时人工批准 |
| 改动打红既有测试（D1-D9 回归） | 破坏已修复的缺陷 | 触碰任何路径前先跑对应测试文件；reviewer 逐条核对「不可碰」清单 |
| 权重不进版本库 → CI 干净检出必然红 | CI 失效 | 提供权重生成脚本与 CI 步骤；或让相关测试在权重缺失时显式 skip 而非报错（须人工确认口径） |
| 子 Agent 误改 `core/` 核心机制 | 破坏分层与回归 | core/ 的改动集中在「只补 `__all__` 导出」，由 reviewer 逐行核对 diff |

