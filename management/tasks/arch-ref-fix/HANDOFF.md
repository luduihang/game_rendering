# 交接

目标：校正 docs/ARCHITECTURE.md 中因 T1~T4 重构而失效的 129 处 file:line 引用。清单已由 Main Agent 用脚本预先算好（含每条引用的旧内容、新行号、匹配方式），worker 不需要重新探索，只需定点核对并应用。这是 final-audit 拆分后的第一个 Task。
验收：129 处失效 file:line 引用全部校正：清单中 108 处「自动定位」的直接应用；21 处「锚点定位」的逐条定点核对后确认或修正；无法确认的改写为不依赖具体行号的表述并在报告中列明；校正后重跑校验脚本 management/evidence/retrospective/check_refs.py，失效引用数降为 0，且未引入新的越界引用；提交到分支，commit message 说明校正了哪些文件的引用
权限：{"commitBranch":true,"integrateBranch":false,"paths":["docs"],"readRepository":true,"tools":["bash","read","edit","write","grep","find","ls"],"writeWorkspace":true}
当前工作空间：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/arch-ref-fix
基线：c30b4f996f0208b256a36a8e58b5bc647c6b9e8b
未提交文件：M .agent/telemetry-state.json； M .agent/telemetry.jsonl； M PROGRESS.md
最新交付：7f593394c68b4a5d7c18bb80f87b9cb660566af6
交付文件：M docs/ARCHITECTURE.md
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
