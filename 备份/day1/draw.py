import time
import pygame
import sys
from const import *
from pygame.locals import *


def get_spirit(gender,nickname):
    last_char = nickname[-1]  # 获取字符串的最后一个字符
    ascii_value = ord(last_char)  # 获取字符的ASCII值
    if gender == 'male':
        if ascii_value % 2 == 1:
            return fire_spirit
        else:
            return cat_spirit
    elif gender == 'female':
        if ascii_value % 2 == 1:
            return water_spirit
        else:
            return ice_spirit
    else:
        print("不符合格式的输入")
        return

pygame.init()
clock = pygame.time.Clock()  # 创建一个Clock对象来帮助跟踪时间
class Draw_Pic:
    def __init__(self):
        self.window_surface = pygame.display.set_mode((GAME_WIDTH_SIZE, GAME_HEIGHT_SIZE))
        self.bk_img = pygame.image.load(f"{Background}")
        self.bk_img = pygame.transform.scale(self.bk_img, (BACKGROUND_W, BACKGROUND_H))
        self.window_surface.blit(self.bk_img, (0, 0))
        self.font = pygame.font.Font(None, 36)  # 使用默认字体，字号为36

        self.json = None
        self.sorted_json = None
        self.numeric_keys = None
        self.bgm_dest = bgm_directory
        self.order = 2

    def update_json(self, json):
        self.json = json
        self.numeric_keys = sorted([key for key in self.json.keys() if key.isdigit()],
                              key=lambda x: (int(x) - int(my_id)) % len(self.json))
        self.sorted_json = {key: self.json[key] for key in self.numeric_keys}
        self.add_single_spirit()


    def add_single_spirit(self):
        if self.numeric_keys and self.sorted_json is not None:
            for i in range(len(self.numeric_keys)):
                self.order = i
                # spirit = self.get_spirit()
                #更新用户头像
                spirit = get_spirit(self.sorted_json[self.numeric_keys[i]]["gender"],self.sorted_json[self.numeric_keys[i]]["nickname"])
                my_img = pygame.image.load(f"{spirit.Destination}")
                my_img = pygame.transform.scale(my_img, (spirit.CHARACTERS_W, spirit.CHARACTERS_H))
                # my_img = pygame.transform.flip(my_img, True, False)
                self.window_surface.blit(my_img, Player_Icon_Location.player_loca[self.order])
                #更新用户钱包标志
                wallet = pygame.image.load(f"{wallet_spirit.Destination}")
                wallet = pygame.transform.scale(wallet, wallet_spirit.CHARACTERS_SIZE[self.order])
                self.window_surface.blit(wallet, Player_Icon_Location.wallet_loca[self.order])
                #更新用户性别标志
                player_gender = self.sorted_json[self.numeric_keys[i]]["gender"]
                gender = pygame.image.load(f"{gender_spirit.Destination[player_gender]}")
                my_img = pygame.transform.scale(gender, gender_spirit.CHARACTERS_SIZE[self.order])
                self.window_surface.blit(my_img, Player_Icon_Location.gender_loca[self.order])
                # 更新用户昵称
                self.font = pygame.font.Font(font_spirit.Destination['ShangShouHanShuTi'],font_spirit.CHARACTERS_SIZE[self.order])
                text = self.font.render('填入json字段数据', True, (255, 255, 255))  # 白色文本
                self.window_surface.blit(text, Player_Icon_Location.nickname_loca[self.order])  # 文本位置
                # 更新用户钱包金额
                text = self.font.render('500', True, (255, 255, 255))  # 白色文本
                self.window_surface.blit(text, Player_Icon_Location.money_loca[self.order])
        else:
            print("键值列表为空，存在问题")

    def refresh_page(self):
        pygame.display.update()
        clock.tick(FPS)  # 通过设置帧率来控制循环速度




my_id = '1'
json = {'game_process': 'preparing', 'ready_clients': 1,
'0': {'nickname': 'lc', 'gender': 'male', 'preparing': False, 'money': 500, 'bet_money': 0},
'1': {'nickname': 'ldh', 'gender': 'female', 'preparing': False, 'money': 500, 'bet_money': 0},
'2': {'nickname': 'jsl', 'gender': 'male', 'preparing': True, 'money': 500, 'bet_money': 0}}

FPS = 1  # 设置期望的帧率
draw_pic = Draw_Pic()
draw_pic.update_json(json)

running = True  # 设置一个运行标志
while running:
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        elif event.type == KEYDOWN:
            if event.key == K_q:  # 检查是否按下了 'q' 键
                running = False

    draw_pic.refresh_page()
    print("1")


pygame.quit()
sys.exit()