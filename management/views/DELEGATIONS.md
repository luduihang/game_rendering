# 委派

## architecture-survey：建设 game_rendering 架构知识库：派发 3 个 reader 子 Agent 对 core/agents/ui/scripts/tests 四个层做互斥模块的只读调查，收集带 file:line 的代码证据，汇总产出 docs/ARCHITECTURE.md（8 章节），并由 reviewer 逐条核对证据与冲突。Main Agent 只做调度与编排，不亲自读代码、不亲自写文档正文。

- 状态：已取消；未验收
- 预算：1800000 tokens；授权路径 .

- Delegation G-39520e2a-0e87-48bb-81c5-471ab857416d：reader
    - 目标：【调查范围 A：领域层】只读调查 game_rendering 仓库的领域层代码，产出带 file:line 证据的结构化报告，供 Main Agent 汇总进 docs/ARCHITECTURE.md。

你负责且仅负责这些文件（互斥切分，不要越界到 agents/ ui/ scripts/）：
- core/ 全部文件（cards.py, rules.py, strength.py, dealing.py, evaluator.py, __init__.py）
- algorithm.py
- const.py

必须回答的问题：
1. core/ 每个模块的职责边界、关键公开类/函数（名字 + file:line）。
2. 数据模型：Card/Rank/Suit 等数据结构定义在哪、有哪些字段、不变式是什么（file:line）。
3. 牌型判定六类分别在哪里实现、判定顺序是什么（file:line）。比大小如何处理平局与花色决胜（file:line）。
4. strength.py 的精确表：C(52,3)=22100 穷举表在哪里生成、是模块 import 期还是显式调用期生成、如何被查询（file:line）。这一点很重要——请给出确切的行号证据。
5. dealing.py 的发牌逻辑：默认是否为均匀发牌、draw_strength_biased() 这个可选开关是否存在及其行为（file:line）。
6. rules.py 的状态机：状态有哪些、谁持有权威状态、押注与结算规则在哪几行（file:line）。
7. evaluator.py 的职责与对外接口（file:line）。
8. algorithm.py 里的 RepeatedTimer：是否还存在、其调度语义、是否 daemon、stop() 是否幂等（file:line）。
9. const.py 持有什么常量（file:line）。
10. core/ 的依赖禁令：core/ 是否 import pygame / numpy / scipy / torch？给出每个文件的 import 清单与行号证据。

严格约束：
- 只读。你只有 read/grep/find/ls 工具，禁止写任何文件。
- 每一条结论必须给 `文件路径:行号` 证据。无法确认的明确写 UNKNOWN，不要推测。
- 不要把 README 的自述当作事实，一切以代码为准。

输出格式：
## 调查目标
## 涉及文件（含行数）
## 关键代码位置（file:line + 该处代码在做什么）
## 调用关系（谁调用谁）
## 发现的问题（分层违例、残留重复实现、遗留 bug）
## 结论与建议（重构风险点：改这里会牵连什么）
## UNKNOWN 清单
    - 授权：工具 read, grep, find, ls；路径 ./core, ./algorithm.py, ./const.py；额度 30000 tokens
        - Run R-b9853e0d-6e92-4850-88e2-7ba398568e00：FAILED；reader；模型 vllm-local/Qwen3.8-27B；216659 tokens
- Delegation G-70a7308a-5dc7-4dbb-9215-6184a4bd2f94：reader
    - 目标：【调查范围 B：智能体层与入口层】只读调查 game_rendering 仓库的智能体层与训练/评估入口，产出带 file:line 证据的结构化报告，供 Main Agent 汇总进 docs/ARCHITECTURE.md。

你负责且仅负责这些文件（互斥切分，不要越界到 core/ ui/）：
- agents/ 全部文件（base.py, dqn.py, robot.py, __init__.py）
- scripts/ 全部文件（env.py, train.py, evaluate.py, __init__.py）
- draw_me_vs_DQN_Plus.py（根目录唯一保留的交互入口）
- agents/robot.py 与 mymath/robot2.py 的关系（若 mymath/ 存在则只确认其内容，不要深入其它 mymath 文件）

必须回答的问题：
1. agents/base.py 的 BaseAgent 接口：具体方法签名（act / observe / reset / save / load 各自签名 + file:line）、抽象方法有哪些、是否有返回值类型约定。
2. agents/dqn.py：DQN 类结构、__init__ 的超参（哪些是 dataclass 或显式参数 + file:line）、状态空间维度如何确定、动作空间是什么。
3. from_checkpoint 工厂：是否存在、签名、是否按 checkpoint 实际维度构建网络（给出确切行号证据）。这是关键项——历史上存在过「权重维度与模型声明不匹配」的问题，请确认现在如何避免。
4. 经验回放 / 目标网络的实现在哪几行（file:line）。
5. agents/robot.py：对手策略 Robot2 的实现位置与行为（file:line）。
6. scripts/env.py：环境封装了什么、状态如何观测（file:line）。
7. scripts/train.py：命令行参数有哪些（file:line）、随机种子如何控制、产物输出到哪里、是否可复现（同种子两次运行 state_dict 逐位一致）。
8. scripts/evaluate.py：评估入口做什么（file:line）。
9. draw_me_vs_DQN_Plus.py：作为唯一交互入口，它实际有多长、调用了 ui/ 与 agents/ 的哪些函数、是否真正加载了已训练权重（file:line）。注意：这个文件很小，请给出完整行号证据说明它到底做了什么。
10. 依赖方向：agents/ 与 scripts/ 是否 import pygame？core/ 是否被它们依赖？给出 import 清单与行号。
11. 权重文件与产物：代码引用了哪些 .pth 权重文件名（file:line）？这些文件在仓库里是否存在（用 ls 确认，不要 git 回显）？

严格约束：
- 只读。你只有 read/grep/find/ls 工具，禁止写任何文件。
- 每一条结论必须给 `文件路径:行号` 证据。无法确认的明确写 UNKNOWN，不要推测。
- 不要把 README 的自述当作事实，一切以代码为准。

输出格式：
## 调查目标
## 涉及文件（含行数）
## 关键代码位置（file:line + 该处代码在做什么）
## 调用关系（谁调用谁）
## 发现的问题（分层违例、残留重复实现、遗留 bug、权重路径风险）
## 结论与建议（重构风险点：改这里会牵连什么）
## UNKNOWN 清单
    - 授权：工具 read, grep, find, ls；路径 ./agents, ./scripts, ./draw_me_vs_DQN_Plus.py；额度 30000 tokens
        - Run R-c087e5df-6c86-4acb-aef4-a315fb801999：FAILED；reader；模型 vllm-local/Qwen3.8-27B；405622 tokens
- Delegation G-d49008ee-6910-44ee-91a6-efb2e1f19e8c：reader
    - 目标：【调查范围 C：表现层、测试与质量守护】只读调查 game_rendering 仓库的表现层与测试体系，产出带 file:line 证据的结构化报告，供 Main Agent 汇总进 docs/ARCHITECTURE.md。

你负责且仅负责这些范围（互斥切分，不要越界到 core/ agents/ scripts/）：
- ui/ 全部文件（app.py, clock.py, render.py, theme.py, __init__.py）
- tests/ 全部文件（test_rules.py, test_dealing.py, test_ui.py, test_strength.py, test_evaluator.py, test_agents.py, test_scripts.py, test_purity.py, baseline/）
- pyproject.toml（依赖与 ruff/pytest 配置）
- .github/workflows/ci.yml（CI 实际跑什么）
- src/ 目录只需 ls 确认资源结构与规模（美术/字体/BGM/button/card_pic 等），不要逐个打开二进制资源
- README.md（只为核对「文档声明 vs 代码事实」是否一致；README 的自述不算事实证据）

必须回答的问题：
1. ui/app.py：主循环结构（file:line）、是否用 pygame.event.get() 驱动状态机、事件循环是否零阻塞、有无 time.sleep（file:line 证据）。历史上存在过「忙等 while not signal 且不处理 pygame.QUIT」的缺陷，请确认现在如何。
2. ui/clock.py：节奏器有哪几种模式（real / fixed-step / immediate？以代码为准）、如何注入、file:line。
3. ui/render.py：渲染层职责边界——是否只渲染而不含规则/记账（file:line 证据）。
4. ui/theme.py：布局常量与资源路径如何管理、是否用 pathlib 相对包根（file:line）。历史上有 '../game_exercise/' 这类坏路径，请确认现状。
5. 非阻塞输入：人类输入如何实现 poll_input()、等待期间是否持续重绘并响应 QUIT（file:line）。
6. tests/test_purity.py：它如何守护「core/ 不 import pygame/numpy/scipy/torch」（file:line），断言的确切形式是什么。
7. tests/ 每个文件守护了什么行为？逐个给 file:line。这是「被测试锁定的行为清单」的核心，请务必完整。
8. tests/baseline/ 里有哪些复现脚本，分别复现哪个历史缺陷（file:line）。
9. pyproject.toml：依赖列表（锁定版本）、ruff 配置、pytest 配置（file:line）。
10. .github/workflows/ci.yml：CI 触发条件与实际执行的命令（file:line）。
11. src/ 资源规模：目录清单与大致文件数（用 ls 统计），资源路径如何被代码引用（给出 ui/ 或 root 里引用 src/ 的 file:line）。
12. 一致性核对：README.md 里关于分层约束、依赖方向的声明，逐条与代码事实比对，指出任何**不一致**（给双方行号）。这是本次调查的重点之一。

严格约束：
- 只读。你只有 read/grep/find/ls 工具，禁止写任何文件。
- 每一条结论必须给 `文件路径:行号` 证据。无法确认的明确写 UNKNOWN，不要推测。
- 不要把 README 的自述当作事实，一切以代码为准；发现 README 与代码冲突时明确指出。

输出格式：
## 调查目标
## 涉及文件（含行数）
## 关键代码位置（file:line + 该处代码在做什么）
## 调用关系（谁调用谁）
## 被测试锁定的行为清单（测试文件 → 守护的约束 → file:line）
## 发现的问题（含 README 与代码的不一致项）
## 结论与建议（重构风险点：改这里会牵连什么）
## UNKNOWN 清单
    - 授权：工具 read, grep, find, ls；路径 ./ui, ./tests, ./pyproject.toml, ./README.md；额度 30000 tokens
        - Run R-148f4a06-7cfa-432c-81c0-17ccca18db30：FAILED；reader；模型 vllm-local/Qwen3.8-27B；1638055 tokens

## architecture-knowledge-base：续做 game_rendering 架构知识库（首次委派因 reader timeoutMs=900000 超时全部失败，但范围 A/B 的报告已从会话留存中回收，证据完整可用）。本轮：派发 2 个 reader 分别补齐「ui/ 表现层」与「tests/+CI/pyproject 质量守护」两块缺口（切分更小、超时已提高到 2700000ms）；随后派发 1 个 worker 把 A/B/C1/C2 四份报告汇总成 docs/ARCHITECTURE.md（8 章节）；最后派发 1 个 reviewer 逐条核对证据与冲突。Main Agent 只做调度与编排，不亲自读代码、不亲自写文档正文。

- 状态：已验收；已验收
- 预算：1800000 tokens；授权路径 .

- Delegation G-a88f315c-6c68-4198-8275-09b455c7dc4e：reader
    - 目标：【调查范围 C1：表现层 ui/】只读调查 game_rendering 仓库的表现层，产出带 file:line 证据的结构化报告，供 Main Agent 汇总进 docs/ARCHITECTURE.md。

你负责且仅负责 ui/ 目录（app.py, clock.py, render.py, theme.py, __init__.py）。不要碰 core/ agents/ scripts/ tests/（别人负责）。const.py 只在需要确认资源路径常量时读取。

必须回答的问题：
1. ui/app.py 主循环结构（file:line）：App.run() 在哪一行、循环体是什么、是否无 sleep。
2. ui/app.py 事件泵 pump_events()：pygame.event.get() 在哪一行、pygame.QUIT 如何处理（file:line）、KEYDOWN/MOUSEBUTTONDOWN 分派到哪里、pygame 未初始化时的行为（file:line）。
3. ui/app.py 状态机 Controller.update()：状态如何推进（file:line）、AI 回合的等待是如何表达的（是忙等还是提前 return）、人类回合如何交还控制权（file:line）。
4. ui/clock.py：节奏器有哪几种模式（以代码为准，可能是 real/fixed-step/immediate 之类）、类名与关键方法（file:line）、如何被注入使用。
5. ui/render.py：渲染层的职责边界——它是否只做绘制而不含规则/记账（给 file:line 证据说明它从哪里取状态、是否自己算胜负）。
6. ui/theme.py：持有哪些布局常量与资源路径映射（file:line）、资源路径是否用 pathlib 相对包根解析、是否存在 '../game_exercise/' 这类相对父目录的坏路径（用 grep 确认）。
7. 非阻塞输入：人类输入如何实现（是否 poll_input 之类）、等待期间是否持续重绘并响应 QUIT（file:line）。
8. ui/ 的依赖：ui/ import 了哪些内部模块与第三方库（给出 import 清单与行号）。ui/ 是否依赖 agents/ 或 core/（file:line）。
9. ui/__init__.py 导出了什么（file:line）。
10. app.py 里是否还残留 time.sleep / threading.Timer / 忙等 while 循环（用 grep 全目录确认，给出行号）。

严格约束：
- 只读。你只有 read/grep/find/ls 工具，禁止写任何文件。
- 每一条结论必须给 `文件路径:行号` 证据。无法确认的明确写 UNKNOWN，不要推测。
- 不要把 README 的自述当作事实，一切以代码为准。
- 报告控制在 6000 字以内，优先给 file:line 证据，文字说明从简。

输出格式：
## 调查目标
## 涉及文件（含行数）
## 关键代码位置（file:line + 该处代码在做什么）
## 调用关系（谁调用谁）
## 发现的问题
## 结论与建议（重构风险点）
## UNKNOWN 清单
    - 授权：工具 read, grep, find, ls；路径 ./ui；额度 30000 tokens
        - Run R-c57e84c3-c2a9-4f49-872b-7aaf754dfe91：SUCCEEDED；reader；模型 vllm-local/Qwen3.8-27B；66157 tokens
- Delegation G-1c678f99-910c-45ee-a092-afa9eea4b988：reader
    - 目标：【调查范围 C2：测试体系与质量守护】只读调查 game_rendering 仓库的测试与 CI，产出带 file:line 证据的结构化报告，供 Main Agent 汇总进 docs/ARCHITECTURE.md。

你负责且仅负责：
- tests/ 全部文件（含 tests/baseline/ 子目录）
- pyproject.toml
- .github/workflows/ci.yml
- README.md（只为核对「文档声明 vs 代码事实」是否一致；README 自述不算事实证据）
- src/ 只需 ls 确认资源目录结构与规模，不要逐个打开二进制资源

不要碰 core/ agents/ ui/ scripts/（别人负责）。

必须回答的问题：
1. **被测试锁定的行为清单**（本次最重要的交付）：逐个测试文件说明它守护什么行为、断言的确切形式，给 file:line。
   - tests/test_rules.py（D1/D2/D4 规则）
   - tests/test_dealing.py（D6 发牌）
   - tests/test_ui.py（时序/一致性/贴图/性能）
   - tests/test_strength.py（精确强度表）
   - tests/test_evaluator.py（牌型判定）
   - tests/test_agents.py（D8/D9/智能体契约）
   - tests/test_scripts.py（训练/评估入口）
   - tests/test_purity.py（分层纯度）
2. tests/test_purity.py 如何守护「core/ 不 import pygame/numpy/scipy/torch」：断言的确切形式是什么（file:line）、它如何扫描 core/ 文件。
3. tests/baseline/ 里每个复现脚本分别复现哪个历史缺陷（文件名 + file:line），它们是如何被调用的。
4. tests/test_ui.py 里的时序契约断言：QUIT 在等待期间是否被断言、headless 单步耗时上限、零 sleep 断言——分别在哪些行（file:line）。
5. tests/test_agents.py 的 D8/D9 断言：权重维度自适应与「真正加载已训练权重」如何被验证（file:line）。
6. tests/test_scripts.py 的可复现性断言：同种子两次运行如何比较、断言在哪（file:line）。
7. pyproject.toml：依赖列表与锁定版本、ruff 配置、pytest 配置（file:line）。
8. .github/workflows/ci.yml：触发条件、实际执行的命令、是否含 matrix（file:line）。
9. src/ 资源规模：目录清单与文件数（ls 统计即可），资源路径如何被代码引用（给引用 src/ 的 file:line；可以只读 ui/theme.py 或 const.py 来确认）。
10. **README 一致性核对（重点）**：README.md 中关于分层约束、依赖方向、测试守护的每一条声明，逐条与代码/测试事实比对，明确指出任何**不一致**（给出 README 行号与代码侧行号双方证据）。同时确认 README 提到的文件是否都存在。

严格约束：
- 只读。你只有 read/grep/find/ls 工具，禁止写任何文件。
- 每一条结论必须给 `文件路径:行号` 证据。无法确认的明确写 UNKNOWN，不要推测。
- 不要把 README 的自述当作事实，一切以代码为准。
- 报告控制在 7000 字以内，优先给 file:line 证据，文字说明从简。

输出格式：
## 调查目标
## 涉及文件（含行数）
## 被测试锁定的行为清单（测试文件 → 守护的约束 → file:line）
## 关键代码位置（file:line + 该处代码在做什么）
## README 与代码的一致性核对（逐条结论 + 双方行号）
## 发现的问题
## 结论与建议（重构风险点）
## UNKNOWN 清单
    - 授权：工具 read, grep, find, ls；路径 ./tests, ./pyproject.toml, ./README.md；额度 30000 tokens
        - Run R-59b098c2-921a-4e06-bdd1-c027f6bae2a1：SUCCEEDED；reader；模型 vllm-local/Qwen3.8-27B；1308222 tokens
- Delegation G-a26daaac-b26c-4c8b-ac58-2afb2d2de2cd：reader
    - 目标：【调查范围 C1：表现层 ui/】只读调查 game_rendering 的表现层 ui/，产出带 file:line 证据的精简报告，供 Main Agent 汇总进 docs/ARCHITECTURE.md。

工作目录：/home/kipley/Documents/code/learning/game_rendering
负责且仅负责 ui/ 目录：app.py, clock.py, render.py, theme.py, __init__.py。必要时可读 const.py 确认资源路径常量。不要碰 core/ agents/ scripts/ tests/。

**重要输出约束**：报告总长不超过 4500 字。直接给结论和 file:line，不要长篇推理、不要复述代码内容，每个问题 2-4 行即可。请先完成全部调查再一次性输出最终报告。

必须回答（每条都要 file:line）：
1. ui/app.py：App.run() 主循环在哪一行、循环体结构、是否无 sleep。
2. ui/app.py：pump_events() 中 pygame.event.get() 与 pygame.QUIT 处理（file:line）。
3. ui/app.py：Controller.update() 状态推进；AI 回合等待是忙等还是提前 return（file:line）；人类回合如何交还控制权。
4. ui/clock.py：节奏器模式名称（以代码为准）、类名与关键方法（file:line）。
5. ui/render.py：是否只绘制不记账——它从哪取状态、是否自己算胜负（file:line）。
6. ui/theme.py：布局常量与资源路径映射（file:line）；是否有 '../' 坏路径（grep 确认）。
7. 非阻塞输入：人类输入如何实现、等待期间是否持续重绘并响应 QUIT（file:line）。
8. ui/ 的 import 清单（内部模块 + 第三方，给行号）；ui/ 是否依赖 core/ 或 agents/。
9. ui/__init__.py 导出什么（file:line）。
10. grep 确认 ui/ 是否残留 time.sleep / threading.Timer / 忙等 while（给出行号；没有就写"无"）。

严格约束：
- 只读。你只有 read/grep/find/ls 工具，禁止写任何文件。
- 每条结论必须给 `文件路径:行号`；无法确认写 UNKNOWN。
- 不要把 README 自述当事实，一切以代码为准。

输出格式（严格照此，不要加前言）：
## 调查目标
## 涉及文件（含行数）
## 关键代码位置（file:line + 该处做什么）
## 调用关系
## 发现的问题
## 结论与建议
## UNKNOWN 清单
    - 授权：工具 read, grep, find, ls；路径 ./ui；额度 30000 tokens
        - Run R-6277d607-f2cc-4fb1-990f-b740b4fb6c2d：SUCCEEDED；reader；模型 vllm-local/Qwen3.8-27B；363778 tokens
- Delegation G-14dbf053-c4e8-47cb-be02-f33b67a543d3：reader
    - 目标：【调查范围 C2b：README 一致性核对 + 构建配置 + 资源规模】只读调查 game_rendering 的三件事，产出精简报告供 Main Agent 汇总进 docs/ARCHITECTURE.md。

工作目录：/home/kipley/Documents/code/learning/game_rendering

负责且仅负责：
1. **README.md 与代码事实的一致性核对**（本次最重要的交付）
2. pyproject.toml 的依赖与工具配置
3. .github/workflows/ci.yml 的 CI 实际行为
4. src/ 资源目录的结构与规模（只 ls，不打开二进制）

不要重新调查 tests/ 各测试文件守护了什么行为（已完成），不要碰 core/ agents/ ui/ scripts/。

**重要输出约束**：报告总长不超过 3500 字。先完成全部调查再一次性输出最终报告。不要长篇推理，每个问题给结论 + file:line 即可。

必须回答：
A. README.md 逐条声明核对：把 README 里关于「分层约束」「依赖方向」「测试守护」「架构图」「运行方式」「清理历史脚本」的每一条声明列出来，逐条标注 [一致] 或 [不一致]，不一致的给出 README 行号 + 代码侧证据行号。已知需重点核对：README 声称 core/ 不 import pygame/numpy/scipy/torch（由 tests/test_purity.py 守护）；README 的架构图声称依赖方向为 ui → core/agents、scripts → core/agents；README 声称只保留一种策略实现（draw_me_vs_DQN_Plus.py + mymath/robot2.py）。
B. **特别核对**：README 与 management/legacy/project/r5/contract.json 声称保留 mymath/robot2.py，但另一份调查（范围 B）报告说 mymath/ 下**没有** robot2.py，agents/robot.py 才是 robot2 迁入后的实现。请直接 ls mymath/ 并读 mymath/ 内容，给出确定结论与 file:line。这条必须回答且要给出证据。
C. pyproject.toml：依赖列表与版本锁定、ruff 配置项、pytest 配置项（每项给 file:line）。
D. .github/workflows/ci.yml：触发条件、实际执行的命令序列、是否有 matrix（给 file:line）。
E. src/ 资源规模：顶层子目录清单、各自大致文件数（ls 统计）、总大小量级；资源路径如何被代码引用（给引用 src/ 的 file:line）。
F. tests/baseline/ 里剩余的 repro_d7_timing.py 复现的是哪个历史缺陷（给 file:line）。

严格约束：
- 只读。你只有 read/grep/find/ls 工具，禁止写任何文件。
- 每条结论必须给 `文件路径:行号`；无法确认写 UNKNOWN。
- 不要把 README 的自述当作事实，一切以代码为准。

输出格式（严格照此，不要加前言）：
## README 一致性核对（逐条 + 双方行号）
## pyproject.toml 配置
## CI 行为
## src/ 资源规模
## repro_d7 复现的缺陷
## 发现的问题
## 结论与建议
## UNKNOWN 清单
    - 授权：工具 read, grep, find, ls；路径 ./README.md, ./pyproject.toml, ./src, ./mymath；额度 30000 tokens
        - Run R-e756980e-4a01-45c5-bd73-01681cdce55a：SUCCEEDED；reader；模型 vllm-local/Qwen3.8-27B；392507 tokens
- Delegation G-e00d0375-4b2b-4dd6-8d1d-a92aecc9fd4c：worker
    - 目标：把 5 份只读调查报告汇总成仓库的架构知识库文档 docs/ARCHITECTURE.md。

**你的工作目录（worktree）**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/architecture-knowledge-base
所有读写都在这个 worktree 里进行。不要去改主工作树。

**输入材料**（都在 worktree 的 management/evidence/ 下，全部已提交，可直接读）：
- report-A-domain-core.md —— core/ 领域层 + algorithm.py + const.py（233 处 file:line）
- report-B-agents-scripts.md —— agents/ + scripts/ + draw_me_vs_DQN_Plus.py（31 处 file:line）
- report-C1-ui.md —— ui/ 表现层（51 处 file:line）
- report-C2-tests-quality.md —— tests/ 全量「被测试锁定的行为清单」（这是最重要的一份，完整保留）
- report-C2b-readme-consistency.md —— README 逐条一致性核对、pyproject、CI、src 资源规模
- report-C-partial-ui-tests.md —— 早期被截断的 ui 报告，仅作参考，不要优先采信

**你要产出的唯一文件**：docs/ARCHITECTURE.md（新建）

**硬约束**：
1. 只允许新建 docs/ARCHITECTURE.md 这一个文件。**禁止修改任何其它文件**（包括 management/、README.md、代码、tests/）。不要改 README 的错——把不一致写进文档的「发现的问题」一节即可。
2. 所有事实性结论必须带 `文件路径:行号` 证据，直接取自上述报告，不要自己重新推导、不要编造行号。
3. 报告说 UNKNOWN 的地方，文档里就写 UNKNOWN，不要用 README 的自述补齐。
4. 不得引入报告中没有的新结论。

**文档结构（严格按这 8 节，标题用下面给的中文）**：
1. `## 1. 概览` —— 项目是什么、生成时的 commit（用 `git rev-parse HEAD`）、证据来源清单（5 份报告各自覆盖什么）、如何使用本文档
2. `## 2. 分层结构与依赖方向` —— 四层职责 + 严格单向依赖图（用 ASCII 文字图）+ 「不得依赖」清单（core/ 不 import pygame/numpy/scipy/torch；agents/ scripts/ 不 import pygame）+ README 架构图箭头方向有误的提示
3. `## 3. 模块职责表` —— 逐模块表格：路径 | 行数 | 职责 | 关键公开符号 | file:line
4. `## 4. 关键调用链` —— 交互入口 → ui/app → core.GameRoom → agents 的完整链路，以及训练链路 scripts/train.py → scripts/env.py → core/agents。每条链给出 file:line
5. `## 5. 数据流与状态管理` —— 权威状态在哪（core.GameRoom.snapshot()）、UI 如何只读消费、状态机推进方式、AI 回合与人类回合的 deadline 表达
6. `## 6. 被测试锁定的行为清单` —— 以表格逐条列出：测试文件 | 守护的约束 | file:line。这是文档最重要的一节，必须完整覆盖 report-C2-tests-quality.md 的全部条目
7. `## 7. 重构风险点` —— 改哪里会牵连什么，每条带 file:line 证据。必须包含：核心状态契约（GameRoom.snapshot 与 UI view 的逐字段相等）、D1-D9 历史缺陷已被哪些测试钉住、精确强度表的建表时机、权重维度自适应、D6 默认均匀发牌与 draw_strength_biased() 开关、README 与代码的 2 处不一致
8. `## 8. 遗留疑点与未核实项` —— 汇总所有报告的 UNKNOWN，另加一节 `### README 与代码的不一致` 列出已知 2 处（"6 行"实为 14 行；架构图箭头方向与文字相反），以及 mymath/robot2.py 已迁入 agents/robot.py 的历史说明

**完成后**：
- 用 `git add docs/ARCHITECTURE.md && git commit -m "docs: 新增架构知识库 docs/ARCHITECTURE.md"` 提交。
- 最终回复给出：文件路径、总行数、8 个章节各自的行数、file:line 证据条数、你实际写入的 git commit hash、以及你为遵守「只改一个文件」所做的确认（贴 git status 输出）。

**注意输出长度**：文档本身可以长（写进文件，不受输出限制），但你的**最终回复**控制在 800 字以内。若单次写不完，分多次 edit 追加，但每段都要写进文件。
    - 授权：工具 read, grep, find, ls, edit, write, bash；路径 ./docs, ./management/evidence；额度 120000 tokens
        - Run R-d54bff1a-f47b-4a96-834c-e80648fe70c1：SUCCEEDED；worker；模型 vllm-local/Qwen3.8-27B；1022624 tokens
- Delegation G-41ba4180-9ac2-4944-815a-36187cf228ab：reviewer
    - 目标：独立审核 docs/ARCHITECTURE.md 的证据准确性与完整性。你是审核者，不修改任何文件。

**待审文件**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/architecture-knowledge-base/docs/ARCHITECTURE.md（422 行，8 个章节，412 处 file:line 引用）

**参考材料**（原始调查报告，用来核对文档有没有曲解原意）：
- /home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/architecture-knowledge-base/management/evidence/report-A-domain-core.md
- .../management/evidence/report-B-agents-scripts.md
- .../management/evidence/report-C1-ui.md
- .../management/evidence/report-C2-tests-quality.md
- .../management/evidence/report-C2b-readme-consistency.md

**你要做的四件事**：

1. **抽样核验行号真实性（最重要）**：从文档中随机抽 **20 条** file:line 引用（尽量覆盖 6 个章节、不同文件）。对每一条，用 read/grep 打开被引用的文件对应行号，核对那一行的代码内容是否真的支持文档给出的结论。
   - 输出表格：文档位置 | 引用 | 该行实际内容 | 命中(✓)/不命中(✗)/无法确认
   - 命中率必须 ≥ 90%（即 ≤ 2 条不命中）
   - 若发现行号错位（内容对但行号偏了 N 行），单独列出并给出正确行号

2. **与 tests/ 实际断言比对**：文档第 6 节声称的「被测试锁定的行为清单」共 158 行。抽查 **10 个测试文件**里的断言，确认文档描述的守护内容与测试里真实的 assert 一致（不是复述测试文件名的想当然）。重点检查 tests/test_purity.py、tests/test_agents.py、tests/test_ui.py、tests/test_scripts.py、tests/test_rules.py。

3. **与 README/代码冲突排查**：文档第 8 节列出了 README 的 2 处不一致（「6 行」实为 14 行、架构图箭头方向与文字相反）。请独立复核这两处是否成立（给 README 行号 + 代码/文件证据），并检查文档里**自己**是否又引入了与代码矛盾的陈述。

4. **UNKNOWN 完整性**：文档标了 17 处 UNKNOWN。确认这些确实是报告里无法确认的项，而不是该确认却偷懒标记；并确认文档**没有**用 README 的自述去补齐报告里标 UNKNOWN 的事实。

**严格约束**：
- 只读。你只有 read/grep/find/ls 工具，**禁止写任何文件**（包括不要去修 README 或文档）。
- 不修改 docs/ARCHITECTURE.md。你的职责是报告问题，不是修问题。
- 每条结论必须给 `文件路径:行号` 证据。
- 不要重复报告原文已知的截断问题（A/B/C2 报告尾部截断已被 worker 标注）。

**输出格式**（严格照此）：
## 核验结论（通过 / 有条件通过 / 不通过）+ 一句话理由
## 抽样行号核验表（20 条）
## 行号错位清单
## tests/ 断言比对结果（10 个文件）
## README/代码冲突复核
## UNKNOWN 完整性评估
## 发现的具体问题（按严重度排序：阻断 / 需修正 / 建议）
## 总体结论（通过 / 不通过 / 证据不足）

最终回复控制在 1200 字以内，但核验表格可以紧凑呈现。
    - 授权：工具 read, grep, find, ls；路径 ./docs, ./tests, ./management/evidence, ./README.md；额度 60000 tokens
        - Run R-7d6a65d2-d66a-43cc-bfee-67c85cd0416a：FAILED；reviewer；模型 vllm-local/Qwen3.8-27B；739599 tokens
- Delegation G-db4c5db9-c402-4879-b6da-cf1ed85bc1b6：reviewer
    - 目标：审核任务 R1：抽样核验 docs/ARCHITECTURE.md 中 file:line 引用是否指向真实且支持结论的代码行。你是审核者，只读，禁止写任何文件。

**待审文件**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/architecture-knowledge-base/docs/ARCHITECTURE.md（422 行）

**只做一件事**：从该文档中抽 **20 条** file:line 引用（尽量覆盖 8 个章节、不同文件），逐条用 read 或 grep 打开被引用的文件对应行号，核对那一行的实际内容是否支持文档给出的结论。

**效率要求（重要）**：用 grep -n 一次定位多处，不要逐个 read 整个大文件。最多 25 次工具调用就要给出结论。请先全部核验完成，再一次性输出最终报告（不要边核验边输出）。

**判定口径**：
- 命中 ✓：该行代码内容确实支持文档结论
- 行号错位 ±N：内容正确但行号偏了 N 行 → 单独列出并给出正确行号
- 不命中 ✗：该行内容与文档结论无关或矛盾
- 无法确认：该文件不可读/该行不存在

**输出格式**（严格照此，不要加前言）：
## 核验结论（通过 / 有条件通过 / 不通过）+ 一句话理由
## 抽样核验表
| # | 文档位置 | 引用 | 该行实际内容摘要 | 判定 |
（20 行，紧凑写，每行 ≤ 60 字）
## 行号错位清单
## 不命中清单
## 总体结论（通过 / 不通过 / 证据不足）

最终回复控制在 900 字以内。
    - 授权：工具 read, grep, find, ls；路径 ./docs；额度 60000 tokens
        - Run R-c0feb4e1-6de9-4e0f-8add-196900d2a697：SUCCEEDED；reviewer；模型 vllm-local/Qwen3.8-27B；131240 tokens
- Delegation G-bc2f0aa1-1c9c-4f7c-bef7-e6e85e131de0：reviewer
    - 目标：审核任务 R2：核对 docs/ARCHITECTURE.md 第 6 节「被测试锁定的行为清单」与 tests/ 真实断言是否一致，并复核文档自述的 README 不一致项。你是审核者，只读，禁止写任何文件。

**待审文件**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/architecture-knowledge-base/docs/ARCHITECTURE.md 第 6 节（约 166-323 行）与第 8 节（约 386-422 行）
**被审对象**：同 worktree 下的 tests/ 目录与 README.md

**要做两件事**：

1. **tests/ 断言比对（重点）**：文档第 6 节有 158 行声称的「被测试锁定的行为清单」。抽 **8 个测试文件**，逐个核对文档描述与测试里真实的 assert 是否一致：
   - tests/test_purity.py —— 「core/ 不 import pygame/numpy/scipy/torch」的守护形式
   - tests/test_agents.py —— D8 维度自适应、D9 真正加载权重的断言
   - tests/test_ui.py —— 零 sleep、QUIT 响应、view 与 snapshot 相等、性能上限
   - tests/test_scripts.py —— 同种子可复现性断言
   - tests/test_rules.py —— D1/D2/D4 断言
   - tests/test_dealing.py —— D6 均匀发牌断言
   - tests/test_strength.py —— 22100 精确表断言
   - tests/test_evaluator.py —— 六类牌型断言
   对每个文件给出：文档声称守护了什么 | 真实 assert 在哪一行 | 一致(✓)/描述有偏差(△)/矛盾(✗) | 若为 △ 或 ✗ 给出真实断言内容摘要。
   并说明：文档第 6 节相对测试里的 assert 是否有整类遗漏。

2. **README 不一致复核**：文档第 8 节声称 README 有 2 处不一致：
   - (a) README 说入口文件「6 行」，实际是 14 行
   - (b) README 架构图的箭头方向（core/agents → scripts）与文字和代码实际方向相反
   请独立验证这两条是否成立，给出 README.md 行号 + 代码侧证据行号。并顺带抽 5 条文档中的技术陈述核对是否与代码矛盾。

**效率要求（重要）**：用 grep -n 批量定位，不要逐个 read 大文件。最多 30 次工具调用给出结论。先全部核验完成再一次性输出最终报告。

**严格约束**：只读，禁止写任何文件（包括不要去修 README 或文档）。每条结论给 `文件路径:行号` 证据。

**输出格式**（严格照此，不要加前言）：
## 核验结论（通过 / 有条件通过 / 不通过）+ 一句话理由
## tests/ 断言比对
| 测试文件 | 文档声称 | 真实 assert 行号 | 判定 | 偏差摘要 |
（8 行）
## 第 6 节遗漏项检查
## README 不一致复核（a）(b) 两条各给双方行号）
## 文档自身陈述抽查（5 条）
## 发现的具体问题（按 阻断 / 需修正 / 建议 分级）
## 总体结论（通过 / 不通过 / 证据不足）

最终回复控制在 1100 字以内。
    - 授权：工具 read, grep, find, ls；路径 ./docs, ./tests, ./README.md；额度 60000 tokens
        - Run R-31dae8ab-8645-4f6d-a1da-7c179c9222aa：SUCCEEDED；reviewer；模型 vllm-local/Qwen3.8-27B；220910 tokens
- Delegation G-3d3d0aa0-483c-4b50-ac1e-69553fe8d506：worker
    - 目标：按两份审核报告的结论，修正 docs/ARCHITECTURE.md 的 1 处措辞问题、补充 1 条新发现、并校准若干行号边界。

**你的工作目录（worktree）**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/architecture-knowledge-base
所有读写都在这个 worktree 内进行。

**唯一允许修改的文件**：docs/ARCHITECTURE.md。禁止修改任何其它文件。

**审核报告**（worktree 内 management/evidence/）：
- review-R1-line-sampling.md —— 抽样 20 条行号核验，结论：通过（19 精确命中 + 1 范围偏 1 行，命中率 95%）
- review-R2-tests-readme.md —— tests 断言比对，结论：有条件通过（1 需修正 + 3 建议）

**要做的三件事**：

1. **需修正（必做）**：第 6.3 节中「合法动作仅在人类回合非空」措辞偏强。tests/test_ui.py:147-148 只断言了人类回合合法动作非空，**没有**断言 AI 回合为空。改为「人类回合合法动作非空（未断言 AI 回合为空）」这类准确表述，并在该行后补一句注明测试的实际断言范围与 file:line。

2. **建议①（必做，新增一条发现）**：README 关于「ui/、scripts/ 无 time.sleep」的声明存在 overclaim —— 守护它的 tests/test_ui.py:63-65 **只扫 ui/**，并未覆盖 scripts/（scripts/ 无 sleep 目前靠 grep 而非测试守护）。请在第 8 节「README 与代码的不一致」里新增这一条，标明：README 声明范围（README.md:63）与测试实际守护范围（tests/test_ui.py:63-65）不符。

3. **行号边界校准（逐条核对后再改）**：两份报告共指出以下行号边界偏差。**每一条都要先打开对应文件确认正确值再改**，不要盲改；确认后发现原引用其实正确的，保持不动。
   - pyproject.toml:15-19 → 报告称应为 14-18
   - rules.py:160-170 → 报告称应为 161-170
   - rules.py:162（费用行）→ 报告称应为 163
   - tests/test_purity.py:15-16 → 14-15；:19-25 → 18-24；:28-52 → 起于 26
   - core/__init__.py:16-30（__all__）→ 16-31
   - tests/test_agents.py:100-105 → 100-106
   - tests/test_dealing.py:69-74 → 69-75
   在第 8 节末尾或第 7 节末尾新增一小段「行号校准说明」，记录这些偏差已修正，并说明校准方式（reviewer 抽样核验）。不要为了改而改——内容正确但行号偏 1 行的，若确认后能定位到更准确的行号就改。

**完成后**：
- `git add docs/ARCHITECTURE.md && git commit -m "docs: 按审核结论修正 ARCHITECTURE.md 的措辞与行号边界"` 提交
- 最终回复给出：修改了哪几处（逐条：位置 | 原内容 | 新内容 | 依据 file:line）、最终文件行数、file:line 引用总数、git commit hash、git status 输出（确认只动了 docs/ARCHITECTURE.md）

**输出长度**：最终回复控制在 700 字以内。文档本体可以长，写进文件不受限。
    - 授权：工具 read, grep, find, ls, edit, write, bash；路径 ./docs, ./management/evidence；额度 120000 tokens
        - Run R-3b7f69cb-4da6-43f2-b1ea-2741e27f651f：SUCCEEDED；worker；模型 vllm-local/Qwen3.8-27B；342303 tokens

## dqn-vs-dqn-investigation：为「重构 + 人类 vs 机器 + DQN 对抗 DQN」做只读调研，产出可直接写入基线 PRD 的结论：(1) 训练侧 scripts/train.py 与 scripts/env.py 当前如何选对手、用什么状态/动作空间，能否改成 DQN-vs-DQN 自博弈；(2) 交互侧 ui/app.py 如何加载并推理机器对手（epsilon、状态编码、动作映射、checkpoint 缺失回退），换成自博弈权重要动哪些点；(3) 仓库现有 .pth 权重清单与各自维度；(4) 按 docs/ARCHITECTURE.md 第 7.7 节梳理 10 个小问题的可执行重构清单，并按第 7.1-7.6 节标出哪些是高风险不可碰。Main Agent 只做调度与编排。

- 状态：已批准；未验收
- 预算：90000 tokens；授权路径 agents, scripts, ui, core, tests, docs, README.md, CHANGELOG.md, pyproject.toml

- Delegation G-68b33d7d-8691-49e8-80f1-29e62fd62eef：reader
    - 目标：【调研 D：训练侧 —— DQN-vs-DQN 自博弈可行性】只读调查 game_rendering 的训练侧，产出带 file:line 证据的结论。你只读，禁止写文件。

工作目录：/home/kipley/Documents/code/learning/game_rendering
负责且仅负责：scripts/train.py、scripts/env.py、scripts/evaluate.py、agents/dqn.py、agents/base.py。不要深入 ui/（别人负责）。

必须回答：
1. **scripts/env.py 的环境封装**：CardGameEnv 暴露什么（状态空间维度、动作空间、step 返回值、done 语义），对手是谁（内置 Robot？随机？）——给出 file:line。这决定了训练时"对手"从哪来。
2. **scripts/train.py 的训练循环**：对手策略是怎么选出来的（是否用 agents/robot.py 的 Robot、是否有 epsilon-greedy 的对手）、状态如何编码（StateEncoder？4 维？）、奖励如何计算、回合如何结束、checkpoint 怎么存（文件名规则）、产物目录（file:line）。
3. **agents/dqn.py 的网络与超参**：input_dim / action_dim 如何确定、超参（学习率/批量/目标网络更新/探索率与衰减）、DQN 类公开接口（act/observe/replay/save/load 签名，file:line）。
4. **DQN-vs-DQN 自博弈的可行性分析（核心）**：
   a. 现在的状态空间是「相对某一方」的 4 维表示吗？两个 DQN 能否共用同一个状态编码与动作空间（对称性）？给出证据（file:line）。
   b. 若两个智能体共用一张牌桌，每个智能体的观察是否只含「自己的手牌 + 公共信息」？有没有信息泄漏（对手真手牌是否进了状态）？给出 file:line。
   c. 训练时的对手若也用 DQN，需要哪些改动：对手实例如何创建/加载/更新（在线学习 vs 固定快照）、探索策略如何处理、如何避免两个 agent 互相退化（self-play collapse）。
   d. 结论：给出**最小可行改造方案**——要改哪几个文件、哪几个函数、新增什么函数，附 file:line。
5. **权重文件清单**：用 ls 找出仓库里所有 *.pth（及 *.pt）文件，给出路径与文件大小；对每个用 python3 一行命令读出 checkpoint 的 input_dim/action_dim（fc1.weight.shape 与 fc3.weight.shape），给出一张表。注意：只读不改，不要移动或删除任何文件。python3 命令要写成 `python3 -c "import torch; ..."`。
6. **训练成本**：训练一轮（多少回合）大概多久？scripts/train.py 有没有回合数/种子参数（file:line）？仓库里有没有现成的训练产物目录（run/）？给出 file:line。
7. **如果要产出「DQN 对抗 DQN」训练出来的权重，现有代码能直接支持吗？** 明确指出缺什么（缺什么就说缺什么，不要脑补）。

**输出约束**：报告 ≤ 6000 字。先完成全部调查再一次性输出最终报告。每条结论必须给 `文件路径:行号`；无法确认写 UNKNOWN。

**输出格式**：
## 调查目标
## 涉及文件（含行数）
## 关键代码位置（file:line + 该处做什么）
## 当前训练流程（对手选择 / 状态编码 / 奖励 / 回合结束 / checkpoint）
## 权重文件清单与维度表
## DQN-vs-DQN 自博弈可行性分析（a 对称性 / b 信息泄漏 / c 所需改动 / d 最小可行方案）
## 训练成本
## 发现的问题
## UNKNOWN 清单
    - 授权：工具 read, grep, find, ls；路径 ./agents, ./scripts；额度 30000 tokens
        - Run R-a76db659-51d1-48f0-a73b-f57628a4d889：SUCCEEDED；reader；模型 vllm-local/Qwen3.8-27B；647753 tokens
- Delegation G-20128c9b-2e26-45aa-8c78-588a28520ef4：reader
    - 目标：【调研 E：交互侧 —— 机器对手接线与替换点】只读调查 game_rendering 的交互侧，产出带 file:line 证据的结论。你只读，禁止写文件。

工作目录：/home/kipley/Documents/code/learning/game_rendering
负责且仅负责：ui/app.py、ui/render.py、ui/theme.py、draw_me_vs_DQN_Plus.py、const.py、algorithm.py。不要深入 core/ agents/ scripts/（别人负责）。

必须回答：
1. **交互入口**：draw_me_vs_DQN_Plus.py 全文逻辑（file:line），它如何调起 ui.app.main。
2. **机器对手在 ui/app.py 里如何接线**：
   - 默认 checkpoint 是什么（DEFAULT_CHECKPOINT，file:line）、在哪里加载（from_checkpoint 调用点）
   - 加载失败时的回退行为是什么（file:line，app.py:25、57-62 附近）
   - 机器推理在哪个函数（_ai_move？file:line）、每回合如何构造状态、epsilon 是多少
   - 机器的动作输出如何映射到 core.GameRoom 的 Action（file:line）
3. **状态编码一致性**：ui/app.py 构造的状态与 scripts/env.py、agents/dqn.py 训练时用的状态编码是同一套吗？给出双方 file:line，并明确结论（一致 / 不一致 / 无法确认）。这是把「自博弈 DQN 权重」接进交互界面的前提。
4. **机器对手当前策略**：交互界面里的机器到底是 DQN 还是别的？有没有用 agents/robot.py 的 Robot？给出 file:line 证据。
5. **换 checkpoint 需要改哪些点**：如果要把机器换成「DQN-vs-DQN 自博弈训练出来的权重」，ui/ 侧需要改哪些文件/哪些行/新增什么参数（例如把 checkpoint 路径做成可配置、启动时校验存在）。给出 file:line。
6. **ui/theme.py 资源自检**：missing_assets() 提供什么（file:line）、为什么 app.py 没用它（file:line）、改成用它需要动哪里。
7. **ui/app.py 的 4 个已知小问题**（请给出准确行号与最小改法）：
   - Action(key - pygame.K_1) 键码差值映射（app.py:212 附近）
   - _on_click 在 renderer=None 时 rects 为空 dict（app.py:222 附近）
   - last_now 是类级属性（app.py:141 附近）与 set_now 的风格不统一
   - view 恒含对手真手牌（app.py:156 附近）——信息泄漏如何被抑制（render.py:159-171、176-178）
8. **algorithm.py 的 RepeatedTimer**：现状（file:line）、是否还有调用点（grep 全仓）、加固后的语义（daemon / stop 幂等 / 异常隔离）在哪里。
9. **const.py**：持有什么常量（file:line），资源路径如何解析（ROOT/src 相对路径），是否有 pygame 依赖。

**输出约束**：报告 ≤ 5500 字。先完成全部调查再一次性输出最终报告。每条结论必须给 `文件路径:行号`；无法确认写 UNKNOWN。

**输出格式**：
## 调查目标
## 涉及文件（含行数）
## 关键代码位置（file:line + 该处做什么）
## 交互入口与机器对手接线
## 状态编码一致性核对（结论 + 双方行号）
## 换 checkpoint 的改动点清单
## ui/theme.py 资源自检
## 4 个已知小问题的准确行号与最小改法
## RepeatedTimer 现状与调用点
## const.py 与资源路径
## 发现的问题
## UNKNOWN 清单
    - 授权：工具 read, grep, find, ls；路径 ./ui, ./draw_me_vs_DQN_Plus.py, ./const.py, ./algorithm.py；额度 30000 tokens
        - Run R-30f786fa-07bc-45e5-8102-c936d9bc440d：SUCCEEDED；reader；模型 vllm-local/Qwen3.8-27B；508191 tokens
- Delegation G-54034708-3481-41b1-afb1-70a232892ef3：reader
    - 目标：【调研 F：重构清单 —— 按架构知识库第 7 节梳理可执行改动】只读调查 game_rendering，产出带 file:line 证据的重构清单。你只读，禁止写文件。

工作目录：/home/kipley/Documents/code/learning/game_rendering
**先读** docs/ARCHITECTURE.md 的第 7 节（重构风险点）与第 8 节（遗留疑点），那是本次重构的依据。

必须回答：
1. **第 7.7 节 10 个小问题逐条落地**：对 7.7 节的每一条，给出：
   - 问题在代码里的**准确位置**（file:line，务必自行核对，不要照抄文档行号）
   - **最小改法**（具体到改哪几行、改成什么）
   - **会被打红的测试**（对应 tests/ 里哪个文件的哪个断言会失败；若无则写「无现有测试守护」）
   - **改动代价分级**：S(一行内) / M(一个函数内) / L(跨文件)
   7.7 的 10 条是：(1) Action(key - pygame.K_1) 键码映射；(2) 资源自检过粗、theme.missing_assets() 未被使用；(3) button_rects 返回注解不精确；(4) checkpoint 缺失启动回退未文档化；(5) view 恒含对手真手牌、信息克制依赖 render 阶段；(6) last_now 是类级属性；(7) _on_click 在 renderer=None 时 rects 为空；(8) core __all__ 白名单缺 strength_ordinal/strongest_hand/dealing 符号；(9) ui/theme.py 资源路径解析方式与 '../' 坏路径现状；(10) 其它你能在 7.7/8 节里找到的可动项。
2. **第 7.1-7.6 节的高风险项判定**：对 7.1（snapshot/view 状态契约）、7.2（D1-D9 回归测试钉死）、7.3（22100 精确表惰性建表）、7.4（from_checkpoint 维度自适应）、7.5（D6 均匀发牌与 deal_strength_biased 开关）、7.6（README 3 处不一致），各给出判定：
   - **可安全做**（有测试兜底 + 改动局部）/ **需测试先行**（要新增测试才能动）/ **不可碰**（动了必红核心测试）
   - 附对应的守护测试 file:line
3. **第 8 节遗留疑点**：第 8 节列出的 UNKNOWN 与未核实项，逐条判断是否值得在本次重构中查清、怎么查（给出具体的 grep/read 路径）。
4. **README 3 处不一致的修法**：给出 README.md 中需要改的确切行号与建议文案（架构图箭头方向怎么改、6 行改成什么、time.sleep 守护声明怎么改才不 overclaim）。
5. **重构可行性总评**：按 S/M/L 分级汇总本次可做的改动条数，指出哪些必须先补测试、哪些依赖 DQN-vs-DQN 的训练结果。

**输出约束**：报告 ≤ 6500 字。先完成全部调查再一次性输出最终报告。每条结论必须给 `文件路径:行号`（行号以你实际读到的代码为准）；无法确认写 UNKNOWN。

**输出格式**：
## 调查目标
## 涉及文件（含行数）
## 第 7.7 节 10 个小问题逐条清单（表格 + 详细条目）
## 第 7.1-7.6 节高风险项判定表
## 第 8 节遗留疑点处置建议
## README 3 处不一致的修法
## 重构可行性总评（S/M/L 计数 + 前置条件）
## UNKNOWN 清单
    - 授权：工具 read, grep, find, ls；路径 ./docs, ./core, ./agents, ./ui, ./scripts, ./tests, ./README.md, ./const.py, ./algorithm.py；额度 30000 tokens
        - Run R-f241bbd7-1559-42ee-b13e-23974b06e795：SUCCEEDED；reader；模型 vllm-local/Qwen3.8-27B；2118392 tokens

## selfplay-engine：实现 DQN 对抗 DQN（自博弈）训练机制：在 scripts/env.py 与 scripts/train.py 上让两个 DQN 互相对弈，产出可加载的策略文件。本 Task 只做机制与测试，不跑长训练（训练由下游独立 Task 执行）。Main Agent 只调度编排，编码全部由子 Agent 完成。

- 状态：已验收；已验收
- 预算：1800000 tokens；授权路径 scripts, tests

- Delegation G-bb2be362-f780-433a-9cc2-fd51f4485672：worker
    - 目标：【实现 DQN 对抗 DQN 自博弈训练机制】在 game_rendering 的 scripts/ 与 tests/ 上实现自博弈训练，产出可加载的策略文件机制。

**你的独立工作区（worktree）**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-engine
**在这个 worktree 里工作并提交**（分支 governance/selfplay-engine）。不要改主仓库目录。
授权范围：scripts/、tests/。**不要改 core/、agents/、ui/、README.md**。

## 背景（已由只读调研核实，可直接采信）
- `scripts/env.py:31-41` `CardGameEnv.__init__(seed, opponent: Robot|None, agent_player=0)`；`:38` 默认对手 `Robot("1", seed=seed)`；`:39` 持有 `StateEncoder`。
- `scripts/env.py:44-55` `reset()`：`:45-46` new_deck + 两次 deal_uniform；`:47` `GameRoom.new(hands)`（座位 0/1 顺序固定）；`:51-52` `opponent.reset()` + `opponent.init_dick(["1","0"], hands[opponent_seat])`（**Robot 专属协议**）；`:54` 若对手先手则代打至 agent 回合。
- `scripts/env.py:64-94` `step()`：`:69-70` room.apply；`:76-77` reward 0、done=room.finish；`:80-84` `_advance_opponent_until_agent_turn()`；`:85-86` 超 MAX_STEPS 强制 done；`:88-94` 返回 StepResult(observation, reward, done, legal_actions, info)。
- `scripts/env.py:97-100` `_observation()`：`StateEncoder.encode(snapshot, self.agent_player, room.own_hand(self.agent_player))` —— 仅自己视角。
- `scripts/env.py:102-106` `_settle_reward()`：赢 +room.all_bet，输 -玩家已押注（**非严格反对称**）。
- `scripts/env.py:108-118` `_advance_opponent_until_agent_turn()`：`:113` `_opponent_snapshot()`、`:114` `opponent.act(snapshot, legal)`、`:116` 应用、`:118` `_notify_opponent`。
- `scripts/env.py:120-124` `_opponent_snapshot()` 注入 "hand" 键（**Robot 专属 dict 协议**）；`:126-145` `_notify_opponent()` 用 json update_dick（**Robot 专属**）。
- `scripts/train.py:38-45` `train()`；`:53` `env = CardGameEnv(seed=seed)`；`:59-82` 训练循环；`:71` 每步一次 replay；`:85-96` summary（`:95` elapsed_sec）；`:100` checkpoint 命名；`:112-119` `main()` CLI（`:114` --episodes 默认 20、`:115` --seed、`:116` --device、`:117` --out）；`:27` 产物写入 `run/`。
- `agents/dqn.py:99-120` `DQNAgent(input_dim=4, action_dim=6, config=..., seed=...)`；`:124-145` `from_checkpoint`；`:153-162` `act(observation, legal_actions)`；`:191-192` epsilon 在 replay() 内衰减；`:197-198` update_target；`:200` reset()；`:204-212` save()/load()；`:209-212` load 会自动同步 target；`:45` target_sync_every=1；`:117` replay buffer 是独立 deque；`:29-32` DEFAULT_STATE_DIM=4 / DEFAULT_ACTION_DIM=6；`:62-67` checkpoint_dims；`:70-94` StateEncoder.encode(snapshot, player, own_hand) → 4 维 [circle/10, 己方押注/1000, 对方押注/1000, 己方手牌击败随机手牌概率]。
- `core/rules.py:60` 玩家 0 恒先手；`:70-87` `GameRoom.new()` 无先手参数；`:99-102` 动作空间座位无关 6 动作；`:107-120` snapshot 不含手牌（无信息泄漏）；`:156-170` 回合结束。
- `agents/base.py:34` `act(observation, legal_actions)` 统一接口。

## 必须实现的内容

### A. scripts/env.py
1. `opponent` 参数类型放宽为 `BaseAgent | None`（保留 Robot 完全兼容）。保留 `opponent_seat` 为实例属性。
2. `reset()` 按对手类型分支：**DQN 对手走自己的路径**（跳过 Robot 专属的 `init_dick`），Robot 行为**逐字节不变**（既有 Robot 相关测试必须仍通过）。
3. **新增 `_opponent_observation()`**：以对手座位为视角编码 → `self.encoder.encode(snapshot, opp_seat, room.own_hand(opp_seat))`，得到 4 维。这是自博弈的对称性基础。
4. **新增/改 `_settle_rewards()`**：返回 `(agent_reward, opponent_reward)` 双值，**零和**（agent_reward + opponent_reward == 0）。现有 `_settle_reward` 口径是"赢 +all_bet / 输 -己方已押"，两方口径不同所以不严格反对称 —— 你需要定义一个自洽的零和口径（建议：赢方 +all_bet、输方 -all_bet，对称且零和），并在报告里说明你选的口径与理由。
5. `_advance_opponent_until_agent_turn()`：DQN 对手每次行动后，用**对手视角**构造 transition 并调 `opponent.observe()` / `opponent.replay()`；Robot 仍走 `_notify_opponent`。注意 `agents/dqn.py:126-145` 的 `_notify_opponent` 吞异常，DQN 路径不要复用它。
6. **座位交换**：消除 `core/rules.py:60` 的先手偏置。**在 env 层实现**（按局奇偶交换发牌顺序或交换 agent_player），**不要改 core/rules.py**。

### B. scripts/train.py
1. `train()` 增参：`opponent_mode`（`"robot" | "self" | "snapshot"`）、`opponent_ckpt`、`opponent_sync_every`、`opponent_replay_every`、`opponent_epsilon`。
2. `self` 模式：对手是在线 DQN，**降频 replay**（默认每 k 步才 replay 一次，`opponent_replay_every`）—— 因为 `agents/dqn.py:191-192` 的 epsilon 在 replay 内衰减，两边同频会导致探索同步消失（塌缩风险）。
3. **周期性用主策略快照重置对手**（`agent.save(tmp)` + `opponent.load(tmp)`，`agents/dqn.py:204-212`），周期由 `opponent_sync_every` 控制。
4. `snapshot` 模式：对手从 `opponent_ckpt` 加载（`DQNAgent.from_checkpoint`）。
5. checkpoint 命名：主 `dqn_sp_ep{N}_seed{S}.pth`，对手 `dqn_sp_opp_ep{N}_seed{S}.pth`（写到 `run/`，`scripts/train.py:27` 已有约定）。
6. summary 增：`opponent_mode`、双方胜率、双方动作分布、训练耗时、局数。
7. `main()` 加对应 CLI 参数。

### C. scripts/evaluate.py
新增**双 checkpoint 对战模式**（现只支持单 agent vs Robot，`scripts/evaluate.py:35-36`），输出双方胜率。

### D. 测试（新建 tests/test_selfplay.py，或并入 tests/test_scripts.py）
必须覆盖：
1. DQN 对手可注入 env 并完成一整局（done 为 True，信息合法）。
2. 对手视角观测维度为 4，且与 agent 视角编码**对称**（同一局面下两个视角编码出的语义互为镜像：己方押注↔对方押注）。
3. **座位交换生效**：连续两局的先手方不同。
4. **奖励零和**：每局结束时 agent_reward + opponent_reward == 0。
5. 自博弈训练**冒烟**：用极小局数（如 2-3 局）跑完，产出 2 个 checkpoint，summary 含新增字段。
6. **同种子可复现**：同 seed 两次训练的 summary 关键字段一致。

### E. 不可碰清单（改动会让既有测试变红）
- `agents/dqn.py`：**原则上不改**（act/observe/replay/save/load/from_checkpoint 已够用）。若确需改，只允许"纯新增、不改既有语义"，并在报告中逐条说明理由。
- `core/rules.py`、`core/strength.py`、`core/dealing.py`：**零改动**。
- `core/__init__.py`：零改动。
- 状态编码仍必须是 4 维输入 / 6 维动作。

## 执行要求
1. **先读** scripts/env.py、scripts/train.py、scripts/evaluate.py、agents/dqn.py、agents/base.py、core/rules.py 全文。
2. **先跑一次基线**：`python -m pytest tests/ -q` 记下改动前的通过/失败数（注意：仓库内没有 .pth 权重，`tests/test_agents.py` 与 `tests/test_scripts.py` 中依赖 `dqn_model_1.pth` 的用例可能本就失败 —— 记录基线即可，不要试图修复，那是另一个 Task 的事）。
3. 改完后**再跑一次** `python -m pytest tests/ -q`，与基线对比：**不允许有新的失败**。
4. 也要跑 `python -m ruff check .`（若仓库有 ruff 配置）。
5. **自博弈冒烟**要真的跑起来（2-3 局即可），确认两个 checkpoint 文件真实生成、summary 字段真实存在。不要声称没验证。
6. 提交到你自己的分支（commitBranch=true），commit message 说清改了什么。

## 交付报告（≤5000 字）
- 改了什么：逐文件逐处，带 `文件路径:行号`
- 零和奖励口径的选择与理由
- 座位交换的实现方式与位置
- DQN 对手 vs Robot 对手的两条代码路径如何分叉（带行号）
- 你对 agents/dqn.py 的改动（若有）及理由；若无改动明确说"零改动"
- 新增测试清单（每个测试名 + 它验证什么）
- **实际执行的命令与真实输出**（pytest 基线 vs 改动后、ruff、冒烟训练的实际 summary JSON）
- 发现的问题与遗留项
- 未确认的内容标 UNKNOWN
    - 授权：工具 bash, read, edit, write, grep, find, ls；路径 scripts, tests；额度 120000 tokens
        - Run R-81abd01e-48ce-4f38-bc63-6d3063d46641：SUCCEEDED；worker；模型 vllm-local/Qwen3.8-27B；2501820 tokens
- Delegation G-5145214f-79fa-4ae5-8e1c-78b049089d6e：reviewer
    - 目标：【独立核验 DQN 对抗 DQN 自博弈训练机制】不要相信 worker 的报告，自己复核。

**被核验的 worktree（只在这里核验，不要改任何东西）**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-engine
**分支**：`governance/selfplay-engine`，**待核验 commit**：`cb813cf`（基线 `6bd6253`）
**核验方式**：在这个 worktree 里运行命令、读代码。**只读**，不要修改或提交任何文件（临时脚本放 /tmp）。

## 核验清单（逐条给结论 + 证据）

### 1. 交付物与报告一致
worker 声称改了 4 个文件：scripts/env.py（+163）、scripts/evaluate.py（+71）、scripts/train.py（+136）、tests/test_selfplay.py（+252）。
**核对**：`git show --stat cb813cf` 的实际改动与之一致吗？有没有**没在报告里说**的改动？有没有多改了 core/ agents/ ui/ README.md？

### 2. agents/dqn.py 零改动
亲自跑 `git diff 6bd6253 cb813cf -- agents/ core/ ui/ README.md`，必须为空。

### 3. 零和奖励
worker 声称 `scripts/env.py:188-194` 的 `_settle_rewards()` 返回 `(agent_reward, opponent_reward)`，赢方 +all_bet、输方 -all_bet，严格反对称。
**核验**：读代码；写临时脚本（放 /tmp）用 DQN 对手跑多局（不同 seed），每局检查 `agent_reward + opponent_reward == 0`，终局符号与 winner 一致。
**特别注意**：worker 说「robot 模式输局奖励由 `-agent_bet` 变为 `-all_bet`」——这是**行为变更**。请判断：
- 该变更是否与 `core/rules.py` 的实际结算一致（赢家拿走全池）？
- 既有测试是否真的不依赖旧数值？（自己 grep 断言，不要只看报告说法）
- 若有测试依赖旧数值，那是**打红隐患**，必须指出。

### 4. 座位交换
worker 声称 `scripts/env.py:100-111` 按局序翻转 `agent_player = (base + (episode-1)) % 2`，仅 DQN 对手自动启用，Robot 默认不换。
**核验**：读代码；独立跑 ≥4 局，用 `room.history`（或等价证据）确认**先手方确实交替**。
**关键追问**：交换座位是否真的消除了「玩家 0 恒先手」的结构性偏置？还是只换了 agent 视角而先手方仍固定？

### 5. 对手视角编码对称性
worker 声称 `_opponent_observation()`（env.py:182-186）产出 4 维且与 agent 视角镜像对称（agent[1]↔opp[2]、agent[2]↔opp[1]、circle 共享）。
**核验**：读 `agents/dqn.py:70-94` 的 StateEncoder.encode 确认语义；独立构造非对称押注局面，**打印两个视角的 4 维向量**，自己判断是否真镜像。

### 6. 测试真实性
worker 声称新增 `tests/test_selfplay.py` 15 例，基线 110 passed/8 failed → 改动后 125 passed/8 failed（8 个失败全是缺 `dqn_model_1.pth`）。
**核验**：
- **自己跑** `python -m pytest tests/ --tb=short -q`（在 worktree 里），看真实数字。
- **基线复现**：另开一个临时 worktree 到 /tmp checkout 基线 commit 跑一遍（**别弄脏当前 worktree**），对比数字。
- **重点看 8 个失败的用例名**，逐个确认确实是「缺 `dqn_model_1.pth`」导致，而非本次改动弄坏。**这条很重要**。
- 检查新测试是否真在测东西：有无断言恒真、skip、或只测 mock。

### 7. 训练可复现与 checkpoint 真实性
worker 声称同 seed 两次训练 summary 的 9 个关键字段一致（含双方权重 hash）。
**核验**：独立跑两次同 seed 小规模训练（各 3 局，`--episodes 3 --seed <同一个>`），对比两次 summary JSON。**自己确认 hash 字段是否真相同**。
**核验 checkpoint 真实性**：`python -c` 读出产出 .pth 的 `fc1.weight.shape` 与 `fc3.weight.shape`，确认是 (4, 6)，且**能被 `DQNAgent.from_checkpoint` 加载**。

### 8. 降频 replay 与防塌缩机制
worker 声称对手默认 `opponent_replay_every=4`、`opponent_sync_every` 默认 `max(1, episodes//4)`、`opponent_epsilon` self 模式默认 1.0。
**核验**：读代码确认这些默认值真实生效（不只是参数签名）。确认**对手的 epsilon 衰减节奏确实比 agent 慢**（否则自博弈塌缩风险未解决）。

### 9. evaluate 双 checkpoint 模式
worker 声称 `scripts/evaluate.py` 新增 `--opponent-checkpoint` 双 checkpoint 对战，输出双方胜率。
**核验**：真跑一次（20 轮），看输出是否真有**双方**胜率，数字是否合理（两者之和≈1）。

### 10. 双路径兼容性
worker 声称 Robot 路径「逐字不变」。
**核验**：`git diff 6bd6253 cb813cf -- scripts/env.py` 逐行读 Robot 相关段，确认 Robot 分支**行为**没变（语义不变即可）。跑既有测试确认。

### 11. 边界与异常
worker 声称有非法 mode 拒绝、缺 ckpt 报错等测试。核验这些路径是否真被覆盖，错误信息是否可读。

## 交付
报告 ≤5500 字：
- **逐条结论**：通过 / 不通过 / 有条件通过（每条附 `文件路径:行号` 或实际命令输出）
- **实测命令的真实输出**（pytest 数字、两次训练 summary JSON、checkpoint 维度、evaluate 输出）
- **必须返工的点**（若有），按严重度排序，每条给出文件行号与建议
- **不影响验收的小问题**
- 无法确认的内容标 UNKNOWN

**独立判断原则**：报告与代码/实测不符就直接指出，不要因为报告写得好就放过；一切属实就明确说通过。
    - 授权：工具 bash, read, grep, find, ls；路径 scripts, tests；额度 60000 tokens
        - Run R-19d2f6bd-8e3a-4464-a95a-ab2cf8ba526e：SUCCEEDED；reviewer；模型 vllm-local/Qwen3.8-27B；27471 tokens
- Delegation G-39d442cf-5679-4366-b203-a5edc6fa18a6：reviewer
    - 目标：【独立核验 DQN 对抗 DQN 自博弈训练机制】不要相信 worker 的报告，自己复核。**你已获授 bash 工具**，本任务要求大量实测。

**被核验的 worktree（只在这里核验，不要改任何东西）**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-engine
**分支**：`governance/selfplay-engine`，**待核验 commit**：`cb813cf`（基线 `6bd6253`）
**约束**：writeWorkspace=false —— **不得修改或提交 worktree 内任何文件**。临时脚本一律放 `/tmp`。基线对比请另开临时 worktree 到 `/tmp`，不要弄脏被核验 worktree。结论必须区分「实测确认」与「静态推断」，推断一律标 UNKNOWN。

## 核验清单（逐条给结论 + 证据）

### 1. 交付物与报告一致
worker 声称改了 4 个文件：scripts/env.py（+163）、scripts/evaluate.py（+71）、scripts/train.py（+136）、tests/test_selfplay.py（+252）。
**核对**：`git show --stat cb813cf` 与之一致吗？有没有**没在报告里说**的改动？有没有多改了 core/ agents/ ui/ README.md？

### 2. agents/dqn.py 零改动
亲自跑 `git diff 6bd6253 cb813cf -- agents/ core/ ui/ README.md`，必须为空。

### 3. 零和奖励
worker 声称 `scripts/env.py:188-194` 的 `_settle_rewards()` 返回 `(agent_reward, opponent_reward)`，赢方 +all_bet、输方 -all_bet，严格反对称。
**核验**：读代码；写 /tmp 临时脚本用 DQN 对手跑多局（不同 seed），每局检查 `agent_reward + opponent_reward == 0`，终局符号与 winner 一致。
**特别注意**：worker 说「robot 模式输局奖励由 `-agent_bet` 变为 `-all_bet`」——这是**行为变更**。请判断：
- 该变更是否与 `core/rules.py` 的实际结算一致（赢家拿走全池）？
- 既有测试是否真的不依赖旧数值？（自己 grep 断言，不要只看报告说法）
- 若有测试依赖旧数值，那是**打红隐患**，必须指出。

### 4. 座位交换
worker 声称 `scripts/env.py:100-111` 按局序翻转 `agent_player = (base + (episode-1)) % 2`，仅 DQN 对手自动启用，Robot 默认不换。
**核验**：读代码；独立跑 ≥4 局，用 `room.history`（或等价证据）确认**先手方确实交替**。
**关键追问**：交换座位是否真的消除了「玩家 0 恒先手」的结构性偏置？还是只换了 agent 视角而先手方仍固定？

### 5. 对手视角编码对称性
worker 声称 `_opponent_observation()`（env.py:182-186）产出 4 维且与 agent 视角镜像对称（agent[1]↔opp[2]、agent[2]↔opp[1]、circle 共享）。
**核验**：读 `agents/dqn.py:70-94` 的 StateEncoder.encode 确认语义；独立构造非对称押注局面，**打印两个视角的 4 维向量**，自己判断是否真镜像。

### 6. 测试真实性
worker 声称新增 `tests/test_selfplay.py` 15 例，基线 110 passed/8 failed → 改动后 125 passed/8 failed（8 个失败全是缺 `dqn_model_1.pth`）。
**核验**：
- **自己跑** `python -m pytest tests/ --tb=short -q`（在 worktree 里），记录真实数字。
- **基线复现**：`git worktree add /tmp/baseline-check 6bd6253` 另开临时 worktree 跑一遍，对比数字（**用完 `git worktree remove` 清理**）。
- **重点看 8 个失败的用例名**，逐个确认确实是「缺 `dqn_model_1.pth`」导致，而非本次改动弄坏。**这条很重要**。
- 检查新测试是否真在测东西：有无断言恒真、skip、或只测 mock。

### 7. 训练可复现与 checkpoint 真实性
worker 声称同 seed 两次训练 summary 的 9 个关键字段一致（含双方权重 hash）。
**核验**：独立跑两次同 seed 小规模训练（各 3 局），对比两次 summary JSON。**自己确认 hash 字段是否真相同**。
**核验 checkpoint 真实性**：`python -c` 读出产出 .pth 的 `fc1.weight.shape` 与 `fc3.weight.shape`，确认是 (4, 6)，且**能被 `DQNAgent.from_checkpoint` 加载**。

### 8. 降频 replay 与防塌缩机制
worker 声称对手默认 `opponent_replay_every=4`、`opponent_sync_every` 默认 `max(1, episodes//4)`、`opponent_epsilon` self 模式默认 1.0。
**核验**：读代码确认默认值真实生效（不只是参数签名）。确认**对手的 epsilon 衰减节奏确实比 agent 慢**（否则自博弈塌缩风险未解决）。

### 9. evaluate 双 checkpoint 模式
worker 声称 `scripts/evaluate.py` 新增 `--opponent-checkpoint` 双 checkpoint 对战，输出双方胜率。
**核验**：真跑一次（20 轮），看输出是否真有**双方**胜率，数字是否合理（两者之和≈1）。

### 10. 双路径兼容性
worker 声称 Robot 路径「逐字不变」。
**核验**：`git diff 6bd6253 cb813cf -- scripts/env.py` 逐行读 Robot 相关段，确认 Robot 分支**行为**没变（语义不变即可）。跑既有测试确认。

### 11. 边界与异常
worker 声称有非法 mode 拒绝、缺 ckpt 报错等测试。核验这些路径是否真被覆盖，错误信息是否可读。

### 12. 你的判断
基于实测，worker 的实现**是否真的实现了「DQN 对抗 DQN」**？还是只是把对手换成了另一个 DQN 但两者并不真正对弈（例如对手的经验来源不对、双方看到的状态不对称、奖励传递断裂）？这一条请给出明确结论。

## 交付
报告 ≤5500 字：
- **逐条结论**：通过 / 不通过 / 有条件通过（每条附 `文件路径:行号` 或实际命令输出）
- **实测命令的真实输出**（pytest 数字与失败用例名、ruff、两次训练 summary JSON、checkpoint 维度、evaluate 输出、零和与座位交换实测结果）
- **必须返工的点**（若有），按严重度排序，每条给出文件行号与建议
- **不影响验收的小问题**
- 无法确认的内容标 UNKNOWN

**独立判断原则**：报告与代码/实测不符就直接指出，不要因为报告写得好就放过；一切属实就明确说通过。
    - 授权：工具 bash, read, grep, find, ls；路径 scripts, tests；额度 60000 tokens
        - Run R-44ac84dd-8e85-4a6b-a120-6a76aaf0e431：SUCCEEDED；reviewer；模型 vllm-local/Qwen3.8-27B；993580 tokens

## cleanup-refactor：按 docs/ARCHITECTURE.md 第 7.7/7.6 节完成 S/M 级重构清理与 README 不一致修正，零行为风险。本 Task 与 selfplay-engine 文件不重叠，可并行。Main Agent 只调度编排，编码全部由子 Agent 完成。

- 状态：已验收；已验收
- 预算：1800000 tokens；授权路径 ui, core, tests, docs, README.md, CHANGELOG.md, pyproject.toml

- Delegation G-de39db46-800c-4591-9b6b-fb5a291cfcc4：worker
    - 目标：【按架构知识库完成 S/M 级重构清理与 README 不一致修正】零行为风险的一组收尾改动。

**你的独立工作区（worktree）**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/cleanup-refactor
**在这个 worktree 里工作并提交**（分支 governance/cleanup-refactor）。不要改主仓库目录。
授权范围：ui/、core/__init__.py、tests/、README.md、CHANGELOG.md、pyproject.toml。
**不要改** scripts/、agents/、core/rules.py、core/strength.py、core/dealing.py（别人在改 scripts/）。

## 依据
`docs/ARCHITECTURE.md` 第 7.6、7.7 节。行号以**你实际读到的代码**为准，不要照抄文档。

## 必须完成的改动（逐条，全部要改）

### 1. ui/app.py 键码映射（已知问题：Action(key - pygame.K_1)）
`ui/app.py` 里按键码算 Action 的地方（调研记录约 :211-212）现在用「键码差值」映射（K_1→Action(0)、K_2→Action(1)…）。差值映射在小键盘/非标准布局下会错位。
**改法**：改成**显式映射表**（逐个键码对应到真实 Action 枚举值）。
**注意**：先读 core/rules.py 或相关模块确认 Action 枚举的**真实成员与顺序**，不要假设 0..5 的顺序就是 K_1..K_6 的映射 —— 映射错了会让按键选错动作。
**测试**：新增一条测试断言显式映射表覆盖所有 Action（每个 Action 都有唯一键码）。

### 2. ui/app.py 资源自检接入 theme.missing_assets()
`ui/theme.py` 已有 `missing_assets()`（调研记录约 :77-90）能精确列出缺失资源，但 `ui/app.py` 启动时（调研记录约 :269-271）只做了「const.ROOT/"src" 目录是否存在」这种过粗的检查，没用 missing_assets()。
**改法**：启动自检改用 `missing_assets()`，缺失时打印**具体缺哪些资源**。
**测试**：用 monkeypatch/mock 造一个缺失资源场景，断言启动自检能报出具体文件名。

### 3. ui/theme.py button_rects 返回注解
`ui/theme.py` 约 :130 的 `button_rects` 返回注解写成了 `dict[int, "object"]`，实际返回的是 `dict[int, pygame.Rect]`。
**改法**：改成 `dict[int, pygame.Rect]`（保持现有 import 风格）。
**测试**：新增一条断言 `isinstance(result[k], pygame.Rect)`。

### 4. ui/app.py last_now 归位
`ui/app.py` 约 :141 的 `last_now: float = 0.0` 是**类级属性**，约 :143-144 的 `set_now` 把它覆盖成实例属性，风格不统一（其他状态都在 `__init__` 里）。
**改法**：把 `last_now` 移进 `__init__`（约 :31-54 的初始化块），删掉类级属性。
**测试**：现有 UI 测试必须仍全绿（`tests/test_ui.py`）。

### 5. core/__init__.py 的 __all__ 补全
`core/__init__.py` 约 :16-31 的 `__all__` 白名单**不含** `strength_ordinal`、`strongest_hand` 和 dealing 模块的符号，导致依赖这些符号的代码只能直接 import 子模块。
**改法**：把这些符号补进 `__all__` 并按需 import。
**关键约束**：**必须保持惰性导入不变** —— `core/strength.py` 的 22100 手精确强度表是**惰性建表**（模块级不触发），`tests/test_dealing.py:86-95` 断言「默认均匀发牌路径下建表缓存命中数为 0」。你补的 import **不能**在 `core` 导入期触发 `strength` 的建表函数（`table_size`/`beats_probability`/`strength_ordinal`/`strength_bin`）。
**测试**：新增一条断言 —— 全新解释器里 `import core` 后，`core.strength` 的 lru_cache 命中数仍为 0（即 import core 不触发建表）。

### 6. README.md 三处不一致（架构知识库 7.6 节）
调研记录的行号（**请自己核实**）：
- **:28**「draw_me_vs_DQN_Plus.py (6 行)」→ 实际是 14 行。改成实际行数。
- **:44-48** 架构图箭头方向错误：图中 core/、agents/ 的框底用向下箭头指向 scripts/，但文字说明和实际 import 方向相反（实际是 scripts → core/agents）。**改法**：把 scripts/ 框整体上移到顶部入口层，与 draw_me_vs_DQN_Plus.py 并排，箭头由 scripts 框底向下指向 core/ 与 agents/；删掉 core/agents 指向 scripts 的向下箭头。**改完务必核对 ASCII 图对齐正确**（框线不错位）。
- **:63**「ui/、scripts/ 无 time.sleep」的声明 overclaim：pytest 守护**只扫 ui/**（`tests/test_ui.py:63-65` 的 `(REPO/"ui").glob("*.py")`），scripts/ 无 sleep 目前只有 grep 证实（由 `tests/baseline/repro_d7_timing.py:36-41` 在 CI 里守护，非 pytest）。
  **改法**：把那一行拆成两行 ——「`ui/` 无 time.sleep ｜ 守护：`tests/test_ui.py::TestTicker::test_no_sleep_in_source`」和「`scripts/` 无 time.sleep ｜ 守护：`tests/baseline/repro_d7_timing.py`（CI 缺陷回归步骤，非 pytest）」。**不要扩大 pytest 扫描范围**（那是测试改动，不在本 Task 范围）。

### 7. 文档/配置同步
- `pyproject.toml` 约 :42 有「备份」相关的残留描述，与实际不符 → 改准确。
- `README.md` 约 :73 的目录说明与实际目录内容不符（实际 `src/` 下有 `card_pic备用/`、`login/` 等残留目录）→ 改准确。
- `CHANGELOG.md` 末尾追加一条本次改动的记录。

## 执行要求
1. **先读** ui/app.py、ui/theme.py、core/__init__.py、core/strength.py、core/rules.py、core/dealing.py、README.md、pyproject.toml 相关段落，以及 tests/test_ui.py、tests/test_dealing.py、tests/test_strength.py。
2. **先跑基线**：`python -m pytest tests/ -q` 记录通过/失败数（仓库内没有 .pth 权重，`tests/test_agents.py`/`tests/test_scripts.py` 中依赖 `dqn_model_1.pth` 的用例可能本就失败 —— 记录基线，不要修）。
3. **改完再跑** `python -m pytest tests/ -q`，与基线对比：**不允许有新的失败**。
4. 跑 `python -m ruff check .`（若仓库有 ruff 配置）。
5. 提交到你自己的分支，commit message 说清改了什么。

## 交付报告（≤4500 字）
- 逐条列出上面 7 项的改动结果：位置 `文件路径:行号` + 改前改后
- Action 枚举的真实成员与顺序是什么（带行号），你的显式映射表长什么样
- **新 import 的惰性性验证结果**（你用什么命令确认 import core 不触发建表，实际输出是什么）
- 新增测试清单（每个测试名 + 验证什么）
- **实际执行的命令与真实输出**（pytest 基线 vs 改动后、ruff）
- 发现的问题与遗留项
- 未确认的内容标 UNKNOWN
    - 授权：工具 bash, read, edit, write, grep, find, ls；路径 ui, core/__init__.py, tests, README.md, CHANGELOG.md, pyproject.toml；额度 120000 tokens
        - Run R-948ba62d-36c6-4b93-9e87-2db4f92db8c9：SUCCEEDED；worker；模型 vllm-local/Qwen3.8-27B；3779913 tokens
- Delegation G-1eead647-919e-4a3a-bcd2-135ed3c71ee9：reviewer
    - 目标：【独立核验 S/M 级重构清理与 README 不一致修正】不要相信 worker 的报告，自己复核。

**被核验的 worktree（只在这里核验，不要改任何东西）**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/cleanup-refactor
**分支**：`governance/cleanup-refactor`，**待核验 commit**：`5170642`（基线 `6bd6253`）
**核验方式**：在这个 worktree 里运行命令、读代码。**只读**，不要修改或提交任何文件（临时脚本放 /tmp）。

## 核验清单

### 1. 改动范围核对
worker 声称改了 8 个文件：CHANGELOG.md(+19)、README.md(±53)、core/__init__.py(+31)、pyproject.toml(±2)、tests/test_purity.py(+21)、tests/test_ui.py(+39)、ui/app.py(±42)、ui/theme.py(+6)。
**核对**：`git show --stat 5170642` 与之一致吗？有没有报告没说的改动？有没有越权改动 scripts/ agents/ core/rules.py core/strength.py core/dealing.py？

### 2. 键码映射（最重要的正确性风险）
worker 声称 `ui/app.py:28-44` 新增 `key_to_action_map()`，映射 `{K_1: BET_10, K_2: BET_20, K_3: BET_50, K_4: BET_100, K_f: FOLD, K_c: COMPARE}`。
**核验 —— 独立验证这个映射的正确性，不要只看 worker 的推理**：
1. 读 `core/rules.py` 的 Action 枚举，确认真实成员与整数值。
2. 读 `core/rules.py` 的 `legal_actions()`（或等价函数），确认在 `rest_option` 不同取值时**哪些 Action 是合法的**（例如 rest_option=2 时只有 BET_50/BET_100/FOLD/COMPARE 合法？）。
3. **用真实代码路径验证**：驱动一次 `_on_key(K_2)`，断言落库的动作确实是 BET_20（worker 说 history[-1]==(0,1) 且 bet 5→25）。
4. **重点检查**：`Action` 枚举里有没有 worker **漏掉的成员**？映射表是否覆盖全部 6 个 Action？有没有哪个 Action 被映射到两个键、或某个键重复？
5. **反向检查**：改前是 `Action(key - pygame.K_1)` 差值映射 —— 请确认差值映射**原来到底对应什么语义**（K_1→Action(0) 即 BET_10？），如果原本 K_1 就是 BET_10，那新映射是等价的；如果不等价，说明这次改动**改变了按键语义**，那是重大发现，必须指出。
6. 检查 `ui/theme.py` 的 BUTTON_IMAGES 与 README 的操作说明（1-4 押注、F 弃牌、C 看牌）是否与新映射一致。

### 3. 惰性建表（红线）
worker 声称 `core/__init__.py:12-30` 补入 `strength_ordinal`、`strongest_hand`、`new_deck`、`deal_uniform`、`deal_strength_biased`、`verify_uniformity`、`EmptyDeckError` 等符号到 `__all__`，且**保持惰性导入**。
**核验（这条是红线，必须实测）**：
- `core/strength.py` 的 22100 手精确表是**惰性建表**（模块级不触发）。
- 跑 `tests/test_dealing.py:86-95`（断言默认均匀发牌路径下 lru_cache 命中数为 0）必须通过。
- **独立验证**：在**全新解释器**里跑 `python -c "import core; print(core.strength._table_cache.cache_info() if hasattr(core.strength,'_table_cache') else 'N/A')"` 之类的命令，或直接 `python -c "import core, sys; from core import strength; print(strength.<lru_cache名>.cache_info())"`，确认 import core 后建表**没有**被触发。
- 确认 `core/__init__.py` 没有在模块级调用 `table_size`/`beats_probability`/`strength_ordinal`/`strength_bin`。
- **注意**：worker 提到了给 `ui/theme.py` 加了 `if TYPE_CHECKING: import pygame`。请确认这**没有**导致 pygame 在运行时被 import（ui/app.py 原本的风格是「模块 import 期不 import pygame」）。实测 `python -c "import ui.theme, sys; print('pygame' in sys.modules)"`。

### 4. 资源自检
worker 声称 `ui/app.py:47-51` 新增 `check_assets()`，`:291-293` 的 main() 改用它替代原先只查 `const.ROOT/"src"` 是否存在的过粗检查。
**核验**：读代码确认；实测缺失资源时**打印出来的内容是否真的列出了具体缺失文件名**（用 mock 或临时构造）。确认没有把「资源缺失」变成致命错误导致启动失败（原行为是提示后继续）。

### 5. last_now 归位
worker 声称删掉类级 `last_now: float = 0.0`（原 :141），移入 `__init__`（`ui/app.py:80`），`set_now`（:168-169）不变。
**核验**：读代码；确认没有遗漏其它引用点（grep `last_now` 全仓）；跑既有 UI 测试确认仍全绿。

### 6. button_rects 注解
worker 声称 `ui/theme.py:134` 改为 `dict[int, pygame.Rect]`（未加引号），并加了 `if TYPE_CHECKING: import pygame`（:15、:19-20）。
**核验**：读代码；确认 `pygame.Rect` 在注解求值时不会 NameError（`from __future__ import annotations` 在 :11）；**实测** `python -c "from ui.theme import button_rects"` 或实际调用一次，确认运行时正常。

### 7. README 三处修正
worker 声称：
- :28「6 行」→ 实际行数
- :44-48 架构图箭头方向：scripts/ 框上移为入口层，箭头由 scripts 向下指向 core/ 与 agents/，删掉 core/agents 指向 scripts 的向下箭头
- :63 time.sleep 声明拆成两行（ui/ 由 pytest 守护，scripts/ 由 tests/baseline/repro_d7_timing.py 守护，非 pytest）
**核验**：
1. `draw_me_vs_DQN_Plus.py` **实际**多少行？README 写的对吗？
2. **把 ASCII 图完整打印出来，逐行核对框线对齐**（不能有框线错位）。同时核对**文字说明**与**图**的方向一致，且与**实际 import 方向**一致（自己 grep 一下 scripts/ 下各文件 import 了谁、ui/ import 了谁）。
3. time.sleep 声明的两行表述是否与**实际测试扫描范围**一致？亲自看 `tests/test_ui.py` 的 glob 范围，和 `tests/baseline/repro_d7_timing.py` 的扫描范围。

### 8. 测试真实性
worker 声称 `tests/test_purity.py`(+21) 与 `tests/test_ui.py`(+39) 新增用例。
**核验**：读新测试，**逐个判断它们是否真的在验证东西**（有没有断言恒真、有没有空测试、有没有 skip）。特别检查：
- 惰性建表那条测试，是否真的在**全新解释器**里验证（而不是在已被其它测试污染的同一进程里断言 cache_info 命中数为 0 —— 那样是无效测试）？
- 键码映射那条，是否真的断言了映射内容与 Action 枚举一致？

### 9. 回归
- **自己跑** `python -m pytest tests/ --tb=short -q`（在 worktree 里），记录真实数字。
- 8 个失败预期是缺 `dqn_model_1.pth`（test_agents 6 例 + test_scripts TestEvaluate 2 例）。**逐个确认失败原因**，有没有被本次改动弄坏的新失败。
- **基线复现**：另开临时 worktree 到 /tmp checkout 基线 commit 跑一遍对比数字（**别弄脏当前 worktree**）。
- 跑 `python -m ruff check .`。

## 交付
报告 ≤5000 字：
- **逐条结论**：通过 / 不通过 / 有条件通过（每条附 `文件路径:行号` 或实际命令输出）
- **实测命令的真实输出**（pytest 数字与失败用例名、ruff、import 惰性性验证、ASCII 图对齐核对结论）
- **必须返工的点**（若有），按严重度排序，给出文件行号与建议
- **不影响验收的小问题**
- 无法确认的内容标 UNKNOWN

**独立判断原则**：报告与代码/实测不符就直接指出；一切属实就明确说通过。**键码映射的语义正确性和惰性建表这两条是重点，务必实测而非推理。**
    - 授权：工具 bash, read, grep, find, ls；路径 ui, core, tests, README.md, CHANGELOG.md, pyproject.toml；额度 60000 tokens
        - Run R-9994d3e0-f2b2-4c02-99f9-30663d4f5165：CANCELLED；reviewer；模型 vllm-local/Qwen3.8-27B；32156 tokens
- Delegation G-eb221a5f-04f5-4357-b72d-0db9e1ffa5d4：reviewer
    - 目标：【独立核验 S/M 级重构清理与 README 不一致修正】不要相信 worker 的报告，自己复核。**你已获授 bash 工具**，本任务要求大量实测。

**被核验的 worktree（只在这里核验，不要改任何东西）**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/cleanup-refactor
**分支**：`governance/cleanup-refactor`，**待核验 commit**：`5170642`（基线 `6bd6253`）
**约束**：writeWorkspace=false —— **不得修改或提交 worktree 内任何文件**。临时脚本一律放 `/tmp`。基线对比请另开临时 worktree 到 `/tmp`，用完 `git worktree remove` 清理。结论必须区分「实测确认」与「静态推断」，推断一律标 UNKNOWN。

## 核验清单

### 1. 改动范围核对
worker 声称改了 8 个文件：CHANGELOG.md(+19)、README.md(±53)、core/__init__.py(+31)、pyproject.toml(±2)、tests/test_purity.py(+21)、tests/test_ui.py(+39)、ui/app.py(±42)、ui/theme.py(+6)。
**核对**：`git show --stat 5170642` 与之一致吗？有没有报告没说的改动？有没有越权改动 scripts/ agents/ core/rules.py core/strength.py core/dealing.py？

### 2. 键码映射（最重要的正确性风险）
worker 声称 `ui/app.py:28-44` 新增 `key_to_action_map()`，映射 `{K_1: BET_10, K_2: BET_20, K_3: BET_50, K_4: BET_100, K_f: FOLD, K_c: COMPARE}`。
**独立验证，不要只看 worker 的推理**：
1. 读 `core/rules.py` 的 Action 枚举，确认真实成员与整数值。
2. 读 `core/rules.py` 的 `legal_actions()`（或等价函数），确认在 `rest_option` 不同取值时**哪些 Action 合法**。
3. **用真实代码路径验证**：驱动一次 `_on_key(K_2)`，断言落库动作确实是 BET_20（worker 说 history[-1]==(0,1) 且 bet 5→25）。
4. **反向检查**：改前是 `Action(key - pygame.K_1)` 差值映射 —— 确认差值映射**原本对应什么语义**（K_1→Action(0) 是否就是 BET_10？）。如果原本 K_1 就是 BET_10，新映射等价；如果不等价，说明这次改动**改变了按键语义**，那是重大发现，必须指出。
5. 检查 `ui/theme.py` 的 BUTTON_IMAGES 与 README 操作说明（1-4 押注、F 弃牌、C 看牌）是否与新映射一致。

### 3. 惰性建表（红线）
worker 声称 `core/__init__.py:12-30` 补入 `strength_ordinal`、`strongest_hand`、`new_deck`、`deal_uniform`、`deal_strength_biased`、`verify_uniformity`、`EmptyDeckError` 等符号到 `__all__`，且**保持惰性导入**。
**必须实测**：
- 跑 `tests/test_dealing.py:86-95`（断言默认均匀发牌路径下 lru_cache 命中数为 0），必须通过。
- **独立验证**：全新解释器里跑 `python -c "import core; from core import strength; print(strength.<实际lru_cache名>.cache_info())"`，确认 import core 后建表**没有**被触发（先读 strength.py 找到 lru_cache 的真实名字）。
- 确认 `core/__init__.py` 没在模块级调用 `table_size`/`beats_probability`/`strength_ordinal`/`strength_bin`。
- **注意**：worker 给 `ui/theme.py` 加了 `if TYPE_CHECKING: import pygame`。确认这**没有**导致 pygame 在运行时被 import（ui/app.py 原本的风格是「模块 import 期不 import pygame」）。实测 `python -c "import ui.theme, sys; print('pygame' in sys.modules)"`。

### 4. 资源自检
worker 声称 `ui/app.py:47-51` 新增 `check_assets()`，`:291-293` 的 main() 改用它替代原先只查 `const.ROOT/"src"` 是否存在的过粗检查。
**核验**：读代码确认；实测缺失资源时**打印出来的内容是否真的列出具体缺失文件名**（用 /tmp 脚本 + monkeypatch）。确认没把「资源缺失」变成致命错误导致启动失败（原行为是提示后继续）。

### 5. last_now 归位
worker 声称删掉类级 `last_now: float = 0.0`（原 :141），移入 `__init__`（`ui/app.py:80`），`set_now`（:168-169）不变。
**核验**：读代码；grep `last_now` 全仓确认无遗漏引用；跑既有 UI 测试确认仍全绿。

### 6. button_rects 注解
worker 声称 `ui/theme.py:134` 改为 `dict[int, pygame.Rect]`（未加引号），并加了 `if TYPE_CHECKING: import pygame`（:15、:19-20）。
**核验**：读代码；确认注解求值不会 NameError（`from __future__ import annotations` 在 :11）；**实测**实际调用一次 `button_rects(...)`，确认运行时正常且返回值确实是 `pygame.Rect` 实例。

### 7. README 三处修正
worker 声称：:28「6 行」→ 实际行数；:44-48 架构图箭头方向修正（scripts/ 框上移为入口层，箭头由 scripts 向下指向 core/ 与 agents/）；:63 time.sleep 声明拆成两行。
**核验**：
1. `draw_me_vs_DQN_Plus.py` **实际**多少行？README 写的对吗？
2. **把 ASCII 图完整打印出来，逐行核对框线对齐**（不能错位）。核对**文字说明**、**图**、**实际 import 方向**三者一致（自己 grep scripts/ 下各文件 import 了谁、ui/ import 了谁）。
3. time.sleep 声明的两行表述是否与**实际测试扫描范围**一致？亲自看 `tests/test_ui.py` 的 glob 范围和 `tests/baseline/repro_d7_timing.py` 的扫描范围。

### 8. 测试真实性
worker 声称 `tests/test_purity.py`(+21) 与 `tests/test_ui.py`(+39) 新增用例。
**核验**：读新测试，**逐个判断是否真在验证东西**（有无断言恒真、空测试、skip）。特别检查：
- 惰性建表那条，是否真在**全新解释器**里验证（而不是在已被其它测试污染的同一进程里断言 cache_info 命中数为 0 —— 那样是无效测试）？
- 键码映射那条，是否真断言了映射内容与 Action 枚举一致？

### 9. 回归
- **自己跑** `python -m pytest tests/ --tb=short -q`（在 worktree 里），记录真实数字与失败用例名。
- 8 个失败预期是缺 `dqn_model_1.pth`。**逐个确认失败原因**，有没有被本次改动弄坏的新失败。
- **基线复现**：`git worktree add /tmp/baseline-check2 6bd6253` 跑一遍对比数字（**用完 remove 清理**）。
- 跑 `python -m ruff check .`。

## 交付
报告 ≤5000 字：
- **逐条结论**：通过 / 不通过 / 有条件通过（每条附 `文件路径:行号` 或实际命令输出）
- **实测命令的真实输出**（pytest 数字与失败用例名、ruff、import 惰性性验证、pygame 未被 import 的验证、ASCII 图对齐核对结论）
- **必须返工的点**（若有），按严重度排序，给出文件行号与建议
- **不影响验收的小问题**
- 无法确认的内容标 UNKNOWN

**独立判断原则**：报告与代码/实测不符就直接指出；一切属实就明确说通过。**键码映射的语义正确性和惰性建表这两条是重点，务必实测而非推理。**
    - 授权：工具 bash, read, grep, find, ls；路径 ui, core, tests, README.md, CHANGELOG.md, pyproject.toml；额度 60000 tokens
        - Run R-645c1980-4d3a-41fe-a644-60ee2a64b1f8：SUCCEEDED；reviewer；模型 vllm-local/Qwen3.8-27B；1776605 tokens

## selfplay-train-100：在 CPU 上完成 ≤100 局 DQN 对抗 DQN 自博弈训练，产出「真正会因手牌强弱而改变动作」的可加载策略文件，并把它固化成可一条命令复现的训练配置。上一次委派的 worker 在 worktree 中留下了未验证的 strength_shaping 实现与 --preset selfplay-v1（已实测：修好了坍缩，但对局贪心策略仍是恒定动作，未满足状态依赖），本次要求在其基础上收敛到达标并提交交付。Main Agent 只做调度与编排，编码与训练全部由子 Agent 完成。

- 状态：已验收；已验收
- 预算：1800000 tokens；授权路径 scripts, tests, run, docs

- Delegation G-3016adc8-6c12-4f35-a1e5-ea7e852452e8：worker
    - 目标：【CPU 跑 DQN 自博弈训练，产出可用的策略文件】这是用户的第一优先事项。

**你的独立工作区（worktree）**：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100
**在这个 worktree 里工作并提交**（分支 governance/selfplay-train-100）。不要改主仓库目录。
**该 worktree 已合入 T1 的自博弈实现**（merge commit 7343ca7，含 scripts/env.py 的 `_opponent_observation`、零和 `_settle_rewards`、座位交换；scripts/train.py 的 `--opponent-mode`；scripts/evaluate.py 双 checkpoint 模式；tests/test_selfplay.py 15 例）。**不要重新实现这些。**
授权范围：scripts/、tests/、run/、docs/。**不要改 core/、agents/、ui/、README.md**。

## 硬约束
- 训练局数 **≤ 100 局**（用户批准的上限）。**不要超过 100 局。**
- 纯 CPU。
- 必须固定种子可复现。
- `agents/dqn.py`、`core/` 零改动。超参只能通过 `scripts/train.py` 构造 `DQNConfig` 传入，不改 `agents/dqn.py` 的默认值。

## Main Agent 已经做过的探测（结论可直接采信，但你必须自己复现关键项）
我在 `governance/selfplay-engine` worktree 上实测过：

1. **100 局自博弈只花 0.244 秒**（`python -m scripts.train --episodes 100 --seed 7 --opponent-mode self`）。所以**墙钟时间完全不是约束**，真正的约束是 100 局这个上限本身。这意味着你可以**多次试不同配置**，每次都几秒钟。

2. **默认配置下 100 局训出的策略是退化的**：加载 checkpoint 后对 3000 个随机状态取贪心动作，结果是 **100% 都是 `bet_100`（动作 3）**，且对手侧同样 100% `bet_100`。分强度分组后（手牌强度 0.0~1.0 共 11 档）每一档都是同一个动作 —— 也就是说该策略**完全不响应手牌强度，行为上等同于恒定动作的随机策略**。
   - 贪心双 checkpoint 评估结果：`win_rate=0.0, opponent_win_rate=0.0, action_distribution={bet_100: 1.0}`，且 20/20 轮全部撞 `MAX_STEPS=200` 强停（avg_pot 涨到 20060）—— 对局根本不会自然结束。
   - 这**不满足**用户的要求「机器的逻辑不是随机概率，而是训练出来的逻辑」。

3. **根因已定位**：不是 batch_size 门槛，而是**总环境步数太少**。100 局 × 每局约 1~3 步 = 全程仅约 100~260 个 transition。DQN 在这个样本量下学不出状态依赖性。证据：
   - `epsilon_final=0.656`（100 局默认配置）→ 只发生了约 86 次成功梯度更新（epsilon_decay=0.995，每次成功 replay 衰减一次）。
   - 把 `batch_size` 从 32 降到 4 或 8：仍然退化（贪心分布仍是单一动作），说明**降低 batch 不是解法**。
   - 把 `epsilon_decay` 改成 0.999（保持更多探索）、把 `lr` 提到 0.01/0.005：仍然 100% 单一动作。

4. **注意 `opponent_replay_every` 的语义陷阱**：`scripts/env.py` 里 `_opp_actions` 每局清零，所以 `opponent_replay_every=4` 实际含义是「**单局内**每 4 次对手行动」。短局下对手几乎不学习（实测 200 局只有 4 次成功 replay）。对手侧要用 `opponent_replay_every=1`。

## 你的任务：找出在 ≤100 局内能训出「状态依赖」策略的配置

**核心目标**：训出的 checkpoint，其贪心动作分布必须**随状态变化**（不是单一动作），并且**明显区别于均匀随机**。

**建议的探索方向**（请自行验证，不要盲从）：
- **A. 让一局变长**：如果一局只有 1~3 步，100 局就没有样本。可以让 agent 在早期倾向于**加注**（不结束对局），从而拉长回合数。探索如何通过超参（更低的 epsilon_decay、更高的 epsilon_start）或对局设置来提高每局步数与总步数。**先量化：每局平均步数是多少？总步数是多少？**
- **B. 奖励塑形信号**：观察 `beats_probability`（手牌强度，状态第 4 维）在策略里到底有没有被利用。检查梯度是否真的在更新与该特征相关的权重。
- **C. 超参搜索**：因为一次训练只要 0.24 秒，你可以在 /tmp 里写一个**临时搜索脚本**（放 /tmp，不要提交进仓库），批量跑多组 (batch_size, lr, epsilon_decay, epsilon_start, opponent_replay_every, gamma) 组合，用统一指标评估并挑出最好的一组。

**评估指标**（自己定义，但要能量化「状态依赖」）：对训练出的 checkpoint，在一批随机但真实的状态上取贪心动作，统计：
- 动作分布的**熵**或**最大占比**（单一动作则占比 1.0，退化）
- 动作与 `beats_probability`（强度）的**相关性**（强手该加注/看牌，弱手该弃牌 —— 期望动作随强度变化）

### 必须达成的验收（逐条对应 Task acceptance）
1. 先完成 5 局测速并记录墙钟耗时。
2. 完成一轮 **≤100 局**的 CPU 自博弈训练，实际产出可加载的 `.pth`（主策略 + 对手策略）。
3. 训练 summary 含双方胜率、双方动作分布、耗时、局数。
4. **无塌缩**：双方胜率不一边倒；**动作分布不退化为单一动作**。
5. 策略文件能被 `DQNAgent.from_checkpoint` 正常加载，`input_dim=4` / `action_dim=6`。
6. 固定种子下训练可复现。
7. 产出训练报告（命令、耗时、胜率、产物路径）。

### 额外交付（比 Task acceptance 更严格，请务必做到）
- **把训练出的最佳配置固化进 `scripts/train.py`**（作为自博弈模式的默认超参，或新增 CLI 参数如 `--batch-size` / `--lr` / `--epsilon-decay`），使「一条命令就能复现这次训练」。不要只在 /tmp 脚本里跑一次了事。
- **把权重产出到稳定位置**：权重受 `.gitignore` 的 `*.pth` 与 `run/` 规则影响，不会进版本库。请确保产物路径固定且在报告里写清楚（下游 Task 要引用它）。
- **验证对局能自然结束**：用训练出的双 checkpoint 跑 `python -m scripts.evaluate --checkpoint ... --opponent-checkpoint ... --rounds 50`，确认**不是**全部 MAX_STEPS 强停，双方胜率之和 ≈ 1.0（自然终局）。
- 若经过合理努力仍无法在 100 局内达到「状态依赖」，**如实报告**：说明你试了哪些配置、各自的量化指标、最好的结果是什么、瓶颈在哪（例如「100 局只提供约 N 个 transition，样本量不足」）。**不要为了让指标好看而伪造或挑选数据**；如实汇报比勉强达标更重要。

## 执行要求
1. 先读 `scripts/train.py`、`scripts/env.py`、`agents/dqn.py`（尤其 `DQNConfig` 的全部字段、`replay()` 的 batch 门槛、`act()` 的 epsilon 逻辑）、`core/strength.py` 的 `beats_probability`。
2. 改动前后各跑一次 `python -m pytest tests/ -q`，不允许有新的失败（已知 8 个失败是缺 `dqn_model_1.pth` 的既有环境问题）。
3. 跑 `python -m ruff check .`。
4. 提交到你的分支，commit message 说清改了什么、用了什么配置、为什么。

## 交付报告（≤5500 字）
- 你的搜索过程：试了哪些配置、每组的关键指标（每局步数/总步数/epsilon_final/贪心动作分布最大占比/与强度的相关性）—— 用表格
- 最终选定的配置与**选择理由**（引用具体指标）
- 最终训练的实际命令、耗时、summary JSON 全文
- 产出 checkpoint 的**绝对路径**与文件名
- 贪心评估的完整输出（双方胜率、动作分布）
- 你对 `scripts/train.py` 做的固化改动（逐处，带 `文件路径:行号`）
- 若未达标：明确说明未达标、瓶颈量化、后续建议
- 未确认的内容标 UNKNOWN
    - 授权：工具 bash, read, edit, write, grep, find, ls；路径 scripts, tests, run, docs；额度 120000 tokens
        - Run R-dd2699b1-5cc3-4f78-91a2-1081a599975e：FAILED；worker；模型 vllm-local/Qwen3.8-27B；3565367 tokens
- Delegation G-33f8c566-afb9-4317-8b4d-e0cd1f99228a：worker
    - 目标：【在 ≤100 局内训出「会因牌力改变动作」的 DQN 策略，并固化配置、提交交付】

**上一位 worker 超时了，但它的成果还在你的 worktree 里（未提交）。你必须先评估并接着做，不要推倒重来。**

**你的 worktree**：`/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100`
**分支**：governance/selfplay-train-100（HEAD 7343ca7，已含 T1 的自博弈实现）

## 0. 纪律要求（上一轮就是死在这里）
上一位 worker 花了 90 分钟、10.4 万 token 在 `/tmp` 里反复写搜索脚本，**从未提交**。本轮：
- **不要再做开放式参数搜索。** 我已经用 15 次实测确定了可行解，下面直接给你。
- **不要修改 pi 的源码**（`/home/kipley/Documents/code/learning/pi` 下的任何文件）—— 硬红线。
- **总实验次数 ≤ 12 次**，每次训练约 1~3 秒。整个任务以「跑通 → 验证 → 提交 → 写报告」为主线。
- **目标节奏**：前 15 分钟内完成方案落地，后 15 分钟内完成验证与提交，剩下的时间写报告。**不要超过 45 分钟。**

## 1. 授权范围
可改：`scripts/`、`tests/`、`run/`、`docs/`
**不可改**：`core/`、`agents/`、`ui/`、`README.md`、`pyproject.toml`

## 2. 已完成的诊断（我已实测确认，直接采信，但你要复现一次关键项）

### 2.1 问题根因
终局奖励是 `±all_bet`（赢家拿走全池），**量级随押注额线性增长**（±数百到数千）。于是 Q 值天然单调偏好最大押注 → argmax 恒为 `bet_100` → 对局永不自然结束（撞 MAX_STEPS=200 强停）、动作分布退化为单一动作。

证据（我用默认超参训练 100 局后实测）：贪心动作分布 `{bet_100: 3000}`，按手牌强度 0.0~1.0 分 11 档**每一档都是 bet_100**；Q 值扫描显示 Q(bet_100) 恒 > Q(bet_50) > Q(bet_20) > Q(bet_10)。

### 2.2 解法（已验证可行）
在 `scripts/env.py` 引入**按押注额计酬的稠密奖励塑形**（上一位 worker 已实现，代码在 worktree 里未提交）：

```
本方押注时：reward += k·(p - 0.5)·押注额        # p = 己方手牌击败随机手牌概率
             reward -= k·(0.5 - p_opp)·押注额     # 对手同步记零和的对应量
对方押注时：reward -= k·(0.5 - p)·对方押注额
```
- `p > 0.5`（强牌）时押注为正 → 强牌加注；`p < 0.5`（弱牌）时押注为负 → 弱牌弃牌。
- **关键：按「押注额」而不是「底池」计酬**，避免大底池下 Q(加注) 自增强成死循环。
- 严格零和：`agent_reward + opponent_reward == 0` 恒成立。

### 2.3 已验证的关键配置与效果（**你直接用这套**）
```
塑形系数 k = 50.0
lr = 3e-2,  batch_size = 4,  epsilon_decay = 0.99,  hidden = (128, 64)（默认架构）
opponent_replay_every = 1
episodes = 100,  seed 变化
```
实测（5 个 seed 的统计）：
- **弱牌（beats_probability 0.0~0.3）大注占比 ≈ 0.01；强牌（0.7~1.0）大注占比 ≈ 0.40 → 差值 +0.39**，即策略确实随牌力改变动作。
- 对局**自然结束 100/100**（不撞 MAX_STEPS）。
- 胜率：seed=1 → 42胜/58负；seed=7 → 50/50；seed=42 → 50/50。**不一边倒**。
- **可复现**：用 `scripts/train.py` 的 `--preset selfplay-v1` 路径，同 seed 两次训练的 checkpoint 字节完全一致（已实测 sha256 相同）。

### 2.4 必须保留的约束
- **最终 checkpoint 必须用默认隐藏层 (128, 64)**。`DQNAgent.from_checkpoint` 只自适应 input/action 维度，不推断隐藏层宽度；用自定义 hidden（如 (32,16)）训练出的 checkpoint，`from_checkpoint` 会报 `size mismatch for fc1.weight`（我实测过）。下游 UI 要直接加载这个权重。
- **不要改 `_settle_rewards` 的 `±all_bet` 零和结算口径**（那是已验收的契约；缩放终局奖励会触碰「改变自博弈对称性口径」的人工审批红线）。**只调塑形系数 k**。

## 3. 你要交付的东西

### 3.1 先修两个已知缺陷
worktree 里上一位 worker 的代码有 2 个缺陷，**必须修掉**：

**(a) CLI 崩溃**：`scripts/train.py:329` 的 `opponent_epsilon=p["opponent_epsilon"]` 无条件访问，但该键只在 `--preset selfplay-v1` 时才被 `p` 带入。任何非 preset 调用（例：`python -m scripts.train --episodes 100 --seed 7 --opponent-mode self`）会抛 `KeyError: 'opponent_epsilon'`。
→ 改成 `p.get("opponent_epsilon", ...)` 并给出合理缺省值。

**(b) `--preset selfplay-v1` 的超参不符合 2.3**：worktree 里当前 preset 是 `strength_shaping=0.5, hidden=(32,16), lr=3e-2, batch_size=4, epsilon_decay=0.99`。
→ 必须改成 2.3 的那套：`strength_shaping=50.0, hidden=None`（= 默认 (128,64)）, `lr=3e-2, batch_size=4, epsilon_decay=0.99`。
**注意 `hidden` 必须是 None 或 (128,64)，不能是 (32,16)。**

### 3.2 跑通正式训练并验证 9 条验收
运行（一条命令可复现）：
```
python -m scripts.train --preset selfplay-v1 --episodes 100 --seed 7 --out run/final
```
然后逐条验证，**每条都要有实测数字**：

1. **5 局测速**：记录墙钟耗时（我实测 100 局约 1~3 秒）。
2. **产出 .pth**：`run/final/dqn_sp_ep100_seed7.pth` 与 `run/final/dqn_sp_opp_ep100_seed7.pth`。
3. **summary 含**双方胜率、双方动作分布、耗时、局数。
4. **训练期无塌缩**：双方胜率不一边倒；训练期动作分布不退化为单一动作。
5. **【最关键】部署用贪心策略（epsilon=0）不得退化为单一动作**：写一个临时脚本（放 `/tmp`，不要提交），加载 checkpoint，构造 ≥2000 个**真实**状态（用 `core.dealing.new_deck` + `deal_uniform` 发真手牌 + `core.strength.beats_probability` 算强度，第 1~3 维用 `random.Random(固定种子)` 取值），对每个状态调 `agent.act(obs, list(range(6)))`，统计：
   - 动作分布（必须 ≥2 个动作，且**最大动作占比 < 0.95**）
   - **按手牌强度分组**（分 0.0~0.3 弱 / 0.4~0.6 中 / 0.7~1.0 强 三档）的动作分布 —— 必须显示**强牌比弱牌更倾向大注**
   - 我已用 `k=50` 实测到的参考值：弱牌大注占比 ≈0.01，强牌 ≈0.40
6. **对局自然结束**：`python -m scripts.evaluate --checkpoint run/final/dqn_sp_ep100_seed7.pth --opponent-checkpoint run/final/dqn_sp_opp_ep100_seed7.pth --rounds 50 --seed 7` → `natural_end_rate ≥ 0.9`，且双方胜率之和 ≈ 1.0。（我实测 k=50 时训练期自然结束 100/100。）
7. **可加载**：`DQNAgent.from_checkpoint('run/final/dqn_sp_ep100_seed7.pth')` 不报错，网络为 `fc1=(128,4)`、`fc2=(64,128)`、`fc3=(6,64)`。
8. **可复现**：同 seed 跑两次，checkpoint sha256 一致（我已实测 preset 路径一致）。
9. **配置固化 + 报告**：preset 已含 2.3 超参；写 `docs/selfplay_train_report.md`（命令、耗时、胜率、动作分布、产物绝对路径、验证结论）。

### 3.3 补充测试
在 `tests/` 里加测试（不要破坏既有测试）：
- `--preset selfplay-v1` 能跑通且产出 checkpoint
- CLI 不带 preset 时不再 KeyError（回归测试 3.1(a)）
- preset 的超参是 2.3 那套（防回归）
- `_settle_rewards` 的零和性仍成立（`agent_reward + opponent_reward == 0`）

### 3.4 常规检查
- `python -m pytest tests/ -q`：**已知 8 个失败是既有环境问题**（缺被 .gitignore 忽略的 `dqn_model_1.pth`），**不允许新增失败**。基线是 `8 failed / 110 passed`。
- `python -m ruff check .` → All checks passed。
- 提交到你的分支，commit message 说清：改了什么、用了哪套配置、为什么。

### 3.5 诚实汇报
若 2.3 的配置在你的复现下**没有**达到验收 5 或 6，**如实报告**：给出你实测到的具体数字（动作分布、强度分组占比、natural_end_rate、胜率），说明哪些验收项达成、哪些没达成、瓶颈是什么。
**不要为了让指标好看而挑选 seed 或改口径。** 如实汇报比勉强达标重要得多。

## 4. 交付报告（≤4500 字）
- 修了哪两个缺陷（带 `文件路径:行号`）
- preset 最终超参（逐项）
- 正式训练的**完整命令 + 墙钟耗时 + summary JSON 全文**
- 贪心评估：动作分布 + **三档强度分组的动作分布** + natural_end_rate + 双方胜率
- 复现性证据（两次 sha256）
- checkpoint 的**绝对路径**
- pytest / ruff 结果
- 未达标的项与瓶颈（若有）

所有结论带 `文件路径:行号`；无法确认的标 UNKNOWN。
    - 授权：工具 bash, read, edit, write, grep, find, ls；路径 scripts, tests, run, docs；额度 70000 tokens
        - Run R-c1712b23-6c72-4d3e-983a-9976034da077：SUCCEEDED；worker；模型 vllm-local/Qwen3.8-27B；1289853 tokens
- Delegation G-5a017dfe-0060-4d0c-bfc6-2cee44a00f9a：reviewer
    - 目标：【独立复核 T2 交付：selfplay-train-100，commit ea2f024】

**你的工作区**：`/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100`
**分支**：governance/selfplay-train-100，HEAD = `ea2f024`（基线 `7343ca7` + 上一位 worker 未提交成果 + 本轮 worker 的修复）
**只读复核**：不要修改任何源码，不要提交。你只做核验并出具报告。

**不要修改 pi 的源码**（`/home/kipley/Documents/code/learning/pi` 下任何文件）—— 硬红线。

## 背景：为什么这次复核特别重要
上一位 worker 超时未提交，留下未验证的改动；第二位 worker 修复并声称「9 条验收全过」。**Main Agent 已独立复测了核心指标**，但你要做的是**你自己独立跑一遍**，不要采信 Main 或 worker 的任何数字。

Main Agent 的独立复测结果（供你对照，**必须自己重算，不要直接引用**）：
- 同 seed 两次训练 sha256 一致：主 `52144d10ec7061362b236780…`、对手 `528a3c641856cf493debff21…`
- 贪心（ε=0）2400 状态：总分布 `{bet_20: 664, bet_100: 1736}`，最大占比 0.7233
  - 弱牌 p≤0.3 (n=751) 大注占比 **0.1491**；中牌 (n=714) **0.9650**；强牌 p>0.6 (n=935) **1.0000**
- 双 checkpoint 50 轮 ε=0：`natural_end_rate=1.0`，胜率 0.50/0.50
- `from_checkpoint`：fc1=(128,4)、fc2=(64,128)、fc3=(6,64)、epsilon=0.0
- pytest：基线 8 failed/110 passed → 现在 **8 failed/129 passed**，失败集合逐条一致
- ruff：All checks passed

worker 报告的数字与 Main 的略有差异（worker 说弱牌大注 0.000、总分布 bet_20 0.3917；Main 复测 0.1491 / 0.2767）。**请查清差异来源**（很可能是随机采样顺序或状态构造方式不同）并说明你的测量方法。

## 需要你逐条核验的 9 条验收
1. **5 局测速**有墙钟耗时记录
2. **≤100 局**（确认没有超过 100 局；查 summary 的 episodes 与代码里的实际循环）
3. **summary 含**双方胜率、双方动作分布、耗时、局数
4. **训练期无塌缩**：双方胜率不一边倒、动作分布不退化为单一动作
5. **【最关键】部署用贪心策略（ε=0）不得退化为单一动作，且随牌力变化** —— 你自己写脚本复测（放 `/tmp`，不要提交）：
   - 加载 `run/final/dqn_sp_ep100_seed7.pth`
   - 构造 ≥2000 个**真实**状态：用 `core.dealing.new_deck` + `deal_uniform` 发真手牌，`core.strength.beats_probability` 算强度，第 1~3 维用固定种子的 `random.Random`
   - 统计动作分布 + **按手牌强度分档**（弱/中/强）的大注占比
   - 判据：最大动作占比 < 0.95，且强牌大注占比显著高于弱牌（单调）
6. **对局自然结束**：`natural_end_rate ≥ 0.9`，不得全撞 MAX_STEPS
7. **可加载**：`DQNAgent.from_checkpoint` 无报错，input_dim=4 / action_dim=6，隐藏层 (128,64)
8. **可复现**：同 seed 两次训练产出字节一致
9. **配置固化 + 报告**：`scripts/train.py` 的 `SELFPLAY_V1` 含验收配方；`docs/selfplay_train_report.md` 存在且内容属实

## 额外必须核验的技术点
- **零和口径未被破坏**：`scripts/env.py` 的 `_settle_rewards` 仍返回 `±all_bet`（**不得**被缩放成别的量级 —— 缩放会触碰「改变自博弈对称性口径」的人工审批红线）。查 git diff 确认该函数未被改动。
- **新增的 `strength_shaping` 塑形是否严格零和**：任意一步 `agent_reward + opponent_reward == 0`（含对手侧塑形与终局塑形叠加的情形）。请构造多个随机种子、多个 episode 逐步断言。
- **`opponent_replay_every` 的语义**：确认 `scripts/env.py` 里 `_opp_actions` 每局清零，因此 `opponent_replay_every=1` 才是"每步都 replay"。
- **红线确认**：`git diff 7343ca7..ea2f024 --stat` 的改动范围只在 `scripts/`、`tests/`、`docs/`；`core/`、`agents/`、`ui/` **零改动**。特别确认 `agents/dqn.py` 未被改（`from_checkpoint` 机制是红线）。
- **`scripts/evaluate.py` 新增的 "checkpoint 隐藏层自适应加载"** 是否**没有**修改 `agents/dqn.py` 的 `from_checkpoint` 机制（而是在 evaluate.py 侧自己读 state_dict 的形状）。请看具体实现，判断是否与红线冲突。
- **测试真实性**：`tests/test_selfplay_preset.py` 的 4 个新测试是否真的断言了行为，而不是恒真断言。挑 1~2 个做变异测试（故意改坏实现看测试是否失败）。
- **pytest 失败集合**与基线 `6bd6253` 逐条一致（Main 已在 `/tmp/basecheck` 建了基线 worktree，可直接复跑对比；用完请 `git worktree remove /tmp/basecheck` 清理）。

## 交付
把复核报告写到 **`docs/review_train_100.md`**（在你的工作区里写，**不要 git 提交**；Main 会取走归档）。内容：
- 9 条验收逐条：判定（通过/不通过/部分通过）+ 你**自己实测的数字** + 证据（`文件路径:行号` 或命令输出）
- worker 数字与你的数字差异的来源分析
- 额外技术点的核验结论
- **必须返工项**（明确列出；没有就写"无"）
- 风险与遗留
- 无法确认的标 UNKNOWN

篇幅 ≤5000 字。**不要替 worker 补写代码**，只报告问题。
    - 授权：工具 bash, read, grep, find, ls；路径 scripts, tests, run, docs；额度 60000 tokens
        - Run R-e6879920-cfcb-4958-94b9-1e802a3ef28f：FAILED；reviewer；模型 vllm-local/Qwen3.8-27B；699729 tokens
- Delegation G-a0156e8d-84b1-4a1b-9648-e40276d600ef：worker
    - 目标：【T2 收尾返工：补 2 个测试 + 清理陈旧产物 —— 这是个小任务，不要做大搜索】

**你的 worktree**：`/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100`
**分支**：governance/selfplay-train-100，HEAD = `3b5226c`（含 `ea2f024` 功能实现）
**上一个 worker 已经完成主体工作并提交。你的任务只有下面 3 件事。**

**硬约束**：
- **不要修改 pi 的源码**（`/home/kipley/Documents/code/learning/pi` 下任何文件）。
- 不要改动 `scripts/`、`docs/` 的功能实现 —— 除非下面明确要求。**不要重做超参搜索**。
- 改动只允许在 `scripts/`、`tests/`、`run/`、`docs/`。
- **目标 20 分钟内完成。** 不要做开放式探索。

## 背景：为什么有这两件事
独立 reviewer 对 `ea2f024` 的复核结论：9 条验收全部通过，但发现**一个测试覆盖缺口**和**一个产物路径歧义**。

## 任务 1：补上零和性在「带塑形的押注步」的测试（核心）

**现有缺口**：`tests/test_selfplay_preset.py` 里的零和测试**只断言了最后一步**，而那一步恰好是 `fold`（零塑形，塑形增量为 0），所以**没有覆盖到真正会产生非零塑形增量的押注步**。
reviewer 只在代码层证明了 `agent_reward + opponent_reward == 0.0` 在押注步也成立（IEEE-754 符号对称），但没有测试锁住它。

**你要做的**：在 `tests/test_selfplay_preset.py`（或 `tests/test_selfplay.py`）新增测试，**逐步**断言每一个环境步的 `agent_reward + opponent_reward == 0.0`，且**必须包含至少一个非零塑形增量的押注步**（即 `strength_shaping > 0` 且动作为 BET_* 之一的那一步）。

要求：
- 用 `strength_shaping=50.0`（preset 值）构造 `CardGameEnv`，跑**多个随机种子**（至少 3 个）和**多个 episode**（至少 20 局），覆盖押注步、对手跟注步、fold 步、终局步。
- 断言用 `== 0.0` 精确相等（不是 `abs(x) < 1e-6`）—— 因为 IEEE-754 下 `fl(A+N) + fl(-A-N)` 应当精确为 0。如果实测发现不是精确 0，**如实报告**实际残差，不要放宽断言来掩盖。
- 断言测试**确实覆盖到了非零塑形步**（例如统计 `bet_steps_with_nonzero_shaping > 0` 并 assert），避免写出一个「碰巧没触发塑形所以恒真」的测试。

## 任务 2：补上「checkpoint 可被 UI 侧标准加载」的回归测试

**背景**：`DQNAgent.from_checkpoint` 只自适应 input/action 维度，**不推断隐藏层宽度**。若用自定义 hidden（如 `(32,16)`）训练，产出的 checkpoint 用默认 config 加载会报 `size mismatch for fc1.weight` —— 下游 UI 直接加载会崩。上一轮 worker 正是因为这个把 preset 的 hidden 移除了（让 `hidden` 缺省 = 默认 `(128,64)`）。

**你要做的**：新增一个测试，断言 preset 训练产出的 checkpoint 满足：
- `DQNAgent.from_checkpoint(path)` **无异常**（用默认 config，不传 hidden）
- `agent.model.fc1.in_features == 4`、`fc1.out_features == 128`、`fc2.out_features == 64`、`fc3.out_features == 6`
- `agent.epsilon == 0.0`

注意：这个测试需要真实训练一次（100 局约 1~3 秒，很便宜）。用 `tmp_path` 输出目录，跑 `--preset selfplay-v1 --episodes 100 --seed 7` 的等价调用即可。

## 任务 3：清理陈旧产物，消除路径歧义

`run/` 目录下有**上一轮 worker 留下的陈旧 checkpoint**（hidden=(32,16)，约 6KB，2026-11-02 19:18）：
```
run/dqn_sp_ep100_seed7.pth
run/dqn_sp_opp_ep100_seed7.pth
run/_sync_tmp_seed7.pth
```
它们与**正确的当前产物**（hidden=(128,64)，约 40KB）并存于：
```
run/final/dqn_sp_ep100_seed7.pth
run/final/dqn_sp_opp_ep100_seed7.pth
run/final/_sync_tmp_seed7.pth
```
陈旧产物如果被误用，UI 加载会 size mismatch。

**你要做的**：
- 删除 `run/` 根目录下那 3 个陈旧 `.pth`（它们被 .gitignore 忽略，删除不产生 git 变更，但会消除本 worktree 内的歧义）。
- **不要**删除 `run/final/` 下的当前产物。
- 另外，`run/` 下还有一批历史实验目录（`base100/`、`k1/`、`k2a/`、`k2b/`、`robust_1..7/`、`repro/`、`sped5/`、`eval_seed7.json`、`eval_seed20261021.json` 等）。请检查并**删除其中含 hidden=(32,16) 的陈旧 checkpoint**，只保留 `run/final/` 下当前正确的产物。用一个脚本逐个 `torch.load` 检查 `fc1.weight` 的形状来判断。
- 在 `docs/selfplay_train_report.md` 里**明确写出唯一权威产物路径**是 `run/final/dqn_sp_ep100_seed7.pth` 与 `run/final/dqn_sp_opp_ep100_seed7.pth`，并加一句说明「`run/` 根目录下若有同名旧文件则是历史遗留、隐藏层宽度不同、不可使用」。

## 交付要求
- 改动后 `python -m pytest tests/ -q`：**必须仍是 8 failed / 129+N passed**（8 个失败是既有环境问题：缺被 gitignore 的 `dqn_model_1.pth`，基线 `6bd6253` 也是同样 8 个失败，失败集合逐条一致）。**不允许新增失败。**
  - 你新加的 2 个测试会**增加通过数**并可能让总数变成 131+，这是正常的。
- `python -m ruff check .` → All checks passed
- 提交到你的分支，commit message 说清加了什么测试、清理了哪些产物。
- **交付报告 ≤2000 字**：
  - 新增测试的文件路径 + 行号 + 断言内容摘要
  - 逐步零和断言的**实测残差**（是否为精确 0.0）
  - 覆盖到的「非零塑形押注步」计数证据
  - checkpoint 加载测试的结果
  - 删除了哪些陈旧产物（列出路径 + 各自的 hidden 宽度）
  - pytest / ruff 结果
  - 未确认的标 UNKNOWN

所有结论带 `文件路径:行号`。
    - 授权：工具 bash, read, edit, write, grep, find, ls；路径 scripts, tests, run, docs；额度 30000 tokens
        - Run R-2569c185-4b3b-4693-a102-cd8b1ad43986：SUCCEEDED；worker；模型 vllm-local/Qwen3.8-27B；1950422 tokens
- Delegation G-2c079edd-b85c-4e44-b7e7-b02b9fb5316b：reviewer
    - 目标：【T2 最终独立复核 —— 必须用 bash 重跑，不要只读代码】

**worktree**：`/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100`
**分支**：governance/selfplay-train-100，HEAD = `fad9206`（= `3b5226c` 证据日志 + `ea2f024` 功能 + `fad9206` 返工测试）
**只读复核**：不修改源码、不提交。

## ⚠️ 最重要的工作方式要求（上一轮 reviewer 栽在这里）
上一轮 reviewer **只用了 read/grep/find/ls，0 次 bash**，导致训练/评估/pytest/sha256 全部「未重跑」，报告质量打折，最后还因超时空转 40 分钟。
**这次必须用 bash 实际执行命令。** 你有 bash 工具（expectedTools 含 bash），请实际跑：
- 训练（100 局约 1~3 秒，很便宜）
- pytest
- python 脚本（状态依赖性实测）
- sha256
**不要通读大文件**。用 `sed -n 'M,Np'` / `grep -n` 定点看，不要 `cat` 整个文件。

## ⚠️ 报告纪律（上一轮因超时被截断）
**边做边写**：先在你要输出的文件里写好标题和已确认的小节，每验证完一项就补进去。
**不要**攒到最后一次性输出。
**总输出控制在 4000 字以内。**
**目标 20 分钟内完成。** 宁可少查几项，也不要超时。

## 背景
这是 T2（selfplay-train-100）的最终复核。前面已有：
- worker 实现（ea2f024）
- reviewer 复核（已归档 `management/evidence/investigation/review-train-100.md`，9 条验收全通过，但因未用 bash 属于静态/产物级核验）
- 返工（fad9206）：补「逐步零和（含非零塑形押注步）」测试 + 「checkpoint 可被默认 config 加载」测试 + 清理 run/ 陈旧产物

**Main Agent 已独立跑过的结果（供对照，你必须自己重算，不要直接引用）**：
- pytest：基线 6bd6253 = 8 failed/110 passed → 现在 **8 failed/131 passed**，失败名逐条一致
- ruff：All checks passed
- 同 seed 两次训练 sha256 一致：`52144d10ec7061362b236780…`（主）、`528a3c641856cf493debff21…`（对手）
- 贪心 ε=0、2400 真实状态：总分布 `{bet_20: 664, bet_100: 1736}`（max 0.7233）
  - 弱牌 p≤0.3 (n=751) 大注占比 0.1491；中牌 (n=714) 0.9650；强牌 p>0.6 (n=935) 1.0000
- 双 checkpoint ε=0、50 局：`natural_end_rate=1.0`，胜率 0.50/0.50
- `from_checkpoint`：fc1=(128,4)、fc2=(64,128)、fc3=(6,64)、epsilon=0.0
- 变异测试：故意让 `opp_reward` 不减塑形增量 → 新测试立即失败（残差 188.235），证明非恒真断言
- run/ 下仅剩 `run/final/` 3 个 .pth，`fc1` 均为 (128,4)

## 请用 bash 逐条核验（这才是你的核心产出）
1. 5 局测速（墙钟 + summary elapsed_sec）
2. ≤100 局（`grep` 训练循环 + summary episodes）
3. summary 含双方胜率/双方动作分布/耗时/局数
4. 训练期无塌缩（胜率不一边倒、动作分布非单一）
5. **【最关键】贪心 ε=0 状态依赖**：自己写 `/tmp` 脚本，≥2000 真实状态（`core.dealing.new_deck` + `deal_uniform` + `core.strength.beats_probability`，前 3 维用固定种子 `random.Random`），统计动作分布 + 弱/中/强三档的大注占比。判据：max 占比 < 0.95 且强≫弱单调
6. **对局自然结束**：`natural_end_rate ≥ 0.9`
7. `from_checkpoint` 加载 + 维度 4/6 + hidden (128,64) + epsilon 0.0
8. **可复现**：同 seed 两次训练 sha256 一致
9. 配置固化（`grep` `SELFPLAY_V1`）+ `docs/selfplay_train_report.md` 存在且属实

## 追加核验（本轮新增）
10. **逐步零和**：新测试 `tests/test_selfplay_preset.py` 里的 `TestStepwiseZeroSumWithShaping` 是否真的覆盖了**非零塑形的押注步**（不是恒真）。请**实际跑一次变异测试**验证它能抓到破坏：
    - 先 `cp scripts/env.py /tmp/env.bak`
    - 改坏零和（例如把 `opp_reward -= net_shaping` 改成 `pass`）
    - 跑该测试，确认它 **FAILED**
    - `cp /tmp/env.bak scripts/env.py` 还原，并用 `git diff --stat scripts/env.py` 确认已还原（必须为空）
11. **checkpoint 可加载性测试**：`test_preset_checkpoint_loadable_with_default_config` 是否真的用默认 config（不传 hidden）加载并断言了 fc1/fc2/fc3 形状
12. **红线**：`git diff 7343ca7..fad9206 --stat` 改动范围；确认 `agents/`、`core/`、`ui/` **零改动**（特别 `agents/dqn.py` 的 `from_checkpoint`）
13. **`_settle_rewards` 未被缩放**：仍是 `±all_bet`
14. **run/ 产物唯一性**：`find run -name '*.pth'` 应只有 `run/final/` 下 3 个，且 `fc1` 均为 (128,4)

## 输出方式（重要）
你的会话**可能有写文件工具，也可能没有**。两种情况都要处理：
- **有写工具**：写到 `docs/review_train_100_final.md`（不要 git 提交）
- **没有写工具**：直接把完整报告作为最终消息返回（**控制在 4000 字内**）

报告结构：
- 每项：判定（通过/不通过/部分通过）+ **你自己实测的数字** + 证据（命令输出或 `文件路径:行号`）
- 第 10 项变异测试的**实际输出**（FAILED 的断言信息）
- **必须返工项**（没有就明确写"无"）
- 风险与遗留
- 未确认的标 UNKNOWN

**不要替 worker 补写代码**，只报告问题。**不要修改 pi 源码**（`/home/kipley/Documents/code/learning/pi` 下任何文件）。
    - 授权：工具 bash, read, edit, write, grep, find, ls；路径 scripts, tests, run, docs；额度 45000 tokens
        - Run R-f3136e0a-a69b-4dd4-8add-51a06956a570：FAILED；reviewer；模型 vllm-local/Qwen3.8-27B；231040 tokens
- Delegation G-7ed9290b-79f7-44d2-b516-b709dd5a44e5：reviewer
    - 目标：【T2 最终独立复核 —— 你是修复后的第一个带 bash 的 reviewer】

**worktree**：`/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100`
**分支**：governance/selfplay-train-100，**HEAD = `7d58d4e`**
**只读复核**：不改源码、不提交。

## 第一步：确认你有 bash
先跑：`bash -lc 'echo TOOL_OK; cd /home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/selfplay-train-100 && git log --oneline -1'`
**如果 bash 不存在**：立刻回复说明，不要空等。

## 背景：为什么之前两轮 reviewer 都没能动态核验
根因已查明并修复：子 Agent 工具集由 Agent 定义文件 + `.pi/settings.json` 的 `subagents.agentOverrides` 共同决定，后者会**覆盖**前者的 tools；而 `gov init` 写入的 `.pi/settings.json` 里 reviewer 只声明了 `read/grep/find/ls`（无 bash），且我早前的修改**从未提交** → 所有 worktree 拿到的都是无 bash 的版本。
已修复并提交：`.pi/agents/reviewer.md`（d67a0c0）、`.pi/settings.json`（e4e44f6），已同步到你的 worktree。
**前两轮 reviewer 的结论**：9 条验收的静态部分全部通过，但动态项全部标 UNVERIFIED —— **你的任务就是把这些 UNVERIFIED 变成实跑结论**。

## 已知的两处待裁决分歧（前一轮 reviewer 提出）
1. **ε=0 状态依赖的两套数字矛盾**：
   - worker 报告：总分布 `{bet_20: 0.3917, bet_100: 0.6083}`，弱/中/强大注占比 `0.000 / 0.7353 / 1.0000`
   - Main Agent 实测：总分布 `{bet_20: 664, bet_100: 1736}`（max 0.7233），弱/中/强 `0.1491 / 0.9650 / 1.0000`
   - 两套的分档数完全一致（弱 751 / 中 714 / 强 935），但 bet_100 计数 1460 vs 1736 不同。
   → **请你裁决**：用 bash 实跑一次，说明差异来源（大概率是前 3 维盘面特征的随机采样种子/取值范围不同，因为第 4 维 beats_probability 是确定性的），并给出**你自己**的最终数字。
2. **HEAD 实际是 `7d58d4e`**（在 `fad9206` 之后追加了一个证据日志提交），请覆盖 `7343ca7..7d58d4e` 全量核验，并用 `git diff 7343ca7..HEAD --stat` 核验该提交内容。
3. `run/final/_sync_tmp_seed7.pth` 是 `train.py:203` 的对手同步临时文件，**不是**第三个权威产物；权威产物只有 `run/final/dqn_sp_ep100_seed7.pth` 与 `run/final/dqn_sp_opp_ep100_seed7.pth`。

## 必须用 bash 实跑核验的项（你的核心产出）
1. **5 局测速**：墙钟 + summary elapsed_sec
2. **≤100 局**：`grep` 训练循环 + summary episodes
3. **summary 字段**齐全（双方胜率/双方动作分布/耗时/局数）
4. **训练期无塌缩**（胜率不一边倒、动作分布非单一）
5. **【最关键】ε=0 状态依赖**：自己写 `/tmp` 脚本，≥2000 个真实状态（`core.dealing.new_deck` + `deal_uniform` + `core.strength.beats_probability`；前 3 维用固定种子 `random.Random`），统计动作分布 + 弱(≤0.3)/中(0.4~0.6)/强(>0.6)三档的大注(bet_50/bet_100)占比。判据：max 占比 < 0.95 且强≫弱单调。**顺带裁决上面的分歧 1**。
6. **natural_end_rate ≥ 0.9**：`python -m scripts.evaluate --checkpoint run/final/dqn_sp_ep100_seed7.pth --opponent-checkpoint run/final/dqn_sp_opp_ep100_seed7.pth --rounds 50 --seed 7`
7. **from_checkpoint**：加载无异常、`fc1=(128,4)`/`fc2=(64,128)`/`fc3=(6,64)`、`epsilon==0.0`
8. **可复现**：同 seed 两次训练 sha256 一致
9. **配置固化**：`grep` `SELFPLAY_V1`（`scripts/train.py:51`）含 k=50.0 / lr=3e-2 / batch_size=4 / epsilon_decay=0.99 / opponent_replay_every=1 / hidden 未设；`docs/selfplay_train_report.md` 存在且属实
10. **逐步零和 + 变异测试实跑**：把 `scripts/env.py` 里 `opp_reward -= net_shaping` 改成 `pass`，跑 `tests/test_selfplay_preset.py` 确认 **FAILED**，然后 `cp` 还原并用 `git diff --stat scripts/env.py` 确认已还原（必须为空）
11. **checkpoint 可加载性测试**：`test_preset_checkpoint_loadable_with_default_config` 是否用默认 config 加载并断言 fc1/fc2/fc3
12. **红线**：`git diff 7343ca7..HEAD --stat`；确认 `agents/`、`core/`、`ui/` **零改动**（特别 `agents/dqn.py` 的 `from_checkpoint`）
13. **`_settle_rewards` 未被缩放**：仍是 `±all_bet`（`scripts/env.py:226-232`）
14. **pytest 失败集合与基线一致**：与 `/tmp/basecheck`（基线 6bd6253）逐条 diff；现有应为 `8 failed / 131 passed`；**额外跑一次**：把 `run/final/dqn_sp_ep100_seed7.pth` 复制为仓库根的 `dqn_model_1.pth`，确认 8 个既有失败**全部转绿**、套件全绿，然后删掉该临时文件
15. **ruff**：`python -m ruff check .` → All checks passed
16. **run/ 产物唯一性**：`find run -name '*.pth'` 应只有 `run/final/` 下 3 个，用 `torch.load` 核验 `fc1` 形状均为 (128,4)

## 输出纪律（上一轮因超时被截断）
- **边做边写**：先写好报告标题与已确认的小节，每验证完一项就补进去。
- **总输出 ≤4000 字**。
- **目标 20 分钟内完成**。宁可少查几项，也不要超时。
- 定点查看代码用 `sed -n 'M,Np'` / `grep -n`，**不要 cat 整个文件**。

## 报告落点
- 有写工具 → 写 `docs/review_train_100_final.md`（不要 git 提交）
- 无写工具 → 直接把完整报告作为最终消息返回

报告结构：每项判定（通过/不通过/部分通过/UNVERIFIED）+ 你**自己实测的数字** + 证据（命令输出或 `文件路径:行号`）；分歧 1 的裁决结论；**必须返工项**（没有就明确写"无"）；风险与遗留；未确认标 UNKNOWN。

**不要替 worker 补写代码**，只报告问题。**不要修改 pi 源码**（`/home/kipley/Documents/code/learning/pi` 下任何文件）。
    - 授权：工具 bash, read, edit, write, grep, find, ls；路径 scripts, tests, run, docs；额度 40000 tokens
        - Run R-f20e8e16-850c-4ad7-acfc-f3fe439648d5：SUCCEEDED；reviewer；模型 vllm-local/Qwen3.8-27B；727041 tokens

## human-vs-machine：跑通「玩家 vs 机器」的对抗：ui/ 侧默认加载自博弈训练产出的策略文件，机器用训练出来的逻辑（epsilon=0.0 贪心）而不是随机概率，并做 headless 端到端验证一局完整走通。这是用户的第二优先事项。Main Agent 只调度编排，编码全部由子 Agent 完成。

- 状态：已批准；未验收
- 预算：1800000 tokens；授权路径 ui, tests, docs, README.md

- Delegation G-f7aa2f09-a403-4b56-98fd-e2b42051d6c6：worker
    - 目标：【T3：让 UI 的机器对手真正使用训练产出的 DQN 策略】

**你的 worktree**：`/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/human-vs-machine`
**分支**：governance/human-vs-machine，HEAD = `7d58d4e`（已合入 T1+T2 的自博弈与训练代码）
**权重已在你的 worktree 里就位**（被 .gitignore 忽略，不要提交）：
- `dqn_model_1.pth`（= `run/final/dqn_sp_ep100_seed7.pth`，UI 的默认加载位置）
- `run/final/dqn_sp_opp_ep100_seed7.pth`

**硬约束**：
- **不要修改 pi 的源码**（`/home/kipley/Documents/code/learning/pi` 下任何文件）。
- **不要改 `core/`、`agents/`** —— 尤其 `agents/dqn.py` 的 `from_checkpoint` 机制、`core/rules.py` 规则语义、`core/dealing.py` 发牌、`core/strength.py` 惰性建表。
- **不要改 UI 的 snapshot/view 五字段契约**。
- 可改范围：`ui/`、`tests/`、`docs/`、`README.md`。
- 不要新增第三方依赖。
- **目标 30 分钟内完成**，不要做开放式探索。

## 现状（已实测，采信即可）
`ui/app.py:25`：`DEFAULT_CHECKPOINT = REPO / "dqn_model_1.pth"`
`ui/app.py:55-62` `_load_agent`：
```python
try:
    return DQNAgent.from_checkpoint(checkpoint, seed=self.seed)
except (FileNotFoundError, ValueError, RuntimeError) as exc:
    print(f"[提示] 未能加载权重 {checkpoint}（{exc}），回退为未训练策略")
    return DQNAgent(input_dim=4, action_dim=6, seed=self.seed, epsilon=0.15)
```
- `DQNAgent.from_checkpoint` 的 `epsilon` 默认是 **0.0**（`agents/dqn.py:129`），所以**权重存在时机器已经是 epsilon=0.0 的贪心训练策略**。
- 但路径**写死**在 `REPO / "dqn_model_1.pth"`，无法指向别的权重。
- 权重缺失时**静默回退**为 `epsilon=0.15` 的随机策略，只 print 一行提示 —— 用户看不出机器在瞎打。

## 任务

### 任务 1：checkpoint 路径可配置
新增一个 CLI 参数（建议 `--checkpoint`，也可用环境变量如 `DQN_CHECKPOINT`，**两者都支持更好**），优先级：命令行参数 > 环境变量 > 默认 `REPO / "dqn_model_1.pth"`。
- 入口在 `draw_me_vs_DQN_Plus.py`（看它怎么调用 `ui.app.main`）。
- 参数可以接受绝对路径或相对路径（相对路径按 REPO 解析）。
- 在 `ui/app.py` 里加一个清晰的解析函数（如 `resolve_checkpoint(arg=None) -> Path`），便于测试。

### 任务 2：权重缺失时明确可见告警，不要静默
- 保留回退行为（不崩溃更友好），但必须让用户**明显知道**机器当前用的是未训练随机策略。
- 至少做到：清晰的中文提示，写明「当前为未训练随机策略（epsilon=0.15），不是训练出的策略」，并提示如何提供权重。
- 建议同时提供**程序化可见性**：例如给 `Controller` 加一个属性（如 `self.trained: bool` 或 `self.policy_source`），让调用方/测试能判断当前是不是训练策略。**这个属性是任务 5/6 的测试钩子，必须有。**
- 加载成功时也应有一行提示（说明加载了哪个权重、epsilon=0.0）。

### 任务 3：headless 端到端测试（核心）
写一个 headless 测试，**不依赖 pygame 显示**（`SDL_VIDEODRIVER=dummy` 或直接用 `Controller` 而不开窗口），完整走通一局：
**人类输入 → 机器应招 → 回合交替 → 结算**
- 用 `ui.app.Controller`（它已有 `auto_human` 参数与回合调度逻辑）。
- 断言：
  1. 对局**自然结束**（`room.finish` 为 True）且 `room.winner` 不为 None；
  2. **回合确实交替**：`room.history` 里的 actor 序列在人类/机器之间来回（检查 `history` 中相邻的 actor 不同，或统计两侧各行动了若干次）；
  3. 人类动作走 `Controller.human_action(...)`（UI 的公开入口），机器动作走 `Controller` 内部的 AI 分支；
  4. **结算正确**：赢家是 `room.winner`，底池 `room.all_bet` > 0。
- **必须用真实权重**：断言 `controller.agent.epsilon == 0.0`，且 `controller` 的「已训练」标志为 True。

### 任务 4：断言机器动作确实来自训练权重，而非随机
这是验收第 6 条，必须做到。具体做法建议（可自行优化）：
- 构造若干个**已知状态**（用 `core.dealing.new_deck` + `deal_uniform` 发真手牌，`core.strength.beats_probability` 算强度），用**同一个训练权重**的 `DQNAgent.from_checkpoint` 算出期望动作；
- 再让 `Controller` 在相同状态下走一遍，确认**输出的动作完全一致**；
- 进一步：断言该动作**不等于**随机策略会做的动作 —— 注意随机策略会随机选，正确的做法是断言「加载权重的 agent 在相同状态下多次调用结果恒定（确定性）」，且**与未加载权重的 epsilon=1.0 随机 agent 显著不同**（例如跑 N 次统计动作分布，断言两者的分布不同，或断言加载权重的分布明显更集中）。
- 更强的做法：用 `agents.dqn.StateEncoder` 编码真实对局状态，把 `Controller` 实际执行的那个动作与 checkpoint 的 argmax 对比。

### 任务 5：补充其他测试
- 路径优先级测试：CLI 参数 > 环境变量 > 默认值。
- 权重缺失时的可见告警测试：断言「已训练」标志为 False，且提示文本包含关键信息。
- 权重存在时：断言 `epsilon == 0.0`、「已训练」标志为 True。

### 任务 6：文档
- `docs/` 下写一份简短说明：如何用训练产出的权重启动 UI、权重从哪来、如何指定自定义路径、缺权重时的行为。
- `README.md` 同步更新相关说明（README 在你的授权范围内）。注意 README 的架构图与目录说明要与实际一致。

## 验收标准（逐条对应）
1. `ui/app.py` 的 DEFAULT_CHECKPOINT 指向自博弈训练产出的策略文件
2. checkpoint 路径可配置（CLI 参数或环境变量）
3. checkpoint 缺失时启动给出明确可见告警，而不是静默回退
4. 机器加载训练权重后 `epsilon == 0.0`，不是回退的 0.15
5. headless 端到端测试：一局中人类输入 → 机器应招 → 回合交替 → 结算，全程走通
6. 测试断言机器动作确实来自训练权重输出，而非随机采样
7. pytest 与 ruff 全绿，且相对改动前无既有测试被打红

## 常规检查
- `python -m pytest tests/ -v --tb=no`：**基线是 8 failed / 131 passed**，那 8 个失败是**既有环境问题**（`tests/test_agents.py` 与 `tests/test_scripts.py` 找 `REPO/dqn_model_1.pth`）—— **但注意：你的 worktree 里现在有 `dqn_model_1.pth` 了，所以这 8 个应该会转绿，全套件应该 139 passed / 0 failed**。请实测确认并如实报告（如果因为 `.gitignore` 或别的原因仍然失败，说明清楚）。
- `python -m ruff check .` → All checks passed
- 提交到你的分支。

## 交付报告（≤3500 字）
- 每个任务的改动（带 `文件路径:行号`）
- 路径优先级的最终规则
- 「已训练标志」的实现方式（属性名、类型）
- headless 端到端测试的**实际输出**（对局步数、history 交替情况、winner、底池）
- 「动作来自训练权重」的断言方式与实际结果
- pytest / ruff 结果（含那 8 个基线失败是否转绿）
- 未确认的标 UNKNOWN

所有结论带 `文件路径:行号`。
    - 授权：工具 bash, read, edit, write, grep, find, ls；路径 ui, tests, docs, README.md；额度 80000 tokens
        - Run R-0054a175-50bb-42b0-8a33-4f1feaa76bb7：SUCCEEDED；worker；模型 vllm-local/Qwen3.8-27B；1252548 tokens
- Delegation G-f97cbe4a-94ef-4db9-87bf-94ea63b07184：reviewer
    - 目标：【T3 独立复核：玩家 vs 机器对抗接线，commit 4e6570a + bfa9881】

**worktree**：`/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/human-vs-machine`
**分支**：governance/human-vs-machine，**HEAD = `bfa9881`**（`4e6570a` 功能 + `bfa9881` 证据日志）
**只读复核**：不改源码、不提交。

## 第一步：确认你有 bash
跑：`bash -lc 'echo TOOL_OK && git log --oneline -1'`
**若 bash 不存在 → 立刻回复说明，不要空等。**（前几轮 reviewer 栽在这里，根因已修：`.pi/settings.json` 的 agentOverrides 覆盖了 agent 定义文件的 tools 且当时未提交。已修复并提交 d67a0c0 + e4e44f6。）

## 背景
T3 目标：让 UI 的机器对手真正使用 T2 自博弈训练产出的 DQN 策略，而不是随机策略。
**你的 worktree 里已放置真实权重**（被 .gitignore 忽略，不在 git diff 内）：
- `dqn_model_1.pth`（= `run/final/dqn_sp_ep100_seed7.pth`，UI 默认加载位置）
- `run/final/dqn_sp_opp_ep100_seed7.pth`

worker 声称已实现：checkpoint 路径可配置（CLI > 环境变量 > 默认）、缺失时三行醒目告警、`Controller.trained` 标志、headless 端到端测试、动作与训练权重 argmax 逐回合比对。

**Main Agent 已独立实测（供对照，你必须自己重算）**：
- pytest：**156 passed / 0 failed**（原 8 个基线失败因权重就位而全部转绿）；ruff All checks passed
- 路径优先级实测：默认 → `REPO/dqn_model_1.pth`；`DQN_CHECKPOINT=/tmp/from_env.pth` → 生效；CLI `/tmp/from_cli.pth` + env 同时给 → CLI 生效；相对路径 `run/final/...` → 按 REPO 解析
- headless 端到端：`trained=True`、`epsilon=0.0`、对局自然结束（winner=1、底池 420）、history 座位序列 `[0,1,0,1,0]` **严格交替**、双方行动 3/2 次
- 缺失权重：三行 `[警告]`，明确写「未训练随机策略（epsilon=0.15），不是训练出的策略」，`trained=False`、`policy_source=untrained-random(epsilon=0.15)`
- **变异测试**（Main 实做）：把 `ui/app.py:84` 的 `DQNAgent.from_checkpoint(checkpoint, ...)` 改成 `DQNAgent(input_dim=4, action_dim=6, ..., epsilon=0.15)` → 6 个测试 FAILED；还原后 17 passed
- 红线：`git diff 7d58d4e..4e6570a --stat` 仅 `README.md` / `docs/TRAINED-WEIGHTS-UI.md` / `tests/test_trained_ui.py` / `ui/app.py`；`core/`、`agents/` **零改动**

## 请用 bash 逐条核验 7 条验收
1. `ui/app.py` 的 `DEFAULT_CHECKPOINT` 指向自博弈训练产出的策略文件 —— 用 md5/sha256 比对 `dqn_model_1.pth` 与 `run/final/dqn_sp_ep100_seed7.pth` 是否一致；并确认 T2 的权威产物路径。
2. checkpoint 路径可配置 —— 实测三种优先级；确认 CLI `--checkpoint` 真的能被 `draw_me_vs_DQN_Plus.py` 透传（**注意：`draw_me_vs_DQN_Plus.py` 不在 worker 的授权路径内，worker 声称靠 argparse 自动读 sys.argv，请实测 `python draw_me_vs_DQN_Plus.py --help` 与实际传参路径**）。
3. 缺失时明确可见告警 —— 实测缺失与**损坏**权重两种情况；检查告警文本是否明确说明「不是训练出的策略」。
4. 加载训练权重后 `epsilon == 0.0`（不是 0.15）—— 实测。
5. headless 端到端：人类输入 → 机器应招 → 回合交替 → 结算 —— 实跑并给出步数/history/交替性/winner/底池。
6. **动作确实来自训练权重输出，而非随机采样** —— 检查 `tests/test_trained_ui.py` 的断言强度，并**自己做一次变异测试**确认能抓到「换成随机策略」：
   - `cp ui/app.py /tmp/app.bak`
   - 把 `DQNAgent.from_checkpoint(checkpoint, seed=self.seed)` 改成 `DQNAgent(input_dim=4, action_dim=6, seed=self.seed, epsilon=0.15)`
   - 跑 `python -m pytest tests/test_trained_ui.py -q` 确认 **FAILED**
   - `cp /tmp/app.bak ui/app.py` 还原，用 `git diff --stat ui/app.py` 确认已还原（必须为空）
7. pytest 与 ruff —— 实测，并**与基线对比**：基线 `7d58d4e` 在**有权重**的条件下应为 156 passed / 0 failed；请确认无既有测试被打红（特别 `tests/test_ui.py`、`tests/test_agents.py`、`tests/test_scripts.py`）。

## 追加核验
8. **红线**：`git diff 7d58d4e..HEAD --stat`；确认 `core/`、`agents/` 零改动；`ui/` 的 snapshot/view 五字段契约未变；状态编码仍 4 维输入 / 6 维动作。
9. **worker 声称的额外改动**：`ui/app.py:85` 的 except 元组补了 `pickle.PickleError` —— 实测损坏权重（写一个随机字节的 .pth）是否真的不再崩溃，而是走可见告警回退。**这是 worker 自行扩大的健壮性改动，请判断是否恰当。**
10. **`docs/TRAINED-WEIGHTS-UI.md` 与 `README.md`** 内容是否属实、有无与实现不一致。
11. 检查有无**遗留问题**：例如 `ui/app.py` 里 `Controller.__init__` 的 `checkpoint` 默认改为 None 后，其他调用方（`tests/test_ui.py`、`draw_me_vs_DQN_Plus.py`）是否都还能正常工作。

## 输出纪律
- **边做边写**：先写好标题与已确认小节，每验证完一项就补进去。
- **总输出 ≤4000 字**。**目标 20 分钟内完成**。
- 定点看代码用 `sed -n 'M,Np'` / `grep -n`，不要 cat 整个文件。

## 报告落点
- 有写工具 → 写 `docs/review_human_vs_machine.md`（不要 git 提交）
- 无写工具 → 直接把完整报告作为最终消息返回

报告结构：每条判定（通过/不通过/部分通过/UNVERIFIED）+ **你自己实测的数字** + 证据（命令输出或 `文件路径:行号`）；变异测试的实际输出；**必须返工项**（没有就明确写"无"）；风险与遗留；未确认标 UNKNOWN。

**不要替 worker 补写代码**，只报告问题。**不要修改 pi 源码**。
    - 授权：工具 bash, read, edit, write, grep, find, ls；路径 ui, tests, docs, README.md；额度 45000 tokens
        - Run R-14cb6c25-afc2-4d9a-9e41-35986e27b782：RUNNING；reviewer；模型 vllm-local/Qwen3.8-27B；用量未知
