# 交接

目标：恢复原始贴图渲染：下注/弃牌/看牌按钮使用 src/button 原图、双方头像使用 src/character 角色原图、钱包与押注显示 src/item_pic/金币.png 图标；游戏逻辑、规则与智能体零改动，仅替换 UI 绘制来源，并在缺图时安全回退。
验收：六个动作按钮改用原始贴图：src/button/{十注,二十注,五十注,一百注,弃牌,看牌}.png，按布局等比缩放；双方头像改用原始角色图：人类=src/character/火花.png，DQN=src/character/雪影娃娃第三阶段.png（可配置）；钱包与押注金额前显示 src/item_pic/金币.png 图标；任一贴图缺失时回退为现有文本/占位绘制，不崩溃、不影响行动；逻辑零改动：core/、agents/、scripts/ 无任何修改（git diff 为空）；UI↔core 状态一致性测试仍通过；按钮命中区域与实际绘制图像重合（命中测试断言）；新增贴图相关测试（资源映射、缺图回退、命中区域），pytest 与 ruff 全绿；截图验证渲染正确，并附在任务验收说明中
权限：{"commitBranch":true,"integrateBranch":false,"paths":["."],"readRepository":true,"tools":["bash","read","edit","write"],"writeWorkspace":true}
当前工作空间：无
基线：无
未提交文件：无工作空间
最新交付：无
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
