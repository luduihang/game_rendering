import os
import sys
import time
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from sympy import false
from card_deck import *
from const import *
import pygame
from algorithm import *
from game_room_deepseek_cp import *
import torch
import numpy as np
from card_deck import  *
all_option = ["10", "20", "50", "100", "throw_card", "compare_card"]
pygame.init()
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


# 初始化模型并加载权重
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = DQN(4, 6).to(device)  # 初始化时直接放到 device 上
model.load_state_dict(torch.load('dqn_model_1.pth', map_location=device))
model.eval()


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

if __name__ == "__main__":
    room = Game_room()
    draw = Draw_Pic()
    dqn_agent = DQNAgent()

    print("CUDA 是否可用:", torch.cuda.is_available())
    print("GPU 数量:", torch.cuda.device_count())
    print("当前 GPU 名称:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "无")

    reward_history = []
    win_rate_history = []
    wallet_history_0 = []  # DQN玩家的钱包历史
    wallet_history_1 = []  # 对手的钱包历史
    # 记录初始钱包金额
    wallet_history_0.append(room.player_money[0])
    wallet_history_1.append(room.player_money[1])
    round = 50
    who_first = 1
    for episode in range(round):
        who_first = 1 - who_first
        current_player = who_first
        room.init_arg()  # 重置游戏
        cards = []
        cards.append(room.cards1)
        cards.append(room.cards2)
        draw.load_cards(cards)

        state = get_state(room, 0)
        prev_state = state

        total_reward = 0
        done = False
        # 同步图像渲染押注信息
        draw.player_money = room.player_money
        draw.render_player_text_info()
        draw.refresh_page()
        print("重开一局")
        time.sleep(1.5)
        ## 随机决定初始玩家

        room.whose_turn = current_player
        while not room.finish:
            reward = 0
            if current_player == 0:  # DQN玩家回合
                legal_actions = list(range(room.rest_option, 6))
                action = dqn_agent.get_action(state, legal_actions)
                # 执行动作
                prev_state = state
                room.get_choice(action)
                next_state = dqn_agent.get_state(room, 0)

                draw.update_inform(room.whose_turn, action, room.all_bet, room.player_bet, room.player_money)
                draw.gaming_info()
                draw.refresh_page()
                time.sleep(1.5)

            else:  # 对手机器人回合
                draw.add_button()
                draw.refresh_page()
                draw.check_button_click()
                opponent_action = draw.click_option
                print("opponent_action", opponent_action)
                room.get_choice(opponent_action)
                draw.update_inform(room.whose_turn, opponent_action, room.all_bet, room.player_bet, room.player_money)
                draw.gaming_info()
                draw.refresh_page()
                time.sleep(1.5)

            # 检查游戏是否结束
            if room.finish:
                if room.winner == 0:
                    reward = room.all_bet
                else:
                    reward = -room.player_bet[0]
                print("DQN的reward是：", reward)
                done = True
                print("最终的胜利者是：", room.winner)
                room.Settlement()

                # 记录游戏结果
                reward_history.append(reward)
                win_rate = np.mean([1 if r > 0 else 0 for r in reward_history[-100:]])
                win_rate_history.append(win_rate)

                wallet_history_0.append(room.player_money[0])
                wallet_history_1.append(room.player_money[1])

            # if current_player == 0:
            #     dqn_agent.remember(prev_state, action, reward, next_state, done)
            #     # 训练
            #     dqn_agent.replay()
            #     total_reward += reward
            #     state = next_state

            # 切换玩家
            current_player = 1 - current_player

    # 可视化结果
    plt.figure(figsize=(12, 6))
    # 胜率历史 (左图)
    plt.subplot(1, 2, 1)
    games = range(1, len(win_rate_history) + 1)
    plt.plot(games, win_rate_history, 'bo-', label='DQN Player Win Rate')
    plt.axhline(y=0.5, color='r', linestyle='--', label='Baseline (50%)')
    plt.xlabel('Game Number')
    plt.ylabel('Win Rate')
    plt.title('DQN Player Win Rate Over Games')
    plt.ylim(0, 1)
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()

    # 钱包变化 (右图)
    plt.subplot(1, 2, 2)
    games = range(len(wallet_history_0))
    plt.plot(games, wallet_history_0, 'b-', label='DQN Player Wallet')
    plt.plot(games, wallet_history_1, 'g-', label='Opponent Wallet')
    plt.xlabel('Game Number')
    plt.ylabel('Wallet Amount')
    plt.title('Wallet Changes Over Games')
    plt.legend()

    plt.tight_layout()
    plt.savefig('dqn_vs_opponent_stats.png')

    # 显示图表
    plt.show()

    # 安全退出
    safe_exit()

    # # # 最终模型保存
    # torch.save(dqn_agent.model.state_dict(), "dqn_final.pth")
    # dqn_agent.save_memory()