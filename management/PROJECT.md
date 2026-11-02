# 项目契约

## 当前生效基线

状态：ACTIVE
已批准版本：r1
目标：建立一份可被检索、有代码证据的架构知识库（docs/ARCHITECTURE.md），让后续任何重构提议都能引用具体文件路径与行号；同时把「Main Agent 只做调度与编排、不亲自实现」固化为基线约束。
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
- .github
预算：1900000 tokens
已分配任务预算：1800000 tokens
重要人工审批条件：
- 删除、重命名或移动任何既有文件（本次仅允许新增 docs/ARCHITECTURE.md）
- 修改 core/ agents/ ui/ scripts/ tests/ 下任何业务代码
- 新增、升级或移除任何第三方依赖
- 改变 Main Agent 的角色定位（禁止亲自实现）
- 把子 Agent 模型从 vllm-local/Qwen3.8-27B 换成其它模型
- 提高委派深度（当前固定 1 层）或把 maxConcurrent 提到 3 以上
- 任何 git 合并到 main（integrateBranch 需人工执行）
- 超出本基线范围的架构改动或新功能开发
任务审批策略：v1；默认 ask；规则 no-integrate, no-credential-paths, no-repo-internals, no-deep-delegation, no-unbounded-budget, read-only-survey-auto, survey-doc-write-auto

## 待审核草稿

无。
最近拒绝的修订：无
