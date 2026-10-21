# 阶段计划（r3）

## 分支与提交策略（r3 新增）
- 全流程在 `refactor/arch-v2` 特性分支上进行；不开子分支（maxDepth=1 的委派仅限只读分析）。
- 每 Phase 至少一个 commit，commit message 前缀 `P0:`…`P6:`；修复类 commit 附「失败测试先行」的证据（先提交失败测试，再提交修复）。
- `main` 的合并（integrateBranch）由人工执行，agent 不得自行合并。
- 任何历史改写（rebase/squash 已推送提交）禁止。

## Phase 0：基线核实与行为快照（阻塞后续全部阶段）
- T0.1 环境基线：建 venv，安装现有可用依赖，记录 python/torch/pygame/numpy/scipy 版本
- T0.2 仓库清单核实：`git ls-files`、`find` 枚举 .py、grep 计数 `class Game_room`/`class DQN`/`class DQNAgent`、`Cards_Probability`、`time.sleep(`、`threading.Timer`、`load_state_dict`、`from sympy`；检查 .gitignore/requirements.txt/备份/。**把 PRD 全部「未核实」条目落定并回写契约**
- T0.3 行为快照：最小复现脚本对 D1/D2/D4/D6/D7 逐项产出「当前实际行为」记录（看牌判胜反转、draw.py rest_option 下降、已结束局对手仍行动、发牌分布统计、单步耗时分解=计算/sleep/事件泵、等待期 QUIT 丢失），入 `tests/baseline/` 作为长期回归基线
- T0.4 接线复核（R3）：实测打印 DQN 手牌与传给机器人的牌，确认 D5 结论；不符则挂起请示
- T0.5 语义决策确认：R1（D6 是否修复）、R2（D1/D2 规则定义）取得人工结论并写入契约
- 验收：baseline_report.md 提交、基线脚本一键可跑、人工确认

## Phase 1：仓库卫生与依赖锁定
- T1.1 .gitignore + `git rm --cached` 产物（pycache/.pth/remember.txt/png）
- T1.2 备份/ 归档到仓库外（审批项）；无扩展名文件处理（审批项）
- T1.3 pyproject.toml 承载依赖与 ruff/pytest 配置并锁版本；移除 sympy 误依赖；`np.trapz`→`np.trapezoid`
- T1.4 重写 README（结构、入口、运行方式）
- 验收：`git status` 无未预期变更；新 venv 安装成功；ruff 可运行

## Phase 2：core/ 核心包（TDD，最关键）
- T2.1 Card/Suit/Rank + 牌型判定六类（含边界与平局）+ 花色决胜次序；测试先行
- T2.2 穷举精确胜率表：枚举 C(52,3)=22100 建表，O(1) 查询；提供「击败概率」与「档位分箱」两种接口以兼容 `get_state` 与 Robot.win_rate；若 R1 决定不修 D6，则在命名与文档上明确其为「相对强度」而非真实胜率
- T2.3 规则引擎 GameRoom：押注档位递增（沿用 Game_room 正确语义）、弃牌、看牌结算（D1 修复）、金币结算；非法动作抛 `IllegalAction`（D3 契约）；`own_hand`/`opponent_hand` 具名属性消除 D5 标签歧义
- T2.4 D1/D2/D4 回归测试，接 Phase 0 失败基线
- T2.5 旧脚本重复 Game_room 标记 deprecated（删除需审批）
- 验收：pytest 全绿；grep 证明判定/结算逻辑唯一；D1/D2/D4 先红后绿证据留存

## Phase 3：agents/ 智能体层
- T3.1 BaseAgent 接口（act / observe / reset / save / load）
- T3.2 DQN 独立模块：超参 dataclass 化、经验回放、目标网络、remember.txt 持久化显式可选；**权重加载改为显式工厂函数 `DQNAgent.from_checkpoint(path)`，禁止 import 期加载（D7-d）**
- T3.3 Robot 合并：单类 + 保守/激进两档参数；显式 import numpy
- T3.4 行为等价验证：同种子下新 Robot(激进档) 与旧 robot2 动作分布抽样一致
- 验收：接口冒烟通过；行为等价抽样通过；`grep load_state_dict` 仅出现在函数体内

## Phase 4：scripts/ 训练与评估入口
- T4.1 参数化训练入口（对手/回合/种子/设备/输出目录→run/），修复 D4（结束即停）
- T4.2 可复现性验证：≤20 回合、CPU-only、单次 ≤10 分钟，两次运行比对 state_dict 哈希
- T4.3 无头对战/评估入口（agent vs robot，输出胜率与押注统计），供 UI 复用
- 验收：无头跑通；可复现性脚本通过；run/ 不进 git

## Phase 5：ui/ 时序与事件循环重构（D7，工作量最大）
- T5.1 draw_* 副本收敛为 ui/ 包：只持渲染状态，押注/结算一律向 core 查询，删除自算逻辑与复制训练循环；新增 UI↔core 逐字段一致性断言
- T5.2 事件驱动主循环：`pygame.event.get()` 驱动状态机，任何分支不得阻塞；`check_button_click` 的忙等改为非阻塞 `poll_input()`，等待期间持续重绘并响应 SDL_QUIT
- T5.3 时序外置：删除全部 `time.sleep`，替换为可注入节奏器（real / fixed-step / immediate 三档；测试与 headless 用 immediate）
- T5.4 RepeatedTimer 处置：加锁 + 幂等 stop + 回调异常隔离，或删除改由帧 tick 驱动（删除属审批项）
- T5.5 资源路径集中管理（pathlib 相对包根），修复坏路径；`pygame.Rect` 移出类定义期
- 验收：headless 冒烟通过；`grep time.sleep` 为空；等待期 QUIT 响应测试通过；单步耗时断言通过

## Phase 6：质量收尾
- T6.1 ruff 基线清零；CI（ruff + pytest）
- T6.2 README 架构图 + 各入口说明；收尾报告对照 successCriteria 逐条勾选
- 验收：CI 绿；收尾报告人工验收

## 依赖关系
P0（含 T0.4 接线复核与 T0.5 语义决策）→ P1 → P2 → P3 → P4 → P5 → P6。
**P0 未通过不得进入 P2**（否则会在错误规则语义上写测试）。
P4 与 P5 技术上可并行，但同工作区写入者必须串行，故按 P4→P5 顺序执行。

## 调度
每 Phase 1-3 个内部任务；maxDepth=1，maxConcurrent=2；同一工作区写入者串行。任何触发 humanApprovalTriggers 的动作先挂起请示，不得自行推进。
