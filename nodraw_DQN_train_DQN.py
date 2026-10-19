# ... (保留之前的导入和类定义不变)

import json
import numpy as np
import matplotlib.pyplot as plt
import os
import random
import torch
import torch.nn
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

# 原DQN网络定义保持不变
class DQN(torch.nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.fc1 = torch.nn.Linear(input_dim, 128)
        self.fc2 = torch.nn.Linear(128, 64)
        self.fc3 = torch.nn.Linear(64, output_dim)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)


class DQNPlayer:
    def __init__(self, player_id):
        self.player_id = player_id
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = DQN(9, 6).to(self.device)
        self.target_model = DQN(9, 6).to(self.device)
        self.target_model.load_state_dict(self.model.state_dict())
        self.target_update = 32  # 每10局更新一次目标网络

        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        self.memory = []  # 经验回放缓冲区
        self.batch_size = 32
        self.gamma = 0.9
        self.epsilon = 1.0
        self.epsilon_min = 0.1
        self.epsilon_decay = 0.998

        # 加载已有模型
        model_file = f'dqn_model_{player_id}.pth'
        if os.path.exists(model_file):
            self.model.load_state_dict(torch.load(model_file, map_location=self.device))
            print(f"Player {player_id} loaded existing model")

        self.model.eval()
        self.target_model.eval()

    def get_state(self, game_room):
        # 将Game_room状态转换为DQN输入
        state = np.array([
            game_room.circle / 10.0,
            game_room.player_bet[self.player_id] / 1000.0,
            game_room.player_bet[1 - self.player_id] / 1000.0
        ], dtype=np.float32)

        # 手牌特征处理
        card_value = Cards_Probability(game_room.cards1 if self.player_id == 0 else game_room.cards2).get_state()
        card_onehot = np.zeros(6, dtype=np.float32)
        card_onehot[min(card_value - 1, 5)] = 1.0  # 防止越界

        return np.concatenate([state, card_onehot])

    def select_action(self, state, legal_actions):
        state = torch.FloatTensor(state).unsqueeze(0).to(self.device)

        if np.random.rand() < self.epsilon:
            return np.random.choice(legal_actions)
        else:
            with torch.no_grad():
                q_values = self.model(state)
            masked_q = q_values.cpu().numpy()[0]
            masked_q[[i for i in range(6) if i not in legal_actions]] = -np.inf
            return np.argmax(masked_q)

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
        if len(self.memory) > 10000:  # 限制经验回放缓冲区大小
            self.memory.pop(0)

    def replay(self):
        if len(self.memory) < self.batch_size:
            return

        minibatch = random.sample(self.memory, self.batch_size)
        states = torch.FloatTensor(np.array([t[0] for t in minibatch])).to(self.device)
        actions = torch.LongTensor(np.array([t[1] for t in minibatch])).to(self.device)
        rewards = torch.FloatTensor(np.array([t[2] for t in minibatch])).to(self.device)
        next_states = torch.FloatTensor(np.array([t[3] for t in minibatch])).to(self.device)
        dones = torch.FloatTensor(np.array([t[4] for t in minibatch])).to(self.device)

        current_q = self.model(states).gather(1, actions.unsqueeze(1))
        next_q = self.target_model(next_states).max(1)[0].detach()
        target = rewards + (1 - dones) * self.gamma * next_q

        loss = torch.nn.functional.mse_loss(current_q.squeeze(), target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # 更新epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)


    def update_target_model(self):
        self.target_model.load_state_dict(self.model.state_dict())

    def save_model(self):
        torch.save(self.model.state_dict(), f'dqn_model_{self.player_id}.pth')


# 主程序
if __name__ == "__main__":

    room = Game_room()
    player0 = DQNPlayer(0)
    player1 = DQNPlayer(1)

    # 初始化统计变量
    win_counts = [0, 0]  # [玩家0胜利次数, 玩家1胜利次数]
    batch_history = []  # 记录每20局的胜率
    wallet_history_0 = []  # 记录玩家0的钱包历史
    wallet_history_1 = []  # 记录玩家1的钱包历史
    batch_size = 20  # 每20局统计一次

    who_first = 1
    for i in range(1, 300):  # 1-100局
        who_first = 1 - who_first
        current_player = who_first

        room.init_arg()
        # 记录初始钱包金额
        if i == 1:
            wallet_history_0.append(room.wallet1)
            wallet_history_1.append(room.wallet2)

        room.whose_turn = current_player
        last_states = [None, None]
        last_actions = [None, None]

        while not room.finish:
            player_id = current_player
            opponent_id = 1 - player_id

            # 获取当前状态
            state = player0.get_state(room) if player_id == 0 else player1.get_state(room)
            legal_actions = list(range(room.rest_option, 6))

            # 选择动作
            if player_id == 0:
                action = player0.select_action(state, legal_actions)
            else:
                action = player1.select_action(state, legal_actions)

            # 执行动作
            room.get_choice(action)

            # 获取奖励和下一个状态
            reward = 0
            next_state = player0.get_state(room) if player_id == 0 else player1.get_state(room)
            done = room.finish

            if done:
                winner = room.winner
                if winner == player_id:
                    reward = room.all_bet - room.player_bet[player_id]
                else:
                    reward = -(room.all_bet - room.player_bet[player_id])

            if action == 3:  # 下注100
                reward *= 0.6  # 减少大额下注的奖励
            if action == 2:  # 下注50
                reward *= 0.8  # 减少大额下注的奖励

            # 存储经验
            if player_id == 0:
                player0.remember(state, action, reward, next_state, done)
            else:
                player1.remember(state, action, reward, next_state, done)

            # 训练网络
            if player_id == 0:
                player0.replay()
            else:
                player1.replay()

            # 切换玩家
            current_player = 1 - current_player

        # 记录胜负
        winner = room.winner
        win_counts[winner] += 1

        # 结算
        if winner == 0:
            room.wallet1 += room.all_bet - room.player_bet[0]
            room.wallet2 -= room.all_bet - room.player_bet[0]
        else:
            room.wallet1 -= room.all_bet - room.player_bet[1]
            room.wallet2 += room.all_bet - room.player_bet[1]

        # 记录钱包金额
        wallet_history_0.append(room.wallet1)
        wallet_history_1.append(room.wallet2)

        # 定期更新目标网络
        if i % player0.target_update == 0:
            player0.update_target_model()
            player1.update_target_model()

        # 每20局统计一次
        if i % batch_size == 0:
            batch_win_rate = win_counts[0] / batch_size
            batch_history.append(batch_win_rate)
            print(f"第{i - batch_size + 1}-{i}局统计:")
            print(f"玩家0胜率: {batch_win_rate:.1%}")
            print(f"当前钱包 - 玩家0: {wallet_history_0[-1]}, 玩家1: {wallet_history_1[-1]}")
            win_counts = [0, 0]  # 重置计数器

    # 保存最终模型
    player0.save_model()
    player1.save_model()

    # 绘制胜率变化图
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    batches = range(1, len(batch_history) + 1)
    plt.plot(batches, batch_history, 'bo-', label='Player 0 Win Rate')
    plt.axhline(y=0.5, color='r', linestyle='--', label='Baseline (50%)')
    plt.xlabel('Batch (every 20 games)')
    plt.ylabel('Win Rate')
    plt.title('Player 0 Win Rate per 20 Games')
    plt.ylim(0, 1)
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()

    # 绘制钱包变化图
    plt.subplot(1, 2, 2)
    games = range(len(wallet_history_0))
    plt.plot(games, wallet_history_0, 'g-', label='Player 0 Wallet')
    plt.plot(games, wallet_history_1, 'b-', label='Player 1 Wallet')
    plt.xlabel('Game Number')
    plt.ylabel('Wallet Amount')
    plt.title('Wallet Changes Over Time')
    plt.legend()

    plt.tight_layout()
    plt.savefig('dqn_vs_dqn_stats.png')
    plt.show()

