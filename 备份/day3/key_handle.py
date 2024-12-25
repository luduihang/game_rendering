import pygame
import time
from const import *

pygame.init()
clock = pygame.time.Clock()  # 创建一个Clock对象来帮助跟踪时间

class MouseClickHandler:
    def __init__(self, screen):
        self.screen = screen
        self.pressed_buttons = set()  # 用于存储被按下的按钮
        self.button_pressed_signal = {}


        self.cursor = pygame.Surface((2, 30))
        self.cursor.fill(Color.black)
        self.last_time = 0
        self.input_box = Mouce.input_box

        self.state = {
            "log_in": True,
            "register": False,
            "preparing": False,
            "gaming": False,
            "game_over": False,
            "quit": False,
        }
        # self.font = pygame.font.Font(font_spirit.Destination['ShangShouHanShuTi'], 30)
        self.font = pygame.font.SysFont('monospace', 30)
    def login_button_pressed_style(self,event):
        for button_name, region in Mouce.button_region.items():
            if region.collidepoint(event.pos):
                if button_name == 'quit_button':
                    quit_button = pygame.image.load(f"{button_spirit.Destination['quit_button']}")
                    quit_button = pygame.transform.scale(quit_button, button_spirit.Characters_Size['quit_button'])
                    self.screen.blit(quit_button, button_spirit.Location['quit_button_press'])
                    print("quit_button pressed!!!")
                    self.state['log_in'] = False
                    self.state['quit'] = True
                if button_name == 'log_in':
                    log_in = pygame.image.load(f"{button_spirit.Destination['log_in']}")
                    log_in = pygame.transform.scale(log_in, button_spirit.Characters_Size['log_in'])
                    self.screen.blit(log_in, button_spirit.Location['log_in_press'])
                    print("log_in button pressed!!!")
                if button_name == 'register':
                    self.state['log_in'] = False
                    self.state['register'] = True
                    print("register button pressed!!!")
                self.button_pressed_signal[button_name] = True
                print(self.state)

    def input_box_pressed(self,event):
        for box in self.input_box.values():
            if box['rect'].collidepoint(event.pos):
                box['active'] = True
                box['cursor_visible'] = True
            else:
                box['active'] = False
                box['cursor_visible'] = False
    def input_box_text(self,event):
        if event.key == pygame.K_RETURN:
            active_box_key = None
            for box_key, box in self.input_box.items():
                if box['active']:
                    active_box_key = box_key
                    break
            if active_box_key == 'username':
                self.input_box['password']['active'] = True
                self.input_box['username']['active'] = False
            elif active_box_key == 'password':
                self.input_box['username']['active'] = True
                self.input_box['password']['active'] = False

        for box_key, box_value in self.input_box.items():
            if box_value['active']:
                if event.key == pygame.K_BACKSPACE:
                    box_value['text'] = box_value['text'][:-1]
                    if box_value['cursor_position'] > 0:
                        box_value['cursor_position'] -= 1

                else:
                    if event.unicode.isalnum():  # 检查是否为字母数字字符
                        box_value['text'] += event.unicode
                        box_value['cursor_position'] += 1
    def input_box_show(self):
        for box in self.input_box.values():
            surface = pygame.Surface(box['rect'].size, pygame.SRCALPHA)
            surface.set_alpha(220)
            pygame.draw.rect(surface, Color.white, surface.get_rect())
            if box['active']:
                self.screen.blit(surface, box['rect'].topleft)
                # 绘制文本
                text_surface = self.font.render(box['text'], True, Color.black)
                self.screen.blit(text_surface, (box['rect'].x + 5, box['rect'].y + 5))
                # 绘制光标
                if box['cursor_visible']:
                    self.screen.blit(self.cursor, (box['rect'].x + 5 + box['cursor_position'] * 18, box['rect'].y + 5))
                    # screen.blit(cursor, (box['rect'].x + 5 , box['rect'].y + 5))

            else:
                self.screen.blit(surface, box['rect'].topleft)
                # 绘制文本
                text_surface = self.font.render(box['text'], True, Color.black)
                self.screen.blit(text_surface, (box['rect'].x + 5, box['rect'].y + 5))

        if time.time() - self.last_time >= 0.6:
            for box in self.input_box.values():
                box['cursor_visible'] = not box['cursor_visible']
            self.last_time = time.time()

    def check_button_click(self,event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.state["log_in"]:
                self.login_button_pressed_style(event)
                self.input_box_pressed(event)
                print("111")
        if event.type == pygame.MOUSEBUTTONUP:
            for button_name in self.button_pressed_signal.keys():
                if self.button_pressed_signal[button_name]:
                    pass
                    # 此处写入发送到服务端的json数据包代码
                    # print("button reset")
                    # self.button_pressed_signal[button_name] = False
        if event.type == pygame.KEYDOWN:
            if self.state["log_in"]:
                self.input_box_text(event)
