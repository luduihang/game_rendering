# 阶段计划

## Phase 0：基线核实与行为快照（阻塞后续全部阶段）
- T0.1 环境基线：建 venv，安装现有可用依赖，记录 python/torch/pygame/numpy/scipy 版本到 baseline_report.md
- T0.2 仓库清单核实：`git ls-files`、`find` 枚举全部 .py、grep `class Game_room` / `class DQN` / `class DQNAgent` / `def get_state` 计数、grep `Cards_Probability`、检查 .gitignore/requirements.txt/备份/ 是否存在。**把 PRD 中全部「未核实」条目落定并回写本契约**
- T0.3 行为快照：构造最小复现脚本，对 D1-D6 每项产出「当前实际行为」记录（看牌判胜反转、rest_option 下降、已结束局对手仍行动、get_state 读到对手牌、draw_cards_plus 分布统计）。这是后续「先红后绿」的固定失败基线
- T0.4 语义决策确认：就 R1（D6 是否修复）、R3（D1/D2 正确规则定义）取得人工结论并写入契约
- 验收：baseline_report.md 提交，D1-D6 复现脚本可运行，人工确认基线与规则语义

## Phase 1：仓库卫生与依赖锁定
- T1.1 .gitignore + `git rm --cached` 产物（pycache/.pth/remember.txt/png）
- T1.2 备份/ 归档到仓库外（审批项）；无扩展名文件处理（审批项）
- T1.3 requirements.txt 锁版本；移除 sympy 误依赖；`np.trapz`→`np.trapezoid`
- T1.4 重写 README（现仅一行）
- 验收：`git status` 无未预期变更；新 venv 一键安装成功；ruff 可运行

## Phase 2：core/ 核心包（TDD，最关键阶段）
- T2.1 数据模型 Card/Suit + 牌型判定六类（含边界与平局）+ 花色决胜次序；先写测试
- T2.2 穷举精确胜率表：一次性枚举 C(52,3)=22100 手，按牌面值排序建表，O(1) 查询；提供「击败概率」与「档位分箱」两种接口，以兼容 `get_state` 与 Robot 的 win_rate
- T2.3 规则引擎 GameRoom：押注档位递增（D2 统一语义）、弃牌、看牌结算（D1 修复）、金币结算；get_choice 增加合法性校验（D3）
- T2.4 D1/D2/D3 回归测试，接 Phase 0 的失败基线
- T2.5 旧脚本中重复的 Game_room 副本标记 deprecated（删除需审批）
- 验收：pytest 全绿；grep 证明判定/结算逻辑唯一；D1/D2/D3 测试修复前失败修复后通过

## Phase 3：agents/ 智能体层
- T3.1 BaseAgent 接口（act / observe / reset / save / load）
- T3.2 DQN 独立模块：超参 dataclass 化、经验回放、目标网络、remember.txt 持久化改为显式可选；修复 D5（状态改为读取本人手牌）
- T3.3 Robot 合并：robot.py + robot2.py → 单一 Robot，把两者系数差异提为配置档（conservative / aggressive）；显式 import numpy
- T3.4 行为等价验证：同种子下新 Robot(aggressive 档) 与旧 robot2 的动作分布抽样一致；DQN 在修复前旧状态语义下的加载路径给出明确迁移提示
- 验收：接口冒烟测试通过；行为等价抽样通过；旧 remember.txt 加载不崩溃

## Phase 4：scripts/ 训练与评估入口
- T4.1 参数化训练入口（对手类型/回合/种子/设备/输出目录→run/），修复 D4（结束即停）
- T4.2 可复现性验证：同种子跑两次，比对最终 state_dict 哈希逐位一致
- T4.3 评估/对战入口（agent vs robot，输出胜率与押注统计到 run/）
- 验收：无头跑通；可复现性脚本通过；run/ 不进 git

## Phase 5：ui/ 渲染层
- T5.1 draw.py 抽为 ui/ 包：只持有渲染状态，押注/结算一律向 core 查询，删除 UI 内复算逻辑与重复训练循环
- T5.2 资源路径集中管理：以 pathlib 相对包根解析，修复 '../game_exercise/'、'../myclient/'；把 `pygame.Rect` 从 const 类体定义期移到函数内，解耦 import pygame
- T5.3 主循环改为调用 scripts/ 的训练/对战入口，不再自带一份
- 验收：`SDL_VIDEODRIVER=dummy` UI 冒烟通过；静态检查证明 core/、agents/ 不含 `import pygame`

## Phase 6：质量收尾
- T6.1 ruff 基线清零；加 CI（ruff + pytest）
- T6.2 README 架构图 + 各入口说明；收尾报告对照 successCriteria 逐条勾选
- 验收：CI 绿；收尾报告人工验收

## 依赖关系
P0（含 T0.4 语义决策）→ P1 → P2 → P3 → P4/P5（可并行，同工作区串行）→ P6。
**P0 未通过不得进入 P2**，否则会在错误的规则语义上写测试。

## 调度
每 Phase 1-3 个内部任务；maxDepth=1，maxConcurrent=2；同一工作区写入者串行。任何触发 humanApprovalTriggers 的动作先挂起请示，不得自行推进。
