import os
import sys
import time

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

        self.rest_option = 0
        self.turn = 0
        self.option = 0
        self.all_bet = 10
        self.bets = [5, 5]
        self.player_money = [10000, 10000]

        self.ending = True

    def load_cards(self, cards):
        self.card_img_deck = [[] for _ in range(2)]
        self.cards = cards

    def load_and_scale_image(self, path, size):
        img = pygame.image.load(path)
        return pygame.transform.scale(img, size)

    def render_player_text_info(self):
        self.window_surface.blit(self.bk_img, (0, 0))
        # 直接使用self.cards显示卡牌
        for order in range(2):
            # 显示押注金额
            show_font(self.window_surface, '押注', Player_Icon_Location.bet_money_loca[order],
                      font_spirit.Destination['ShangShouHanShuTi'], font_spirit.CHARACTERS_SIZE[order])
            show_font(self.window_surface, str(self.bets[order]), Player_Icon_Location.bet_loca[order],
                      font_spirit.Destination['ShangShouHanShuTi'], font_spirit.CHARACTERS_SIZE[order])

            # 显示钱包还有钱包金额
            show_font(self.window_surface, str(self.player_money[order]), Player_Icon_Location.money_loca[order],
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


    def update_inform(self, turn, option, all_bet, player_bet):
        self.all_bet = all_bet
        self.turn = turn
        self.option = option
        for i in range(len(player_bet)):
            self.bets[i] = player_bet[i]

        if 0 <= self.option <= 3:
            self.bets[self.turn] += int(all_option[self.option])
            self.rest_option = min(self.rest_option, self.option)
            self.player_money[self.turn] -= int(all_option[self.option])
        elif self.option == 5:
            self.bets[self.turn] += int(all_option[self.rest_option])
            self.player_money[self.turn] -= int(all_option[self.rest_option])

    def gaming_info(self):
        self.window_surface.blit(self.bk_img, (0, 0))
        self.render_player_text_info()

        rect_surface = pygame.Surface((245, 70))
        rect_surface.set_alpha(200)  # 设置Surface的透明度
        rect_surface.fill(Color.dark_yellow)  # 用颜色填充Surface
        self.window_surface.blit(rect_surface, (900, 20))
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
    card_value = Cards_Probability(game_room.cards1 if player_id == 0 else game_room.cards2).get_state()
    card_onehot = np.zeros(6, dtype=np.float32)
    card_onehot[min(card_value - 1, 5)] = 1.0  # 防止越界

    return np.concatenate([state, card_onehot])


# 初始化模型并加载权重
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = DQN(9, 6).to(device)  # 初始化时直接放到 device 上
model.load_state_dict(torch.load('dqn_model_ep50.pth', map_location=device))
model.eval()


json_pack = {'game_process': 'inform',
             '1': {'failure': False, 'bet_money': 5},
             '0': {'failure': False, 'bet_money': 5},
             'property': 'table', 'all_bets': 10, 'whose_turn': 0, 'rest_option': 0, 'option': 0,
             'target': -1}

# 主程序
if __name__ == "__main__":
    try:
        room = Game_room()
        draw = Draw_Pic()
        for i in range(10):
            opponent_robot = Robot('1')  # 原robot作为对手
            room.init_arg()  # 重置游戏
            cards = []
            cards.append(room.cards1)
            cards.append(room.cards2)
            draw.load_cards(cards)

            total_reward = 0

            opponent_robot.init_dick(['1', '0'], room.cards2)
            draw.render_player_text_info()
            draw.refresh_page()
            print("重开一局")
            while not room.finish:
                state = get_state(room, 0)
                # DQN玩家（玩家0）的回合
                legal_actions = list(range(room.rest_option, 6))
                action = select_action(device, state, legal_actions)

                room.get_choice(action)
                draw.update_inform(room.whose_turn, action, room.all_bet, room.player_bet)
                draw.gaming_info()
                draw.refresh_page()
                time.sleep(3)

                json_pack['0']['bet_money'] = room.player_bet[0]
                json_pack['all_bets'] = room.all_bet
                json_pack['rest_option'] = room.rest_option
                json_pack['whose_turn'] = 0
                opponent_robot.update_dick(json_pack)
                # 对手机器人（玩家1）的回合
                if not room.finish:
                    opponent_action = opponent_robot.cal_final_option()
                    print("opponent_action", opponent_action)
                    room.get_choice(opponent_action['option'])
                    draw.update_inform(room.whose_turn, opponent_action['option'], room.all_bet, room.player_bet)
                    draw.gaming_info()
                    draw.refresh_page()
                    time.sleep(3)

                    json_pack['1']['bet_money'] = room.player_bet[1]
                    json_pack['all_bets'] = room.all_bet
                    json_pack['rest_option'] = room.rest_option
                    json_pack['whose_turn'] = 1
                    opponent_robot.update_dick(json_pack)



    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        safe_exit()