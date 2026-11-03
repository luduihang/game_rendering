全部完成并验证。交付报告如下：

## T5b 交付报告

### 1. 新增章节及位置（docs/ARCHITECTURE.md，439 → 565 行）
- **4.4 自博弈环境**（L155）：DQN 对手注入、对手视角 4 维观测（`_opponent_observation` env.py:220-224）、严格零和（`_settle_rewards` env.py:226-232 未改 + 塑形对消 :188-189）、逐局座位交换（env.py:112-121，座位 0 恒先手 core/rules.py:60 未改）、MAX_STEPS=200 强停（env.py:31/:190）
- **4.5 根因与解法**（L164）：bet_100 塌缩现象（底池 20060）→ 根因（±all_bet 随押注额线性增长 → Q 单调偏好最大押注）→ strength_shaping 按**押注额**计酬 `k·(p−0.5)·押注额`（env.py:172/:186）→ 按底池计会自增强的死循环论证 → k=50 实测（0.008~0.149 / 0.84~0.97 / 1.000 单调、natural_end_rate=1.0、seed=7 胜率 56/44）
- **4.6 训练与评估入口**（L176）：robot/self/snapshot 三模式（train.py:44）、`--preset selfplay-v1` 全配方逐项行号（train.py:51-62）、复现命令与产物路径、sha256 可复现性依赖 `set_global_seed`（train.py:65-70 + dqn.py:112/114-115）、hidden 陷阱（from_checkpoint 不推断隐藏宽度）、evaluate 双 checkpoint + natural_end_rate + 隐藏层自适应（evaluate.py:35-46）
- **4.7 机器对手接线**（L196）：入口→`resolve_checkpoint`（ui/app.py:33-47，CLI>DQN_CHECKPOINT>默认）→`_load_agent` 三行告警（:113-116）与回退（:117）、`trained`/`policy_source`（:98-99）
- **4.8 权重获取与存放**（L218）：一条命令产出、两种部署方式、`.gitignore` `*.pth`/`run/` 不入版本库、160 passed/0 failed 实测
- **6.10/6.11/6.12**（L398/418/429）：3 份新测试文件断言清单
- **7.4 追加**自博弈陷阱条目（L488 附近）；**7.6/7.7 逐条处置标注**；README 不一致节加处置说明

### 2. 措辞修正（6 处，任务 5 处 + CONTENT-STALE.md 的 button_rects 1 处）
1. `:153` → 「imports（evaluate.py:22-23）：22 → agents.dqn、23 → scripts.env，该文件无 core.rules import（原文为误述，已修正）」
2. `:426` 补充行 → 「已处置（v0.2.1 移除），现 extend-exclude = ["__pycache__", ".venv", "src"]（pyproject.toml:42）」；「概率大小映射」一条标保留
3. `:385` last_now → 「已处置（v0.2.1 移入 `__init__`：def 于 ui/app.py:79，self.last_now 在 :104）」
4. `:381` missing_assets → 「已处置（check_assets() ui/app.py:69 调用 theme.missing_assets()，调用点 ui/app.py:334）」
5. `:380` 键码映射 → 「已处置（key_to_action_map() ui/app.py:50，_on_key :260 调用）」
6. `:382` button_rects → 「已处置（注解现为 dict[int, pygame.Rect]，ui/theme.py:134）」

### 3. 第 6 节测试用例数（`grep -n "def test_"` 实测）
- tests/test_selfplay.py：**15**；tests/test_selfplay_preset.py：**6**；tests/test_trained_ui.py：**15**（共 36）

### 4. sed/grep 确认的代表性 file:line
- scripts/env.py:118（座位翻转式）、:172（塑形押注项）、:226-232（零和结算 docstring+实现）
- scripts/train.py:51-62（SELFPLAY_V1 逐键）、:65-70（set_global_seed）、:236/:240（产物命名）
- agents/dqn.py:112（仅 seed self.rng）、:114-115（torch 全局 RNG 建网）
- ui/app.py:33-47（resolve_checkpoint 全函数）、:113-117（三行告警+回退）、:332/:334（Controller 构造/check_assets 调用）
- core/rules.py:60（whose_turn 初值 0）、evaluate.py:23（确认是 scripts.env import）、pyproject.toml:42、theme.py:134、.gitignore（*.pth/run/）

### 5. CHANGELOG
追加在文件末尾（原最后条目 [0.2.1] 之后）新增 **`## [0.3.0] — 自博弈训练与 UI 机器对手接线`**（沿用 CHANGELOG 时间正序；S/M 清理与 README 修正不重复记录，注明见 [0.2.1]）。

### 6. UNKNOWN
- 6.10~6.12 断言摘要按测试名概括，未逐行引用各用例内部断言行号（已注明）
- core/__init__.py `__all__` 中 deal_strength_biased/verify_uniformity/EmptyDeckError 的逐条字符串行号未单独验证（strength_ordinal :24、new_deck :16、deal_uniform :43 已验证）
- 未跑任何测试（纯文档任务，源码零改动，git diff 仅 docs/ARCHITECTURE.md 与 CHANGELOG.md）