import time
import pygame
import sys
import os
import threading
from const import *
from pygame.locals import *
from algorithm import *
from myserver.math.robot import all_option

# pygame.init()
clock = pygame.time.Clock()  # 创建一个Clock对象来帮助跟踪时间

class Draw_Pic:
    def __init__(self):
        self.music = BGMPlayer()

        self.window_surface = pygame.display.set_mode((GAME_WIDTH_SIZE, GAME_HEIGHT_SIZE))
        self.screen =  pygame.display.set_mode((GAME_WIDTH_SIZE, GAME_HEIGHT_SIZE))

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
        self.order = 2
        self.allocation = None
        self.card_deck = card_spirit()

        self.update_signal = False
        self.target_need_choose = False

        self.inform_list = []

        self.new_json = None

        self.new_json_signal = False

        self.time_left = '10'
        self.update_time_left = False

        self.help_signal = False

        self.angle = 0
        # UserAllocation('1')
    def get_id(self,id):
        self.id = id
        self.allocation = UserAllocation(id)
        print("页面渲染获取到id:",self.id)

    def login(self):
        self.screen.fill((0, 0, 0))
        self.window_surface.fill((0, 0, 0))
        self.window_surface.blit(self.login_bk_img, (0, 0))
        # pygame.draw.rect(self.window_surface, Color.gold, (312, 160, 630, 490), 0)
        if not self.help_signal:
            arr_icon = ['back','frame','logo','age','user','password']
            public_login_pic(arr_icon,self.window_surface)

            show_font(self.screen, '抵制不良游戏，拒绝盗版游戏。注意自我保护，谨防受骗上当。', (700,750), font_spirit.Destination['ShangShouHanShuTi'], 20)
            show_font(self.screen, '用户注册', button_spirit.Location['register'],font_spirit.Destination['ShangShouHanShuTi'], 30)
            show_font(self.screen, '账号', (370,290),font_spirit.Destination['ShangShouHanShuTi'], 25)
            show_font(self.screen, '密码', (370,380), font_spirit.Destination['ShangShouHanShuTi'], 25)
            show_font(self.screen, '帮助', (355,585), font_spirit.Destination['ShangShouHanShuTi'], 22)

            quit_button = pygame.image.load(f"{button_spirit.Destination['quit_button']}")
            quit_button = pygame.transform.scale(quit_button, button_spirit.Characters_Size['quit_button'])
            self.screen.blit(quit_button, button_spirit.Location['quit_button'])

            log_in = pygame.image.load(f"{button_spirit.Destination['log_in']}")
            log_in = pygame.transform.scale(log_in, button_spirit.Characters_Size['log_in'])
            self.screen.blit(log_in, button_spirit.Location['log_in'])

            help_button = pygame.image.load(f"{button_spirit.Destination['help']}")
            help_button = pygame.transform.scale(help_button, button_spirit.Characters_Size['help'])
            self.screen.blit(help_button, button_spirit.Location['help'])
            self.window_surface.blit(self.screen, (0, 0))
        else:
            arr_icon = ['help_frame','help_back']
            public_login_pic(arr_icon, self.screen)
            arr_icon = ['help_return']
            public_button_pic(arr_icon, self.screen)
            show_help_font(self.screen)
            self.window_surface.blit(self.screen, (0, 0))


    def register(self):
        self.screen.fill((0, 0, 0))
        self.window_surface.fill((0, 0, 0))
        self.window_surface.blit(self.login_bk_img, (0, 0))

        arr_icon = ['back', 'frame', 'age', 'user', 'password','male','female','nickname']
        public_login_pic(arr_icon, self.screen)

        quit_button = pygame.image.load(f"{button_spirit.Destination['quit_button']}")
        quit_button = pygame.transform.scale(quit_button, button_spirit.Characters_Size['quit_button'])
        self.screen.blit(quit_button, button_spirit.Location['quit_button_regis'])
        submit_button = pygame.image.load(f"{button_spirit.Destination['submit']}")
        submit_button = pygame.transform.scale(submit_button, button_spirit.Characters_Size['submit'])
        self.screen.blit(submit_button, button_spirit.Location['submit'])
        return_button = pygame.image.load(f"{button_spirit.Destination['return']}")
        return_button = pygame.transform.scale(return_button, button_spirit.Characters_Size['return'])
        self.screen.blit(return_button, button_spirit.Location['return'])

        show_font(self.screen, '用户注册', (550,200), font_spirit.Destination['ShangShouHanShuTi'],40)
        show_font(self.screen, '您的性别:', (350, 570), font_spirit.Destination['ShangShouHanShuTi'], 30)
        show_font(self.screen, '账号', (350, 290), font_spirit.Destination['ShangShouHanShuTi'], 30)
        show_font(self.screen, '密码', (350, 380), font_spirit.Destination['ShangShouHanShuTi'], 30)
        show_font(self.screen, '昵称', (350, 470), font_spirit.Destination['ShangShouHanShuTi'], 30)

        pygame.draw.circle(self.screen, Color.white, login.Location['circle1'], login.CHARACTERS_SIZE['circle1'])
        pygame.draw.circle(self.screen, Color.white, login.Location['circle2'], login.CHARACTERS_SIZE['circle2'])

        pygame.draw.circle(self.screen, Color.gray, login.Location['circle3'],login.CHARACTERS_SIZE['circle3'])
        pygame.draw.circle(self.screen, Color.gray, login.Location['circle4'],login.CHARACTERS_SIZE['circle4'])

        self.window_surface.blit(self.screen, (0, 0))

    def update_json(self,new_json):
        self.new_json = new_json
        self.update_signal = True
        if self.numeric_keys is None and self.sorted_json is None:
            temp_key = sorted([key for key in new_json.keys() if key.isdigit()],
                              key=lambda x: (int(x) - int(self.id)) % len(new_json))
            self.numeric_keys = temp_key
            self.numeric_keys = self.allocation.update_users(temp_key)
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

        self.json_update_signal = False

        self.wait_for_return = False

    def add_single_spirit(self):
        self.screen.fill((0, 0, 0))
        self.window_surface.fill((0, 0, 0))
        # if pygame.display.get_init() and self.update_json_finish: # 检查 Pygame 是否仍然初始化,如果 Pygame 初始化，则继续绘图操作
        if pygame.display.get_init():
            self.window_surface.blit(self.bk_img, (0, 0))
            # 此代码用于渲染旋转音符
            angle_step = 12  # 每次旋转的角度
            music_pic = pygame.image.load(f"{gaming.Destination['music_pic']}")
            music_pic = pygame.transform.scale(music_pic, gaming.CHARACTERS_SIZE['music_pic'])
            rotated_music_pic = pygame.transform.rotate(music_pic, self.angle)
            rotated_rect = rotated_music_pic.get_rect(center=gaming.Location['music_pic'])
            self.screen.blit(rotated_music_pic, rotated_rect)
            if not self.music.paused:
                self.angle += angle_step
                self.angle = self.angle % 360

            song_path = self.music.song_path
            filename = os.path.basename(song_path)
            show_font(self.screen,filename,(50,185),font_spirit.Destination['ShangShouHanShuTi'],25,Color.light_green)
            song_list = self.music.current_playlist
            filename = '歌单: ' + os.path.basename(song_list)
            show_font(self.screen,filename,(28,135),font_spirit.Destination['ShangShouHanShuTi'],25,Color.light_green)

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

                                    self.screen.blit(my_img, Player_Icon_Location.player_loca[self.order])
                                else:
                                    self.screen.blit(my_img, Player_Icon_Location.player_loca[self.order])
                            else:
                                self.screen.blit(my_img, Player_Icon_Location.player_loca[self.order])

                        #更新用户钱包标志
                        wallet = pygame.image.load(f"{wallet_spirit.Destination}")
                        wallet = pygame.transform.scale(wallet, wallet_spirit.CHARACTERS_SIZE[self.order])
                        self.screen.blit(wallet, Player_Icon_Location.wallet_loca[self.order])
                        #更新用户性别标志
                        player_gender = self.sorted_json[self.numeric_keys[i]]["gender"]
                        gender = pygame.image.load(f"{gender_spirit.Destination[player_gender]}")
                        gender = pygame.transform.scale(gender, gender_spirit.CHARACTERS_SIZE[self.order])
                        self.screen.blit(gender, Player_Icon_Location.gender_loca[self.order])
                        # 更新用户昵称
                        player_nickname = self.sorted_json[self.numeric_keys[i]]["nickname"]
                        show_font(self.screen,player_nickname,Player_Icon_Location.nickname_loca[self.order],self.font_location,font_spirit.CHARACTERS_SIZE[self.order])
                        # 更新用户钱包金额
                        player_money = self.sorted_json[self.numeric_keys[i]]["money"]
                        show_font(self.screen,str(player_money),Player_Icon_Location.money_loca[self.order],self.font_location,font_spirit.CHARACTERS_SIZE[self.order])
                        if 'bet_money' in self.sorted_json[self.numeric_keys[i]]:
                            show_font(self.screen, '押注', Player_Icon_Location.bet_money_loca[self.order], font_spirit.Destination['ShangShouHanShuTi'],
                                      font_spirit.CHARACTERS_SIZE[self.order])
                            bet_money = self.sorted_json[self.numeric_keys[i]]['bet_money']
                            show_font(self.screen, str(bet_money), Player_Icon_Location.bet_loca[self.order],
                                      font_spirit.Destination['ShangShouHanShuTi'],
                                      font_spirit.CHARACTERS_SIZE[self.order])
                        if True:
                            if 'game_process' in self.new_json and self.new_json['game_process'] == 'ending':
                                if 'cards' in self.sorted_json[self.numeric_keys[i]]:
                                    cards = self.sorted_json[self.numeric_keys[i]]['cards']
                                    type = self.sorted_json[self.numeric_keys[i]]['cards_type']
                                    if self.numeric_keys[i] == self.id:
                                        buffer = 0
                                        show_font(self.screen, card_type_arr[type],
                                                  (770, 590), self.font_location,
                                                  35, Color.red)
                                        for card in cards:
                                            card_string = f"{card['suit']}{card['value']}"
                                            single_card = pygame.image.load(f"{self.card_deck.Destination[card_string]}")
                                            single_card = pygame.transform.scale(single_card,
                                                                                 self.card_deck.CHARACTERS_SIZE)
                                            self.screen.blit(single_card,
                                                                     Player_Icon_Location.card_loca[self.order][buffer])
                                            buffer += 1
                                    else:
                                        buffer = 0
                                        for card in cards:
                                            card_string = f"{card['suit']}{card['value']}"
                                            single_card = pygame.image.load(f"{self.card_deck.Destination[card_string]}")
                                            single_card = pygame.transform.scale(single_card,
                                                                                 self.card_deck.Smaller_Size)
                                            self.screen.blit(single_card,
                                                                     Player_Icon_Location.card_loca[self.order][buffer])
                                            buffer += 1

                            else:
                                if 'cards' in self.sorted_json[self.numeric_keys[i]]:
                                    if self.numeric_keys[i] == self.id:
                                        cards = self.sorted_json[self.numeric_keys[i]]['cards']
                                        type = self.sorted_json[self.numeric_keys[i]]['cards_type']
                                        buffer = 0
                                        show_font(self.screen, card_type_arr[type],
                                                  (770,590), self.font_location,
                                                  35,Color.red)
                                        for card in cards:
                                            card_string = f"{card['suit']}{card['value']}"
                                            single_card = pygame.image.load(f"{self.card_deck.Destination[card_string]}")
                                            single_card = pygame.transform.scale(single_card, self.card_deck.CHARACTERS_SIZE)
                                            self.screen.blit(single_card, Player_Icon_Location.card_loca[self.order][buffer])
                                            buffer += 1
                                    else:
                                        for j in range(3):
                                            back_card = pygame.image.load(f"{self.card_deck.Destination['Back']}")
                                            back_card = pygame.transform.scale(back_card, self.card_deck.Smaller_Size)
                                            self.screen.blit(back_card,
                                                                     Player_Icon_Location.card_loca[self.order][j])

            else:
                print("键值列表为空，存在问题")
            self.window_surface.blit(self.screen, (0, 0))

    def gaming(self):

        rect_surface = pygame.Surface((245, 70))
        rect_surface.set_alpha(200)  # 设置Surface的透明度
        rect_surface.fill(Color.dark_yellow)  # 用颜色填充Surface
        self.screen.blit(rect_surface, (900, 20))

        arr_icon = ['inform_frame','all_bets']
        public_gaming_pic(arr_icon, self.screen)
        show_font_list(self.screen,(940,620),1060,self.inform_list)

        show_font(self.screen, '总押注:', (980, 35), font_spirit.Destination['ShangShouHanShuTi'], 32, Color.white)

        if "all_bets" in self.new_json:
            all_bets = self.new_json['all_bets']
            show_font(self.screen,str(all_bets),(1090,35), font_spirit.Destination['ShangShouHanShuTi'],32,Color.white)
        if self.new_json["game_process"] == "battle" or self.new_json["game_process"] == "inform":
            # 向此阶段玩家显示PK的图标
            if self.new_json["game_process"] == "battle":
                if self.new_json["whose_turn"] == self.id:
                    if self.new_json["battle_win"]:
                        arr_icon = ["challenge_success"]
                        public_gaming_pic(arr_icon, self.screen)
                    else:
                        arr_icon = ["challenge_failure"]
                        public_gaming_pic(arr_icon, self.screen)
            # 向其他玩家同步此阶段玩家的决策
            if self.new_json["whose_turn"] != self.id:
                inform_id = str(self.new_json["whose_turn"])
                order = self.numeric_keys.index(inform_id)
                string = ""
                if 0 <= self.new_json['option'] <= 3:
                    string = "下注" + select_option[self.new_json['option']]
                elif self.new_json['option'] == 4:
                    string = "弃牌"
                elif self.new_json['option'] == 5:
                    string = "看牌"
                show_font(self.screen, string, Player_Icon_Location.inform_choice[order],
                              font_spirit.Destination['ShangShouHanShuTi'], 48, Color.red)

        elif self.new_json["game_process"] == "requesting":
            if self.new_json["whose_turn"] != self.id:
                player_id_str = str(self.new_json["whose_turn"])
                player_string = "等待" + self.new_json[player_id_str]['nickname'] + "做出选择"
                font = pygame.font.Font(font_spirit.Destination['ShangShouHanShuTi'], 56)
                text_surface = font.render(player_string, True, Color.red)
                text_width, text_height = text_surface.get_size()
                loca = (600 - text_width/2 ,400)
                show_font(self.screen, player_string, loca, font_spirit.Destination['ShangShouHanShuTi'],
                          56, Color.red)

        elif self.new_json["game_process"] == "ending":
            arr_icon = ['inform_frame']
            public_gaming_pic(arr_icon, self.screen)
            show_font_list(self.screen, (940, 620), 1060, self.inform_list)
            if "final_winner" in self.new_json:
                if not self.wait_for_return:
                    if self.new_json["final_winner"] == int(self.id):
                        arr_icon = ["winner"]
                        public_gaming_pic(arr_icon, self.screen)
                    else:
                        arr_icon = ["game_over"]
                        public_gaming_pic(arr_icon, self.screen)
        self.window_surface.blit(self.screen, (0, 0))

    def add_button(self):
        rect_surface = pygame.Surface((245, 70))
        rect_surface.set_alpha(220)  # 设置Surface的透明度
        rect_surface.fill(Color.white)  # 用颜色填充Surface
        self.screen.blit(rect_surface, (20, 20))
        if self.music:
            if self.music.paused:
                arr_icon = ['stop_to_continue','return_play','next_music','shift_list']
                public_button_pic(arr_icon,self.screen)
            else:
                arr_icon = ['continue_to_stop', 'return_play', 'next_music', 'shift_list']
                public_button_pic(arr_icon, self.screen)

        if self.wait_for_return:
            pic_arr = ['return_preparing']
            public_button_pic(pic_arr, self.screen)

        if self.new_json["game_process"] == "preparing":
            if self.inform_list:
                self.inform_list = []
            if self.new_json[self.id]["preparing"] == False:
                button_ready = pygame.image.load(f"{button_spirit.Destination['ready']}")
                self.screen.blit(button_ready, button_spirit.Location['ready'])
            else:
                button_cancel_ready = pygame.image.load(f"{button_spirit.Destination['cancel_ready']}")
                self.screen.blit(button_cancel_ready, button_spirit.Location['cancel_ready'])
            if self.numeric_keys and self.sorted_json is not None:
                for i in range(len(self.numeric_keys)):
                    if self.numeric_keys[i] != '' and self.numeric_keys[i] != self.id:
                        self.order = i
                        if self.sorted_json[self.numeric_keys[i]]["preparing"]:
                            # text = self.font.render('已准备', True, (255, 255, 255))  # 白色文本
                            # self.window_surface.blit(text, Player_Icon_Location.ready_loca[self.order])
                            have_ready = pygame.image.load(f"{have_ready_icon_spirit.Destination}")
                            have_ready = pygame.transform.scale(have_ready, gender_spirit.CHARACTERS_SIZE[self.order])
                            self.screen.blit(have_ready, Player_Icon_Location.have_ready_icon_loca[self.order])
                        else:
                            show_font(self.screen, '等待准备', Player_Icon_Location.ready_loca[self.order],
                                      font_spirit.Destination['ShangShouHanShuTi'], 25)
                            pass
            quit_button = pygame.image.load(f"{button_spirit.Destination['quit_button']}")
            quit_button = pygame.transform.scale(quit_button, button_spirit.Characters_Size['quit_button'])
            self.screen.blit(quit_button, button_spirit.Location['quit_button_regis'])

        elif self.new_json["game_process"] == "requesting":
            if str(self.new_json["whose_turn"]) == self.id:
                if self.update_time_left:
                    if self.time_left == '10':
                        show_font(self.screen,self.time_left,(545,525),font_spirit.Destination['ShangShouHanShuTi'],30,Color.red)
                    else:
                        show_font(self.screen, self.time_left, (553, 526),font_spirit.Destination['ShangShouHanShuTi'], 30, Color.red)
                    arr_icon = ['clock']
                    public_gaming_pic(arr_icon, self.screen)
                if not self.target_need_choose:
                    choice_button_pic(self.new_json["rest_option"],self.screen)
                    rest_option = self.new_json["rest_option"]
                    extra_money = all_option[rest_option]
                    string = "需额外花费" + extra_money + "注"
                    show_font(self.screen, string, (585,480),font_spirit.Destination['ShangShouHanShuTi'],20,Color.red)
                else:
                    arr_icon = ["choose_player_battle"]
                    public_gaming_pic(arr_icon, self.screen)
        elif self.new_json["game_process"] == "inform" or self.new_json["game_process"] == "battle":
            if self.update_signal:
                inform_choice(self.new_json,self.inform_list)
                self.update_signal = False


    def refresh_page(self):
        pygame.display.flip()
        clock.tick(20)  # 通过设置帧率来控制循环速度

class BGMPlayer:
    def __init__(self):
        self.playlists = {
            '轻音乐': BGM.Music_Destination,
            '流行歌曲': BGM.Song_Destination,
            '桌游音乐': BGM.card_Destination,
        }
        self.current_playlist = list(self.playlists.keys())[2]
        self.current_song_index = 0
        self.paused = False
        self.song_path = ''
        self.load_song()
        self.run_once = True


    def load_song(self):
        self.song_path = self.playlists[self.current_playlist][list(self.playlists[self.current_playlist].keys())[self.current_song_index]]
        pygame.mixer.music.load(self.song_path)

    def get_voice_path(self, gender, gender_id, choice):
        # 这里应该是你根据gender, gender_id和choice获取声音文件路径的逻辑
        # 这里只是一个示例，你需要根据实际情况来修改
        base_path = ""
        choice = choice_list[choice]
        if gender == 'man':
            if gender_id == '1':
                base_path = bgm_man1_voice
            if gender_id == '2':
                base_path = bgm_man2_voice
        elif gender == 'woman':
            if gender_id == '1':
                base_path = bgm_woman1_voice
            if gender_id == '2':
                base_path = bgm_woman2_voice
        voice_path = f"{base_path}{choice}"
        return voice_path

    def play_voice(self, gender, gender_id, choice):
        # 根据性别和ID选择对应的声音文件路径
        voice_path = self.get_voice_path(gender, gender_id, choice)
        # 使用pygame.mixer.Sound来加载声音
        voice = pygame.mixer.Sound(voice_path)
        # 播放声音
        voice.play()
        print("人声播放成功")

    def play(self):
        # if self.run_once:
        #     self.run()
        #     self.run_once = False
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(0)
        self.paused = False

    def pause(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False
        else:
            pygame.mixer.music.pause()
            self.paused = True

    def next_song(self):
        self.current_song_index = (self.current_song_index + 1) % len(self.playlists[self.current_playlist])
        self.load_song()
        self.play()

    def next_playlist(self):
        playlist_keys = list(self.playlists.keys())
        current_index = playlist_keys.index(self.current_playlist)
        self.current_playlist = playlist_keys[(current_index + 1) % len(playlist_keys)]
        self.current_song_index = 0
        self.load_song()
        self.play()

    def restart_song(self):
        pygame.mixer.music.rewind()
        self.play()


# def main():
#     bgm_player = BGMPlayer()
#     # bgm_player.play_voice('woman','1',0)
#     # time.sleep(2)
#     bgm_player.next_playlist()
#     bgm_player.next_playlist()
#     bgm_player.run()
#     bgm_player.play()
#     time.sleep(1000)
#
# if __name__== "__main__" :
#     main()

