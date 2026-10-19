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

json_option = ["10", "20", "50", "100", "give_up", "Ac_value","Ab_value"]


class Robot:
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
        # 添加基础手牌强度因子
        hand_strength = min(max(self.win_rate * 10, 1), 10)  # 将胜率映射到1-10

        # 修改威胁惩罚计算
        for i in range(self.desk_dict["rest_option"], 4):
            threaten_rate = int(all_option[i]) / int(all_option[self.desk_dict["rest_option"]])
            # 动态指数计算
            base_exponent = 0.5 + (hand_strength / 20)  # 手牌越强，惩罚越小
            threaten_punish = threaten_rate ** (-base_exponent * 0.2)

            # 修改加注价值公式
            risk_factor = 0.8 - (hand_strength / 15)  # 手牌越强风险系数越低
            extra_bet = self.win_rate * int(all_option[i]) * threaten_punish
            bet_value[all_option[i]] = (self.desk_dict["money_to_win"] * risk_factor + extra_bet) * self.win_rate - \
                                       (self.desk_dict["money_to_lose"] * 1.5 + int(all_option[i])) * (
                                                   1 - self.win_rate)

        # 修改比较牌价值计算
        compare_risk = 0.5 + (1 - self.win_rate) * 0.5  # 胜率越低比较风险越高
        Ab_value = self.win_rate * (self.desk_dict['money_to_win'] * compare_risk) - \
                   (1 - self.win_rate) * (self.desk_dict['money_to_lose'] * 1.8)
        bet_value['Ab_value'] = Ab_value * 1.5 # 增加比较牌权重

        # 添加随机扰动
        for k in bet_value:
            bet_value[k] *= random.uniform(0.95, 1.05)  # 添加5%随机波动

        return bet_value

    # 修改最终选项选择逻辑
    def cal_final_option(self):
        self.bet_value = self.cal_value()

        # 排除负收益选项
        valid_actions = {k: v for k, v in self.bet_value.items() if v > 0}

        if not valid_actions:
            return {'option': 4}  # 无正收益时弃牌

        # 带概率的选项选择
        total_value = sum(valid_actions.values())
        probabilities = {k: v / total_value for k, v in valid_actions.items()}

        # 概率采样
        choice = np.random.choice(list(probabilities.keys()), p=list(probabilities.values()))

        # 动作映射
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

# robot = Robot('5')
# cards1 = [{'suit': '黑桃', 'value': 7}, {'suit': '方块', 'value': 7}, {'suit': '红心', 'value': 2}]
# robot.init_dick(['5', '6'], cards1)
#
# json = {'game_process': 'inform',
#  '5':{'failure':False,'bet_money':5},
#  '6':{'failure':False,'bet_money':15},
#  'property': 'table', 'all_bets': 20, 'whose_turn': 6, 'rest_option': 0, 'option': 0, 'target': -1}
#
#
# robot.update_dick(json)
# res = robot.cal_final_option()
# print("robot option", res)