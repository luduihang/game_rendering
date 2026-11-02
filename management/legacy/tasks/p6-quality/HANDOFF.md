# 交接

目标：质量收尾：建立 CI（ruff+pytest），补齐 README 架构与入口说明，验证干净环境安装可跑通全部入口，产出逐条对照 r5 successCriteria 的收尾报告。
验收：CI 配置建立（ruff + pytest），本地以等价命令验证通过；README 补齐架构图与四个入口（游戏/训练/评估/测试）的使用说明；干净虚拟环境按 pyproject 安装后跑通训练、评估、UI 冒烟（含 headless）；docs/FINAL-REPORT.md 逐条勾选 r5 的 16 项 successCriteria，每项附可验证证据（命令或提交）；全部 ruff 检查通过、pytest 全绿、基线回归脚本 D1-D7 全部 passed；治理任务状态与 CHANGELOG 更新到最终形态
权限：{"commitBranch":true,"integrateBranch":false,"paths":["."],"readRepository":true,"tools":["bash","read","edit","write"],"writeWorkspace":true}
当前工作空间：无
基线：无
未提交文件：无工作空间
最新交付：无
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
