# 交接

目标：按 docs/ARCHITECTURE.md 第 7.7/7.6 节完成 S/M 级重构清理与 README 不一致修正，零行为风险。本 Task 与 selfplay-engine 文件不重叠，可并行。Main Agent 只调度编排，编码全部由子 Agent 完成。
验收：ui/app.py 键码差值映射改为显式映射表；ui/app.py 启动时改用 ui/theme.py 的 missing_assets() 做资源自检；ui/theme.py button_rects 返回注解改为 dict[int, pygame.Rect]；ui/app.py 的 last_now 由类级属性移入 __init__；core/__init__.py 的 __all__ 补齐 strength_ordinal / strongest_hand / dealing 相关符号，且保持惰性导入不变；README.md 三处不一致全部修正：入口行数、架构图箭头方向（scripts 上移为入口层）、time.sleep 守护声明改为不 overclaim 的两行表述；pyproject.toml 与 README.md 的目录说明同步实际内容；core/rules.py、core/strength.py、core/dealing.py、agents/dqn.py 零改动；pytest 与 ruff 全绿，且相对改动前无既有测试被打红
权限：{"commitBranch":true,"integrateBranch":false,"paths":["ui","core","tests","docs","README.md","CHANGELOG.md","pyproject.toml"],"readRepository":true,"tools":["bash","read","edit","write","grep","find","ls"],"writeWorkspace":true}
当前工作空间：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/cleanup-refactor
基线：6bd6253bf9e122fe1df982f50e20b1b47f050db0
未提交文件：M .agent/telemetry-state.json； M .agent/telemetry.jsonl； M .pi/agents/reviewer.md； M .pi/settings.json； M PROGRESS.md
最新交付：d069b77624d022a4f01a6bdd82f1ee473c7120c5
交付文件：M CHANGELOG.md；M README.md；M core/__init__.py；A management/evidence/logs/cleanup-pytest.txt；A management/evidence/logs/cleanup-ruff.txt；M pyproject.toml；M tests/test_purity.py；M tests/test_ui.py；M ui/app.py；M ui/theme.py
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
