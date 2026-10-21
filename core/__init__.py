"""core —— 炸金花核心逻辑（纯 Python，不依赖 pygame）。

分层约定：
- cards.py     牌与牌堆
- evaluator.py 牌型判定与比大小
- strength.py  穷举精确强度表（替代 2000 次蒙特卡洛）
- dealing.py   发牌（默认均匀）
- rules.py     对局状态机与结算
"""

from core.cards import Card, Suit, full_deck
from core.evaluator import HAND_TYPE_NAMES, HandRank, HandType, compare, evaluate
from core.rules import Action, GameRoom, IllegalAction
from core.strength import beats_probability, strength_bin, table_size

__all__ = [
    "Card",
    "Suit",
    "full_deck",
    "HandType",
    "HandRank",
    "HAND_TYPE_NAMES",
    "evaluate",
    "compare",
    "beats_probability",
    "strength_bin",
    "table_size",
    "Action",
    "GameRoom",
    "IllegalAction",
]
