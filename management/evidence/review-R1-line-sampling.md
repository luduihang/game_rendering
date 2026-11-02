## 核验结论：通过——20 条抽样全部打开核对，19 条精确命中、1 条范围偏 1 行（内容正确），命中率 95%≥90%，未发现与结论矛盾的内容。

## 抽样核验表
| # | 文档位置 | 引用 | 该行实际内容摘要 | 判定 |
|---|---|---|---|---|
| 1 | §1 概览 | rules.py:26 | `BET_OPTIONS=(10,20,50,100)` | ✓ |
| 2 | §1 | evaluator.py:18-24 | HandType 六类 HIGH_CARD…TRIPS | ✓ |
| 3 | §1 | strength.py:24-27 | @lru_cache+combinations(full_deck(),3) 全枚举 | ✓ |
| 4 | §2 | core/__init__.py:11-14 | cards/evaluator/rules/strength 四行重导出 | ✓ |
| 5 | §2 | ui/render.py:16 | `import const` | ✓ |
| 6 | §2 | dqn.py:64 | checkpoint_dims 函数体内 torch.load | ✓ |
| 7 | §3 | scripts/env.py:16-17 | from core.dealing / from core.rules | ✓ |
| 8 | §3 | ui/app.py:25 | DEFAULT_CHECKPOINT=dqn_model_1.pth | ✓ |
| 9 | §3 | robot.py:25 | OPTION_INDEX={"10":0,…} | ✓ |
| 10 | §4 | draw_me_vs_DQN_Plus.py:11 | `from ui.app import main` | ✓ |
| 11 | §4 | ui/app.py:247-251 | run(): while self.running: step_frame() | ✓ |
| 12 | §5 | rules.py:58-66 | GameRoom 九字段逐行对应 | ✓ |
| 13 | §5 | ui/render.py:243 | `won = view["winner"] == 0` | ✓ |
| 14 | §5 | rules.py:154 | rest_option=max(rest_option,int(action)) | ✓ |
| 15 | §6 | test_strength.py:19-20 | assert table_size()==22100 | ✓ |
| 16 | §6 | test_ui.py:124-134 | view 与 snapshot 五字段断言 | ✓ |
| 17 | §6 | test_purity.py:8 | PYGAME_IMPORT 正则定义 | ✓ |
| 18 | §7 | algorithm.py:15 | `import pygame` | ✓ |
| 19 | §7 | dealing.py:3-5 | docstring：默认均匀、偏置不启用（D-R1） | ✓ |
| 20 | §8 | pyproject.toml:15-19 | numpy/scipy/matplotlib/torch 版本；pygame==2.6.1 在 :14 | 错位±1 |

## 行号错位清单
- pyproject.toml:15-19 → 实际 14-18（5 个版本锁跨度含 :14，±1，内容正确）
- §5 rules.py:160-170（_compare）→ 实际 161-170；:162 费用行 → 163（±1）
- §6.8 test_purity.py:15-16→14-15、:19-25→18-24、:28-52 起于 26（±1~2）
- §3/§7.7 core/__init__.py:16-30（__all__）→ 16-31（右括号在 31，±1，轻微）

## 不命中清单
无。附带核验的 rules.py:173（finish=True）、:175（money+=all_bet）、robot.py:1-9 迁入自述均精确命中。

## 总体结论：通过