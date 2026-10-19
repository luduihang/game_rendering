import threading
import json
import time
import copy
import random
import numpy as np
import matplotlib.pyplot as plt
import os

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
    def __init__(self):
        self.rest_option = 0  # 这是用于归一化action概率
        self.all_bet = 10
        self.probable = None
        self.card_state = None

        self.rest_option = 0
        self.circle_state = 0  # 获取当前轮次状态
        self.bet_state = 5
        # 初始化 Q 值表
        self.q_table = self.load_q_table()  # 从文件加载 Q 表
        self.alpha = 0.1  # 学习率
        self.gamma = 0.9  # 折扣因子
        self.epsilon = 1.0  # 探索率
        self.epsilon_decay = 0.995  # 探索率衰减
        self.epsilon_min = 0.01  # 最小探索率

        # 用于记录每轮游戏的决策历史
        self.decision_history = []

    def load_q_table(self):
        # 如果 q_table.txt 文件存在，读取并解析 Q 表
        if os.path.exists("q_table.txt"):
            with open("q_table.txt", "r") as file:
                q_table_str = file.read()
                # 如果文件内容为空，返回空字典
                if not q_table_str.strip():
                    print("Q表文件为空，返回空字典")
                    return {}
                # 将字符串键转换为元组键
                try:
                    q_table = {eval(k): v for k, v in json.loads(q_table_str).items()}
                    print("Q表读取成功")
                    return q_table
                except json.JSONDecodeError as e:
                    print(f"Q表文件格式错误: {e}")
                    return {}
        else:
            print("Q表文件不存在，返回空字典")
            return {}

    def save_q_table(self):
        # 将 Q 表保存到 q_table.txt 文件
        # 将元组键转换为字符串键
        q_table_str = json.dumps({str(k): v for k, v in self.q_table.items()})
        with open("q_table.txt", "w") as file:
            file.write(q_table_str)

    def update_cards(self, cards):
        self.rest_option = 0  # 这是用于归一化action概率
        self.all_bet = 10
        self.probable = Cards_Probability(cards)
        self.card_state = self.probable.get_state()  # 获取当前手牌的state大小 情况1-6

    def update_inform(self, option, my_bet, circle):
        self.rest_option = option
        self.bet_state = my_bet
        self.circle_state = circle

    def get_q_value(self, state, action):
        # 获取 Q 值，如果状态不存在则初始化为 0
        return self.q_table.get((state, action), 0.0)

    def update_q_value(self, state, action, reward, next_state):
        # 更新 Q 值
        old_value = self.get_q_value(state, action)
        next_max = max([self.get_q_value(next_state, a) for a in range(self.rest_option, 6)])
        new_value = old_value + self.alpha * (reward + self.gamma * next_max - old_value)
        self.q_table[(state, action)] = new_value

    def choose_action(self, state):
        # 根据 epsilon-greedy 策略选择动作，且动作必须大于等于 self.rest_option
        if np.random.rand() < self.epsilon:
            return np.random.randint(self.rest_option, 6)  # 探索
        else:
            # 选择 Q 值最大的动作
            q_values = [self.get_q_value(state, a) for a in range(self.rest_option, 6)]
            return np.argmax(q_values) + self.rest_option  # 利用

    def get_option(self):
        state = (self.circle_state, self.bet_state, self.card_state)  #这是状态空间
        action = self.choose_action(state)  #这是决策空间
        print(f"机器人选择了选项：{options[action]}")
        print()
        print()
        # 记录决策历史
        self.decision_history.append((state, action))
        return action

    def update_epsilon(self):
        # 更新探索率
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def update_q_table_with_reward(self, reward):
        # 根据决策历史更新 Q 值表，将奖励平均分配给每个决策
        if not self.decision_history:
            return

        # 计算每个决策的平均奖励
        avg_reward = reward / len(self.decision_history)

        # 更新 Q 值表
        for i, (state, action) in enumerate(self.decision_history):
            next_state = self.decision_history[i + 1][0] if i + 1 < len(self.decision_history) else None
            if next_state:
                self.update_q_value(state, action, avg_reward, next_state)
            else:
                self.update_q_value(state, action, avg_reward, state)

        # 清空决策历史
        self.decision_history = []

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
    robot = Player()

    # 记录胜利金额和胜率
    reward_history = []
    win_rate_history = []
    total_wins = 0

    for i in range(100):
        robot.update_cards(room.cards1)
        me = test_player(room.cards2)
        merobot = Robot('1')
        merobot.init_dick(['1', '0'], room.cards2)
        json_pack = {'game_process': 'inform',
                     '1': {'failure': False, 'bet_money': 5},
                     '0': {'failure': False, 'bet_money': 5},
                     'property': 'table', 'all_bets': 10, 'whose_turn': 0, 'rest_option': 0, 'option': 0, 'target': -1}

        print("准备开始游戏")
        while True:
            choice = robot.get_option()
            room.get_choice(choice)
            robot.update_inform(room.rest_option, room.player_bet[0], room.circle)
            me.update_inform(room.rest_option, room.player_bet[1], room.circle)
            room.show_inform()
            if room.finish:
                break

            ## 刚开始是强化学习robot做出决策，此时概率密度机器人更新数据
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

            ## 现在是概率密度机器人做出决策，此时概率密度机器人同样更新数据
            json_pack['1']['bet_money'] = room.player_bet[1]
            json_pack['all_bets'] = room.all_bet
            json_pack['rest_option'] = room.rest_option
            json_pack['whose_turn'] = 1
            merobot.update_dick(json_pack)

        # 游戏结束，根据赢得的钱更新 Q 值表
        if room.winner == 0:
            print("你输了")
            reward = room.all_bet - room.player_bet[0]
            room.wallet1 += reward
            room.wallet2 -= reward
            # 更新 Q 值表
            robot.update_q_table_with_reward(reward)
            # 记录胜利金额
            reward_history.append(reward if room.winner == 1 else -reward)

        elif room.winner == 1:
            print("你赢了")
            reward = room.all_bet - room.player_bet[1]
            room.wallet1 -= reward
            room.wallet2 += reward
            # 更新 Q 值表
            robot.update_q_table_with_reward(reward)
            total_wins += 1
            # 记录胜利金额
            reward_history.append(reward if room.winner == 1 else -reward)

        # 计算胜率
        win_rate = total_wins / (i + 1)
        win_rate_history.append(win_rate)

        room.init_arg()

    print("随机机器人wallet", room.wallet1)
    print("我的机器人wallet", room.wallet2)
    print(robot.q_table)
    # 保存 Q 表到文件
    robot.save_q_table()

    # 绘制胜利金额和胜率的变化曲线
    plt.figure(figsize=(12, 6))

    # 绘制胜利金额
    plt.subplot(1, 2, 1)
    plt.plot(reward_history, label='Reward per Game')
    plt.xlabel('Game Number')
    plt.ylabel('Reward')
    plt.title('Reward History')
    plt.legend()

    # 绘制胜率
    plt.subplot(1, 2, 2)
    plt.plot(win_rate_history, label='Win Rate', color='orange')
    plt.xlabel('Game Number')
    plt.ylabel('Win Rate')
    plt.title('Win Rate History')
    plt.legend()

    plt.tight_layout()
    plt.show()

main()