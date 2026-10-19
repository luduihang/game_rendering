import os
import sys
import time
import json
from sympy import false
from const import *
import pygame
from algorithm import *
from game_room_deepseek_cp import *
import torch
import numpy as np
from card_deck import  *
all_option = ["10", "20", "50", "100", "throw_card", "compare_card"]
# pygame.init()
clock = pygame.time.Clock()  # 创建一个Clock对象来帮助跟踪时间


class Draw_Pic:
    def __init__(self):
        self.window_surface = pygame.display.set_mode((GAME_WIDTH_SIZE, GAME_HEIGHT_SIZE))
        self.bk_img = pygame.image.load(f"{Background}")
        self.bk_img = pygame.transform.scale(self.bk_img, (BACKGROUND_W, BACKGROUND_H))

        self.wallet = self.load_and_scale_image(wallet_spirit.Destination, wallet_spirit.CHARACTERS_SIZE[0])
        self.font = pygame.font.Font(font_spirit.Destination['ShangShouHanShuTi'], 36)  # 使用默认字体，字号为36
        self.font_location = font_spirit.Destination['ShangShouHanShuTi']

        self.card_deck = card_spirit()  # 用于读取const文件当中的卡牌图片路径
        self.card_img_deck = [[] for _ in range(2)]

        self.cards = []
        self.cards = None
        self.id = []
        self.back_card = pygame.image.load(f"{self.card_deck.Destination['Back']}")
        self.back_card = pygame.transform.scale(self.back_card, self.card_deck.Smaller_Size)

        self.choice_button_arr = []
        self.old_choice = 0

        self.rest_option = 0
        self.turn = 0
        self.option = 0
        self.all_bet = 10
        self.bets = [5, 5]
        self.player_money = []

        self.ending = True
        self.click_option = 0

    def load_cards(self, cards):
        self.card_img_deck = [[] for _ in range(2)]
        self.cards = cards

        self.rest_option = 0
        self.choice_button_arr = []
        self.old_choice = 0

    def load_and_scale_image(self, path, size):
        img = pygame.image.load(path)
        return pygame.transform.scale(img, size)

    def add_button(self):
        self.choice_button_arr = choice_button_pic(self.rest_option)
        for i in range(len(self.choice_button_arr)):
            self.window_surface.blit(self.choice_button_arr[i],
                                     button_spirit.Location[select_option[self.rest_option + i]])

    def render_player_text_info(self):
        self.window_surface.blit(self.bk_img, (0, 0))
        # 直接使用self.cards显示卡牌
        for order in range(2):
            # 显示押注金额
            show_font(self.window_surface, '押注', Player_Icon_Location.bet_money_loca[order],
                      font_spirit.Destination['ShangShouHanShuTi'], font_spirit.CHARACTERS_SIZE[order])
            show_font(self.window_surface, str(self.bets[order]), Player_Icon_Location.bet_loca[1 - order],
                      font_spirit.Destination['ShangShouHanShuTi'], font_spirit.CHARACTERS_SIZE[1 - order])
            # print(f"bets[{order}] = ", str(self.bets[order]))
            # 显示钱包还有钱包金额
            show_font(self.window_surface, str(self.player_money[order]), Player_Icon_Location.money_loca[1 - order],
                      self.font_location,
                      font_spirit.CHARACTERS_SIZE[order])
            self.window_surface.blit(self.wallet, Player_Icon_Location.wallet_loca[order])
            # 显示卡片
            if self.cards[order]:
                if not self.card_img_deck[order]:
                    self.card_img_deck[order] = [
                        self.load_and_scale_image(f"{self.card_deck.Destination[card['suit'] + str(card['value'])]}",
                                                  self.card_deck.CHARACTERS_SIZE) for card in self.cards[order]]

                # 这是自己的手牌
                for i, card_img in enumerate(self.card_img_deck[0]):
                    self.window_surface.blit(card_img, Player_Icon_Location.card_loca[0][i])

                # 这是测试机器人的手牌(渲染在对面)
                for i in range(len(self.cards[1])):
                    self.window_surface.blit(self.back_card, Player_Icon_Location.card_loca[1][i])

            # 如果游戏结束，显示所有卡牌
            if self.ending:
                for i, card in enumerate(self.cards[order]):
                    card_img = pygame.transform.scale(self.card_img_deck[order][i], self.card_deck.Smaller_Size)
                    self.window_surface.blit(card_img, Player_Icon_Location.card_loca[order][i])

    def update_inform(self, turn, option, all_bet, player_bet, player_money):
        self.all_bet = all_bet
        self.turn = turn
        self.option = option
        # for i in range(len(player_bet)):
        #     print(f"player_bet[{i}] = ", player_bet[i])
        #     self.bets[i] = player_bet[i]
        self.bets = player_bet
        self.player_money = player_money
        print("player_money", self.player_money)
        print("player_bet", player_bet)
        if 0 <= self.option <= 3:
            self.rest_option = max(self.rest_option, self.option)


    def gaming_info(self):
        self.render_player_text_info()

        rect_surface = pygame.Surface((245, 70))
        rect_surface.set_alpha(200)  # 设置Surface的透明度
        rect_surface.fill(Color.dark_yellow)  # 用颜色填充Surface
        self.window_surface.blit(rect_surface, (950, 20))
        show_font(self.window_surface, '总押注:', (980, 35), font_spirit.Destination['ShangShouHanShuTi'], 32,
                  Color.white)
        show_font(self.window_surface, str(self.all_bet), (1090, 35), font_spirit.Destination['ShangShouHanShuTi'], 32,
                  Color.white)

        string = None
        if 0 <= self.option <= 3:
            string = "下注" + select_option[self.option]
        elif self.option == 4:
            string = "弃牌"
        elif self.option == 5:
            string = "看牌"
        show_font(self.window_surface, string, Player_Icon_Location.inform_choice[self.turn],
                  font_spirit.Destination['ShangShouHanShuTi'], 48, Color.red)

    def refresh_page(self):
        pygame.display.flip()
        clock.tick(20)  # 通过设置帧率来控制循环速度

    def check_button_click(self):
        signal = False
        while not signal:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.gaming_button_pressed_style(event):
                        signal = True

    def gaming_button_pressed_style(self, event):
        for button_name, region in Mouce.button_choice.items():
            if region.collidepoint(event.pos):
                button_index = list(Mouce.button_choice.keys()).index(button_name)
                if 0 <= button_index <= 5:
                    if button_index >= self.rest_option:
                        self.click_option = button_index
                        return True
        return False

def safe_exit():
    """安全退出游戏，释放所有资源"""
    pygame.quit()
    sys.exit()

class DQN(torch.nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.fc1 = torch.nn.Linear(input_dim, 128)  # 保持与训练一致
        self.fc2 = torch.nn.Linear(128, 64)         # 保持与训练一致
        self.fc3 = torch.nn.Linear(64, output_dim)  # 保持与训练一致

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

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
        if os.path.exists("q_table1.txt"):
            with open("q_table1.txt", "r") as file:
                q_table_str = file.read()
                # 如果文件内容为空，返回空字典
                if not q_table_str.strip():
                    print("Q表文件为空，返回空字典")
                    return {}
                # 将字符串键转换为元组键
                try:
                    q_table = {eval(k): v for k, v in json.loads(q_table_str).items()}
                    print("Q表读取成功")
                    print(f"Q表包含的元素个数: {len(q_table)}")  # 打印元素数量
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


def select_action(device, state, legal_actions):
    state = torch.FloatTensor(state).unsqueeze(0).to(device)
    with torch.no_grad():
        q_values = model(state)
    masked_q = q_values.cpu().numpy()[0]
    masked_q[[i for i in range(6) if i not in legal_actions]] = -np.inf
    return np.argmax(masked_q)

def get_state(game_room, player_id):
    # 将Game_room状态转换为DQN输入
    state = np.array([
        game_room.circle / 10.0,
        game_room.player_bet[player_id] / 1000.0,
        game_room.player_bet[1 - player_id] / 1000.0
    ], dtype=np.float32)

    # 假设手牌特征处理
    card_prob = Cards_Probability(game_room.cards1 if player_id == 0 else game_room.cards2).get_probability()
    return np.concatenate([state, [card_prob]])  # 注意这里改为添加单个浮点数


# 初始化模型并加载权重
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = DQN(4, 6).to(device)  # 初始化时直接放到 device 上
model.load_state_dict(torch.load('dqn_model_0.pth', map_location=device))
model.eval()


# 主程序
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

# 主程序
if __name__ == "__main__":
    try:
        room = Game_room()
        # 初始化统计变量
        win_counts = [0, 0]  # [玩家0胜利次数, 玩家1胜利次数]
        batch_history = []  # 记录每20局的胜率
        wallet_history_0 = []  # 记录玩家0的钱包历史
        wallet_history_1 = []  # 记录玩家1的钱包历史
        batch_size = 20  # 每20局统计一次

        QN = Player()
        # 创建画布
        plt.figure(figsize=(12, 6))

        who_first = 1
        for i in range(1, 201):  # 1-100局
            who_first = 1 - who_first
            current_player = who_first

            room.init_arg()
            cards = [room.cards1, room.cards2]
            QN.update_cards(room.cards2)
            # 记录初始钱包金额
            if i == 1:
                wallet_history_0.append(room.player_money[0])
                wallet_history_1.append(room.player_money[1])

            room.whose_turn = current_player
            while not room.finish:
                if current_player == 0:
                    # DQN玩家回合
                    state = get_state(room, 0)
                    legal_actions = list(range(room.rest_option, 6))
                    action = select_action(device, state, legal_actions)
                    room.get_choice(action)
                    QN.update_inform(room.rest_option, room.player_bet[0], room.circle)

                # 机器人回合
                else:  # 对手回合(QN)
                    action = QN.get_option()
                    room.get_choice(action)
                    QN.update_inform(room.rest_option, room.player_bet[1], room.circle)

                # 切换玩家
                current_player = 1 - current_player

            # 记录胜负
            if room.winner == 0:
                win_counts[0] += 1
                room.Settlement()
            else:
                win_counts[1] += 1
                room.Settlement()

            # 记录钱包金额
            wallet_history_0.append(room.player_money[0])
            wallet_history_1.append(room.player_money[1])

            # 每20局统计一次
            if i % batch_size == 0:
                batch_win_rate = win_counts[0] / batch_size
                batch_history.append(batch_win_rate)
                print(f"第{i - batch_size + 1}-{i}局统计:")
                print(f"玩家0胜率: {batch_win_rate:.1%}")
                print(f"当前钱包 - 玩家0: {wallet_history_0[-1]}, 玩家1: {wallet_history_1[-1]}")
                win_counts = [0, 0]  # 重置计数器

        # 绘制胜率变化图
        plt.subplot(1, 2, 1)
        batches = range(1, len(batch_history) + 1)
        plt.plot(batches, batch_history, 'bo-', label='DQN Player 0 Win Rate')
        plt.axhline(y=0.5, color='r', linestyle='--', label='Baseline (50%)')
        plt.xlabel('Batch (every 20 games)')
        plt.ylabel('Win Rate')
        plt.title('DQN Player 0 Win Rate per 20 Games')
        plt.ylim(0, 1)
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
        plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
        plt.legend()

        # 绘制钱包变化图
        plt.subplot(1, 2, 2)
        games = range(len(wallet_history_0))
        plt.plot(games, wallet_history_0, 'g-', label='DQN Player 0 Wallet')
        plt.plot(games, wallet_history_1, 'b-', label='QN Player 1 Wallet')
        plt.xlabel('Game Number')
        plt.ylabel('Wallet Amount')
        plt.title('Wallet Changes Over Time')
        plt.legend()

        plt.tight_layout()
        plt.savefig('game_stats.png')
        plt.show()

    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        safe_exit()