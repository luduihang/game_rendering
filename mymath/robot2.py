import sys
import os
import time
import random
from .probability_func import *
from .func_const import *
import math

project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_dir not in sys.path:
    sys.path.append(project_dir)
import card_deck


all_option = ["10", "20", "50", "100", "throw_card", "compare_card"]

class Robot2:
    def __init__(self, id):
        self.conv = conv_func()
        self.id = id
        self.func_dict = {}
        self.win_rate = 0
        self.desk_dict = {
            "win_rate": 0,
            "money_to_win": 10,
            "money_to_lose": 5,
            "rest_option": 0,  # 确保 rest_option 被初始化
        }
        self.circle_turn = {
            '0': [0, 0, 0, 0],
            '1': [0, 0, 0, 0],
        }
        self.reverse_mapping_dict = {}
        self.mapping_dict = {}
        self.id_list = []
        self.gaming_choice_json = {
            "option": -1,
            "target": -1,
        }

    def reset_para(self):
        self.func_dict = {}
        self.desk_dict = {
            "win_rate": 0,
            "money_to_win": 5,
            "money_to_lose": 5,
            "rest_option": 0,  # 确保 rest_option 被初始化
        }
        self.circle_turn = {
            '0': [0, 0, 0, 0],
            '1': [0, 0, 0, 0],
        }
        self.reverse_mapping_dict = {}
        self.mapping_dict = {}
        self.id_list = []
        self.gaming_choice_json = {
            "option": -1,
            "target": -1,
        }

    def init_dick(self, id_list, cards):
        self.id_list = id_list
        id_list = ['0', '1']
        known_mapping = {self.id: '0'}
        self.reverse_mapping_dict = mapping_dict(self.id_list, id_list, known_mapping)[1]
        self.mapping_dict = mapping_dict(self.id_list, id_list, known_mapping)[0]
        # print('reverse_mapping_dict:', self.reverse_mapping_dict)
        self.func_dict = {id: {} for id in id_list}

        self.cards = cards
        cards_probability = card_deck.Cards_Probability(self.cards)
        cards_probability.get_probability()
        self.win_rate = cards_probability.probability

        self.desk_dict["win_rate"] = self.win_rate

        for id in id_list:
            self.func_dict[id]['bet_option_list'] = []
            self.func_dict[id]['failure'] = False
            self.func_dict[id]['pro_func'] = self.conv.func_init

    # 修改cal_value方法中的价值计算逻辑
    def cal_value(self):
        bet_value = {}
        # 调高基础手牌强度因子权重
        hand_strength = min(max(self.win_rate * 12, 1), 10)  # 更敏感的手牌强度映射

        # 调整威胁惩罚计算（增加惩罚）
        for i in range(self.desk_dict["rest_option"], 4):
            threaten_rate = int(all_option[i]) / int(all_option[self.desk_dict["rest_option"]])
            # 增大指数基数，增强惩罚效应
            base_exponent = 0.7 + (hand_strength / 25)  # 手牌强度影响降低
            threaten_punish = threaten_rate ** (-base_exponent * 0.25)

            # 降低风险系数
            risk_factor = 0.6 - (hand_strength / 20)  # 整体更保守
            # 减少加注带来的收益计算
            extra_bet = self.win_rate * int(all_option[i]) * threaten_punish * 0.8  # 降低额外收益
            bet_value[all_option[i]] = (self.desk_dict["money_to_win"] * risk_factor + extra_bet) * self.win_rate - \
                                       (self.desk_dict["money_to_lose"] * 2.0 + int(all_option[i])) * (
                                                   1 - self.win_rate)

        # 提高比较牌基础价值（特别是低胜率时）
        compare_risk = 0.4 + (1 - self.win_rate) * 0.6  # 更早选择比较
        Ab_value = self.win_rate * (self.desk_dict['money_to_win'] * compare_risk) - \
                   (1 - self.win_rate) * (self.desk_dict['money_to_lose'] * 1.5)
        bet_value['Ab_value'] = Ab_value * 2.0  # 进一步提高比较牌权重

        # 新增弃牌保护机制
        give_up_value = (self.desk_dict["money_to_lose"] * 1.2) * (1 - self.win_rate ** 2)  # 非线性增长
        bet_value['give_up'] = give_up_value * 1.3  # 提高弃牌价值

        # 添加更大的随机扰动（增加不确定性）
        for k in bet_value:
            bet_value[k] *= random.uniform(0.9, 1.1)

        return bet_value
    # 修改最终选项选择逻辑
    def cal_final_option(self):
        self.bet_value = self.cal_value()

        # 新增胜率阈值保护
        if self.win_rate < 0.35:  # 当胜率低于35%时
            self.bet_value['give_up'] *= 1.5  # 大幅提升弃牌价值
            if self.win_rate < 0.25:
                self.bet_value['Ab_value'] *= 0.6  # 极低胜率时降低比较牌价值

        # 排除负收益选项时考虑弃牌优先
        valid_actions = {k: v for k, v in self.bet_value.items() if v > 0}
        if not valid_actions or (
                'give_up' in self.bet_value and self.bet_value['give_up'] > max(valid_actions.values(), default=0)):
            return {'option': 4}

        # 强化保守选项的概率权重
        if 'Ab_value' in valid_actions:
            valid_actions['Ab_value'] *= 1.2  # 提高比较牌概率
        if 'give_up' in valid_actions:
            valid_actions['give_up'] *= 1.3  # 提高弃牌概率

        # 引入非线性概率分布
        total_value = sum(v ** 1.2 for v in valid_actions.values())  # 让高价值选项更突出
        probabilities = {k: (v ** 1.2) / total_value for k, v in valid_actions.items()}

        choice = np.random.choice(list(probabilities.keys()), p=list(probabilities.values()))

        option_map = {
            "10": 0, "20": 1, "50": 2, "100": 3,
            "give_up": 4, "Ab_value": 5
        }
        return {'option': option_map[choice]}

    def update_dick(self, json):
        if json["game_process"] == 'inform' or json["game_process"] == 'battle':
            # 根据字典的id号映射关系，把json文件的id号映射为标准排序
            new_json = {}  # 创建一个新的字典来存储修改后的键值对
            for key, value in json.items():
                if key in self.mapping_dict:
                    new_key = self.mapping_dict[key]
                    new_json[new_key] = value  # 使用新键存储值
                else:
                    new_json[key] = value  # 保持原键不变
            # print('mapping_json', new_json)
            json = new_json

            if 'rest_option' in json:
                if 0 <= json["rest_option"] <= 3:
                    self.desk_dict['rest_option'] = json["rest_option"]
            if '0' in json:
                self.desk_dict['money_to_lose'] = json['0']['bet_money']
                self.desk_dict['money_to_win'] = json["all_bets"] - self.desk_dict['money_to_lose']
                # print("update money to win and lose")
            if 'whose_turn' in json:
                player_option = json['option']
                turn_id = self.mapping_dict[str(json['whose_turn'])]
                if 0 <= player_option <= 3:
                    self.circle_turn[turn_id][player_option] += 1
                    # 下注时需要对 对应注码的概率密度函数进行卷积
                    self.conv.circle_turn = self.circle_turn[turn_id]
                    # print('你好：', self.conv.circle_turn)
                    self.func_dict[turn_id]['pro_func'] = switch_func(self.func_dict[turn_id]['pro_func'], self.conv)

                    self.func_dict[turn_id]['bet_option_list'].append(all_option[player_option])
                elif player_option == 4:
                    self.func_dict[turn_id]['failure'] = True
                elif player_option == 5:
                    self.circle_turn[turn_id][json['rest_option']] += 1
                    self.conv.circle_turn = self.circle_turn[turn_id]

                    if 'battle_win' in json:
                        if json['battle_win'] == False:
                            self.func_dict[turn_id]['failure'] = True
                        else:
                            if 'target' in json:
                                target_id = self.mapping_dict[str(json['target'])]
                                self.func_dict[target_id]['failure'] = True
                    if 'rest_option' in json:
                        equal_bet = all_option[json['rest_option']]
                        # 看牌相当于押注，同样需要对当前玩家概率密度函数进行卷积
                        self.func_dict[turn_id]['pro_func'] = switch_func(self.func_dict[turn_id]['pro_func'], self.conv)
                        self.func_dict[turn_id]['bet_option_list'].append(equal_bet)
