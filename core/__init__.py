"""core —— 炸金花核心逻辑（纯 Python，不依赖 pygame）。

分层约定：
- cards.py     牌与牌堆
- evaluator.py 牌型判定与比大小
- strength.py  穷举精确强度表（替代 2000 次蒙特卡洛）
- dealing.py   发牌（默认均匀）
- rules.py     对局状态机与结算
"""

from core.cards import Card, Suit, full_deck
from core.dealing import (
    EmptyDeckError,
    deal_strength_biased,
    deal_uniform,
    new_deck,
    verify_uniformity,
)
from core.evaluator import HAND_TYPE_NAMES, HandRank, HandType, compare, evaluate
from core.rules import Action, GameRoom, IllegalAction
from core.strength import (
    beats_probability,
    strength_bin,
    strength_ordinal,
    strongest_hand,
    table_size,
)

# 注意：以上均为模块级导入但不触发任何建表 —— core.strength 的 22100 手
# 精确强度表是惰性的（首次调用查询函数才建表，见 tests/test_dealing.py 守护）。

__all__ = [
    "Card",
    "Suit",
    "full_deck",
    "HandType",
    "HandRank",
    "HAND_TYPE_NAMES",
    "evaluate",
    "compare",
    "EmptyDeckError",
    "deal_strength_biased",
    "deal_uniform",
    "new_deck",
    "verify_uniformity",
    "Action",
    "GameRoom",
    "IllegalAction",
    "beats_probability",
    "strength_bin",
    "strength_ordinal",
    "strongest_hand",
    "table_size",
]
