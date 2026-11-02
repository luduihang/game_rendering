## 核验结论（有条件通过）
8 个测试文件、README 两处不一致、5 条技术陈述全部核验一致，仅 1 处文档措辞偏强需修正。

## tests/ 断言比对
| 测试文件 | 文档声称 | 真实 assert 行号 | 判定 | 偏差摘要 |
|---|---|---|---|---|
| test_purity.py | core 不 import pygame；摘 pygame 后 6 模块可导入；不依赖 numpy/scipy/torch/matplotlib | :16、:25、:49（_Blocker 注入 :43-44）、:63（正则 :8） | ✓ | — |
| test_agents.py | D8 (4,6) 自适应/硬编码 9 维报错/D9 epsilon==0.0 等 16 项 | :29-30、:35-37、:45-46、:49-50、:56、:63、:84、:93、:97、:104-106、:114、:124-125、:145、:152、:157-158、:163/168、:180、:191、:199、:219 | ✓ | 个别边界差 1 行（文档 :100-105 实为 100-106），非实质 |
| test_ui.py | 零 sleep/QUIT 响应/view=snapshot 五字段/性能上限等 26 项 | :45、:53、:58/61、:65、:77、:91、:100、:108、:119、:130-134、:140、:147-148、:165、:173、:180-183、:188-189、:207-208、:217-230、:238-241、:247-248、:255-258、:276-277、:289-293、:298、:303 | △ | 6.3 行「合法动作仅在人类回合非空」（:142-148）偏强：真实 assert 只验证人类回合非空（:147-148），未断言 AI 回合为空 |
| test_scripts.py | 同种子 2026 两次 train 的 weights_hash/avg_reward 严格相等 | :73-74（异种子 :79） | ✓ | — |
| test_rules.py | D1 四参数化/D2 单调/D4 结束拒绝等 12 项 | :39-40、:47-48、:57-58、:64、:71/73/78（raises :76-77）、:84-85、:90-92、:100/102-103、:109-111、:121、:127-131、:136-139、:144-146、:154 | ✓ | — |
| test_dealing.py | D6 均匀 3 张不重复、均值∈(0.44,0.56)、偏置差>0.15 等 8 项 | :46-47、:52、:59、:66、:73-75、:83、:94-95、:100-101 | ✓ | 文档 :69-74 实为 69-75（边界差 1 行） |
| test_strength.py | 22100 精确表、确定性/边界/单调/性能等 8 项 | :20、:27、:31、:34-35、:42、:53、:60-61、:72、:80 | ✓ | — |
| test_evaluator.py | 六类牌型、A-K-Q/A-2-3 边界、排序、花色决胜 7 组 | :19-34、:39、:43、:47、:51-52、:55-58、:73-74、:79、:84、:89、:94、:101-102、:107、:112 | ✓ | — |

## 第 6 节遗漏项检查
无整类遗漏：8 个抽样文件的每个 test 函数均在 6.1-6.8 表格出现（计数 4/12/8/8/7/16/13/26 全中）；tests/ 目录恰为这 8 文件 + baseline/，全部列出。tests/baseline/* 的行号引用（6.9）不在抽样范围，标**未核验**；ci.yml:50-58 基线循环已独立验证属实（:53-54 脚本名单吻合）。

## README 不一致复核
- **(a) 成立**：README.md:28「draw_me_vs_DQN_Plus.py (6 行)」vs 实际 14 行（docstring :1-9，可执行 :11、:13、:14）。
- **(b) 成立**：README.md:44-48（▼ 位于 :48）箭头画成 core/agents→scripts，与 README.md:52 文字「scripts → core/agents」相反；代码侧 scripts/env.py:13-17、train.py:23-24、evaluate.py:18-20 均 import core/agents，真实方向为 scripts→core/agents。文档两条声称均准确。

## 文档自身陈述抽查（5 条）
1. 入口薄化 14 行：draw_me_vs_DQN_Plus.py:11,13-14，无星号导入/sleep/load_state_dict/pygame.init() ✓（与 test_ui.py:177-183 一致）
2. 依赖方向 scripts→core/agents：env.py:13-17、train.py:23-24、evaluate.py:18-20 ✓
3. 惰性建表 22100：strength.py:24 @lru_cache、:25-27 combinations 枚举、:30-31 table_size、:58 strongest_hand 不走缓存 ✓
4. D8：dqn.py:62-67 checkpoint_dims（:67 读 shape）、:136→:140 按实际维度构建、torch.load 全在函数体（:64/:141/:210）✓
5. D6 默认均匀：dealing.py:3-5 docstring、deal_uniform :34-38、deal_strength_biased :41-61；全仓 *.py grep `draw_strength_biased` 0 匹配 ✓

## 发现的具体问题
- 阻断：无。
- 需修正：6.3「合法动作仅在人类回合非空」（test_ui.py:142-148）措辞偏强，测试未断言 AI 回合为空，建议改为「人类回合合法动作非空」。
- 建议：① README 分层约束表自称「ui/、scripts/ 无 time.sleep」由 test_no_sleep_in_source 守护，但该测试只扫 ui/（test_ui.py:63-65）——文档未列、属 README 额外 overclaim；② 个别行号边界差 1 行（test_agents.py:100-105→100-106、test_dealing.py:69-74→69-75）；③ 6.9 baseline 行号未核验。

## 总体结论（有条件通过）
文档与 tests/ 断言、README 声明无实质矛盾，1 处措辞修正后即可完全通过。