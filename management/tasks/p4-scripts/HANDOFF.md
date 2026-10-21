# 交接

目标：建立 scripts/ 训练与评估入口：参数化训练（回合/种子/设备/输出目录→run/）、无头对战评估、同种子逐位可复现；产物不进入 git。
验收：scripts/ 包建立：train.py（参数化：回合数/随机种子/设备/输出目录）、evaluate.py（无头 agent vs Robot2 对战统计）；产物统一写入 run/ 且不进 git（.gitignore 已覆盖）；可复现性：同种子两次训练运行最终 state_dict 逐位一致（哈希比对断言），运行限定 ≤20 回合、CPU-only、≤10 分钟；D4 在训练循环层面验证：对局结束后不再有任何行动（IllegalAction 被捕获或循环提前退出）；两个入口均可无头运行（不 import pygame）；入口冒烟测试 + 可复现性测试通过
权限：{"commitBranch":true,"integrateBranch":false,"paths":["."],"readRepository":true,"tools":["bash","read","edit","write"],"writeWorkspace":true}
当前工作空间：无
基线：无
未提交文件：无工作空间
最新交付：无
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
