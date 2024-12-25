import pygame


GAME_WIDTH_SIZE = 1200
GAME_HEIGHT_SIZE = 800

background_directory = '../myclient/src/item_pic/'
character_directory = '../myclient/src/character/'
bgm_directory = '../myclient/src/BGM/'
font_directory = '../myclient/src/Font/'
button_directory = '../myclient/src/button/'
login_directory = '../myclient/src/login/'
card_directory = '../myclient/src/card_pic'

BACKGROUND_W = 1200
BACKGROUND_H = 900
Background = background_directory + '桌面清晰.png'
Login_Background = login_directory + '背景图.png'

card_type_arr = ['单张','对子','顺子','金花','顺金','三张']
select_option = ["10", "20", "50", "100", "throw_card", "compare_card"]


class all_spirit:
    Destination = {
        "ice_spirit":character_directory + '雪影娃娃第三阶段.png',
        "water_spirit":character_directory + '水蓝蓝.png',
        "fire_spirit":character_directory + '火花.png',
        "cat_spirit":character_directory + '喵喵.png',
    }
    Characters_Size = {
        "ice_spirit":(200,200),
        "water_spirit":(180,180),
        "fire_spirit":(180,180),
        "cat_spirit":(180,180),
    }

class have_ready_icon_spirit:
    CHARACTERS_SIZE = (80,80)
    Destination = background_directory + '准备好.png'

class wallet_spirit:
    CHARACTERS_SIZE = [
        (30,30),
        (25,25),
        (25,25)
    ]
    Destination = background_directory + '金币.png'

class gender_spirit:
    Destination = {
        'male': background_directory + '男孩标志.png',
        'female': background_directory + '女孩标志.png'
    }
    CHARACTERS_SIZE = [
        (35,35),
        (30,30),
        (30,30)
    ]

class font_spirit:
    Destination = {
        'ShangShouHanShuTi': font_directory + 'ShangShouHanShuTi.ttf',
        'HeiTi': font_directory + 'HeiTi.ttf',
    }
    CHARACTERS_SIZE = [33,30,30]

class card_spirit:
    def __init__(self):
        self.card_directory = card_directory
        self.Destination = {
            'Back':card_directory + '/扑克牌背面.png',
        }
        self.create_card_variables()
        self.CHARACTERS_SIZE = (140,200)
        self.Smaller_Size = (82,117)

    def create_card_variables(self):
        suits = ["方块", "梅花", "红心", "黑桃"]
        for suit in suits:
            for rank in range(2, 15):  # 修正范围以包括所有牌
                card_name = f"{suit}{rank}"
                variable_name = f"{suit}{rank}"  # 使用具体的牌名作为变量名
                file_name = f"{card_name}.png"
                self.Destination[variable_name] = f"{self.card_directory}/{file_name}"

class button_spirit:
    @staticmethod
    def get_button_rect(name):
        location = button_spirit.Location[name]
        size = button_spirit.Characters_Size[name]
        return pygame.Rect(location, size)

    Destination = {
        "ready":button_directory + '准备游戏.png',
        "ready_press":button_directory + '准备游戏(按下).png',
        "cancel_ready":button_directory + '取消准备.png',
        "cancel_ready_press":button_directory + '取消准备(按下).png',
        "quit_button":background_directory + '退出游戏.png',
        "log_in":login_directory + "登录按钮.png",
        "submit":login_directory + "提交.png",
        "return":login_directory + "图标上一步.png",
        "help_return":login_directory + "图标上一步.png",


        "10": button_directory + "十注.png",
        "20": button_directory + "二十注.png",
        "50": button_directory + "五十注.png",
        "100": button_directory + "一百注.png",
        "throw_card": button_directory + "弃牌.png",
        "compare_card": button_directory + "看牌.png",

        "stop_to_continue":button_directory + "播放停.png",
        "continue_to_stop":button_directory + "播放中.png",
        "return_play":button_directory + "重新播放.png",
        "next_music":button_directory + "下一首.png",
        "shift_list":button_directory + "歌单.png",

        "return_preparing":button_directory + "准备返回.png",
        "help":button_directory + "帮助.png",

    }

    Location = {
        "ready":(450,600),
        "ready_press":(200,300),
        "cancel_ready":(450,600),
        "cancel_ready_press":(200,300),
        "quit_button":(700,560),
        "quit_button_press":(703,563),
        "quit_button_regis":(1000,700),
        "log_in":(530,450),
        "log_in_press": (533, 453),
        "register":(370, 450),
        "submit":(680,560),
        "return":(800,700),
        "help_return":(980,700),

        "10": (310, 330),
        "20": (440, 330),
        "50": (570, 330),
        "100": (700, 330),
        "throw_card": (400, 420),
        "compare_card": (570, 420),

        "left_player": (-20, 250),
        "right_player": (1020, 250),

        "stop_to_continue": (25,30),
        "continue_to_stop": (25,30),
        "return_play": (85,30),
        "next_music": (145,30),
        "shift_list": (205,30),

        "return_preparing": (470,420),
        "help": (350,530)
    }
    Characters_Size = {
        "ready":(150,50),
        "cancel_ready":(150,50),
        "quit_button":(150,50),
        "quit_button_regis": (150, 50),
        "log_in":(200,66),
        "register":(120,60),
        "submit":(180,60),
        "return":(150,50),
        "help_return":(150,50),

        "10":(120,60),
        "20":(120,60),
        "50":(120,60),
        "100":(120,60),
        "throw_card":(150,60),
        "compare_card":(150,60),

        "left_player":(200,200),
        "right_player":(200,200),

        "stop_to_continue": (50,50),
        "continue_to_stop": (50,50),
        "return_play": (50,50),
        "next_music": (50,50),
        "shift_list": (50,50),

        "return_preparing": (240, 90),
        "help": (50, 50)
    }


class Player_Icon_Location:
    player_loca = [
        (100,620),
        (-20,250),
        (1020,250)
    ]
    gender_loca = [
        (320,650),
        (20,440),
        (1050,470)
    ]
    wallet_loca = [
        (320,700),
        (20,475),
        (1050,505)
    ]
    nickname_loca = [
        (365,650),
        (50,440),
        (1080,470)
    ]
    money_loca = [
        (365,700),
        (50,475),
        (1080,505)
    ]
    ready_loca = [
        (0,0),
        (200,390),
        (900,420)
    ]
    have_ready_icon_loca = [
        (0,0),
        (120,410),
        (1120,440)
    ]
    bet_money_loca = [
        (325, 740),
        (20, 505),
        (1050, 535)
    ]
    bet_loca = [
        (395, 740),
        (80, 505),
        (1110, 535)
    ]
    card_loca = [
        [(485,590),(545,590),(605,590)],
        [(160,325),(180,325),(200,325)],
        [(880,325),(900,325),(920,325)]

    ]
    inform_choice = [
        (0,0),
        (160,460),
        (880,460)
    ]

    #这是 准备好.png图标


class login:
    Destination = {
        "logo":login_directory + '图标.png',
        "frame":login_directory + '金色边框.png',
        "back":login_directory + '浅色背景.jpg',
        "age":login_directory + "适龄提醒.png",
        "user":login_directory + '用户名.png',
        "password":login_directory + '密码.png',
        "male":login_directory + '男孩标志.png',
        "female":login_directory + '女孩标志.png',
        "nickname":login_directory + '昵称.png',

        "help_back":login_directory + '浅色背景.jpg',
        "help_frame":login_directory + '金色边框.png',
    }
    Location = {
        "logo": (530, 80),
        "frame":(300, 150),
        "back":(312, 160),
        "age":(10, 10),
        "user":(430, 280),
        "password":(430,370),
        "male":(480, 570),
        "female":(575, 570),
        "nickname":(430, 460),
        "circle1":(545,588),
        "circle2": (645, 588),
        "circle3": (545, 588),
        "circle4": (645, 588),

        "help_back":(312, 110),
        "help_frame":(300, 100),

    }
    CHARACTERS_SIZE = {
        "logo": (160,160),
        "frame": (600,500),
        "back": (580,480),
        "age": (80,103),
        "user":(45,45),
        "password":(45,45),
        "male":(40,40),
        "female":(40,40),
        "nickname":(45,45),
        "circle1": 10,
        "circle2": 10,
        "circle3": 8,
        "circle4": 8,

        "help_back":(580,576),
        "help_frame":(600,600),
    }

class gaming:
    Destination = {
        "inform_frame":background_directory + "留言板.png",
        "game_over":background_directory + "游戏结束.png",
        "winner":background_directory + "胜利者.png",
        "challenge_success":background_directory + "挑战成功.png",
        "challenge_failure":background_directory + "挑战失败.png",
        "choose_player_battle":background_directory + "点击头像看牌.png",
        "all_bets":background_directory + "全部押注.png",
        "clock":background_directory + "倒计时.png",
        "music_pic":background_directory + "音乐.png",
    }
    Location= {
        "inform_frame":(870, 580),
        "game_over":(340,400),
        "winner":(400,400),
        "challenge_success":(360,400),
        "challenge_failure":(360,400),
        "choose_player_battle":(300,400),
        "all_bets":(920,30),
        "clock":(533,511),
        "music_pic":(30,190),
    }
    CHARACTERS_SIZE = {
        "inform_frame": (320,210),
        "game_over": (457,120),
        "winner": (390,139),
        "challenge_success":(426,126),
        "challenge_failure":(426,126),
        "choose_player_battle":(580,69),
        "all_bets":(40,38),
        "clock": (55, 55),
        "music_pic":(20,20),
    }

class Mouce:
    input_box = {
        'username': {'rect': pygame.Rect(500, 280, 280, 48), 'text': '', 'active': False, 'cursor_visible': False,
                     'cursor_position': 0},
        'password': {'rect': pygame.Rect(500, 370, 280, 48), 'text': '', 'active': False, 'cursor_visible': False,
                     'cursor_position': 0}
    }
    register_box = {
        'username': {'rect': pygame.Rect(500, 280, 280, 48), 'text': '', 'active': False, 'cursor_visible': False,
                     'cursor_position': 0},
        'password': {'rect': pygame.Rect(500, 370, 280, 48), 'text': '', 'active': False, 'cursor_visible': False,
                     'cursor_position': 0},
        'nickname': {'rect': pygame.Rect(500, 460, 280, 48), 'text': '', 'active': False, 'cursor_visible': False,
                     'cursor_position': 0}
    }

    button_region = {
        'quit_button': button_spirit.get_button_rect('quit_button'),
        'log_in': button_spirit.get_button_rect('log_in'),
        'register':button_spirit.get_button_rect('register'),
        'help':button_spirit.get_button_rect('help'),
    }
    button_register = {
        'quit_button_regis': button_spirit.get_button_rect('quit_button_regis'),
        'submit': button_spirit.get_button_rect('submit'),
        'return': button_spirit.get_button_rect('return'),
        'male_choice':pygame.Rect(login.Location['circle1'][0] - login.CHARACTERS_SIZE['circle1'],login.Location['circle1'][1] - login.CHARACTERS_SIZE['circle1'], 2 * login.CHARACTERS_SIZE['circle1'],2 * login.CHARACTERS_SIZE['circle1']),
        'female_choice': pygame.Rect(login.Location['circle2'][0] - login.CHARACTERS_SIZE['circle2'],
                                   login.Location['circle2'][1] - login.CHARACTERS_SIZE['circle2'],
                                   2 * login.CHARACTERS_SIZE['circle2'], 2 * login.CHARACTERS_SIZE['circle2'])
    }

    button_help = {
        'help_return': button_spirit.get_button_rect('help_return'),
    }

    button_preparing = {
        'ready': button_spirit.get_button_rect('ready'),
        'cancel_ready': button_spirit.get_button_rect('cancel_ready'),
        'quit_button_regis': button_spirit.get_button_rect('quit_button_regis'),
    }
    button_choice = {
        '10': button_spirit.get_button_rect('10'),
        '20': button_spirit.get_button_rect('20'),
        '50': button_spirit.get_button_rect('50'),
        '100': button_spirit.get_button_rect('100'),
        'throw_card': button_spirit.get_button_rect('throw_card'),
        'compare_card': button_spirit.get_button_rect('compare_card'),
    }
    target_choice = {
        'left_player':button_spirit.get_button_rect('left_player'),
        'right_player':button_spirit.get_button_rect('right_player'),
    }
    button_music = {
        'stop_to_continue': button_spirit.get_button_rect('stop_to_continue'),
        'continue_to_stop': button_spirit.get_button_rect('continue_to_stop'),
        'return_play': button_spirit.get_button_rect('return_play'),
        'next_music': button_spirit.get_button_rect('next_music'),
        'shift_list': button_spirit.get_button_rect('shift_list'),
    }
    press_return_button = {
        "return_preparing": button_spirit.get_button_rect('return_preparing'),
    }



# 这是准备阶段的消息字段
class Color:
    white = (255,255,255)
    black = (0,0,0)
    red = (255,0,0)
    green = (0,255,0)
    blue = (0,0,255)
    yellow = (255,255,0)
    cyan = (0,255,255)
    lemon = (255,250,205)
    orange = (255,165,0)
    gold = (255,215,0)
    gray = (76,76,76)
    dark_yellow =	(255,140,0)  # 浅黄色
    light_green = (0,255,127)
    dark_green = (46,139,87)
    brown = (135,62,35)
Randon_Color = [(220,20,60),(58,255,255),(255,69,100),(255,38,255),(0,170,42)]


bgm_man1_voice = '../myclient/src/BGM/man_voice/man_01/'
bgm_man2_voice = '../myclient/src/BGM/man_voice/man_02/'
bgm_woman1_voice = '../myclient/src/BGM/woman_voice/woman_01/'
bgm_woman2_voice  = '../myclient/src/BGM/woman_voice/woman_02/'
choice_list = ['压10注.mp3','压20注.mp3','压50注.mp3','压100注.mp3','弃牌.mp3','看牌.mp3']

class BGM:
    Music_Destination = {
        'Spring_Festival':bgm_directory + '春节序曲.mp3',
        'happiness':bgm_directory + '喜洋洋.mp3',
        'bird_poem': bgm_directory + '鸟之诗.mp3',
        'jiangnan': bgm_directory + '江南.mp3',
        'Croatian_Rhapsody': bgm_directory + '克罗地亚狂想曲.mp3',
    }
    Song_Destination = {
        'moon_light': bgm_directory + '月光.mp3',
        'Spring_Court_Snow': bgm_directory + '春庭雪.mp3',
        'Songs_of_Heaven': bgm_directory + '天行九歌.mp3',
        'imperial_capital':bgm_directory + '帝都.mp3',
        'zhifou': bgm_directory + '知否知否.mp3',
    }
    card_Destination = {
        'sanguosha': bgm_directory + '三国杀.mp3',
        'jieyinyuan': bgm_directory + '造梦西游接引院.mp3',
        'caihonglou': bgm_directory + '造梦西游彩虹楼.mp3',
        'doudizhu': bgm_directory + '斗地主.mp3',
    }



