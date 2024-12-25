import sys
import pygame
import time
import threading
import json
from const import *
from draw import Draw_Pic
from algorithm import *

pygame.init()
clock = pygame.time.Clock()  # 创建一个Clock对象来帮助跟踪时间
FPS = 60  # 设置期望的帧率

class MouseClickHandler:
    def __init__(self,client_socket):
        self.draw_pic = Draw_Pic()
        self.screen = self.draw_pic.window_surface
        self.client_socket = client_socket

        self.running = True  # 设置一个运行标志

        self.login_fail_wrong = False
        self.login_fail_lock = False
        self.format_mismatch = False
        self.folder_exist = False
        self.folder_set = False
        self.timer_working = False

        self.pressed_buttons = set()  # 用于存储被按下的按钮
        self.button_pressed_signal = {}

        self.cursor = pygame.Surface((2, 30))
        self.cursor.fill(Color.black)
        self.last_time = 0
        self.input_box = Mouce.input_box
        self.register_box =Mouce.register_box

        self.key_lock = threading.Lock()
        self.state = {
            "log_in": True,
            "register": False,
            "preparing": False,
            "gaming": False,
            "game_over": False,
            "quit": False,
        }
        self.state_lock = threading.Lock()  #标志位变化作为一个在整体运行，不需要一前一后，以免多线程不稳定
        self.login_json = {
            "action": "login",
            "username":"",
            "password":"",
        }
        self.register_json = {
            "action": "register",
            "username":"",
            "password":"",
            "nickname":"",
            "gender":"",
        }
        self.preparing_json = {
            "action": "prepare",
            "state": False,

        }

        self.gaming_choice_json = {
            "option": -1,
            "target": -1,
        }
        # self.font = pygame.font.Font(font_spirit.Destination['ShangShouHanShuTi'], 30)
        self.font = pygame.font.SysFont('monospace', 30)

        self.mouse_quit_signal = False
        self.mouse_quit_event = threading.Event()
        self.mouse_quit_lock = threading.Lock()

        self.key_json = None

    def update_state(self, key):
        with self.state_lock:
            for k in self.state:
                self.state[k] = False
                # 将提供的键对应的值设置为 True
            if key in self.state:
                self.state[key] = True
            else:
                raise ValueError(f"Key '{key}' not found in state dictionary.")

    def login_button_pressed_style(self,event):
        for button_name, region in Mouce.button_region.items():
            if region.collidepoint(event.pos):
                if button_name == 'quit_button':
                    print("quit_button pressed!!!")
                    self.update_state('quit')
                if button_name == 'log_in':
                    print("log_in button pressed!!!")
                    self.login_json["username"] = self.input_box['username']['text']
                    self.login_json["password"] = self.input_box['password']['text']
                    for key, items in self.login_json.items():
                        if items != 'login':
                            if items == '':
                                self.format_mismatch = True
                    if not self.format_mismatch:
                        self.client_socket.send(json.dumps(self.login_json).encode())
                        print("发送json数据包:",self.login_json)

                if button_name == 'register':
                    self.update_state('register')
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
        if self.login_fail_wrong:
            show_font(self.screen, '账号密码错误', (520, 530), font_spirit.Destination['HeiTi'], 25, Color.red)
            if not self.timer_working:
                timer = threading.Timer(1, self.login_fail_wrong_callback)
                timer.start()
                self.timer_working = True
        if self.login_fail_lock:
            show_font(self.screen, '此账号已被登录', (520, 530), font_spirit.Destination['HeiTi'], 25, Color.red)
            if not self.timer_working:
                timer = threading.Timer(1, self.login_fail_lock_callback)
                timer.start()
                self.timer_working = True

    def login_fail_wrong_callback(self):
        self.login_fail_wrong = False
        self.timer_working = False
    def login_fail_lock_callback(self):
        self.login_fail_lock = False
        self.timer_working = False

    def register_button_pressed_style(self,event):
        for button_name, region in Mouce.button_register.items():
            if region.collidepoint(event.pos):
                if button_name == 'quit_button_regis':
                    print("quit_button_regis pressed!!!")
                    self.update_state('quit')
                if button_name == 'submit':
                    self.register_json['username'] = self.register_box['username']['text']
                    self.register_json['password'] = self.register_box['password']['text']
                    self.register_json['nickname'] = self.register_box['nickname']['text']
                    for items in self.register_json.values():
                        if items != 'login':
                            if items == '':
                                self.format_mismatch = True
                    if not self.format_mismatch:
                        self.client_socket.send(json.dumps(self.register_json).encode())
                        print("发送json数据包:", self.register_json)
                    print("register submit button pressed!!!")
                if button_name == 'return':
                    self.update_state('log_in')
                    self.format_mismatch = False
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
                        timer = threading.Timer(1, self.format_mixmatch_callback)
                        timer.start()
                        self.timer_working = True
        if self.format_mismatch:
            show_font(self.screen, '请确保信息输入完整', (520, 530), font_spirit.Destination['HeiTi'], 25, Color.red)
            if not self.timer_working:
                timer = threading.Timer(1, self.format_mixmatch_callback)
                timer.start()
                self.timer_working = True
        if self.folder_exist:
            show_font(self.screen, '存档已经存在', (520, 530), font_spirit.Destination['HeiTi'], 25, Color.red)
            if not self.timer_working:
                timer = threading.Timer(1, self.folder_exist_callback)
                timer.start()
                self.timer_working = True
        if self.folder_set:
            show_font(self.screen, '存档建立成功', (520, 530), font_spirit.Destination['HeiTi'], 25, Color.green)
            if not self.timer_working:
                timer = threading.Timer(1, self.folder_set_callback)
                timer.start()
                self.timer_working = True

    def format_mixmatch_callback(self):
        self.format_mismatch = False
        self.timer_working = False
    def folder_exist_callback(self):
        self.folder_exist = False
        self.timer_working = False
    def folder_set_callback(self):
        self.folder_set = False
        self.timer_working = False

    def preparing_button_pressed_style(self, event):
        action_once = True
        for button_name, region in Mouce.button_preparing.items():
            if region.collidepoint(event.pos):
                if button_name is 'ready' or 'cancel_ready':
                    if self.preparing_json["state"] == False:
                        if button_name == 'ready':
                            if action_once:
                                self.preparing_json["state"] = True
                                self.client_socket.send(json.dumps(self.preparing_json).encode())
                                print("发送json数据包:", self.preparing_json)
                                action_once = False
                    else:
                        if button_name == 'cancel_ready':
                            if action_once:
                                self.preparing_json["state"] = False
                                self.client_socket.send(json.dumps(self.preparing_json).encode())
                                print("发送json数据包:", self.preparing_json)
                                action_once = False
                if button_name == 'quit_button_regis':
                    print("quit_button_regis pressed!!!")
                    self.update_state('quit')

    def gaming_button_pressed_style(self,event):
        action_once = True
        if not self.draw_pic.target_need_choose:
            for button_name, region in Mouce.button_choice.items():
                if region.collidepoint(event.pos):
                    button_index = list(Mouce.button_choice.keys()).index(button_name)
                    if 0 <= button_index <=3:
                        if self.draw_pic.new_json["rest_option"] <= button_index:
                            self.gaming_choice_json["option"] = button_index
                            if action_once:
                                self.client_socket.send(json.dumps(self.gaming_choice_json).encode())
                                action_once = False
                        else:
                            print("此选项已经不可选择")
                            action_once = False
                    elif button_index == 4:
                        self.gaming_choice_json["option"] = button_index
                        if action_once:
                            self.client_socket.send(json.dumps(self.gaming_choice_json).encode())
                            action_once = False
                    elif button_index == 5:
                        self.gaming_choice_json["option"] = 5
                        self.draw_pic.target_need_choose = True
                    print("检测到按下按钮", button_name)
        else:
            for button_name, region in Mouce.target_choice.items():
                if region.collidepoint(event.pos):
                    if button_name == 'left_player':
                        if self.draw_pic.sorted_json[self.draw_pic.numeric_keys[1]]["failure"] is True:
                            print("此玩家已经出局")
                        else:
                            self.gaming_choice_json["target"] = int(self.draw_pic.numeric_keys[1])
                            if action_once:
                                self.client_socket.send(json.dumps(self.gaming_choice_json).encode())
                                action_once = False
                                print("已经发送数据包", self.gaming_choice_json)
                            self.draw_pic.target_need_choose = False
                    elif button_name == 'right_player':
                        if self.draw_pic.sorted_json[self.draw_pic.numeric_keys[2]]["failure"] is True:
                            print("次玩家已经出局")
                        else:
                            self.gaming_choice_json["target"] = int(self.draw_pic.numeric_keys[2])
                            if action_once:
                                self.client_socket.send(json.dumps(self.gaming_choice_json).encode())
                                action_once = False
                                print("已经发送数据包",self.gaming_choice_json)
                            self.draw_pic.target_need_choose = False
                    print("检测到选择看牌对象", button_name)

    def check_button_click(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.update_state('quit')
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:  # 检查是否按下了 'q' 键
                    print()
                    self.update_state('quit')
                if self.state:
                    if self.state["log_in"] == True:
                        self.input_box_text(event)
                    if self.state["register"] == True:
                        self.register_box_text(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state["log_in"] == True:
                    self.login_button_pressed_style(event)
                    self.login_input_box_pressed(event)
                elif self.state["register"] == True:
                    self.register_button_pressed_style(event)
                    self.register_input_box_pressed(event)
                elif self.state["preparing"] == True:
                    self.preparing_button_pressed_style(event)
                elif self.state["gaming"] == True:
                    self.gaming_button_pressed_style(event)
            if event.type == pygame.MOUSEBUTTONUP:
                for button_name, region in Mouce.button_region.items():
                    # 此处写入发送到服务端的json数据包代码
                    # print("button reset")
                    # self.button_pressed_signal[button_name] = False
                    pass
    def run(self,event):
        while self.running:
            time.sleep(0.1)
            self.check_button_click()
            with self.mouse_quit_lock:
                if self.draw_pic.new_json_signal:
                    self.draw_pic.update_json(self.key_json)
                    self.draw_pic.new_json_signal = False
                if self.state['log_in'] == True:
                    self.draw_pic.login()
                    self.input_box_show()
                    self.draw_pic.refresh_page()
                elif self.state['register'] == True:
                    self.draw_pic.register()
                    self.register_box_show()
                    self.draw_pic.refresh_page()
                elif self.state["preparing"] == True:
                    if self.draw_pic.numeric_keys is not None:
                        self.draw_pic.add_single_spirit()
                        self.draw_pic.add_button()
                        self.draw_pic.refresh_page()
                elif self.state["gaming"] == True:
                    if self.draw_pic.numeric_keys is not None:
                        self.draw_pic.add_single_spirit()
                        self.draw_pic.gaming()
                        self.draw_pic.add_button()
                        self.draw_pic.refresh_page()
                elif self.state['quit'] == True:
                    event.set()
                    # self.running = False
            if self.mouse_quit_signal:
                self.mouse_quit_event.set()
                self.running = False
        print("游戏结束啦")
        pygame.quit()
        sys.exit()


