# 交接

目标：把 UI 重构为事件驱动、零阻塞的薄渲染层：可注入节奏器替代 time.sleep、非阻塞 poll_input 响应 QUIT、状态一律向 core 查询、资源路径集中管理；并让保留策略在真实显示下完整走完一局且 AI 使用已训练权重。
验收：ui/ 包建立：clock.py（可注入节奏器 real/fixed-step/immediate）、app.py（事件驱动主循环）、render.py（薄渲染层，状态一律向 core 查询）；D7-a：ui/ 与 scripts/ 中不存在 time.sleep（grep 断言为 0）；D7-b：等待人类输入期间非阻塞，持续重绘，SDL_QUIT 被及时响应（headless 回归测试）；D7-c：RepeatedTimer 加锁 + 幂等 stop + daemon=True + 回调异常隔离（或改为帧 tick 驱动），并有单测；D7-d：不存在 import 期加载权重（grep 断言）；UI↔core 状态一致性：渲染使用的押注/金币/池值与 core.snapshot() 逐字段相等（断言测试）；headless 单步/单帧耗时断言（core step <5ms，UI 帧 <50ms）；真实显示下可从发牌到结算完整走完一局，AI 使用 dqn_model_1.pth（非随机）；const.py 坏路径修复（'../myclient/' 与 '../game_exercise/' 消除）、pygame.Rect 移出类体定义期；draw_me_vs_DQN_Plus.py 改为薄入口（无星号导入、无 sleep、无 import 期副作用）
权限：{"commitBranch":true,"integrateBranch":false,"paths":["."],"readRepository":true,"tools":["bash","read","edit","write"],"writeWorkspace":true}
当前工作空间：无
基线：无
未提交文件：无工作空间
最新交付：无
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
