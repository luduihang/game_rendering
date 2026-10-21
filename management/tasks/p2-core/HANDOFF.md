# 交接

目标：建立 core/ 核心包（纯逻辑、无 pygame），以 TDD 方式修复 D1（看牌结算比较方向与 whose_turn）、D6（默认均匀发牌）、D2（rest_option 单调不减纳入契约）与 D4（结束后拒绝继续行动），用穷举 22100 手精确表替代 2000 次蒙特卡洛胜率，并让牌型判定与结算逻辑成为唯一实现。
验收：core/ 包建立：cards.py（Card/Suit/Rank）、evaluator.py（六类牌型判定 + 比大小 + 花色决胜）、strength.py（穷举 22100 手精确表）、dealing.py（deal_uniform 默认 + draw_strength_biased 默认关）、rules.py（GameRoom 状态机 + IllegalAction）；D1 修复并先红后绿：看牌结算改为 winner = whose_turn if 自己手牌较大 else 1 - whose_turn；回归测试在修复前失败（tests/baseline/repro_d1_showcards.py 为证）、修复后通过；D6 修复并先红后绿：默认发牌均匀（分位均值≈0.5、最强档占比≈0.013）；draw_strength_biased() 显著更强且默认不被调用；D2 语义纳入契约测试：rest_option 单调不减（押注高档后不得降档）；GameRoom 对非法动作抛 IllegalAction；D4 修复：GameRoom 结束后拒绝继续行动，训练/对局循环不再出现结束后多走一步；手牌胜率穷举表：同一手牌任意次调用返回同一结果（确定性断言）；单次查询 < 0.1ms（对比基线 30.8ms 蒙特卡洛）；牌型判定六类全覆盖 + 边界/平局/花色决胜用例；pytest 全绿；断言 core/ 不 import pygame（静态检查 + 无 pygame 环境导入测试）；grep 断言 Card/判定/结算逻辑仅存在于 core/，无重复实现
权限：{"commitBranch":true,"integrateBranch":false,"paths":["."],"readRepository":true,"tools":["bash","read","edit","write"],"writeWorkspace":true}
当前工作空间：无
基线：无
未提交文件：无工作空间
最新交付：无
未决审批：无
接管前必须运行 workspace inspect，检查未提交和未跟踪文件。
