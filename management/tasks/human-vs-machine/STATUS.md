# 任务状态

目标：跑通「玩家 vs 机器」的对抗：ui/ 侧默认加载自博弈训练产出的策略文件，机器用训练出来的逻辑（epsilon=0.0 贪心）而不是随机概率，并做 headless 端到端验证一局完整走通。这是用户的第二优先事项。Main Agent 只调度编排，编码全部由子 Agent 完成。
修订：1
类型：executable
父任务：无
子任务：无
批准：是
审批规则：baseline-subset / auto / 风险 low / sha256:80ac9c75f951a1b5532154746c8b7af4eb600324811f4219f30b133a420cf6df
验收：已通过
工作空间：/home/kipley/Documents/code/learning/.pi-governance-worktrees-85e3090611ea/human-vs-machine
最新交付：bfa9881406b07da20dd8947a8c6347b8d2edbffc
验证：passed
交付基线：6bd6253bf9e122fe1df982f50e20b1b47f050db0
交付改动：+1730 / -60

## 交付测试

| 命令 | 通过 | 失败 | 输出文件 | 核验 |
| --- | --- | --- | --- | --- |
| python -m pytest tests/ -v --tb=no | 156 | 0 | `management/evidence/logs/t3-pytest.txt` | 已核验 9b07eb0b5d6f |
| python -m ruff check . | 1 | 0 | `management/evidence/logs/t3-ruff.txt` | 已核验 82b3e6a6c090 |

## 交付文件

| 文件 | 变更 | 新增 | 删除 |
| --- | --- | --- | --- |
| `README.md` | M | 17 | 3 |
| `docs/TRAINED-WEIGHTS-UI.md` | A | 65 | 0 |
| `docs/selfplay_train_report.md` | A | 262 | 0 |
| `management/evidence/logs/selfplay-pytest.txt` | A | 27 | 0 |
| `management/evidence/logs/selfplay-ruff.txt` | A | 1 | 0 |
| `management/evidence/logs/t3-pytest.txt` | A | 20 | 0 |
| `management/evidence/logs/t3-ruff.txt` | A | 1 | 0 |
| `management/evidence/logs/train100-pytest.txt` | A | 28 | 0 |
| `management/evidence/logs/train100-ruff.txt` | A | 1 | 0 |
| `management/evidence/logs/train100-train.txt` | A | 8 | 0 |
| `scripts/env.py` | M | 198 | 19 |
| `scripts/evaluate.py` | M | 76 | 23 |
| `scripts/train.py` | M | 224 | 7 |
| `tests/test_selfplay.py` | A | 252 | 0 |
| `tests/test_selfplay_preset.py` | A | 245 | 0 |
| `tests/test_trained_ui.py` | A | 254 | 0 |
| `ui/app.py` | M | 51 | 8 |

## Run

- R-0054a175-50bb-42b0-8a33-4f1feaa76bb7 SUCCEEDED；Pi f6a1110c-cd4f-40a7-af95-40a445799bba；原生状态 complete；Agent worker；模型 vllm-local/Qwen3.8-27B；配置 qwen38；策略 4335f677177386421e266568c171f7539dde74107847c2bd3e7cee6a553a649c；Session /home/kipley/.pi/agent/sessions/--home-kipley-Documents-code-learning-game_rendering--/2026-11-01T15-12-21-269Z_01a197ab-3114-7697-b9c6-48613cba46e1/beb3a0cc-84f2-4049-9b11-91e206c72d06/run-0/session.jsonl；检查：`node .pi/governance/cli.ts run inspect R-0054a175-50bb-42b0-8a33-4f1feaa76bb7`；终态对账：`node .pi/governance/cli.ts run reconcile R-0054a175-50bb-42b0-8a33-4f1feaa76bb7`
- R-14cb6c25-afc2-4d9a-9e41-35986e27b782 SUCCEEDED；Pi 85c6e478-0b8d-4345-b82e-78d98573a104；原生状态 complete；Agent reviewer；模型 vllm-local/Qwen3.8-27B；配置 qwen38；策略 4335f677177386421e266568c171f7539dde74107847c2bd3e7cee6a553a649c；Session /home/kipley/.pi/agent/sessions/--home-kipley-Documents-code-learning-game_rendering--/2026-11-01T15-12-21-269Z_01a197ab-3114-7697-b9c6-48613cba46e1/57a75a2c-0704-4607-8f21-a4240f3fc4f5/run-0/session.jsonl；检查：`node .pi/governance/cli.ts run inspect R-14cb6c25-afc2-4d9a-9e41-35986e27b782`；终态对账：`node .pi/governance/cli.ts run reconcile R-14cb6c25-afc2-4d9a-9e41-35986e27b782`
