import json
import numpy as np
import matplotlib.pyplot as plt
import os

from matplotlib.ticker import MaxNLocator

from card_deck import Cards, Cards_Value, Cards_Probability

options = ['10', '20', '50', '100', 'give_up', 'cmp']  # 显示action空间


class Game_room:
    def __init__(self):
        self.deck = Cards()
        self.deck.shuffle_deck()
        self.rest_option = 0

        self.circle = 1  # 显示当前轮次
        self.all_bet = 10  # 桌面上面的所有押注金额
        self.player_bet = [5, 5]
        self.whose_turn = 0  # 当前出牌的玩家
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

        print("玩家1的手牌是", self.cards1)
        print("玩家2的手牌是", self.cards2)

    def init_arg(self):
        self.deck.reset_deck()
        self.deck.shuffle_deck()
        self.rest_option = 0
        self.circle = 1  # 显示当前轮次
        self.all_bet = 10  # 桌面上面的所有押注金额
        self.player_bet = [5, 5]
        self.whose_turn = 0  # 当前出牌的玩家
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
            print(f"玩家{i + 1}已经押注{self.player_bet[i]}")
        print(f"玩家1的手牌是{self.cards1}")
        print(f"玩家2的手牌是{self.cards2}")
        print()
        print(f"当前总共押注金额是{self.all_bet}")

    def get_choice(self, action):
        if action <= 3:
            self.rest_option = action  # 更新接下来的选项
            self.player_bet[self.whose_turn] += int(options[action])
            self.all_bet += int(options[action])
        elif action == 4:
            self.winner = 1 - self.whose_turn
            self.finish = True
        elif action == 5:
            self.player_bet[self.whose_turn] += int(options[self.rest_option])
            self.all_bet += int(options[self.rest_option])
            if self.cards1_value < self.cards2_value:
                self.winner = 1
                self.finish = True
            else:
                self.winner = 0
                self.finish = True
        print(f"玩家{self.whose_turn + 1}选择了", options[action])
        self.whose_turn += 1
        self.whose_turn %= 2


class QLearningPlayer:
    def __init__(self, player_id):
        self.player_id = player_id
        self.rest_option = 0
        self.all_bet = 10
        self.probable = None
        self.card_state = None
        self.circle_state = 0
        self.bet_state = 5

        # Q-learning参数
        self.q_table = self.load_q_table(player_id)  # 加载时也根据player_id加载不同的文件
        self.alpha = 0.1  # 学习率
        self.gamma = 0.9  # 折扣因子
        self.epsilon = 1.0  # 探索率
        self.epsilon_decay = 0.997  # 探索率衰减
        self.epsilon_min = 0.05  # 最小探索率
        self.decision_history = []

    def load_q_table(self, player_id):
        filename = f"q_table{player_id}.txt"  # player1用q_table0.txt, player2用q_table1.txt
        if os.path.exists(filename):
            with open(filename, "r") as file:
                q_table_str = file.read()
                if not q_table_str.strip():
                    return {}
                try:
                    q_table = {eval(k): v for k, v in json.loads(q_table_str).items()}
                    return q_table
                except json.JSONDecodeError:
                    return {}
        else:
            return {}

    def save_q_table(self, pos):
        q_table_str = json.dumps({str(k): v for k, v in self.q_table.items()})
        filename = f"q_table{pos}.txt"  # 根据pos参数生成不同的文件名
        with open(filename, "w") as file:
            file.write(q_table_str)

    def update_cards(self, cards):
        self.rest_option = 0
        self.all_bet = 10
        self.probable = Cards_Probability(cards)
        self.card_state = self.probable.get_state()

    def update_inform(self, option, my_bet, circle):
        self.rest_option = option
        self.bet_state = my_bet
        self.circle_state = circle

    def get_q_value(self, state, action):
        return self.q_table.get((state, action), 0.0)

    def update_q_value(self, state, action, reward, next_state):
        old_value = self.get_q_value(state, action)
        next_max = max([self.get_q_value(next_state, a) for a in range(self.rest_option, 6)])
        new_value = old_value + self.alpha * (reward + self.gamma * next_max - old_value)
        self.q_table[(state, action)] = new_value

    def choose_action(self, state):
        if np.random.rand() < self.epsilon:
            return np.random.randint(self.rest_option, 6)
        else:
            q_values = [self.get_q_value(state, a) for a in range(self.rest_option, 6)]
            return np.argmax(q_values) + self.rest_option

    def get_option(self):
        state = (self.circle_state, self.bet_state, self.card_state)
        action = self.choose_action(state)
        print(f"玩家{self.player_id}选择了选项：{options[action]}")
        self.decision_history.append((state, action))
        return action

    def update_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def update_q_table_with_reward(self, reward):
        if not self.decision_history:
            return

        avg_reward = reward / len(self.decision_history)

        for i, (state, action) in enumerate(self.decision_history):
            next_state = self.decision_history[i + 1][0] if i + 1 < len(self.decision_history) else None
            if next_state:
                self.update_q_value(state, action, avg_reward, next_state)
            else:
                self.update_q_value(state, action, avg_reward, state)

        self.decision_history = []


def main():
    room = Game_room()
    player1 = QLearningPlayer(1)
    player2 = QLearningPlayer(2)

    # 记录训练数据
    reward_history = []
    win_rate_history_player1 = []
    win_rate_history_player2 = []
    wallet_history_0 = []  # 记录玩家1钱包
    wallet_history_1 = []  # 记录玩家2钱包
    total_wins_player1 = 0
    total_wins_player2 = 0
    total_games = 0

    who_first = 1
    for i in range(500):  # 增加训练轮次
        who_first = 1 - who_first
        current_player = who_first
        player1.update_cards(room.cards1)
        player2.update_cards(room.cards2)

        room.whose_turn = current_player
        while True:
            # 玩家1的回合
            if room.whose_turn == 0:
                choice = player1.get_option()
                room.get_choice(choice)
                player1.update_inform(room.rest_option, room.player_bet[0], room.circle)
                player2.update_inform(room.rest_option, room.player_bet[1], room.circle)
                if room.finish:
                    break

            # 玩家2的回合
            if room.whose_turn == 1:
                choice = player2.get_option()
                room.get_choice(choice)
                player1.update_inform(room.rest_option, room.player_bet[0], room.circle)
                player2.update_inform(room.rest_option, room.player_bet[1], room.circle)
                if room.finish:
                    break

        # 游戏结束，更新Q表
        total_games += 1
        if room.winner == 0:  # 玩家1获胜
            reward = room.all_bet - room.player_bet[0]
            room.wallet1 += reward
            room.wallet2 -= reward
            player1.update_q_table_with_reward(reward)
            player2.update_q_table_with_reward(-reward)
            total_wins_player1 += 1
            reward_history.append(reward)
        else:  # 玩家2获胜
            reward = room.all_bet - room.player_bet[1]
            room.wallet1 -= reward
            room.wallet2 += reward
            player1.update_q_table_with_reward(-reward)
            player2.update_q_table_with_reward(reward)
            reward_history.append(-reward)
            total_wins_player2 += 1

        # 记录钱包金额
        wallet_history_0.append(room.wallet1)
        wallet_history_1.append(room.wallet2)

        # 更新探索率
        player1.update_epsilon()
        player2.update_epsilon()

        # 计算胜率
        win_rate_p1 = total_wins_player1 / total_games
        win_rate_p2 = total_wins_player2 / total_games
        win_rate_history_player1.append(win_rate_p1)
        win_rate_history_player2.append(win_rate_p2)

        # 每100轮显示一次进度
        if (i + 1) % 100 == 0:
            print(f"\n=== 训练进度: {i + 1}/1000 ===")
            print(f"玩家1钱包: {room.wallet1}")
            print(f"玩家2钱包: {room.wallet2}")
            print(f"玩家1胜率: {win_rate_p1:.2f}")
            print(f"玩家2胜率: {win_rate_p2:.2f}")
            print(f"玩家1探索率: {player1.epsilon:.4f}")
            print(f"玩家2探索率: {player2.epsilon:.4f}")

        room.init_arg()

    # 保存Q表
    player1.save_q_table(1)
    player2.save_q_table(2)

    # 绘制训练曲线
    plt.figure(figsize=(12, 6))

    # 胜率历史 (左图)
    plt.subplot(1, 2, 1)
    games = range(1, len(win_rate_history_player1) + 1)
    plt.plot(games, win_rate_history_player1, 'bo-', label='QN Player 1 Win Rate')
    plt.plot(games, win_rate_history_player2, 'go-', label='QN Player 2 Win Rate')
    plt.axhline(y=0.5, color='r', linestyle='--', label='Baseline (50%)')
    plt.xlabel('Game Number')
    plt.ylabel('Win Rate')
    plt.title('Win Rate Over Time')
    plt.ylim(0, 1)
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()

    # 绘制钱包变化图 (右图)
    plt.subplot(1, 2, 2)
    games = range(len(wallet_history_0))
    plt.plot(games, wallet_history_0, 'b-', label='QN Player 1 Wallet')
    plt.plot(games, wallet_history_1, 'g-', label='QN Player 2 Wallet')
    plt.xlabel('Game Number')
    plt.ylabel('Wallet Amount')
    plt.title('Wallet Changes Over Time')
    plt.legend()

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()