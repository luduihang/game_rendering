"""对手策略 Robot（由 mymath/robot2.py 迁入，行为保持等价）。

相对原实现的改动：
- 显式 ``import numpy as np``（原实现靠 ``from .probability_func import *`` 泄漏 numpy）
- 两个近乎逐行重复的类（Robot / Robot2）合并为一个类 + ``RobotConfig`` 参数化
- 手牌胜率改用 core 的穷举精确值（原实现每次 2000 轮蒙特卡洛）
- 增加 ``act()`` 统一接口，与 DQN 智能体可互换
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from agents.base import BaseAgent
from core.cards import Card
from core.strength import beats_probability
from mymath.func_const import conv_func
from mymath.probability_func import mapping_dict, switch_func

BET_OPTIONS = ("10", "20", "50", "100")
ALL_OPTIONS = ("10", "20", "50", "100", "throw_card", "compare_card")
OPTION_INDEX = {"10": 0, "20": 1, "50": 2, "100": 3, "give_up": 4, "Ab_value": 5}


@dataclass(frozen=True)
class RobotConfig:
    """激进档为原 Robot2 的参数（默认）；保守档会降低加注倾向、提高弃牌倾向。"""

    hand_strength_scale: float = 12.0
    hand_strength_cap: float = 10.0
    base_exponent_offset: float = 0.7
    base_exponent_div: float = 25.0
    punish_exponent_scale: float = 0.25
    risk_base: float = 0.6
    risk_div: float = 20.0
    extra_bet_scale: float = 0.8
    lose_penalty: float = 2.0
    compare_risk_base: float = 0.4
    compare_risk_slope: float = 0.6
    compare_lose_penalty: float = 1.5
    compare_weight: float = 2.0
    give_up_base: float = 1.2
    give_up_weight: float = 1.3
    noise_low: float = 0.9
    noise_high: float = 1.1
    probability_power: float = 1.2
    low_win_rate: float = 0.35
    very_low_win_rate: float = 0.25
    give_up_boost: float = 1.5
    compare_penalty_when_weak: float = 0.6
    compare_boost: float = 1.2

    @classmethod
    def aggressive(cls) -> "RobotConfig":
        return cls()

    @classmethod
    def conservative(cls) -> "RobotConfig":
        """更保守：加注收益打折、弃牌权重更高。"""
        return cls(
            hand_strength_scale=10.0,
            risk_base=0.5,
            risk_div=25.0,
            extra_bet_scale=0.6,
            lose_penalty=2.4,
            compare_weight=1.5,
            give_up_base=1.4,
            give_up_weight=1.6,
            low_win_rate=0.40,
        )


def _hand_strength(hand) -> float:
    cards = tuple(c if isinstance(c, Card) else Card.from_legacy(c) for c in hand)
    return beats_probability(cards)


class Robot(BaseAgent):
    """基于胜率与威胁评估的概率采样策略。"""

    name = "robot"

    def __init__(self, id: str = "1", config: RobotConfig | None = None, seed: int | None = None):
        self.id = id
        self.config = config or RobotConfig.aggressive()
        self.rng = np.random.default_rng(seed)
        self.conv = conv_func()
        self.reset()

    # ---------- 生命周期 ----------
    def reset(self) -> None:
        self.func_dict: dict = {}
        self.win_rate = 0.0
        self.desk_dict = {
            "win_rate": 0.0,
            "money_to_win": 10,
            "money_to_lose": 5,
            "rest_option": 0,
        }
        self.circle_turn = {"0": [0, 0, 0, 0], "1": [0, 0, 0, 0]}
        self.reverse_mapping_dict: dict = {}
        self.mapping_dict: dict = {}
        self.id_list: list = []
        self.gaming_choice_json = {"option": -1, "target": -1}
        self.bet_value: dict = {}

    def init_dick(self, id_list, cards, hand=None) -> None:
        """开局：登记座位映射，并用**自己的手牌**计算胜率。"""
        self.id_list = id_list
        known_mapping = {self.id: "0"}
        self.mapping_dict, self.reverse_mapping_dict = mapping_dict(list(id_list), ["0", "1"], known_mapping)
        self.func_dict = {pid: {} for pid in ("0", "1")}

        self.hand = hand if hand is not None else cards
        self.win_rate = _hand_strength(self.hand)
        self.desk_dict["win_rate"] = self.win_rate

        for pid in ("0", "1"):
            self.func_dict[pid]["bet_option_list"] = []
            self.func_dict[pid]["failure"] = False
            self.func_dict[pid]["pro_func"] = self.conv.func_init

    # ---------- 决策 ----------
    def cal_value(self) -> dict:
        cfg = self.config
        bet_value: dict = {}
        hand_strength = min(max(self.win_rate * cfg.hand_strength_scale, 1), cfg.hand_strength_cap)

        for i in range(self.desk_dict["rest_option"], 4):
            threaten_rate = int(ALL_OPTIONS[i]) / int(ALL_OPTIONS[self.desk_dict["rest_option"]])
            base_exponent = cfg.base_exponent_offset + (hand_strength / cfg.base_exponent_div)
            threaten_punish = threaten_rate ** (-base_exponent * cfg.punish_exponent_scale)

            risk_factor = cfg.risk_base - (hand_strength / cfg.risk_div)
            extra_bet = self.win_rate * int(ALL_OPTIONS[i]) * threaten_punish * cfg.extra_bet_scale
            bet_value[ALL_OPTIONS[i]] = (
                (self.desk_dict["money_to_win"] * risk_factor + extra_bet) * self.win_rate
                - (self.desk_dict["money_to_lose"] * cfg.lose_penalty + int(ALL_OPTIONS[i])) * (1 - self.win_rate)
            )

        compare_risk = cfg.compare_risk_base + (1 - self.win_rate) * cfg.compare_risk_slope
        ab_value = (
            self.win_rate * (self.desk_dict["money_to_win"] * compare_risk)
            - (1 - self.win_rate) * (self.desk_dict["money_to_lose"] * cfg.compare_lose_penalty)
        )
        bet_value["Ab_value"] = ab_value * cfg.compare_weight

        give_up_value = (self.desk_dict["money_to_lose"] * cfg.give_up_base) * (1 - self.win_rate**2)
        bet_value["give_up"] = give_up_value * cfg.give_up_weight

        for key in bet_value:
            bet_value[key] *= float(self.rng.uniform(cfg.noise_low, cfg.noise_high))
        return bet_value

    def cal_final_option(self) -> dict:
        cfg = self.config
        self.bet_value = self.cal_value()

        if self.win_rate < cfg.low_win_rate:
            self.bet_value["give_up"] *= cfg.give_up_boost
            if self.win_rate < cfg.very_low_win_rate:
                self.bet_value["Ab_value"] *= cfg.compare_penalty_when_weak

        valid = {k: v for k, v in self.bet_value.items() if v > 0}
        if not valid or (
            "give_up" in self.bet_value and self.bet_value["give_up"] > max(valid.values(), default=0)
        ):
            return {"option": 4}

        if "Ab_value" in valid:
            valid["Ab_value"] *= cfg.compare_boost
        if "give_up" in valid:
            valid["give_up"] *= cfg.give_up_weight

        total = sum(v**cfg.probability_power for v in valid.values())
        probabilities = {k: (v ** cfg.probability_power) / total for k, v in valid.items()}
        keys = list(probabilities)
        choice = keys[int(self.rng.choice(len(keys), p=[probabilities[k] for k in keys]))]
        return {"option": OPTION_INDEX[choice]}

    def act(self, observation, legal_actions: Sequence[int]) -> int:
        """统一接口：observation 可为盘面快照 dict，legal_actions 为合法动作。

        若尚未 init_dick，则依据快照与 legal_actions 就地构造最小可用状态。
        """
        if not self.func_dict:
            self.init_dick(["1", "0"], observation.get("hand"))
        if "rest_option" in observation:
            self.desk_dict["rest_option"] = int(observation["rest_option"])
        if "bets" in observation:
            own = observation["bets"][1]
            self.desk_dict["money_to_lose"] = own
            self.desk_dict["money_to_win"] = observation.get("all_bet", own * 2) - own
        option = self.cal_final_option()["option"]
        return self._pick_legal(option, legal_actions)

    # ---------- 观测 ----------
    def update_dick(self, json: dict) -> None:
        if json.get("game_process") not in ("inform", "battle"):
            return

        remapped = {}
        for key, value in json.items():
            remapped[self.mapping_dict.get(key, key)] = value
        json = remapped

        if "rest_option" in json and 0 <= json["rest_option"] <= 3:
            self.desk_dict["rest_option"] = json["rest_option"]
        if "0" in json:
            self.desk_dict["money_to_lose"] = json["0"]["bet_money"]
            self.desk_dict["money_to_win"] = json["all_bets"] - self.desk_dict["money_to_lose"]
        if "whose_turn" not in json:
            return

        turn_id = self.mapping_dict.get(str(json["whose_turn"]), "0")
        player_option = json.get("option", -1)

        if 0 <= player_option <= 3:
            self.circle_turn[turn_id][player_option] += 1
            self.conv.circle_turn = self.circle_turn[turn_id]
            self.conv._sum_circle_turn_cache = None
            self.func_dict[turn_id]["pro_func"] = switch_func(self.func_dict[turn_id]["pro_func"], self.conv)
            self.func_dict[turn_id]["bet_option_list"].append(BET_OPTIONS[player_option])
        elif player_option == 4:
            self.func_dict[turn_id]["failure"] = True
        elif player_option == 5:
            self.circle_turn[turn_id][json.get("rest_option", 0)] += 1
            self.conv.circle_turn = self.circle_turn[turn_id]
            self.conv._sum_circle_turn_cache = None

            if "battle_win" in json:
                if json["battle_win"] is False:
                    self.func_dict[turn_id]["failure"] = True
                elif "target" in json:
                    target_id = self.mapping_dict.get(str(json["target"]), "1")
                    self.func_dict[target_id]["failure"] = True
            if "rest_option" in json:
                equal_bet = BET_OPTIONS[json["rest_option"]]
                self.func_dict[turn_id]["pro_func"] = switch_func(self.func_dict[turn_id]["pro_func"], self.conv)
                self.func_dict[turn_id]["bet_option_list"].append(equal_bet)

    def save(self, path) -> None:
        import pickle

        with open(path, "wb") as fh:
            pickle.dump({"win_rate": self.win_rate, "desk_dict": self.desk_dict}, fh)

    def load(self, path) -> None:
        import pickle

        with open(path, "rb") as fh:
            data = pickle.load(fh)
        self.win_rate = data.get("win_rate", 0.0)
        self.desk_dict.update(data.get("desk_dict", {}))
