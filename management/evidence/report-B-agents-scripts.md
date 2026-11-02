All evidence gathered. Compiling the final investigation report.

---

## 调查目标

范围 B（智能体层与入口层）只读调查：`agents/` 全部、`scripts/` 全部、根目录交互入口 `draw_me_vs_DQN_Plus.py`，以及 `agents/robot.py` 与 `mymath/robot2.py` 的关系确认。产出带 `file:line` 证据的结构化报告，供 Main Agent 汇总进 `docs/ARCHITECTURE.md`。全程只读（read/grep/find/ls），未写任何文件。

## 涉及文件（含行数）

| 文件 | 行数 | 角色 |
|---|---|---|
| `agents/base.py` | 57 | BaseAgent 统一接口 + Transition |
| `agents/dqn.py` | 224 | DQN 网络/超参/智能体/from_checkpoint/权重指纹 |
| `agents/robot.py` | 257 | 对手策略 Robot（robot2 迁入） |
| `agents/__init__.py` | 20 | 包导出 |
| `scripts/env.py` | 158 | CardGameEnv 环境封装 |
| `scripts/train.py` | 124 | 无头训练入口 |
| `scripts/evaluate.py` | 108 | 无头评估入口 |
| `scripts/__init__.py` | 1 | 仅 docstring |
| `draw_me_vs_DQN_Plus.py` | 14 | 唯一交互入口（纯启动器） |
| `mymath/`（仅确认） | — | `__init__.py`（空）、`func_const.py`、`probability_func.py`、`概率大小映射`（21 行纯文本概率表，非代码）；**无 robot2.py** |

跨边界取证说明：问题 9 要求确认交互入口"是否真正加载已训练权重"，该证据位于 `ui/app.py`（约 282 行），属另一 reader 范围；我仅对 `ui/app.py` 做了针对性行号取证（line 25/49/57-62/257-278），未深入 ui/ 其余文件。

## 关键代码位置（file:line + 该处代码在做什么）

### Q1 BaseAgent 接口（`agents/base.py`）
- `base.py:19-25` — `Transition` frozen dataclass：`state: np.ndarray` / `action: int` / `reward: float` / `next_state: np.ndarray` / `done: bool`。
- `base.py:28` — `class BaseAgent(ABC)`；`base.py:31` 类属性 `name: str = "agent"`。
- `base.py:33-35` — **唯一抽象方法** `act`：`@abstractmethod`（33 行）+ `def act(self, observation: Any, legal_actions: Sequence[int]) -> int`（34 行），默认体 raise NotImplementedError（35 行）。
- `base.py:37-38` — `observe(self, transition: Transition) -> None`，默认空实现（无学习能力可忽略）。
- `base.py:40-41` — `reset(self) -> None`，默认空实现。
- `base.py:43-44` — `save(self, path) -> None`，默认 raise NotImplementedError（44 行）。
- `base.py:46-47` — `load(self, path) -> None`，默认 raise NotImplementedError（47 行）。
- `base.py:49-57` — `@staticmethod _pick_legal(action, legal_actions) -> int`：非法动作时兜底取最接近的合法动作（56-57 行），保证 act 返回值一定 ∈ legal_actions（docstring 约定见 `base.py:4`）。
- 返回类型约定：act→int（必须在 legal_actions 内）；observe/reset→None；save/load 的 `path` 参数**无类型标注**。

### Q2 DQN 结构（`agents/dqn.py`）
- `dqn.py:35-46` — `DQNConfig` frozen dataclass（显式超参）：`hidden=(128,64)`（37）、`lr=1e-3`（38）、`gamma=0.95`（39）、`batch_size=32`（40）、`buffer_size=5000`（41）、`epsilon_start=1.0`（42）、`epsilon_min=0.01`（43）、`epsilon_decay=0.995`（44）、`target_sync_every=1`（45）、`device="cpu"`（46）。
- `dqn.py:49-59` — `class DQN(nn.Module)`：`__init__(self, input_dim, output_dim, hidden=(128,64))`（50 行），fc1（52）/fc2（53）/fc3（54）；forward = relu→relu→linear（56-59）。
- 状态空间维度：`dqn.py:29-31` — `BOARD_FEATURES=3`、`CARD_FEATURES=1`、`DEFAULT_STATE_DIM=4`；编码实现在 `StateEncoder`（70-93 行）：盘面 3 维 = `circle/10`、`bets[player]/1000`、`bets[1-player]/1000`（86-88 行），手牌 1 维 = `beats_probability`（92 行）；`dqn.py:80` 对 `core.strength` 是 **lazy import**（在 `StateEncoder.__init__` 内）。`DQNAgent.__init__` 默认 `input_dim=DEFAULT_STATE_DIM`（101 行）。
- 动作空间：`dqn.py:32` — `DEFAULT_ACTION_DIM=6`；动作语义 0-3=押 10/20/50/100、4=弃牌、5=比牌（映射证据：`agents/robot.py:25` `OPTION_INDEX`、`scripts/evaluate.py:62-69` action_names 与 `core.rules.Action` 对应）。
- `dqn.py:96-120` — `DQNAgent(BaseAgent)`：`name="dqn"`（97）；`__init__(self, input_dim=4, action_dim=6, config=None, seed=None, epsilon=None)`（99-106）；独立 `self.rng = random.Random(seed)`（112）；model（114）/target_model（115）/optimizer（116）/memory deque（117）/epsilon 初值（118）/构造后立即 `update_target()`（120）。

### Q3 from_checkpoint 工厂（关键项，D8 修复）
- **存在**。`dqn.py:123-145` — `@classmethod from_checkpoint(cls, path, config=None, seed=None, epsilon=0.0, device=None) -> DQNAgent`（124 行签名）。
- 维度推断：`dqn.py:62-67` — `checkpoint_dims(path)` 用 `torch.load(..., weights_only=True)`（64 行）读取 `fc1.weight.shape[1]`（input_dim）与 `fc3.weight.shape[0]`（output_dim）（67 行），缺键则 raise ValueError（65-66）。
- 工厂体内：`path.exists()` 检查否则 FileNotFoundError（133-135）；**136 行** `input_dim, action_dim = checkpoint_dims(path)`——按 checkpoint 实际维度构建；140 行 `cls(input_dim=..., action_dim=...)`；141-142 行 `torch.load` + `model.load_state_dict`；143 行 `model.eval()`；144 行同步目标网络；145 行返回。
- 历史"权重维度与模型声明不匹配"（D8）的规避机制：网络维度不再由调用方声明，而由 checkpoint 张量形状决定（136→140 行）。
- import 期零磁盘 IO（D7-d）：全部 `torch.load` 均在函数体内（64、141、210 行），模块级仅常量与类定义（26-32 行）。
- `dqn.py:215-224` — `weights_hash(agent) -> str`：对排序后 state_dict 逐张量 sha256，用于同种子可复现性比对。

### Q4 经验回放 / 目标网络
- 回放缓冲：`dqn.py:117` `self.memory = deque(maxlen=config.buffer_size)`；写入 `observe`（165-166 行 append）；采样 `dqn.py:171` `self.rng.sample(self.memory, batch_size)`（注意用 agent 自己的 rng，非全局 random）。
- TD 更新：`dqn.py:180-188` — `current_q`（180）、target 网络算 `next_q`（181-182）、`target_q = rewards + (1-dones)*gamma*next_q`（183）、MSE loss（184）、backward/step（186-188）。
- 目标网络：`dqn.py:115` 构造；`dqn.py:197-198` `update_target()` = `target_model.load_state_dict(model.state_dict())`；同步节奏 `dqn.py:193-194`（每 `target_sync_every` 步，默认 1 = 每步硬拷贝）；epsilon 衰减 `dqn.py:191-192`。

### Q5 对手策略 Robot2（`agents/robot.py`）
- `robot.py:1-9` — 模块 docstring 自述"由 mymath/robot2.py 迁入，行为保持等价"，Robot/Robot2 两类合并为一个类 + `RobotConfig` 参数化。
- `mymath/robot2.py` **已不在仓库**：`ls mymath/` 仅 `__init__.py`、`func_const.py`、`probability_func.py`、`概率大小映射`；`docs/FINAL-REPORT.md:33` 记录其随 commit `e0263e1` 删除。
- `robot.py:28-72` — `RobotConfig` frozen dataclass，25 个超参（31-54 行）；`aggressive()`（56-58）= 原 Robot2 参数（默认）；`conservative()`（60-72）。
- `robot.py:81-91` — `class Robot(BaseAgent)`（`name="robot"` 83 行），`__init__(id="1", config=None, seed=None)`，`self.rng = np.random.default_rng(seed)`（89 行），显式 `import numpy as np`（15 行，修复了原星号导入泄漏）。
- 行为核心：`_hand_strength` 用 core 穷举精确值 `beats_probability`（7