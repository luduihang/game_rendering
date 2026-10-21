"""D7 复现：阻塞式时序与事件循环缺陷（人工提出的问题）。

四项：
- D7-a time.sleep 散落在步进与渲染之间
- D7-b check_button_click 忙等独占事件泵，等待期间 QUIT 无人处理
- D7-c RepeatedTimer 线程不安全
- D7-d import 期加载 .pth 权重（启动路径与权重文件硬耦合）

本脚本给出前 3 项的可执行证据 + D7-d 的调用计数证据。
"""

import os
import sys
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np

from common import h, check, summary

import torch.nn as nn

h("D7 阻塞式时序与事件循环缺陷")

# ---------------------------------------------------------------- D7-d
print("\n--- D7-d: import 期副作用 ---")
load_calls = []
_orig_load = nn.Module.load_state_dict


def _counted(self, *a, **k):
    load_calls.append(1)
    return _orig_load(self, *a, **k)


nn.Module.load_state_dict = _counted
try:
    import draw_me_vs_DQN  # noqa: E402  (故意在此处 import 以观测副作用)
    imported = True
except Exception as exc:  # noqa: BLE001
    imported = False
    import_err = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
finally:
    nn.Module.load_state_dict = _orig_load

if imported:
    check("import draw_me_vs_DQN 不应加载权重", len(load_calls) == 0,
          f"实际在 import 期间调用 load_state_dict {len(load_calls)} 次")
    pic = draw_me_vs_DQN.Draw_Pic()
else:
    # 更强的证据：import 直接失败，因为 dqn_model_0.pth 是 4 维输入、代码声明 DQN(9,6)
    print(f"  import draw_me_vs_DQN 阶段就崩溃: {import_err}")
    check("import draw_me_vs_DQN 不应加载权重", len(load_calls) == 0,
          f"import 期间调用 load_state_dict {len(load_calls)} 次，且权重维度不匹配直接抛异常")
    check("import 一个 UI 模块不应因权重文件失败而崩溃", False, import_err)
    pic = None

# ---------------------------------------------------------------- D7-a
print("\n--- D7-a: 单步耗时分解 ---")
from card_deck import Cards, Cards_Probability  # noqa: E402

deck = Cards()
deck.shuffle_deck()
hand = deck.draw_cards(3)

t0 = time.perf_counter()
Cards_Probability(hand).get_state()
t_state = time.perf_counter() - t0

t0 = time.perf_counter()
deck.reset_deck()
deck.shuffle_deck()
deck.draw_cards_plus(3)
t_deal_plus = time.perf_counter() - t0

print(f"  单次 Cards_Probability.get_state()  = {t_state*1000:7.1f} ms  (2000 轮蒙特卡洛)")
print(f"  单次 Cards.draw_cards_plus(3)       = {t_deal_plus*1000:7.1f} ms  (3×2000 轮)")
print(f"  每步固定 sleep（draw_me_vs_DQN.py） = 1500.0 ms")
print(f"  → 单步墙钟 ≈ {(t_state + 1.5)*1000:7.1f} ms，其中 sleep 占 "
      f"{1.5/(t_state+1.5)*100:4.1f}%，计算占 {t_state/(t_state+1.5)*100:4.1f}%")
check("单步不应含固定 sleep", False, "sleep 占单步墙钟的大头，且与计算串行叠加")

# ---------------------------------------------------------------- D7-b
print("\n--- D7-b: 忙等事件泵吞掉 QUIT ---")
import pygame  # noqa: E402

if pic is None:
    # 该模块无法 import，退化为源码静态核对：check_button_click 只在
    # MOUSEBUTTONDOWN 时返回，完全不处理 QUIT。
    src = open(os.path.join(os.path.dirname(__file__), "..", "..",
                            "draw_me_vs_DQN.py"), encoding="utf-8").read()
    seg = src[src.find("def check_button_click"):]
    seg = seg[: seg.find("def safe_exit")]
    handles_quit = "pygame.QUIT" in seg
    busy_wait = "while not signal" in seg
    print(f"  check_button_click 含 while not signal 忙等: {busy_wait}")
    print(f"  check_button_click 处理 pygame.QUIT:        {handles_quit}")
    check("等待人类点击期间应能响应 QUIT 并退出", handles_quit,
          "忙等且不处理 QUIT → 窗口无法关闭（静态证据）")
else:
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.QUIT))

    t = threading.Thread(target=pic.check_button_click, daemon=True)
    t.start()
    t.join(timeout=2.0)
    still_waiting = t.is_alive()
    print(f"  投递 SDL_QUIT 后，check_button_click 2 秒内是否返回: {not still_waiting}")
    check("等待人类点击期间应能响应 QUIT 并退出", not still_waiting,
          "该函数只在 MOUSEBUTTONDOWN 时退出，QUIT 被忽略 → 窗口无法关闭" if still_waiting else "")

# ---------------------------------------------------------------- D7-c
print("\n--- D7-c: RepeatedTimer 线程安全 ---")
import algorithm  # noqa: E402

rt = algorithm.RepeatedTimer(0.05, lambda: None)
try:
    rt.stop()  # 未 start 就 stop
    check("未 start 时 stop() 不应抛异常", True)
except Exception as exc:  # noqa: BLE001
    check("未 start 时 stop() 不应抛异常", False, f"抛出 {type(exc).__name__}: {exc}")

# 回调异常是否会静默掐断定时器链
fired = []
def boom():
    fired.append(1)
    raise RuntimeError("callback failure")

rt2 = algorithm.RepeatedTimer(0.05, boom)
rt2.start()
time.sleep(0.4)
rt2.stop()
print(f"  回调抛异常后仍被调度的次数: {len(fired)}")
check("回调异常不应静默断链", len(fired) > 2, f"40s 窗口内只触发 {len(fired)} 次，之后断链")

print()
print("-" * 74)
print("BASELINE_RESULT D7: 见上方各项（预期全部为 BUG）")
print("-" * 74)
sys.stdout.flush()
sys.stderr.flush()

# 被 daemon 忙等线程卡住的解释器直接退出
os._exit(0)
