## 调查目标
只读调查 game_rendering 表现层 ui/（app.py、clock.py、render.py、theme.py、__init__.py），对 10 个必答项给出 file:line 证据，供 Main Agent 汇总进 docs/ARCHITECTURE.md。

## 涉及文件（含行数）
- `ui/app.py`（283 行）：`Controller`（回合状态机，非阻塞）+ `App`（pygame 事件循环）+ `main()`
- `ui/clock.py`（75 行）：`TickPolicy` 枚举 + `Ticker` 节奏器
- `ui/render.py`（253 行）：`Renderer` 薄渲染层
- `ui/theme.py`（170 行）：资源路径映射 + `Layout` 布局常量
- `ui/__init__.py`（12 行）：包导出
- 参照 `const.py`（资源路径常量，ROOT/src 相对路径，const.py:15-23）

## 关键代码位置（file:line + 该处做什么）
1. **主循环**：`App.run()` ui/app.py:247-251；`while self.running:`（248）循环体仅 `self.step_frame()`（249）+ max_frames 提前退出（250-251）。**无 sleep**，帧率上限在 `Ticker.end_frame` 的 `pygame.time.Clock.tick(60)`（ui/app.py:244 → ui/clock.py:44-51）。`step_frame` 帧结构 ui/app.py:229-245：begin_frame(230)→now(231)→set_now(232)→pump_events(233)→`if not running: return`(234-235)→update(236)→draw+flip(237-243)→end_frame(244)。
2. **pump_events**：ui/app.py:185-200；`pygame.event.get()`（191，非阻塞一次取空队列）；QUIT（195-196）→`self.running=False`；KEYDOWN→`_on_key`（197-198）；左键→`_on_click`（199-200）；pygame 未初始化时提前 return（188-189，纯逻辑模式）。
3. **Controller.update**：ui/app.py:88-106；`while not finish and guard<64`（90）。AI 回合：`if now < self.ai_deadline: return`（93-94）——**提前 return，非忙等**；到期→`_ai_move`(95)→`_schedule`(97)→若仍 AI 回合 return(98-99)。人类回合：非 auto_human（或未到 deadline）`return`（101-102）——控制权交还主循环，由其持续重绘并等事件；auto_human 到期自动随机出牌（103）。人类输入入口 `human_action` ui/app.py:131-139：校验回合/合法性(132-135)→`_apply`(136)→`_schedule(last_now)`(137)。
4. **clock.py**：模式名 **`TickPolicy`**（enum）ui/clock.py:18-22（REAL/FIXED/IMMEDIATE）；类 **`Ticker`** ui/clock.py:24；关键方法：`begin_frame`(36-42 返回 dt)、`end_frame`(44-51，REAL 惰性建 pygame.time.Clock 限帧 48-50)、`now()`(54-61：REAL=perf_counter 57 / FIXED=虚拟时钟 59 / IMMEDIATE=每帧 1 秒步长 61)、`deadline()`(63-64)、`due()`(66-67)。
5. **render.py 只绘制不记账**：`Renderer.draw(surface, view)` ui/render.py:101-118，状态全部取自 view dict（由 `Controller.view()` 生成，ui/app.py:150-171，数据源 `room.snapshot()` app.py:151）；render.py 仅 import const 与 ui.theme（10-17），**不 import core/agents，不算胜负**：`won = view["winner"] == 0`（ui/render.py:243），winner 来自 snapshot（app.py:158）。
6. **theme.py**：布局常量在 `Layout` dataclass ui/theme.py:92-123（width/height 94-95、own_hand_origin 98、gap 99/101、avatar 104-105、info/pot/status 位置 108-111、button_width/height/gap/y 114-117、coin_size 123）；资源映射：BUTTON_IMAGES 20-27、COIN_IMAGE 29、AVATAR_IMAGES 32-35、AVATAR_LIBRARY 36-41、`asset_paths()` 44-53、`button_image_path` 57-62、`avatar_image_path` 64-71、`coin_image_path` 73-74、`missing_assets` 77-90。**'../' 坏路径：无**（ui/ 全目录 grep 字面 `../` = 0 匹配；const.py:15-23 全部为 ROOT/"src" 相对路径）。
7. **非阻塞输入**：键盘 `_on_key` ui/app.py:202-216（Esc 退出 205-206、R 重开 207-208、1-4 押注 211-212、f 弃牌 213-214、c 看牌 215-216）；鼠标 `_on_click` 218-226（与 `layout.button_rects` 碰撞检测 222-225）；均汇入 `human_action`(131)。等待期间主循环不阻塞：每帧 pump_events（app.py:233）+ draw/flip（237-243），QUIT/按键持续响应（195-199）；REAL 模式 60fps 限帧防空转（clock.py:44-51）。
8. **import 清单**：
   - ui/app.py：stdlib `__future__`(10)、random(12)、pathlib(13)；第三方 numpy(15)；内部 `agents.dqn`(17)、`core.dealing`(18)、`core.evaluator`(19)、`core.rules`(20)、`core.strength`(21)、`ui.clock`(22)；函数内惰性 import pygame(186/203/238/258)、const(260)、ui.render(261)。
   - ui/clock.py：`__future__`(12)、time(14)、enum(15)；无顶层第三方，pygame 惰性 import(48)。
   - ui/render.py：`__future__`(10)、pathlib(12)、pygame(14)、const(16)、ui.theme(17)。
   - ui/theme.py：`__future__`(11)、dataclasses(13)、pathlib(14)、const(16)；pygame 在 Layout 方法内惰性 import(126/132/150/159)。
   - ui/__init__.py：ui.clock(9)、ui.theme(10)。
   **ui/ 同时依赖 core/ 与 agents/**（仅 app.py:17-21）；render/theme/clock 只依赖仓库根 const.py。
9. **ui/__init__.py 导出**：`__all__ = ["TickPolicy","Ticker","Layout","asset_paths"]` ui/__init__.py:12，重导出自 ui.clock(9)、ui.theme(10)；**App/Controller/Renderer 未重导出**。
10. **grep 结果**：time.sleep / threading.Timer / 忙等 while —— **无**。"time.sleep" 仅出现于 docstring（ui/__init__.py:5、ui/app.py:5、ui/clock.py:1）；仅存的 while 为 `run()` 主循环（app.py:248）与 `update()` 的 guard<64（app.py:90，各分支均提前 return 94/99/102/106），非忙等；`../` 坏路径亦**无**。

## 调用关系
`main()`(app.py:257) → 构造 Controller(267)/Renderer(268)/Ticker(273) → `App.run`(275) → `step_frame`(229) → [Ticker.begin_frame/now：clock.py:36/54] → `pump_events`(185) → `_on_key`/`_on_click` → `Controller.human_action`(131) → `room.apply` → `_schedule`(74)；→ `Controller.update`(88) → `_ai_move`(108)→StateEncoder.encode+agent.act→room.apply / `_auto_human_move`(116)；→ `Renderer.draw`(101，数据=`Controller.view()` app.py:150 ← `room.snapshot()`) → `display.flip`(243) → `Ticker.end_frame`(44)。依赖方向：ui/app → core/{rules,dealing,evaluator,strength} + agents/dqn；ui/render + ui/theme → const；ui/app → ui/{clock,render,theme}。

## 发现的问题
1. ui/app.py:212 `Action(key - pygame.K_1)` 依赖键码差值映射 1→Action(0)，小键盘/特殊布局下不触发，健壮性小瑕疵。
2. ui/app.py:269-271 资源自检过粗：只查 `const.ROOT/"src"` 存在性；`theme.missing_assets()`（theme.py:77-90）已提供精确检查但未被使用。
3. ui/theme.py:130 `button_rects` 返回注解为 `dict[int, "object"]`，应为 `pygame.Rect`（注解不精确）。
4. ui/app.py:25 `DEFAULT_CHECKPOINT` 指向 `dqn_model_1.pth`，仓库内**不存在该 .pth**（find 无结果）→ 启动必走回退：未训练策略 + print 提示（app.py:57-62）；属设计内回退但需文档注明。
5. ui/app.py:169 结算时 view 向 UI 暴露对手真实牌型（render.py:176-178 显示）；且 view 恒含对手真手牌（app.py:156），靠 render 阶段克制（render.py:159-171 未结算只画背面），耦合偏隐式。
6. ui/app.py:141 `last_now` 为类级属性（未写于 `__init__`），`set_now`(143-144) 覆盖为实例属性；可用但风格不统一。
7. ui/app.py:222 `_on_click` 在 renderer=None 时 rects 为空 dict，鼠标输入失效（键盘仍可用）。

## 结论与建议
- ui/ 符合"薄表现层"：render 只绘制（render.py:101-118），状态唯一来源 `core.GameRoom.snapshot()`（app.py:150-171），UI 不算胜负（render.py:243）。
- 全链路零阻塞：无 sleep/忙等；AI 思考与人类等待统一表达为 deadline（app.py:74-85、93-94、101-102），主循环每帧重绘并响应 QUIT（app.py:233-243、195-196）。
- 节奏器命名为 `TickPolicy`/`Ticker`（clock.py:18、24），REAL/FIXED/IMMEDIATE 三态可注入；IMMEDIATE 供测试整局零等待。
- 无 '../' 坏路径；资源路径统一走 const.py 的 ROOT/src 相对路径（const.py:15-23）。
- ARCHITECTURE.md 建议：依赖方向写"ui/app → core + agents；ui/render、ui/theme → const"；`update()` 的 guard<64（app.py:90）应描述为死循环防护而非忙等；注明 checkpoint 缺失时的回退行为（app.py:57-62）。

## UNKNOWN 清单
- git status：只读角色无 bash 工具，无法执行；本次调查未修改/创建任何文件（仅 read/grep/find/ls）。
- `pygame`/`numpy` 具体版本号：未读 pyproject（属 C2 范围）。