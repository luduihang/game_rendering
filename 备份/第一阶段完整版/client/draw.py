import time
import pygame
import sys
import threading
from const import *
from pygame.locals import *
from algorithm import *


# pygame.init()
clock = pygame.time.Clock()  # 创建一个Clock对象来帮助跟踪时间

class Draw_Pic:
    def __init__(self):
        self.window_surface = pygame.display.set_mode((GAME_WIDTH_SIZE, GAME_HEIGHT_SIZE))

        self.bk_img = pygame.image.load(f"{Background}")
        self.bk_img = pygame.transform.scale(self.bk_img, (BACKGROUND_W, BACKGROUND_H))
        self.login_bk_img = pygame.image.load(f"{Login_Background}")
        self.login_bk_img = pygame.transform.scale(self.login_bk_img, (BACKGROUND_W, BACKGROUND_H))
        # self.window_surface.blit(self.bk_img, (0, 0))
        self.update_json_finish = False

        self.font = pygame.font.Font(font_spirit.Destination['ShangShouHanShuTi'], 36)  # 使用默认字体，字号为36
        self.font_location = font_spirit.Destination['ShangShouHanShuTi']
        self.json = None
        self.sorted_json = None
        self.numeric_keys = None
        self.bgm_dest = bgm_directory
        self.order = 2
        self.allocation = None
        self.card_deck = card_spirit()

        self.update_signal = False
        self.target_need_choose = False

        self.inform_list = []
        # UserAllocation('1')
    def get_id(self,id):
        self.id = id
        self.allocation = UserAllocation(id)
        print("页面渲染获取到id:",self.id)

    def login(self):
        self.window_surface.blit(self.login_bk_img, (0, 0))

        # pygame.draw.rect(self.window_surface, Color.gold, (312, 160, 630, 490), 0)
        arr_icon = ['back','frame','logo','age','user','password']
        public_login_pic(arr_icon,self.window_surface)

        show_font(self.window_surface, '抵制不良游戏，拒绝盗版游戏。注意自我保护，谨防受骗上当。', (700,750), font_spirit.Destination['ShangShouHanShuTi'], 20)
        show_font(self.window_surface, '用户注册', button_spirit.Location['register'],font_spirit.Destination['ShangShouHanShuTi'], 30)
        show_font(self.window_surface, '账号', (370,290),font_spirit.Destination['ShangShouHanShuTi'], 25)
        show_font(self.window_surface, '密码', (370,380), font_spirit.Destination['ShangShouHanShuTi'], 25)

        quit_button = pygame.image.load(f"{button_spirit.Destination['quit_button']}")
        quit_button = pygame.transform.scale(quit_button, button_spirit.Characters_Size['quit_button'])
        self.window_surface.blit(quit_button, button_spirit.Location['quit_button'])

        log_in = pygame.image.load(f"{button_spirit.Destination['log_in']}")
        log_in = pygame.transform.scale(log_in, button_spirit.Characters_Size['log_in'])
        self.window_surface.blit(log_in, button_spirit.Location['log_in'])

    def register(self):
        self.window_surface.blit(self.login_bk_img, (0, 0))
        arr_icon = ['back', 'frame', 'age', 'user', 'password','male','female','nickname']
        public_login_pic(arr_icon, self.window_surface)

        quit_button = pygame.image.load(f"{button_spirit.Destination['quit_button']}")
        quit_button = pygame.transform.scale(quit_button, button_spirit.Characters_Size['quit_button'])
        self.window_surface.blit(quit_button, button_spirit.Location['quit_button_regis'])
        submit_button = pygame.image.load(f"{button_spirit.Destination['submit']}")
        submit_button = pygame.transform.scale(submit_button, button_spirit.Characters_Size['submit'])
        self.window_surface.blit(submit_button, button_spirit.Location['submit'])
        return_button = pygame.image.load(f"{button_spirit.Destination['return']}")
        return_button = pygame.transform.scale(return_button, button_spirit.Characters_Size['return'])
        self.window_surface.blit(return_button, button_spirit.Location['return'])

        show_font(self.window_surface, '用户注册', (550,200), font_spirit.Destination['ShangShouHanShuTi'],40)
        show_font(self.window_surface, '您的性别:', (350, 570), font_spirit.Destination['ShangShouHanShuTi'], 30)
        show_font(self.window_surface, '账号', (350, 290), font_spirit.Destination['ShangShouHanShuTi'], 30)
        show_font(self.window_surface, '密码', (350, 380), font_spirit.Destination['ShangShouHanShuTi'], 30)
        show_font(self.window_surface, '昵称', (350, 470), font_spirit.Destination['ShangShouHanShuTi'], 30)

        pygame.draw.circle(self.window_surface, Color.white, login.Location['circle1'], login.CHARACTERS_SIZE['circle1'])
        pygame.draw.circle(self.window_surface, Color.white, login.Location['circle2'], login.CHARACTERS_SIZE['circle2'])

        pygame.draw.circle(self.window_surface, Color.gray, login.Location['circle3'],login.CHARACTERS_SIZE['circle3'])
        pygame.draw.circle(self.window_surface, Color.gray, login.Location['circle4'],login.CHARACTERS_SIZE['circle4'])

    def update_json(self, new_json):
        self.new_json = new_json
        self.update_signal = True
        if self.numeric_keys is None and self.sorted_json is None:
            temp_key = sorted([key for key in new_json.keys() if key.isdigit()],
                              key=lambda x: (int(x) - int(self.id)) % len(new_json))
            self.numeric_keys = temp_key
            self.sorted_json = {key: new_json[key] for key in self.numeric_keys if key in new_json}
        else:
            temp_key = sorted([key for key in new_json.keys() if key.isdigit()],
                              key=lambda x: (int(x) - int(self.id)) % len(new_json))
            self.numeric_keys = self.allocation.update_users(temp_key)
            self.sorted_json = {key: new_json[key] for key in self.numeric_keys if key in new_json}

            # 确保 self.sorted_json 中的键与 self.numeric_keys 中的键一一对应
            for numeric_key in self.numeric_keys:
                if numeric_key in new_json and new_json[numeric_key] is not None:
                    self.sorted_json[numeric_key] = new_json[numeric_key]
                else:
                    self.sorted_json[numeric_key] = {}
        # print('numeric_keys',self.numeric_keys)
        # print('sorted_json',self.sorted_json)
        self.update_json_finish = True

        # self.add_single_spirit()
        # self.add_button()

    def add_single_spirit(self):
        # if pygame.display.get_init() and self.update_json_finish: # 检查 Pygame 是否仍然初始化,如果 Pygame 初始化，则继续绘图操作
        if pygame.display.get_init():
            self.window_surface.blit(self.bk_img, (0, 0))
            if self.numeric_keys and self.sorted_json is not None:
                for i in range(len(self.numeric_keys)):
                    if self.numeric_keys[i] != '':
                        self.order = i
                        # spirit = self.get_spirit()
                        #更新用户头像
                        spirit = get_spirit(self.sorted_json[self.numeric_keys[i]]["gender"],self.sorted_json[self.numeric_keys[i]]["nickname"])

                        my_img = pygame.image.load(all_spirit.Destination[spirit])
                        my_img = pygame.transform.scale(my_img, all_spirit.Characters_Size[spirit])
                        # my_img = pygame.transform.flip(my_img, True, False)
                        if True:
                            if 'game_process' in self.new_json and 'failure' in self.new_json[str(self.numeric_keys[i])]:
                                if self.new_json[str(self.numeric_keys[i])]['failure']:
                                    # 将图片转换为可编辑的格式，并保留透明度
                                    my_img = my_img.convert_alpha()
                                    for x in range(my_img.get_width()):
                                        for y in range(my_img.get_height()):
                                            # 计算灰度值
                                            pixel_color = my_img.get_at((x, y))
                                            if pixel_color.a == 0:
                                                continue  # 如果是透明的，则跳过此像素
                                            gray = (pixel_color.r + pixel_color.g + pixel_color.b) // 3
                                            # 设置像素为灰度值，保持原有的alpha值
                                            my_img.set_at((x, y), (gray, gray, gray, pixel_color.a))

                                    self.window_surface.blit(my_img, Player_Icon_Location.player_loca[self.order])
                                else:
                                    self.window_surface.blit(my_img, Player_Icon_Location.player_loca[self.order])
                            else:
                                self.window_surface.blit(my_img, Player_Icon_Location.player_loca[self.order])

                        #更新用户钱包标志
                        wallet = pygame.image.load(f"{wallet_spirit.Destination}")
                        wallet = pygame.transform.scale(wallet, wallet_spirit.CHARACTERS_SIZE[self.order])
                        self.window_surface.blit(wallet, Player_Icon_Location.wallet_loca[self.order])
                        #更新用户性别标志
                        player_gender = self.sorted_json[self.numeric_keys[i]]["gender"]
                        gender = pygame.image.load(f"{gender_spirit.Destination[player_gender]}")
                        gender = pygame.transform.scale(gender, gender_spirit.CHARACTERS_SIZE[self.order])
                        self.window_surface.blit(gender, Player_Icon_Location.gender_loca[self.order])
                        # 更新用户昵称
                        player_nickname = self.sorted_json[self.numeric_keys[i]]["nickname"]
                        show_font(self.window_surface,player_nickname,Player_Icon_Location.nickname_loca[self.order],self.font_location,font_spirit.CHARACTERS_SIZE[self.order])
                        # 更新用户钱包金额
                        player_money = self.sorted_json[self.numeric_keys[i]]["money"]
                        show_font(self.window_surface,str(player_money),Player_Icon_Location.money_loca[self.order],self.font_location,font_spirit.CHARACTERS_SIZE[self.order])
                        if 'bet_money' in self.sorted_json[self.numeric_keys[i]]:
                            show_font(self.window_surface, '押注', Player_Icon_Location.bet_money_loca[self.order], font_spirit.Destination['ShangShouHanShuTi'],
                                      font_spirit.CHARACTERS_SIZE[self.order])
                            bet_money = self.sorted_json[self.numeric_keys[i]]['bet_money']
                            show_font(self.window_surface, str(bet_money), Player_Icon_Location.bet_loca[self.order],
                                      font_spirit.Destination['ShangShouHanShuTi'],
                                      font_spirit.CHARACTERS_SIZE[self.order])
                        if True:
                            if 'game_process' in self.new_json and self.new_json['game_process'] == 'ending':
                                if 'cards' in self.sorted_json[self.numeric_keys[i]]:
                                    cards = self.sorted_json[self.numeric_keys[i]]['cards']
                                    type = self.sorted_json[self.numeric_keys[i]]['cards_type']
                                    if self.numeric_keys[i] == self.id:
                                        buffer = 0
                                        show_font(self.window_surface, card_type_arr[type],
                                                  (770, 590), self.font_location,
                                                  35, Color.red)
                                        for card in cards:
                                            card_string = f"{card['suit']}{card['value']}"
                                            single_card = pygame.image.load(f"{self.card_deck.Destination[card_string]}")
                                            single_card = pygame.transform.scale(single_card,
                                                                                 self.card_deck.CHARACTERS_SIZE)
                                            self.window_surface.blit(single_card,
                                                                     Player_Icon_Location.card_loca[self.order][buffer])
                                            buffer += 1
                                    else:
                                        buffer = 0
                                        for card in cards:
                                            card_string = f"{card['suit']}{card['value']}"
                                            single_card = pygame.image.load(f"{self.card_deck.Destination[card_string]}")
                                            single_card = pygame.transform.scale(single_card,
                                                                                 self.card_deck.Smaller_Size)
                                            self.window_surface.blit(single_card,
                                                                     Player_Icon_Location.card_loca[self.order][buffer])
                                            buffer += 1

                            else:
                                if 'cards' in self.sorted_json[self.numeric_keys[i]]:
                                    if self.numeric_keys[i] == self.id:
                                        cards = self.sorted_json[self.numeric_keys[i]]['cards']
                                        type = self.sorted_json[self.numeric_keys[i]]['cards_type']
                                        buffer = 0
                                        show_font(self.window_surface, card_type_arr[type],
                                                  (770,590), self.font_location,
                                                  35,Color.red)
                                        for card in cards:
                                            card_string = f"{card['suit']}{card['value']}"
                                            single_card = pygame.image.load(f"{self.card_deck.Destination[card_string]}")
                                            single_card = pygame.transform.scale(single_card, self.card_deck.CHARACTERS_SIZE)
                                            self.window_surface.blit(single_card, Player_Icon_Location.card_loca[self.order][buffer])
                                            buffer += 1
                                    else:
                                        for j in range(3):
                                            back_card = pygame.image.load(f"{self.card_deck.Destination['Back']}")
                                            back_card = pygame.transform.scale(back_card, self.card_deck.Smaller_Size)
                                            self.window_surface.blit(back_card,
                                                                     Player_Icon_Location.card_loca[self.order][j])

            else:
                print("键值列表为空，存在问题")

    def gaming(self):
        arr_icon = ['inform_frame']
        public_gaming_pic(arr_icon, self.window_surface)
        show_font_list(self.window_surface,(940,620),1060,self.inform_list)
        if self.new_json["game_process"] == "battle":
            if self.new_json["battle_win"]:
                show_font(self.window_surface, '挑战成功', (400,400), font_spirit.Destination['HeiTi'],45,Color.red)
            else:
                show_font(self.window_surface, '挑战失败', (400, 400), font_spirit.Destination['HeiTi'], 45, Color.red)
        elif self.new_json["game_process"] == "ending":
            if self.new_json["final_winner"] == int(self.id):
                show_font(self.window_surface, '恭喜你，获胜啦', (400, 400), font_spirit.Destination['HeiTi'], 45, Color.red)
            else:
                show_font(self.window_surface, '游戏结束，等待结算', (400, 400), font_spirit.Destination['HeiTi'], 45,
                          Color.red)
            self.inform_list = []

    def add_button(self):
        if self.new_json["game_process"] == "preparing":
            if self.new_json[self.id]["preparing"] == False:
                button_ready = pygame.image.load(f"{button_spirit.Destination['ready']}")
                self.window_surface.blit(button_ready, button_spirit.Location['ready'])
            else:
                button_cancel_ready = pygame.image.load(f"{button_spirit.Destination['cancel_ready']}")
                self.window_surface.blit(button_cancel_ready, button_spirit.Location['cancel_ready'])
            if self.numeric_keys and self.sorted_json is not None:
                for i in range(len(self.numeric_keys)):
                    if self.numeric_keys[i] != '' and self.numeric_keys[i] != self.id:
                        self.order = i
                        if self.sorted_json[self.numeric_keys[i]]["preparing"]:
                            # text = self.font.render('已准备', True, (255, 255, 255))  # 白色文本
                            # self.window_surface.blit(text, Player_Icon_Location.ready_loca[self.order])
                            have_ready = pygame.image.load(f"{have_ready_icon_spirit.Destination}")
                            have_ready = pygame.transform.scale(have_ready, gender_spirit.CHARACTERS_SIZE[self.order])
                            self.window_surface.blit(have_ready, Player_Icon_Location.have_ready_icon_loca[self.order])
                        else:
                            show_font(self.window_surface, '等待准备', Player_Icon_Location.ready_loca[self.order],
                                      font_spirit.Destination['ShangShouHanShuTi'], 25)
                            pass
            quit_button = pygame.image.load(f"{button_spirit.Destination['quit_button']}")
            quit_button = pygame.transform.scale(quit_button, button_spirit.Characters_Size['quit_button'])
            self.window_surface.blit(quit_button, button_spirit.Location['quit_button_regis'])

        elif self.new_json["game_process"] == "requesting":
            if str(self.new_json["whose_turn"]) == self.id:
                if not self.target_need_choose:
                    choice_button_pic(self.new_json["rest_option"],self.window_surface)
                else:
                    show_font(self.window_surface, '请点击头像，选择看牌对象', (350,400), font_spirit.Destination['HeiTi'],45,Color.red)
        elif self.new_json["game_process"] == "inform":
            if self.update_signal:
                inform_choice(self.new_json,self.inform_list)
                self.update_signal = False

    def refresh_page(self):
        pygame.display.flip()
        clock.tick(60)  # 通过设置帧率来控制循环速度


# gaming_json =  {'game_process': 'requesting',
# '0': {'nickname': 'kipley', 'gender': 'female', 'preparing': True, 'money': 497, 'bet_money': 3,'cards_type':0, 'cards': [{'suit': '方块', 'value': 8}, {'suit': '方块', 'value': 4}, {'suit': '梅花', 'value': 2}], 'failure': False, 'cards_value': 0},
# '1': {'nickname': 'jsl', 'gender': 'male', 'preparing': True, 'money': 494, 'bet_money': 6,'cards_type':0, 'cards': [{'suit': '方块', 'value': 5}, {'suit': '红心', 'value': 11}, {'suit': '方块', 'value': 7}], 'failure': False, 'cards_value': 0},
# '2': {'nickname': 'lc', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1,'cards_type':1 ,'cards': [{'suit': '梅花', 'value': 7}, {'suit': '方块', 'value': 7}, {'suit': '红心', 'value': 9}], 'failure': True, 'cards_value': 0},
# 'property': 'table', 'all_bets': 3, 'whose_turn': 0, 'rest_option': 1, 'user_ids_list': [0, 1, -1], 'option': 6, 'target': -1}

# gaming_json = {'game_process': 'requesting',
#  '0': {'nickname': 'kipley', 'gender': 'female', 'preparing': True, 'money': 495, 'bet_money': 5, 'cards_type':0,'cards': [{'suit': '黑桃', 'value': 13}, {'suit': '黑桃', 'value': 4}, {'suit': '方块', 'value': 5}], 'failure': False, 'cards_value': 0},
#  '1': {'nickname': 'lc', 'gender': 'male', 'preparing': True, 'money': 495, 'bet_money': 5, 'cards_type':0,'cards': [{'suit': '梅花', 'value': 7}, {'suit': '梅花', 'value': 14}, {'suit': '红心', 'value': 6}], 'failure': False, 'cards_value': 0},
#  '2': {'nickname': 'tjl', 'gender': 'male', 'preparing': True, 'money': 495, 'bet_money': 5, 'cards_type':0,'cards': [{'suit': '红心', 'value': 14}, {'suit': '红心', 'value': 2}, {'suit': '方块', 'value': 8}], 'failure': False, 'cards_value': 0},
#  'property': 'table', 'all_bets': 15, 'whose_turn': 1, 'rest_option': 0, 'user_ids_list': [0, 1, 2], 'option': 0, 'target': -1}
#

def main():
    gaming_json = {'game_process': 'inform',
                   '0': {'nickname': 'lc', 'gender': 'male', 'preparing': True, 'money': 475, 'bet_money': 25, 'cards': [{'suit': '红心', 'value': 2}, {'suit': '黑桃', 'value': 11}, {'suit': '红心', 'value': 7}], 'failure': True, 'cards_value': 57843, 'cards_type': 0},
                   '1': {'nickname': 'jsl', 'gender': 'male', 'preparing': True, 'money': 475, 'bet_money': 25, 'cards': [{'suit': '方块', 'value': 3}, {'suit': '红心', 'value': 9}, {'suit': '黑桃', 'value': 12}], 'failure': False, 'cards_value': 63663, 'cards_type': 0},
                   '2': {'nickname': 'kipley', 'gender': 'female', 'preparing': True, 'money': 445, 'bet_money': 55, 'cards': [{'suit': '黑桃', 'value': 13}, {'suit': '方块', 'value': 7}, {'suit': '方块', 'value': 4}], 'failure': False, 'cards_value': 67883, 'cards_type': 0},
                   'all_bets': 105, 'whose_turn': '1', 'rest_option': 2, 'user_ids_list': [-1, '1', '2'], 'option': 5, 'target': 2}
    draw_pic = Draw_Pic()

    draw_pic.get_id('1')
    # # button_click_thread = threading.Thread(target=draw_pic.key_handle.check_button_click(event))
    # # button_click_thread.start()
    running = True  # 设置一个运行标志
    draw_pic.update_json(gaming_json)
    while running:
        # if draw_pic.key_handle.state['log_in'] == True:
        #     draw_pic.login()
        #     draw_pic.key_handle.input_box_show()
        #     draw_pic.refresh_page()
        # elif draw_pic.key_handle.state['register'] == True:
        #     draw_pic.register()
        #     draw_pic.refresh_page()


        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_q:  # 检查是否按下了 'q' 键
                    running = False

            # draw_pic.refresh_page()


        draw_pic.add_single_spirit()
        draw_pic.gaming()
        draw_pic.add_button()
        draw_pic.refresh_page()


    pygame.quit()
    sys.exit()


# if __name__== "__main__" :
#     main()

# 押注：
# {'game_process': 'inform',
#  '0': {'username': 'ldh', 'gender': 'female', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '黑桃', 'value': 13}, {'suit': '黑桃', 'value': 4}, {'suit': '方块', 'value': 5}], 'failure': False, 'cards_value': 0},
#  '1': {'username': 'lc', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '梅花', 'value': 7}, {'suit': '梅花', 'value': 14}, {'suit': '红心', 'value': 6}], 'failure': False, 'cards_value': 0},
#  '2': {'username': 'tjl', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '红心', 'value': 14}, {'suit': '红心', 'value': 2}, {'suit': '方块', 'value': 8}], 'failure': False, 'cards_value': 0},
#  'property': 'table', 'all_bets': 3, 'whose_turn': 1, 'rest_option': 0, 'user_ids_list': [0, 1, 2], 'option': 0, 'target': -1}

# 询问：
# {'game_process': 'requesting',
#  '0': {'username': 'ldh', 'gender': 'female', 'preparing': True, 'money': 497, 'bet_money': 3, 'cards': [{'suit': '黑桃', 'value': 13}, {'suit': '黑桃', 'value': 4}, {'suit': '方块', 'value': 5}], 'failure': False, 'cards_value': 0},
#  '1': {'username': 'lc', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '梅花', 'value': 7}, {'suit': '梅花', 'value': 14}, {'suit': '红心', 'value': 6}], 'failure': True, 'cards_value': 0},
#  '2': {'username': 'tjl', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '红心', 'value': 14}, {'suit': '红心', 'value': 2}, {'suit': '方块', 'value': 8}], 'failure': False, 'cards_value': 0},
#  'property': 'table', 'all_bets': 3, 'whose_turn': 2, 'rest_option': 0, 'user_ids_list': [0, -1, 2], 'option': 6, 'target': -1}

# 弃牌：
# {'game_process': 'inform',
#  '0': {'username': 'ldh', 'gender': 'female', 'preparing': True, 'money': 497, 'bet_money': 3, 'cards': [{'suit': '黑桃', 'value': 13}, {'suit': '黑桃', 'value': 4}, {'suit': '方块', 'value': 5}], 'failure': False, 'cards_value': 0},
#  '1': {'username': 'lc', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '梅花', 'value': 7}, {'suit': '梅花', 'value': 14}, {'suit': '红心', 'value': 6}], 'failure': True, 'cards_value': 0},
#  '2': {'username': 'tjl', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '红心', 'value': 14}, {'suit': '红心', 'value': 2}, {'suit': '方块', 'value': 8}], 'failure': False, 'cards_value': 0},
#  'property': 'table', 'all_bets': 3, 'whose_turn': 2, 'rest_option': 0, 'user_ids_list': [0, -1, 2], 'option': 7, 'target': 0}

# 看牌：
# 发送数据包：{'option': 7, 'target': 0}
# 其他用户接收到的inform数据包：
# {'game_process': 'inform',
#  '0': {'username': 'ldh', 'gender': 'female', 'preparing': True, 'money': 497, 'bet_money': 3, 'cards': [{'suit': '黑桃', 'value': 13}, {'suit': '黑桃', 'value': 4}, {'suit': '方块', 'value': 5}], 'failure': False, 'cards_value': 0},
#  '1': {'username': 'lc', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '梅花', 'value': 7}, {'suit': '梅花', 'value': 14}, {'suit': '红心', 'value': 6}], 'failure': True, 'cards_value': 0},
#  '2': {'username': 'tjl', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '红心', 'value': 14}, {'suit': '红心', 'value': 2}, {'suit': '方块', 'value': 8}], 'failure': False, 'cards_value': 0},
#  'property': 'table', 'all_bets': 3, 'whose_turn': 2, 'rest_option': 0, 'user_ids_list': [0, -1, 2], 'option': 7, 'target': 0}

# 看牌大小提示：
# {'game_process': 'battle',
#  '0': {'username': 'ldh', 'gender': 'female', 'preparing': True, 'money': 497, 'bet_money': 3, 'cards': [{'suit': '黑桃', 'value': 13}, {'suit': '黑桃', 'value': 4}, {'suit': '方块', 'value': 5}], 'failure': False, 'cards_value': 0},
#  '1': {'username': 'lc', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '梅花', 'value': 7}, {'suit': '梅花', 'value': 14}, {'suit': '红心', 'value': 6}], 'failure': True, 'cards_value': 0},
#  '2': {'username': 'tjl', 'gender': 'male', 'preparing': True, 'money': 497, 'bet_money': 3, 'cards': [{'suit': '红心', 'value': 14}, {'suit': '红心', 'value': 2}, {'suit': '方块', 'value': 8}], 'failure': False, 'cards_value': 0},
#  'property': 'table', 'all_bets': 3, 'whose_turn': 2, 'rest_option': 0, 'user_ids_list': [0, -1, -1], 'option': 7, 'target': 0, 'battle_win': False}
