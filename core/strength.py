"""穷举精确手牌强度表。

替代原实现 `Cards_Probability` 的 2000 轮蒙特卡洛抽样：
- 原实现：单次调用 ~30.8ms（基线实测，见 docs/BASELINE-REPORT.md），结果每次抖动
- 本实现：一次性穷举 C(52,3)=22100 手并排序缓存，之后每次查询为二分查找（O(log n)）

「胜率」定义为：**击败一副均匀随机 3 张手牌的概率**。
这正是原蒙特卡洛在估计的量，因此可直接替换，且结果确定、可复现。
"""

from __future__ import annotations

from bisect import bisect_left
from functools import lru_cache
from itertools import combinations

from core.cards import full_deck
from core.evaluator import evaluate

# 原实现的档位分箱阈值（get_state 用），保留以兼容既有 DQN 状态语义
BIN_THRESHOLDS = (0.4, 0.7, 0.9, 0.96, 0.99)


@lru_cache(maxsize=1)
def _ranked_keys() -> tuple[tuple, ...]:
    """全部 22100 手的比较键，按强度升序排列。首次调用约数十毫秒，之后命中缓存。"""
    return tuple(sorted(evaluate(hand).key() for hand in combinations(full_deck(), 3)))


def table_size() -> int:
    return len(_ranked_keys())


def beats_probability(hand) -> float:
    """该手牌击败均匀随机手牌的概率，取值 [0, 1)，确定性结果。"""
    keys = _ranked_keys()
    return bisect_left(keys, evaluate(hand).key()) / len(keys)


def strength_ordinal(hand) -> int:
    """手牌在全部 22100 手中的强度排名序号（0 = 最弱）。

    纯单调整数，供需要可排序标量的调用方（如遗留 Cards_Value.Get_Value）使用。
    """
    return bisect_left(_ranked_keys(), evaluate(hand).key())


def strength_bin(hand) -> int:
    """按原实现的阈值把胜率映射为 1..6 档（兼容既有 DQN 状态特征）。"""
    p = beats_probability(hand)
    for index, threshold in enumerate(BIN_THRESHOLDS):
        if p < threshold:
            return index + 1
    return len(BIN_THRESHOLDS) + 1


def strongest_hand() -> tuple:
    return max(combinations(full_deck(), 3), key=lambda h: evaluate(h).key())
