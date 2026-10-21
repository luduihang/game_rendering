"""【兼容层】旧版卡牌 API，判定与强度计算全部委托给 core。

保留原因：``draw_me_vs_DQN_Plus.py``（唯一策略入口）、``mymath/robot2.py`` 与
``game_room_deepseek_cp.py`` 仍按旧接口调用。P3/P5 完成后本文件将被移除。

相对旧版的变化：
- 删除模块级 import 副作用（原先 import 就会跑 2000 轮蒙特卡洛并 print）
- ``Cards_Value`` / ``Cards_Probability`` 不再自己实现判定，而是委托 core
- ``draw_cards_plus()`` 保留为**遗留的偏置发牌**（三抽一取最优），默认路径
  请改用 ``draw_cards()``（均匀发牌，契约 D-R1）
"""

import random

from core.cards import Card
from core.evaluator import HAND_TYPE_NAMES, evaluate
from core.strength import beats_probability, strength_bin, strength_ordinal

__all__ = ["Cards", "Cards_Value", "Cards_Probability"]


def _to_core(cards):
    """接受旧式 {'suit','value'} 字典或 core.Card，统一转成 core.Card。"""
    return tuple(c if isinstance(c, Card) else Card.from_legacy(c) for c in cards)


def _to_legacy(cards):
    return [c.to_legacy() for c in cards]


class Cards:
    """52 张牌堆（旧式字典表示，保持与旧调用方兼容）。"""

    def __init__(self):
        self.cards = []
        self.reset_deck()

    def reset_deck(self):
        self.cards = [
            {"suit": suit, "value": value}
            for suit in ["黑桃", "红心", "方块", "梅花"]
            for value in range(2, 15)
        ]

    def shuffle_deck(self):
        random.shuffle(self.cards)

    def draw_cards(self, num_cards=3):
        """均匀发牌（默认路径）。"""
        if len(self.cards) < num_cards:
            print("Not enough cards in the deck.")
            return None
        return [self.cards.pop() for _ in range(num_cards)]

    def draw_cards_plus(self, num_cards=3):
        """【遗留行为，不推荐】抽 3 组候选并保留最强的一组，其余弃置。

        这会破坏牌局公平性（契约 D6：默认必须用 draw_cards）。为可复现历史实验保留。
        """
        best_cards = None
        best_probability = -1.0
        for _ in range(3):
            drawn = self.draw_cards(num_cards)
            if drawn is None:
                return None
            probability = Cards_Probability(drawn).get_probability()
            if probability > best_probability:
                best_probability = probability
                best_cards = drawn
        return best_cards


class Cards_Value:
    """手牌强度（委托 core.evaluator）。"""

    def __init__(self, cards):
        self.cards = cards
        self.value = 0
        self.type = None
        self.probability = None

    def Get_Type(self):
        self.type = int(evaluate(_to_core(self.cards)).hand_type)
        return self.type

    def Get_Value(self):
        """返回该手牌在 22100 手中的强度名次（越大越强，确定性）。"""
        self.type = self.Get_Type()
        self.value = strength_ordinal(_to_core(self.cards))
        return self.value

    def max_consecutive_value(self):
        cards = sorted(_to_core(self.cards), key=lambda c: c.rank)
        ranks = [c.rank for c in cards]
        if ranks[0] + 1 == ranks[1] and ranks[1] + 1 == ranks[2]:
            return ranks[-1]
        return None

    def type_name(self):
        if self.type is None:
            self.Get_Type()
        return HAND_TYPE_NAMES[int(self.type)]


class Cards_Probability:
    """手牌击败随机手牌的概率（穷举精确值，委托 core.strength）。"""

    def __init__(self, cards):
        self.cards = cards
        self.value = None
        self.probability = None
        self._core = None

    def _hand(self):
        if self._core is None:
            self._core = _to_core(self.cards)
        return self._core

    def get_probability(self):
        self.value = strength_ordinal(self._hand())
        self.probability = beats_probability(self._hand())
        return self.probability

    def get_state(self):
        self.value = strength_ordinal(self._hand())
        self.probability = beats_probability(self._hand())
        return strength_bin(self._hand())
