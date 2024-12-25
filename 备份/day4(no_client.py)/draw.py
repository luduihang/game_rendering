import time
import pygame
import sys
import threading
from const import *
from pygame.locals import *
from algorithm import *


clock = pygame.time.Clock()  # 创建一个Clock对象来帮助跟踪时间

class Draw_Pic:
    def __init__(self,id):
        self.window_surface = pygame.display.set_mode((GAME_WIDTH_SIZE, GAME_HEIGHT_SIZE))

        self.bk_img = pygame.image.load(f"{Background}")
        self.bk_img = pygame.transform.scale(self.bk_img, (BACKGROUND_W, BACKGROUND_H))
        self.login_bk_img = pygame.image.load(f"{Login_Background}")
        self.login_bk_img = pygame.transform.scale(self.login_bk_img, (BACKGROUND_W, BACKGROUND_H))
        # self.window_surface.blit(self.bk_img, (0, 0))
        self.font = pygame.font.Font(None, 36)  # 使用默认字体，字号为36

        self.json = None
        self.sorted_json = None
        self.numeric_keys = None
        self.bgm_dest = bgm_directory
        self.order = 2
        self.id = id  #这里id是字符串类型的
        self.allocation = UserAllocation('1')

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

        self.add_single_spirit()
        self.add_button()

    def add_single_spirit(self):

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
                    show_font(self.window_surface,player_nickname,Player_Icon_Location.nickname_loca[self.order],None,font_spirit.CHARACTERS_SIZE[self.order])
                    # 更新用户钱包金额
                    show_font(self.window_surface,'500',Player_Icon_Location.money_loca[self.order],None,font_spirit.CHARACTERS_SIZE[self.order])

        else:
            print("键值列表为空，存在问题")

    def add_button(self):
        if self.new_json["game_process"] == "preparing":
            if self.new_json[self.id]["preparing"]:
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
                            # text = self.font.render('等待准备', True, (255, 255, 255))  # 白色文本
                            # self.window_surface.blit(text, Player_Icon_Location.ready_loca[self.order])
                            pass

    def refresh_page(self):
        pygame.display.flip()
        clock.tick(FPS)  # 通过设置帧率来控制循环速度

# my_id = '1'
# json = {'game_process': 'preparing', 'ready_clients': 1,
# '0': {'nickname': 'lc', 'gender': 'male', 'preparing': True, 'money': 500, 'bet_money': 0},
# '1': {'nickname': 'ldh', 'gender': 'female', 'preparing': False, 'money': 500, 'bet_money': 0},
# '2': {'nickname': 'jsl', 'gender': 'male', 'preparing': True, 'money': 500, 'bet_money': 0}}
#
#
# new_json = {'game_process': 'preparing', 'ready_clients': 1,
# '0': {'nickname': 'lc', 'gender': 'male', 'preparing': False, 'money': 500, 'bet_money': 0},
# '1': {'nickname': 'ldh', 'gender': 'female', 'preparing': False, 'money': 500, 'bet_money': 0}}
#
FPS = 60  # 设置期望的帧率
# draw_pic = Draw_Pic(my_id)
# # button_click_thread = threading.Thread(target=draw_pic.key_handle.check_button_click(event))
# # button_click_thread.start()
# running = True  # 设置一个运行标志
# while running:
#     if draw_pic.key_handle.state['log_in'] == True:
#         draw_pic.login()
#         draw_pic.key_handle.input_box_show()
#         draw_pic.refresh_page()
#     elif draw_pic.key_handle.state['register'] == True:
#         draw_pic.register()
#         draw_pic.refresh_page()
#
#
#     for event in pygame.event.get():
#         if event.type == QUIT:
#             running = False
#         elif event.type == KEYDOWN:
#             if event.key == K_q:  # 检查是否按下了 'q' 键
#                 running = False
#
#         # draw_pic.refresh_page()
#
#
#
#     # draw_pic.update_json(new_json)
#     # draw_pic.refresh_page()
#     # print("1")
#     #
#     # time.sleep(1)
#     # draw_pic.update_json(json)
#     # draw_pic.refresh_page()
#     # time.sleep(1)
#
# pygame.quit()
# sys.exit()