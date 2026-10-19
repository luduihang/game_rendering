import torch
import numpy as np
from collections import deque
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
        # print(f"玩家{self.whose_turn}选择了", options[action])
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


class DQNAgent:
    def __init__(self, state_dim=9, action_dim=6):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DQN(state_dim, action_dim).to(self.device)
        self.target_model = DQN(state_dim, action_dim).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        self.memory = deque(maxlen=2000)
        self.batch_size = 32
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.update_target()

    def update_target(self):
        self.target_model.load_state_dict(self.model.state_dict())

    def get_state(self, game_room, player_id):
        # 将Game_room状态转换为DQN输入
        state = np.array([
            game_room.circle / 10.0,
            game_room.player_bet[player_id] / 1000.0,
            game_room.player_bet[1 - player_id] / 1000.0
        ], dtype=np.float32)

        # 假设手牌特征处理
        card_value = Cards_Probability(game_room.cards1 if player_id == 0 else game_room.cards2).get_state()
        card_onehot = np.zeros(6, dtype=np.float32)
        card_onehot[min(card_value - 1, 5)] = 1.0  # 防止越界

        return np.concatenate([state, card_onehot])

    def get_action(self, state, legal_actions):
        if np.random.rand() < self.epsilon:
            return random.choice(legal_actions)
        else:
            state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            with torch.no_grad():
                q_values = self.model(state)
            masked_q = q_values.cpu().numpy()[0]
            masked_q[[i for i in range(6) if i not in legal_actions]] = -np.inf
            return np.argmax(masked_q)

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def replay(self):
        if len(self.memory) < self.batch_size:
            return

        minibatch = random.sample(self.memory, self.batch_size)
        states = torch.FloatTensor([t[0] for t in minibatch]).to(self.device)
        actions = torch.LongTensor([t[1] for t in minibatch]).to(self.device)
        rewards = torch.FloatTensor([t[2] for t in minibatch]).to(self.device)
        next_states = torch.FloatTensor([t[3] for t in minibatch]).to(self.device)
        dones = torch.FloatTensor([t[4] for t in minibatch]).to(self.device)

        current_q = self.model(states).gather(1, actions.unsqueeze(1))
        next_q = self.target_model(next_states).max(1)[0].detach()
        target_q = rewards + (1 - dones) * self.gamma * next_q

        loss = torch.nn.functional.mse_loss(current_q.squeeze(), target_q)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay


def main():
    room = Game_room()
    dqn_agent = DQNAgent()

    # 训练参数
    total_episodes = 101
    reward_history = []
    win_rate_history = []

    for episode in range(total_episodes):
        opponent_robot = Robot('1')  # 原robot作为对手
        room.init_arg()  # 重置游戏
        state = dqn_agent.get_state(room, 0)
        total_reward = 0
        done = False

        opponent_robot.init_dick(['1', '0'], room.cards2)
        json_pack = {'game_process': 'inform',
                     '1': {'failure': False, 'bet_money': 5},
                     '0': {'failure': False, 'bet_money': 5},
                     'property': 'table', 'all_bets': 10, 'whose_turn': 0, 'rest_option': 0, 'option': 0, 'target': -1}
        while not done:
            # DQN玩家（玩家0）的回合
            legal_actions = list(range(room.rest_option, 6))
            action = dqn_agent.get_action(state, legal_actions)

            # 执行动作
            prev_state = state
            room.get_choice(action)
            next_state = dqn_agent.get_state(room, 0)
            reward = 0

            json_pack['0']['bet_money'] = room.player_bet[0]
            json_pack['all_bets'] = room.all_bet
            json_pack['rest_option'] = room.rest_option
            json_pack['whose_turn'] = 0
            opponent_robot.update_dick(json_pack)

            # 对手机器人（玩家1）的回合
            if not room.finish:
                opponent_action = opponent_robot.cal_final_option()
                room.get_choice(opponent_action['option'])

                json_pack['1']['bet_money'] = room.player_bet[1]
                json_pack['all_bets'] = room.all_bet
                json_pack['rest_option'] = room.rest_option
                json_pack['whose_turn'] = 1
                opponent_robot.update_dick(json_pack)

            # 计算即时奖励
            if room.finish:
                reward = room.all_bet if room.winner == 0 else -room.player_bet[0]
                done = True

            # 存储经验
            dqn_agent.remember(prev_state, action, reward, next_state, done)

            # 训练
            dqn_agent.replay()

            total_reward += reward
            state = next_state

        # 记录训练数据
        reward_history.append(total_reward)
        win_rate = np.mean([1 if r > 0 else 0 for r in reward_history[-100:]])
        win_rate_history.append(win_rate)

        # 定期保存模型
        if episode != 0 and episode % 100 == 0:
            torch.save(dqn_agent.model.state_dict(), f"dqn_model_ep{episode}.pth")
            print(f"Episode {episode} | WinRate: {win_rate:.2f} | AvgReward: {np.mean(reward_history[-100:]):.2f}")

    # 最终模型保存
    torch.save(dqn_agent.model.state_dict(), "dqn_final.pth")


if __name__ == "__main__":
    main()