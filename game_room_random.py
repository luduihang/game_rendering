import threading
import json
import time
import copy
import random

from mymath.robot import Robot
from card_deck import Cards, Cards_Value, Cards_Probability

options = ['10', '20', '50', '100', 'give_up', 'cmp']  #显示action空间

class Game_room:
    def __init__(self):
        self.deck = Cards()
        self.deck.shuffle_deck()
        self.rest_option = 0

        self.circle = 1  #显示当前轮次
        self.all_bet = 10   #桌面上面的所有押注金额
        self.player_bet = [5, 5]
        self.whose_turn = 0  #当前出牌的玩家
        self.finish = False
        self.winner = 0

        self.cards1 = self.deck.draw_cards_plus()
        self.cards2 = self.deck.draw_cards_plus()
        self.get_value1 = Cards_Value(self.cards1)
        self.wallet1 = 10000
        self.get_value2 = Cards_Value(self.cards2)
        self.wallet2 = 10000
        self.cards1_value = self.get_value1.Get_Value()
        self.cards2_value = self.get_value2.Get_Value()

        print("机器人的手牌是", self.cards1)
        print("玩家的手牌是", self.cards2)

    def init_arg(self):
        self.deck.reset_deck()
        self.deck.shuffle_deck()
        self.rest_option = 0
        self.circle = 1  #显示当前轮次
        self.all_bet = 10   #桌面上面的所有押注金额
        self.player_bet = [5, 5]
        self.whose_turn = 0  #当前出牌的玩家
        self.finish = False
        self.winner = 0
        self.cards1 = self.deck.draw_cards_plus()
        self.cards2 = self.deck.draw_cards_plus()
        self.get_value1 = Cards_Value(self.cards1)
        self.get_value2 = Cards_Value(self.cards2)
        self.cards1_value = self.get_value1.Get_Value()
        self.cards2_value = self.get_value2.Get_Value()

    def show_inform(self):
        for i in range(len(self.player_bet)):
            print(f"玩家{i}已经押注{self.player_bet[i]}")
        print(f"玩家0的手牌是{self.cards1}")
        print(f"玩家1的手牌是{self.cards2}")
        print()
        print(f"当前总共押注金额是{self.all_bet}")
    def get_choice(self, action):
        if action <= 3:
            self.rest_option = action # 更新接下来的选项
            self.player_bet[self.whose_turn] += int(options[action])
            self.all_bet += int(options[action])
        elif action == 4:
            self.winner = 1 - self.whose_turn
            self.finish = True
        elif action == 5:
            self.player_bet[self.whose_turn] += int(options[self.rest_option])
            self.all_bet += int(options[self.rest_option])
            # 玩家0看牌 如果玩家0小 winner = 1
            # 玩家1看牌 如果玩家1小 winner = 0
            if self.cards1_value < self.cards2_value:
                self.winner = 1
                self.finish = True
            else:
                self.winner = 0
                self.finish = True
        print(f"玩家{self.whose_turn}选择了", options[action])
        self.whose_turn += 1
        self.whose_turn %= 2

class Player:
    def __init__(self, cards):
        self.rest_option = 0 # 这是用于归一化action概率
        self.all_bet = 10
        self.probable = Cards_Probability(cards)

        self.circle_state = 0 #获取当前轮次状态
        self.card_state = self.probable.get_state()  #获取当前手牌的state大小 情况1-6
        self.bet_state = 5

    def update_inform(self, option, my_bet, circle):
        self.rest_option = option
        self.bet_state = my_bet
        self.circle_state = circle

    def get_option(self):
        random_choice = random.randint(self.rest_option, 5)
        print(f"机器人选择了选项：{options[random_choice]}")
        print()
        print()
        return random_choice

class test_player:
    def __init__(self, cards):
        self.rest_option = 0 # 这是用于归一化action概率
        self.all_bet = 10
        self.probable = Cards_Probability(cards)

        self.circle_state = 0 #获取当前轮次状态
        self.card_state = self.probable.get_state()  #获取当前手牌的state大小 情况1-6
        self.bet_state = 5

    def update_inform(self, option, my_bet, circle):
        self.rest_option = option
        self.bet_state = my_bet
        self.circle_state = circle

    def get_option(self):
        while True:
            print()
            print()
            print("请输入你的选择：")
            if 1 <= self.rest_option + 1 <= 4:
                options = ["1.押注10", "2.押注20", "3.押注50", "4.押注100"]
                print(options[self.rest_option])
            else:
                print("1.押注10  2.押注20  3.押注50  4.押注100")
            print("5.弃牌  6.看牌")
            option = input()
            try:
                option = int(option)  # 尝试将输入转换为整数
                if self.rest_option + 1 <= option <= 6:
                    # 这里处理选项在1到6之间的情况
                    print(f"你选择了选项：{option}")
                    break
                else:
                    print(f"请输入一个有效的选项（{self.rest_option + 1}-6）。")
            except ValueError:
                print("请输入一个数字。")
        return int(option) - 1

def main():
    room = Game_room()

    for i in range(100):
        robot = Player(room.cards1)
        #把我看做机器人
        me = test_player(room.cards2)
        merobot = Robot('1')
        merobot.init_dick(['1', '0'], room.cards2)
        json_pack =  {'game_process': 'inform',
         '1':{'failure':False,'bet_money':5},
         '0':{'failure':False,'bet_money':5},
         'property': 'table', 'all_bets': 10, 'whose_turn': 0, 'rest_option': 0, 'option': 0, 'target': -1}

        print("准备开始游戏")
        # time.sleep(2)
        while True:
            choice = robot.get_option()
            room.get_choice(choice)
            robot.update_inform(room.rest_option, room.player_bet[0], room.circle)
            me.update_inform(room.rest_option, room.player_bet[1], room.circle)
            room.show_inform()
            if room.finish:
                break
            # time.sleep(2)

            ## 刚开始是robot做出决策，此时我的机器人更新数据
            json_pack['0']['bet_money'] = room.player_bet[0]
            json_pack['all_bets'] = room.all_bet
            json_pack['rest_option'] = room.rest_option
            json_pack['whose_turn'] = 0
            merobot.update_dick(json_pack)

            choice_json = merobot.cal_final_option()
            choice = choice_json["option"]
            room.get_choice(choice)

            robot.update_inform(room.rest_option, room.player_bet[0], room.circle)
            me.update_inform(room.rest_option, room.player_bet[1], room.circle)

            room.show_inform()
            if room.finish:
                break
            # time.sleep(2)
            ## 现在是我的机器人做出决策，此时我的机器人同样更新数据
            json_pack['1']['bet_money'] = room.player_bet[1]
            json_pack['all_bets'] = room.all_bet
            json_pack['rest_option'] = room.rest_option
            json_pack['whose_turn'] = 1
            merobot.update_dick(json_pack)

        if room.winner == 0:
            print("你输了")
            room.wallet1 += room.all_bet - room.player_bet[0]
            room.wallet2 -= room.all_bet - room.player_bet[0]
        if room.winner == 1:
            print("你赢了")
            room.wallet1 -= room.all_bet - room.player_bet[1]
            room.wallet2 += room.all_bet - room.player_bet[1]
        room.init_arg()
    print("随机机器人wallet", room.wallet1)
    print("我的机器人wallet", room.wallet2)
main()