# ARCHITECTURE.md 内容级过期项（T5a worker 发现，行号已对但措辞过时）

> 这些不是行号问题，是**描述与当前代码不符**。T5a（arch-ref-fix）只改行号，未动措辞。
> 供 T5b（arch-doc-update）处理。

## 1. `pyproject.toml` 的 extend-exclude
- 文档位置：`docs/ARCHITECTURE.md:426`（T4 校正后）
- 当前描述：称 `pyproject.toml:42` 的 `extend-exclude` 含「备份」目录
- 实际情况：T4 已**移除**该条目（「备份」目录不存在）。行号 42 仍然正确，但描述已过时。

## 2. `missing_assets()` 的使用情况
- 文档位置：`docs/ARCHITECTURE.md:381`
- 当前描述：称 `missing_assets()` 未被使用
- 实际情况：T4 已改为使用 `ui/theme.py` 的 `missing_assets()`，由 `ui/app.py` 的 `check_assets()` 调用（`ui/app.py:334`）。

## 3. `button_rects` 的返回注解
- 文档位置：`docs/ARCHITECTURE.md:382`
- 当前描述：称注解为 `"object"`
- 实际情况：T4 已改为 `dict[int, pygame.Rect]`（`ui/theme.py:134`）。

---
*来源：T5a worker 交付报告 §6。T5a 未擅自修改措辞（超出该 Task 范围）。*

## 4. reviewer 复核追加的 2 处（T5a 之后发现）

### 4.1 `core.rules.Action` 的逐行归属错误
- 文档位置：`docs/ARCHITECTURE.md:153`
- 文档描述：`imports 仅 core/agents（evaluate.py:22-23），其中 23 → core.rules.Action`
- 实际情况：`scripts/evaluate.py:23` 实为 `from scripts.env import ACTION_NAMES, CardGameEnv`；该文件全文**无** core.rules import。
- reviewer 实测：`evaluate.py` 的 import 为 22 行 `from agents.dqn import ...`、23 行 `from scripts.env import ...`。

### 4.2 `last_now` 被描述为类级属性
- 文档位置：`docs/ARCHITECTURE.md:385`
- 文档描述：`last_now 为类级属性（未写于 __init__）…（ui/app.py:104）`
- 实际情况：`ui/app.py:104` 的 `self.last_now: float = 0.0` **恰在 `__init__` 内**（`def __init__` 于 79 行），与「未写于 __init__」矛盾。（`set_now` 的 198-199 行引用本身正确。）

---
*追加来源：T5a reviewer 报告（`management/evidence/investigation/review-arch-ref-fix.md`）。*
