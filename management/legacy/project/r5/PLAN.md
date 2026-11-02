# 阶段计划（r5）

## 分支与提交策略
- 全流程在 `refactor/arch-v2` 特性分支；`main` 合并由人工执行。
- 每 Phase 至少一个 commit，前缀 `P0:`…`P6:`；修复类 commit 先提交失败测试再提交修复。
- 删除类改动单独成 commit，并在 `CHANGELOG.md` 记录完整删除清单（可 git 恢复）。

## P0 基线核实（已完成）
- 环境恢复可运行：pygame 2.6.1 安装、matplotlib 3.8.0→3.11.2 修复 numpy 2.x ABI、ruff 0.17.1
- 仓库/依赖/阻塞点清单落定；D1/D2/D4/D5/D6/D7 复现脚本入 `tests/baseline/`
- 产出 `docs/BASELINE-REPORT.md`；发现 D8（权重维度失配）、D9（保留策略未加载权重）
- 验收：报告已产出；待人工确认后关闭任务

## P1 单一策略清理与仓库卫生
- T1.1 写 `CHANGELOG.md` 记录删除清单 → 删除 15 个策略脚本 + `mymath/robot.py` + `备份/`
- T1.2 归档多余模型/统计产物（保留 `dqn_model_1.pth`）；`git rm --cached` 产物（pycache/remember/q_table/png）
- T1.3 `.gitignore` + `pyproject.toml`（依赖锁定 + ruff/pytest 配置）；移除 12 处 `from sympy import false`；`np.trapz` 替换
- T1.4 重写 README（单入口、运行方式、架构）
- 验收：仓库只剩保留策略可运行；`git status` 无未预期变更；ruff 可运行；新环境按 pyproject 一键装好

## P2 core/ 核心包（TDD）
- T2.1 Card/Suit/Rank + 牌型判定六类（含边界/平局/花色决胜），测试先行
- T2.2 穷举 22100 手精确表（O(1) 查表替代 30.8ms/次的蒙特卡洛）；提供「击败概率」与「档位分箱」接口
- T2.3 规则引擎 GameRoom：押注档位递增、弃牌、看牌结算（D1 修复）、金币结算；非法动作抛 IllegalAction；`own_hand`/`opponent_hand` 具名属性
- T2.4 D1/D2/D4 回归测试（对接基线失败快照）
- T2.5 吸收 `game_room_deepseek_cp.py` 的 Game_room 后删除该文件
- T2.6 `core/dealing.py`：`deal_uniform()`（默认）+ `draw_strength_biased()`（默认关）；均匀性检验
- 验收：pytest 全绿；D1/D2/D4 先红后绿证据留存；grep 证明规则唯一实现

## P3 agents/ 智能体层
- T3.1 BaseAgent 接口（act/observe/reset/save/load）
- T3.2 DQN 模块：超参 dataclass、回放、目标网络、`from_checkpoint(path)` 按 checkpoint 实际维度构造（D8）
- T3.3 Robot2 迁入 agents/ 成为唯一对手策略，显式 import numpy
- T3.4 保留策略接入真实权重（D9）：`dqn_model_1.pth` 4 维策略生效，`select_action` 不再是死代码；epsilon 不再恒为 1.0
- 验收：接口冒烟；同种子动作分布可复现；`grep load_state_dict` 仅在函数体内；策略加载后首步动作与随机基线显著不同

## P4 scripts/ 入口
- T4.1 参数化训练入口（回合/种子/设备/输出→run/），修复 D4
- T4.2 可复现性：≤20 回合、CPU-only、≤10 分钟，两次 state_dict 哈希一致
- T4.3 无头对战入口（DQN vs Robot2，输出胜率与押注统计）
- 验收：无头跑通；可复现性通过；run/ 不进 git

## P5 ui/ 时序与事件循环重构（保留策略可稳定启动）
- T5.1 Draw_Pic 收敛为 `ui/` 薄渲染层，状态一律向 core 查询，新增 UI↔core 逐字段一致性断言
- T5.2 事件驱动主循环：移除 `while not signal` 忙等，改非阻塞 `poll_input()`；等待期持续重绘并响应 QUIT
- T5.3 删除全部 `time.sleep`，替换为可注入节奏器（real/fixed-step/immediate）
- T5.4 RepeatedTimer：加锁 + 幂等 stop + daemon + 异常隔离，或改由帧 tick 驱动
- T5.5 资源路径集中管理（pathlib 相对包根），修复坏路径；`pygame.Rect` 移出类定义期
- 验收：真实显示下完整走完一局；等待输入时窗口可关闭；`grep time.sleep` 为空；单步耗时断言通过

## P6 质量收尾
- T6.1 ruff 清零；CI（ruff + pytest）
- T6.2 README 架构图 + 入口说明；收尾报告对照 successCriteria 逐条勾选
- 验收：CI 绿；收尾报告人工验收

## 依赖关系
P0（已完成，待确认）→ P1 → P2 → P3 → P4 → P5 → P6。
**P1 的删除不可逆地改变仓库形态，必须在本契约批准后执行**；删除内容始终可经 git 历史恢复。

## 调度
每 Phase 1-3 个内部任务；maxDepth=1，maxConcurrent=2；同工作区写入者串行；触发 humanApprovalTriggers 的动作先挂起请示。
