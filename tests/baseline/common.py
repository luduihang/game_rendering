"""Phase 0 基线复现：公共工具。

用途：
- 提供「精确手牌强度表」（穷举 C(52,3)=22100 手），用于给任意手牌算真实分位。
- 提供输出格式助手，便于 run_all.sh 聚合。

注意：本目录是「修复前失败行为」的固定基线，Phase 2 之后这些断言应随修复翻转。
不要为了让它们变绿而修改它们 —— 它们的价值就在于记录当前错误行为。
"""

import os
import sys
from itertools import combinations

import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

SUITS = ["黑桃", "红心", "方块", "梅花"]
RANKS = list(range(2, 15))


def full_deck():
    return [{"suit": s, "value": v} for s in SUITS for v in RANKS]


def exact_value_table():
    """穷举全部 22100 手三张牌，返回按强度升序排列的 value 数组。

    这是 Phase 2 的 `core/` 精确表原型：用参考实现 Cards_Value.Get_Value
    计算每手强度，排序后即可用二分查找得到「击败了多少比例的手牌」。
    """
    from card_deck import Cards_Value

    hands = list(combinations(full_deck(), 3))
    values = np.empty(len(hands), dtype=np.float64)
    for i, hand in enumerate(hands):
        values[i] = Cards_Value(list(hand)).Get_Value()
    return np.sort(values)


def percentile_of_value(sorted_values, value):
    return float(np.searchsorted(sorted_values, value, side="left")) / len(sorted_values)


def hand_percentile(sorted_values, hand):
    from card_deck import Cards_Value

    return percentile_of_value(sorted_values, Cards_Value(hand).Get_Value())


def h(title):
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


def check(name, ok, detail=""):
    """ok=True 表示「符合规则预期」；False 表示记录到 bug。"""
    tag = "PASS" if ok else "BUG "
    line = f"[{tag}] {name}"
    if detail:
        line += f"\n         {detail}"
    print(line)
    return ok


def summary(code, passed, bugs, notes=""):
    print()
    print("-" * 74)
    print(f"BASELINE_RESULT {code}: passed={passed} bug={bugs}")
    if notes:
        print(f"NOTE: {notes}")
    print("-" * 74)
