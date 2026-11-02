## README 一致性核对（逐条 + 双方行号）
1. [一致] 只保留一种策略实现、历史脚本已清理（README.md:4）：根目录仅 draw_me_vs_DQN_Plus.py 一个交互入口（ls 根目录）；删除清单 CHANGELOG.md:8,85、docs/FINAL-REPORT.md:33（commit e0263e1）。
2. [一致] `pip install -e ".[dev]"`（README.md:11,19）：pyproject.toml:22-26 dev extra（pytest>=9.1、ruff>=0.17）。
3. [一致] `python draw_me_vs_DQN_Plus.py`（README.md:12,82）：draw_me_vs_DQN_Plus.py:11 `from ui.app import main`、:14 `main()`。
4. [不一致] 「draw_me_vs_DQN_Plus.py (6 行)」（README.md:28）：实际文件 14 行（9 行 docstring + 3 行可执行代码）。
5. [一致] 架构图模块清单 ui/app·clock·render·theme、core/5 模块、agents/base·dqn·robot、scripts/env·train·evaluate（README.md:29-49）：与各目录 ls 一致（均含 __init__.py）。
6. 依赖方向（README.md:52）：文字 [一致]——ui 只 import core/agents（ui/app.py:17-21、ui/render.py:14-17），scripts 只 import core/agents（scripts/env.py:13-17、train.py:23-24、evaluate.py:18-20），core/agents 不 import ui/scripts（grep 全量 import：core 仅 core 内部互引，agents 仅 agents.base/core/mymath/numpy/torch）。但架构图 [不一致]：README.md:44-48 箭头画成 core/agents ▼→ scripts，与 :52 文字及代码方向相反（箭头方向错误）。
7. [一致] core/agents 不依赖 pygame、CI SDL dummy（README.md:53）：agents/__init__.py:3、scripts/env.py:3 仅 docstring 提及，无 pygame import；ci.yml:16-17 SDL_VIDEODRIVER/AUDIODRIVER=dummy。
8. [一致] core/ 不 import pygame/numpy/scipy/torch（README.md:60）：core/ 实际仅 core 内部 import（core/__init__.py:11-14、rules.py:23-24、strength.py:17-18 等，grep 无命中重依赖）；守护存在：tests/test_purity.py:19,28,55（:55 额外覆盖 matplotlib）。
9. [一致] agents/、scripts/ 不 import pygame（README.md:61）：grep 无 import；守护 tests/test_agents.py:184、tests/test_scripts.py:104。
10. [一致] 无模块 import 期加载权重（README.md:62）：tests/test_agents.py:183（TestLayeringAndImportPurity）、:193。
11. [一致] ui/、scripts/ 无 time.sleep（README.md:63）：ui/ 仅 docstring 提及（ui/app.py:5、clock.py:1），scripts/ 零命中；守护 tests/test_ui.py:39,63。
12. [一致] UI 不自行记账（README.md:64）：tests/test_ui.py:123,124（TestUICoreConsistency.test_view_matches_core_snapshot）。
13. [一致（补充）] mymath/ = func_const·probability_func（README.md:73）：ls mymath/ 另有空 __init__.py 与纯文本「概率大小映射」（21 行概率表，非代码）；Robot 依赖属实（agents/robot.py:20-21）；mymath 自身 import numpy/scipy（func_const.py:1、probability_func.py:1-2），不受 core 纯度约束。
14. [一致] 训练命令（README.md:83）：scripts/train.py:114-117（--episodes/--seed/--device{cpu,cuda}/--out）。
15. [一致] 评估命令（README.md:84）：scripts/evaluate.py:96-99（--rounds/--seed/--checkpoint/--out）。
16. [一致] 产物写 run/ 且被 gitignore、同种子逐位一致（README.md:87）：.gitignore:23 `run/`；ci.yml:84-97（weights_hash 断言）、tests/test_scripts.py:69。
17. [一致] D7 描述（README.md:106）：repro_d7_timing.py:4-7 基线数值一致。
18. [一致] 环境要求（README.md:115）：pyproject.toml:9（py≥3.11）、:15-19 逐一对应（pygame==2.6.1；numpy 2.3.x；scipy 1.17.x；matplotlib 3.11.x；torch 2.13.x）。

**特别核对 B（robot2.py）——确定结论：mymath/robot2.py 不在仓库。** 直接 ls mymath/：仅 `__init__.py`（空）、`func_const.py`、`probability_func.py`、`概率大小映射`（文本表）。robot2 的实现是 agents/robot.py：agents/robot.py:1「由 mymath/robot2.py 迁入，行为保持等价」；CHANGELOG.md:85「mymath/robot2.py → agents.robot.Robot（行为等价留证 L1=0.076）」；docs/FINAL-REPORT.md:33 记录 mymath/robot2.py 随 commit e0263e1 删除。management/legacy/project/r5/contract.json:17,26,39 的「保留 mymath/robot2.py」是 r5 计划期表述，最终按 r5/PLAN.md:33（T3.3 迁入 agents/）落地为删除+迁移。README 本身并未声称保留 mymath/robot2.py（README.md:73 只列 func_const·probability_func），故 README 与代码一致；范围 B 的说法正确。

## pyproject.toml 配置
- build/元信息：setuptools>=68（pyproject.toml:1-3）；game-exercise 0.2.0（:5-8）；requires-python>=3.11（:9）。
- 依赖（锁定策略：主/次版本锁定、补丁浮动，:11-13 注释）：pygame==2.6.1（:15，精确锁定）；numpy>=2.3,<2.4（:16）；scipy>=1.17,<1.18（:17）；matplotlib>=3.11,<3.12（:18）；torch>=2.13,<2.14（:19，范围以兼容 CUDA 构建）。
- dev extra：pytest>=9.1（:24）、ruff>=0.17（:25）。
- setuptools：packages=["core","agents","ui","scripts","mymath"]（:31）；py-modules=["const","algorithm"]（:32）。
- pytest：testpaths=["tests"]（:35）、pythonpath=["."]（:36）、addopts="-q --strict-markers"（:37）。
- ruff：line-length=120（:40）、target-version="py311"（:41）、extend-exclude=["备份","__pycache__",".venv","src"]（:42）、select=["E","F","W","I"]（:45）、per-file-ignores "tests/baseline/*"=["E501","F401"]（:47-49）。

## CI 行为
- 触发：push→main、refactor/**（ci.yml:3-5）；pull_request→main（:6-7）；workflow_dispatch（:8）；concurrency 同 ref 取消旧跑（:10-12）。
- 全局 env：SDL dummy + PYTHONUNBUFFERED（ci.yml:14-18）。
- matrix：有——python 3.11/3.12，fail-fast=false，ubuntu-latest（ci.yml:22-27）。
- 命令序列：checkout@v4（:30）→ setup-python@v5 + pip cache（:32-36）→ pip upgrade + CPU 版 torch（/whl/cpu）+ `pip install -e ".[dev]"`（:38-42）→ `ruff check . --output-format=github`（:44-45）→ `pytest -q`（:47-48）→ 逐个跑 tests/baseline 下 repro_d1/d2/d4/d5/d6/d7 共 6 个回归脚本，任一失败 exit 1（:50-58）→ 无头冒烟：train --episodes 2 --seed 5 + evaluate --rounds 5 + UI 600 帧冒烟（断言整局完成且 agent.epsilon==0.0 即已加载训练权重）（:60-82）→ 可复现性：同种子 2026 两次 train 比对 summary 的 weights_hash（:84-97）。

## src/ 资源规模
- 8 个顶层子目录，共 207 个文件（find 统计）：BGM/ 38（顶层 14 首 mp3 + man_voice 2×6 + woman_voice 2×6）、Font/ 2（ttf）、button/ 19、card_pic/ 53（背面+4 花色×13）、card_pic备用/ 54、character/ 8、item_pic/ 20（png/jpeg 混合）、login/ 13。
- 总大小：UNKNOWN（无 stat/du 工具）；含 38 个音频文件，估计数十 MB 量级（仅估计）。
- 代码引用：const.py:16 `SRC = ROOT / "src"`；:19-24 各子目录常量；:30-31 背景/牌背；:33-34 字体；:68-77 BGM 保留清单；ui/theme.py:44-55 `asset_paths()`、:57-75 按钮/头像/金币路径函数、:77-93 `missing_assets()` 启动自检；ui/render.py:17,25,37,80,88 加载使用。另 src/ 在 ruff extend-exclude 中（pyproject.toml:42），不做静态检查。

## repro_d7 复现的缺陷
D7「时序与事件循环」历史缺陷（tests/baseline/repro_d7_timing.py:1-10）：修复前单步墙钟 ≈1530.8ms、其中 time.sleep(1.5) 占 98.0%（:4）；check_button_click 忙等且不处理 pygame.QUIT（:5）；RepeatedTimer 未 start 就 stop() 抛 AttributeError 且线程非 daemon（:6）；import 期 load_state_dict 致脚本 import 即崩（:7）。现回归检查：零 sleep（:35-41）、QUIT 立即退出（:43-59）、零等待整局<1s（:68-73）、定时器加固+daemon（:75-93）、无 import 期权重加载（:98-106）。与 README.md:106 表述一致。

## 发现的问题
1. README.md:44-48 架构图箭头方向错误：画成 core/agents ▼→ scripts，实际是 scripts → core/agents（scripts/env.py:13-17 等），与 README.md:52 自相矛盾。
2. README.md:28「(6 行)」与实际 14 行不符（可执行代码仅 3 行）。
3. management/legacy/project/r5/contract.json:17,26,39「保留 mymath/robot2.py」与最终代码状态不符（已迁入 agents/robot.py，原文件 e0263e1 删除）——属计划期陈旧表述。
4. pyproject.toml:42 ruff extend-exclude 含已不存在的「备份」目录（历史残留，无害）。
5. mymath/ 的非代码文件「概率大小映射」未出现在 README.md:73 目录说明中（轻微遗漏）。
6. tests/baseline/ 编号缺 D3（现有 d1/d2/d4/d5/d6/d7 + common.py，CI :53-54 与之吻合）；D3 缺号原因 UNKNOWN。

## 结论与建议
README 总体一致度高：18 条核对中 16 条 [一致]、2 处小 [不一致]（"6 行"、图箭头方向）；分层约束、依赖方向文字、测试守护声明全部有代码与测试双重证据。robot2 归属确定：agents/robot.py 为唯一对手策略（robot2 迁入版），mymath/ 仅为概率工具包。建议 ARCHITECTURE.md：依赖方向按 README.md:52 + 代码证据描述并注明原图箭头有误；robot2 历史写「mymath/robot2.py → agents/robot.py（行为等价）→ 原文件删除（e0263e1）」；src/ 总大小标 UNKNOWN。

## UNKNOWN 清单
- src/ 总大小（无 stat/du 工具）：UNKNOWN，估计数十 MB 量级。
- D3 编号缺失原因：UNKNOWN。
- README.md:19 的 cu130 torch index URL 可用性：UNKNOWN（未联网验证）。
- Git status：本 reader 无 bash 工具无法运行 git status；本次纯只读，未写任何文件；.git/HEAD = refs/heads/main。