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
