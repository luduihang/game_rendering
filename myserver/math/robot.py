import sys
import time

from myserver.math.probability_func import *
from myserver.math.func_const import *
import math

from myserver import card_deck


all_option = ["10", "20", "50", "100", "throw_card", "compare_card"]

json_option = ["10", "20", "50", "100", "give_up", "Ac_value","Ab_value"]


class Robot:
    def __init__(self,id):
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
        self.circle_turn ={
            '0':[0, 0, 0, 0],
            '1':[0, 0, 0, 0],
            '2':[0, 0, 0, 0],
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
            "money_to_win": 10,
            "money_to_lose": 5,
            "rest_option": 0,  # 确保 rest_option 被初始化
        }
        self.circle_turn ={
            '0':[0, 0, 0, 0],
            '1':[0, 0, 0, 0],
            '2':[0, 0, 0, 0],
        }
        self.reverse_mapping_dict = {}
        self.mapping_dict = {}
        self.id_list = []
        self.gaming_choice_json = {
            "option": -1,
            "target": -1,
        }

    def init_dick(self,id_list,cards):
        self.id_list = id_list
        id_list = ['0','1','2']
        known_mapping = {self.id: '0'}
        self.reverse_mapping_dict = mapping_dict(self.id_list,id_list,known_mapping)[1]
        self.mapping_dict = mapping_dict(self.id_list,id_list,known_mapping)[0]
        print('reverse_mapping_dict:',self.reverse_mapping_dict)
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


    def cal_final_option(self):
        self.bet_value = self.cal_value()
        max_key = None
        max_value = float('-inf')  # 初始化为负无穷大
        for key ,key_value in self.bet_value.items():
            if key_value > max_value:
                max_value = key_value
                max_key = key  # 更新最大值对应的键

        print("最大的value对应的key:",max_key)
        if 0 <= json_option.index(max_key) <= 4:
            self.gaming_choice_json['option'] = json_option.index(max_key)
        if json_option.index(max_key) == 5 or json_option.index(max_key) == 6:
            self.gaming_choice_json['option'] = 5
            if json_option.index(max_key) == 5:
                self.gaming_choice_json['target'] = int(self.reverse_mapping_dict['2'])
            else:
                self.gaming_choice_json['target'] = int(self.reverse_mapping_dict['1'])
        # for i in range(6):
        #     print(' ')
        print("gaming_choice_json",self.gaming_choice_json)
        #战术停顿，防止机器人操作太快，玩家思路更不上
        time.sleep(1.8)

        return self.gaming_choice_json

    def cal_value(self):
        bet_value = {}
        # 获得机器人A视角下 相对于玩家B与C的胜率
        winb = integral_func(self.func_dict['1']['pro_func'],self.win_rate)
        winc = integral_func(self.func_dict['2']['pro_func'],self.win_rate)
        print('winb,winc',winb,winc)
        # 获得全体player视角下面的，通过三方押注获得的概率密度函数的均值
        mean_a = mean_func(self.func_dict['0']['pro_func'])
        mean_b = mean_func(self.func_dict['1']['pro_func'])
        mean_c = mean_func(self.func_dict['2']['pro_func'])
        # B的角度预测对于A与C的胜率
        win_rate_Ba = 1 - integral_func(self.func_dict['1']['pro_func'], mean_a)
        win_rate_Bc = 1 - integral_func(self.func_dict['1']['pro_func'], mean_c)
        # C的角度预测对于B与A的胜率
        win_rate_Ca = 1 - integral_func(self.func_dict['2']['pro_func'], mean_a)
        win_rate_Cb = 1 - integral_func(self.func_dict['2']['pro_func'], mean_b)

        rest_option_value = self.desk_dict.get("rest_option", 0)
        # 计算所有下注选项和弃牌选项的估计value
        for i in range(rest_option_value,4):
            threaten_punish = (int(all_option[i]) / int(all_option[self.desk_dict["rest_option"]])) ** (-1.0)
            # print("threaten_punish:", threaten_punish)
            if not self.func_dict['2']['failure'] and not self.func_dict['1']['failure']:
                extra_bet = (win_rate_Ba * win_rate_Bc + win_rate_Ca * win_rate_Cb) * int(all_option[i]) * threaten_punish
                bet_value[all_option[i]] = (self.desk_dict["money_to_win"] + extra_bet) * winb * winc - (self.desk_dict["money_to_lose"] + 1.5 * int(all_option[i])) * (1 - winb * winc)
            if not self.func_dict['2']['failure'] and self.func_dict['1']['failure']:
                extra_bet = win_rate_Ca * int(
                    all_option[i]) * threaten_punish
                bet_value[all_option[i]] = (self.desk_dict["money_to_win"] + extra_bet) * winc - (
                            self.desk_dict["money_to_lose"] +  1.5 * int(all_option[i])) * (1 - winc)
            if self.func_dict['2']['failure'] and not self.func_dict['1']['failure']:
                extra_bet = win_rate_Ba * int(
                    all_option[i]) * threaten_punish
                bet_value[all_option[i]] = (self.desk_dict["money_to_win"] + extra_bet) * winb - (
                        self.desk_dict["money_to_lose"] +  1.5 * int(all_option[i])) * (1 - winb)
        bet_value["give_up"] = -1 * self.desk_dict['money_to_lose']

        # 计算对于其他玩家的看牌选项的估计value
        if '2' in self.func_dict:
            if 'failure' in self.func_dict['2']:
                if not self.func_dict['2']['failure']:
                    if not self.func_dict['1']['failure']:
                        # 计算B的视角下，A看C，B对于A的牌大小的估计，从而预测B接下来可能下注的多少
                        rest_option = str(all_option[self.desk_dict['rest_option']])
                        # print(rest_option)
                        # 暂存当下的循环次数，等会还要赋值回去
                        self.circle_turn['0'][self.desk_dict['rest_option']] += 1
                        self.conv.circle_turn = self.circle_turn['0']
                        Battle_Ba_func = switch_func(self.func_dict['0']['pro_func'],self.conv)
                        self.circle_turn['0'][self.desk_dict['rest_option']] -= 1

                        battle_mean_a = mean_func(Battle_Ba_func)
                        Battle_win_rate_Ba = 1 - integral_func(self.func_dict['1']['pro_func'], battle_mean_a)
                        # print("B认为A看牌C之后，B对A的胜率:", Battle_win_rate_Ba)
                        #这个奖励函数如果不合适的话，还需要考虑如果B的牌特别大的时候，extra_bet数量会更多的情况
                        extra_bet = int(all_option[self.desk_dict['rest_option']]) * Battle_win_rate_Ba
                        Ac_value = (winb * winc) * (self.desk_dict['money_to_win'] + extra_bet) - (1 - winc) * (self.desk_dict['money_to_lose'] + int(all_option[self.desk_dict['rest_option']]))
                    else:
                        Ac_value = winc * self.desk_dict['money_to_win'] - (1 - winc) * (self.desk_dict['money_to_lose'] + int(all_option[self.desk_dict['rest_option']]))
                    bet_value['Ac_value'] = Ac_value
        if '1' in self.func_dict:
            if 'failure' in self.func_dict['1']:
                if not self.func_dict['1']['failure']:
                    if not self.func_dict['2']['failure']:
                        # 计算C的视角下，A看B，C对于A的牌大小的估计，从而预测C接下来可能下注的多少
                        rest_option = str(all_option[self.desk_dict['rest_option']])
                        self.circle_turn['0'][self.desk_dict['rest_option']] += 1
                        self.conv.circle_turn = self.circle_turn['0']
                        Battle_Ca_func = switch_func(self.func_dict['0']['pro_func'],self.conv)
                        self.circle_turn['0'][self.desk_dict['rest_option']] -= 1
                        battle_mean_a = mean_func(Battle_Ca_func)
                        Battle_win_rate_Ca = 1 - integral_func(self.func_dict['2']['pro_func'], battle_mean_a)
                        # print("C认为A看牌B之后，C对A的胜率:", Battle_win_rate_Ca)
                        #这个奖励函数如果不合适的话，还需要考虑如果C的牌特别大的时候，extra_bet数量会更多的情况
                        extra_bet = int(all_option[self.desk_dict['rest_option']]) * Battle_win_rate_Ca
                        Ab_value = (winb * winc) * (self.desk_dict['money_to_win'] + extra_bet) - (1 - winb) * (
                                    self.desk_dict['money_to_lose'] + int(all_option[self.desk_dict['rest_option']]))
                    else:
                        Ab_value = (winb * self.desk_dict['money_to_win'] -
                                    (1 - winb) * (self.desk_dict['money_to_lose'] + int(all_option[self.desk_dict['rest_option']])))

                    bet_value['Ab_value'] = Ab_value
        print("bet_value:",bet_value)
        return bet_value

    def update_dick(self,json):
        if json["game_process"] == 'inform' or json["game_process"] == 'battle':
           # 根据字典的id号映射关系，把json文件的id号映射为标准排序
           new_json = {}  # 创建一个新的字典来存储修改后的键值对
           for key, value in json.items():
               if key in self.mapping_dict:
                   new_key = self.mapping_dict[key]
                   new_json[new_key] = value  # 使用新键存储值
               else:
                   new_json[key] = value  # 保持原键不变
           print('mapping_json',new_json)
           json = new_json

           if 'rest_option' in json:
               if 0 <= json["rest_option"] <= 3:
                    self.desk_dict['rest_option'] = json["rest_option"]
           if '0' in json:
               self.desk_dict['money_to_lose'] = json['0']['bet_money']
               self.desk_dict['money_to_win'] = json["all_bets"] - self.desk_dict['money_to_lose']
               print("update money to win and lose")
           if 'whose_turn' in json:
                player_option = json['option']
                turn_id = self.mapping_dict[str(json['whose_turn'])]
                if 0 <= player_option <= 3:
                   self.circle_turn[turn_id][player_option] += 1
                   #下注时需要对 对应注码的概率密度函数进行卷积
                   self.conv.circle_turn = self.circle_turn[turn_id]
                   print('你好：',self.conv.circle_turn)
                   self.func_dict[turn_id]['pro_func'] = switch_func(self.func_dict[turn_id]['pro_func'],self.conv)

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
                        self.func_dict[turn_id]['pro_func'] = switch_func(self.func_dict[turn_id]['pro_func'],self.conv)
                        self.func_dict[turn_id]['bet_option_list'].append(equal_bet)

# json = {'game_process': 'battle',
#  'property': 'table', 'all_bets': 3, 'whose_turn': 2, 'rest_option': 0, 'user_ids_list': [0, -1, -1], 'option': 5, 'target': 0, 'battle_win': False}
json = {'game_process': 'inform',
 '5':{'failure':False,'bet_money':5},
 '6':{'failure':False,'bet_money':15},
 '7': {'failure': False, 'bet_money': 5},
 'property': 'table', 'all_bets': 25, 'whose_turn': 6, 'rest_option': 0, 'user_ids_list': [0, -1, -1], 'option': 0, 'target': -1}

json2 = {'game_process': 'inform',
 '5':{'failure':False,'bet_money':5},
 '6':{'failure':False,'bet_money':15},
 '7': {'failure': True, 'bet_money': 5},
 'property': 'table', 'all_bets': 25, 'whose_turn': 7, 'rest_option': 0, 'user_ids_list': [0, -1, -1], 'option': 4, 'target': -1}


json3 = {'game_process': 'inform',
 '5':{'failure':False,'bet_money':15},
 '6':{'failure':False,'bet_money':15},
 '7': {'failure': True, 'bet_money': 5},
 'property': 'table', 'all_bets': 35, 'whose_turn': 5, 'rest_option': 0, 'user_ids_list': [0, -1, -1], 'option': 0, 'target': -1}


json4 = {'game_process': 'inform',
 '5':{'failure':False,'bet_money':15},
 '6':{'failure':False,'bet_money':115},
 '7': {'failure': True, 'bet_money': 5},
 'property': 'table', 'all_bets': 135, 'whose_turn': 6, 'rest_option': 3, 'user_ids_list': [0, -1, -1], 'option': 3, 'target': -1}


json5 = {'game_process': 'inform',
 '0':{'failure':False,'bet_money':15},
 '1':{'failure':False,'bet_money':15},
 '2': {'failure': False, 'bet_money': 15},
 'property': 'table', 'all_bets': 45, 'whose_turn': 1, 'rest_option': 0, 'user_ids_list': [0, -1, -1], 'option': 4, 'target': -1}

json6 = {'game_process': 'inform',
 '0':{'failure':False,'bet_money':15},
 '1':{'failure':True,'bet_money':15},
 '2': {'failure': False, 'bet_money': 35},
 'property': 'table', 'all_bets': 65, 'whose_turn': 2, 'rest_option': 1, 'user_ids_list': [0, -1, -1], 'option': 1, 'target': -1}

# robot = Robot('5')
# cards1 = [{'suit': '黑桃', 'value': 7}, {'suit': '方块', 'value': 7}, {'suit': '红心', 'value': 2}]
# robot.init_dick(['5','6','7'],cards1)
# robot.update_dick(json)
# robot.update_dick(json2)
# robot.update_dick(json3)
# robot.update_dick(json4)
# # robot.update_dick(json5)
# # robot.update_dick(json6)
#
# print(robot.desk_dict)
# print(robot.func_dict)
# # print(robot.func_dict)
# robot.cal_final_option()
# # robot.update_dick(json2)
# # print(robot.func_dict)
# # robot.update_dick(json3)
# # print(robot.func_dict)
