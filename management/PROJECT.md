# 项目契约

## 当前生效基线

状态：ACTIVE
已批准版本：r4
目标：按 docs/ARCHITECTURE.md 第 7 节完成 S/M 级重构与 README 三处不一致修正；实现 DQN 对抗 DQN 自博弈训练，用训练产出的真实权重驱动交互界面的机器对手（保持人类 vs 机器模式），消除当前因权重缺失而静默回退为随机策略的问题。
范围（inScope）：
- core
- agents
- ui
- scripts
- tests
- docs
- draw_me_vs_DQN_Plus.py
- algorithm.py
- const.py
- README.md
- CHANGELOG.md
- pyproject.toml
- run
预算：60000000 tokens
已分配任务预算：9090000 tokens
重要人工审批条件：
- 触碰「不可碰」清单：core/rules.py 的规则语义、core/strength.py 的建表时机、agents/dqn.py 的 from_checkpoint 机制、core/dealing.py 的默认发牌、ui/ 的 snapshot/view 五字段契约
- 任何改变状态编码维度（4 维输入 / 6 维动作）或多出/少出动作的改动
- 删除、重命名或移动任何既有源码文件
- 新增、升级或移除任何第三方依赖
- 训练局数超过 100 轮，或需要完整重训/超长训练
- 把机器对手从 DQN 换成非 DQN 策略（Robot、规则、随机）
- 改变自博弈的对称性口径（座位交换、零和奖励）
- 把 .pth 权重文件纳入版本库，或改变 .gitignore 对权重的处理
- 提高委派深度（当前固定 1 层）或把 maxConcurrent 提到 3 以上
- 任何 git 合并到 main（integrateBranch 需人工执行）
任务审批策略：v1；默认 ask；规则 no-integrate, no-credential-paths, no-repo-internals, no-deep-delegation, no-unbounded-budget, read-only-survey-auto, implement-in-scope-auto

## 待审核草稿

无。
最近拒绝的修订：无
