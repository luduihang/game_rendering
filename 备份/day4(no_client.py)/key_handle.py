import sys
import pygame
import time
import threading
from const import *
from draw import Draw_Pic
from algorithm import *

pygame.init()
clock = pygame.time.Clock()  # 创建一个Clock对象来帮助跟踪时间
FPS = 60  # 设置期望的帧率

class MouseClickHandler:
    def __init__(self):
        self.draw_pic = Draw_Pic('1')
        self.screen = self.draw_pic.window_surface
        self.running = True  # 设置一个运行标志

        self.format_mismatch = False
        self.timer_working = False

        self.pressed_buttons = set()  # 用于存储被按下的按钮
        self.button_pressed_signal = {}

        self.cursor = pygame.Surface((2, 30))
        self.cursor.fill(Color.black)
        self.last_time = 0
        self.input_box = Mouce.input_box
        self.register_box =Mouce.register_box

        self.state = {
            "log_in": True,
            "register": False,
            "preparing": False,
            "gaming": False,
            "game_over": False,
            "quit": False,
        }

        self.register_json = {
            "username":"",
            "password":"",
            "nickname":"",
            "gender":"",
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
                    print("log_in button pressed!!!")
                if button_name == 'register':
                    self.state['log_in'] = False
                    self.state['register'] = True
                    print("register button pressed!!!")
                self.button_pressed_signal[button_name] = True
                print(self.state)
    def login_input_box_pressed(self,event):
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

    def register_button_pressed_style(self,event):
        for button_name, region in Mouce.button_register.items():
            if region.collidepoint(event.pos):
                if button_name == 'quit_button_regis':
                    print("quit_button_regis pressed!!!")
                    self.state['register'] = False
                    self.state['quit'] = True
                if button_name == 'submit':
                    self.register_json['username'] = self.register_box['username']['text']
                    self.register_json['password'] = self.register_box['password']['text']
                    self.register_json['nickname'] = self.register_box['nickname']['text']
                    for items in self.register_json.values():
                        if items == '':
                            self.format_mismatch = True
                    if not self.format_mismatch:
                        #此处向服务器发送数据包
                        pass
                    print("submit button pressed!!!")
                if button_name == 'return':
                    self.state['log_in'] = True
                    self.state['register'] = False
                    for box in self.register_box.values():
                        box['text'] = ""
                        box['cursor_position'] = 0
                    print("return button pressed!!!")
                if button_name == 'male_choice':
                    self.register_json['gender'] = 'male'
                    print('male_choice button pressed!!!')
                if button_name == 'female_choice':
                    self.register_json['gender'] = 'female'
                    print('female_choice button pressed!!!')
                self.button_pressed_signal[button_name] = True
                print(self.state)

    def register_input_box_pressed(self,event):
        for box in self.register_box.values():
            if box['rect'].collidepoint(event.pos):
                box['active'] = True
                box['cursor_visible'] = True
            else:
                box['active'] = False
                box['cursor_visible'] = False
    def register_box_text(self,event):
        if event.key == pygame.K_RETURN:
            active_box_key = None
            for box_key, box in self.register_box.items():
                if box['active']:
                    active_box_key = box_key
                    break
            if active_box_key == 'username':
                self.register_box['password']['active'] = True
                self.register_box['username']['active'] = False
                self.register_box['nickname']['active'] = False
            elif active_box_key == 'password':
                self.register_box['nickname']['active'] = True
                self.register_box['username']['active'] = False
                self.register_box['password']['active'] = False
            elif active_box_key == 'nickname':
                self.register_box['nickname']['active'] = False
                self.register_box['username']['active'] = True
                self.register_box['password']['active'] = False
        for box_key, box_value in self.register_box.items():
            if box_value['active']:
                if event.key == pygame.K_BACKSPACE:
                    box_value['text'] = box_value['text'][:-1]
                    if box_value['cursor_position'] > 0:
                        box_value['cursor_position'] -= 1
                else:
                    if event.unicode.isalnum():  # 检查是否为字母数字字符
                        box_value['text'] += event.unicode
                        box_value['cursor_position'] += 1
    def register_box_show(self):
        for box in self.register_box.values():
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
            for box in self.register_box.values():
                box['cursor_visible'] = not box['cursor_visible']
            self.last_time = time.time()
        if self.register_json['gender']:
            if self.register_json['gender'] == 'male':
                pygame.draw.circle(self.screen, Color.black, login.Location['circle3'],
                                   login.CHARACTERS_SIZE['circle3'])
            elif self.register_json['gender'] == 'female':
                pygame.draw.circle(self.screen, Color.black, login.Location['circle4'],
                                   login.CHARACTERS_SIZE['circle4'])
        if 'submit' in self.button_pressed_signal:
            if self.button_pressed_signal['submit']:
                if self.format_mismatch:
                    show_font(self.screen, '请确保信息输入完整', (520, 530), font_spirit.Destination['HeiTi'], 25, Color.red)
                    if not self.timer_working:
                        timer = threading.Timer(5, self.format_mixmatch_callback)
                        timer.start()
                        self.timer_working = True

    def format_mixmatch_callback(self):
        self.format_mismatch = False
        self.timer_working = False

    def check_button_click(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:  # 检查是否按下了 'q' 键
                    self.running = False
                if self.state:
                    if self.state["log_in"] == True:
                        self.input_box_text(event)
                    if self.state["register"] == True:
                        self.register_box_text(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state["log_in"] == True:
                    self.login_button_pressed_style(event)
                    self.login_input_box_pressed(event)
                if self.state["register"] == True:
                    self.register_button_pressed_style(event)
                    self.register_input_box_pressed(event)

            if event.type == pygame.MOUSEBUTTONUP:
                for button_name, region in Mouce.button_region.items():
                    # 此处写入发送到服务端的json数据包代码
                    # print("button reset")
                    self.button_pressed_signal[button_name] = False

json = {'game_process': 'preparing', 'ready_clients': 1,
'0': {'nickname': 'lc', 'gender': 'male', 'preparing': True, 'money': 500, 'bet_money': 0},
'1': {'nickname': 'ldh', 'gender': 'female', 'preparing': False, 'money': 500, 'bet_money': 0},
'2': {'nickname': 'jsl', 'gender': 'male', 'preparing': True, 'money': 500, 'bet_money': 0}}

new_json = {'game_process': 'preparing', 'ready_clients': 1,
'0': {'nickname': 'lc', 'gender': 'male', 'preparing': False, 'money': 500, 'bet_money': 0},
'1': {'nickname': 'ldh', 'gender': 'female', 'preparing': False, 'money': 500, 'bet_money': 0}}


mouse_handle = MouseClickHandler()
while mouse_handle.running:
    mouse_handle.check_button_click()
    if mouse_handle.state['log_in'] == True:
        mouse_handle.draw_pic.login()
        mouse_handle.input_box_show()
        mouse_handle.draw_pic.refresh_page()
    elif mouse_handle.state['register'] == True:
        mouse_handle.draw_pic.register()
        mouse_handle.register_box_show()
        mouse_handle.draw_pic.refresh_page()


    # mouse_handle.draw_pic.update_json(new_json)
    # mouse_handle.draw_pic.refresh_page()
    # print("1")
    # time.sleep(1)
    # mouse_handle.draw_pic.update_json(json)
    # mouse_handle.draw_pic.refresh_page()
    # time.sleep(1)

pygame.quit()
sys.exit()

