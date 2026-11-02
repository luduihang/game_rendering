调查完成。以下为范围 C（表现层、测试与质量守护）的结构化调查报告。

---

## 调查目标

只读调查 game_rendering 仓库（当前分支 `main`，见 `.git/HEAD:1`）的表现层与测试体系，回答 12 个问题，产出带 `file:line` 证据的报告，供 Main Agent 汇总进 `docs/ARCHITECTURE.md`。范围：`ui/`、`tests/`（含 `baseline/`）、`pyproject.toml`、`.github/workflows/ci.yml`、`src/`（仅 ls）、`README.md`（一致性核对）。

**Git 状态说明**：本 Agent 仅有 read/grep/find/ls 工具，无法执行 `git status`；但本次运行**零写入**（无 edit/write/bash），工作区不会因本调查产生任何变更。

## 涉及文件（含行数）

| 文件 | 行数 | 说明 |
|---|---|---|
| ui/app.py | 282 | 主循环 + 控制器 |
| ui/clock.py | 75 | 可注入节奏器 |
| ui/render.py | 252 | 薄渲染层 |
| ui/theme.py | 165 | 资源映射 + 布局 |
| ui/__init__.py | 12 | 包导出 |
| tests/test_rules.py | 154 | D1/D2/D4 规则 |
| tests/test_dealing.py | 101 | D6 发牌 |
| tests/test_ui.py | 303 | 时序/一致性/贴图/性能 |
| tests/test_strength.py | 80 | 精确强度表 |
| tests/test_evaluator.py | 112 | 牌型判定 |
| tests/test_agents.py | 219 | D8/D9/智能体契约 |
| tests/test_scripts.py | 124 | 训练/评估入口 |
| tests/test_purity.py | 63 | 分层纯度 |
| tests/baseline/common.py | 60 | 基线脚本公共工具 |
| tests/baseline/repro_d1_showcards.py | 40 | D1 复现 |
| tests/baseline/repro_d2_rest_option.py | 63 | D2 复现 |
| tests/baseline/repro_d4_lagging_done.py | 45 | D4 复现 |
| tests/baseline/repro_d5_wiring.py | 48 | D5 复现 |
| tests/baseline/repro_d6_dealing.py | 59 | D6 复现 |
| tests/baseline/repro_d7_timing.py | 111 | D7 复现 |
| pyproject.toml | 49 | 依赖/pytest/ruff |
| .github/workflows/ci.yml | 95 | CI |
| README.md | 116 | 一致性核对对象 |
| const.py | 82 | 辅助证据（资源路径定义，ui 的直接依赖） |
| draw_me_vs_DQN_Plus.py | 14 | 辅助证据（test_ui 的守护对象） |

## 关键代码位置（file:line + 该处代码在做什么）

### Q1 ui/app.py 主循环（零阻塞确认）
- `ui/app.py:247-251` `App.run()`：`while self.running: self.step_frame()` —— 唯一主循环，无 sleep。
- `ui/app.py:229-245` `step_frame()`：`begin_frame → now → set_now → pump_events()(233) → update()(236) → draw+flip(237-243) → end_frame(244) → frames+=1(245)`。每帧无条件先抽事件。
- `ui/app.py:185-200` `pump_events()`：`pygame.event.get()`（191，非阻塞取空队列）；`pygame.QUIT → self.running = False`（195-196）；KEYDOWN→`_on_key`（197-198）；MOUSEBUTTONDOWN→`_on_click`（199-200）；pygame 未初始化时直接返回（188-189，纯逻辑模式）。
- `ui/app.py:88-106` `Controller.update()`：状态机推进。AI 回合用截止时间表达等待：`if now < self.ai_deadline: return`（93-94）——**等待=提前 return，不是忙等**；每帧上限 guard<64（90）。人类回合：非 auto_human 时直接 return（101-102），把控制权交回事件循环。
- `ui/app.py:74-85` `_schedule()`：按回合方设置 `ai_deadline/human_deadline`（80-85）。
- **有无 time.sleep**：`grep