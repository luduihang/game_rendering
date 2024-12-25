import pygame

GAME_WIDTH_SIZE = 1200
GAME_HEIGHT_SIZE = 800

background_directory = '../myclient/src/item_pic/'
character_directory = '../myclient/src/character/'
bgm_directory = '../myclient/src/BGM/'
font_directory = '../myclient/src/Font/'
button_directory = '../myclient/src/button/'
login_directory = '../myclient/src/login/'

BACKGROUND_W = 1200
BACKGROUND_H = 900
Background = background_directory + '桌面清晰.jpg'
Login_Background = login_directory + '背景图.png'

class all_spirit:
    Destination = {
        "ice_spirit":character_directory + '雪影娃娃第二阶段.png',
        "water_spirit":character_directory + '水蓝蓝.png',
        "fire_spirit":character_directory + '火花.png',
        "cat_spirit":character_directory + '喵喵.png',
    }
    Characters_Size = {
        "ice_spirit":(200,200),
        "water_spirit":(200,200),
        "fire_spirit":(200,200),
        "cat_spirit":(200,200),
    }

class have_ready_icon_spirit:
    CHARACTERS_SIZE = (80,80)
    Destination = background_directory + '准备好.png'

class wallet_spirit:
    CHARACTERS_SIZE = [
        (50,50),
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
        (45,45),
        (30,30),
        (30,30)
    ]

class font_spirit:
    Destination = {
        'ShangShouHanShuTi': font_directory + 'ShangShouHanShuTi.ttf'
    }
    CHARACTERS_SIZE = [40,30,30]

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
    }
    Location = {
        "ready":(450,600),
        "ready_press":(200,300),
        "cancel_ready":(200,300),
        "cancel_ready_press":(200,300),
        "quit_button":(700,560),
        "quit_button_press":(703,563),
        "log_in":(530,450),
        "log_in_press": (533, 453),
        "register":(370, 450),
    }
    Characters_Size = {
        "quit_button":(150,50),
        "log_in":(200,66),
        "register":(120,60),
    }


class Player_Icon_Location:
    player_loca = [
        (50,610),
        (-40,300),
        (1050,300)
    ]
    gender_loca = [
        (270,700),
        (20,500),
        (1020,500)
    ]
    wallet_loca = [
        (270,750),
        (20,535),
        (1020,535)
    ]
    nickname_loca = [
        (315,700),
        (50,500),
        (1050,500)
    ]
    money_loca = [
        (315,760),
        (50,535),
        (1050,535)
    ]
    ready_loca = [
        (0,0),
        (180,450),
        (850,450)
    ]
    have_ready_icon_loca = [
        (0,0),
        (120,470),
        (1070,470)
    ]#这是 准备好.png图标

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

class login:
    Destination = {
        "logo":login_directory + '图标.png',
        "frame":login_directory + '金色边框.png',
        "back":login_directory + '浅色背景.jpg',
        "age":login_directory + "适龄提醒.png",
        "user":login_directory + '用户名.png',
        "password":login_directory + '密码.png',
    }
    Location = {
        "logo": (530, 80),
        "frame":(300, 150),
        "back":(312, 160),
        "age":(10, 10),
        "user":(430, 280),
        "password":(430,370),
    }
    CHARACTERS_SIZE = {
        "logo": (160,160),
        "frame": (600,500),
        "back": (580,480),
        "age": (80,103),
        "user":(45,45),
        "password":(45,45),
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
    }

# {'game_process': 'requesting',
# '0': {'username': 'lc', 'gender': 'male', 'preparing': True, 'money': 497, 'bet_money': 3, 'cards': [{'suit': '黑桃', 'value': 14}, {'suit': '黑桃', 'value': 2}, {'suit': '红心', 'value': 8}], 'failure': False, 'cards_value': 0},
# '1': {'username': 'ldh', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '方块', 'value': 4}, {'suit': '梅花', 'value': 12}, {'suit': '方块', 'value': 5}], 'failure': False, 'cards_value': 0},
# '2': {'username': 'jsl', 'gender': 'male', 'preparing': True, 'money': 499, 'bet_money': 1, 'cards': [{'suit': '梅花', 'value': 5}, {'suit': '梅花', 'value': 2}, {'suit': '红心', 'value': 4}], 'failure': False, 'cards_value': 0},
# 'property': 'table', 'all_bets': 3, 'whose_turn': 1, 'rest_option': 0, 'user_ids_list': [-1, 1, 2], 'option': 7, 'target': 1, 'battle_win': False}
# 这是下注的时候的消息字段

# {'game_process': 'preparing', 'ready_clients': 1,
# '0': {'username': 'lc', 'gender': 'male', 'preparing': False, 'money': 500, 'bet_money': 0},
# '1': {'username': 'ldh', 'gender': 'male', 'preparing': False, 'money': 500, 'bet_money': 0},
# '2': {'username': 'jsl', 'gender': 'male', 'preparing': True, 'money': 500, 'bet_money': 0}}
# 这是准备阶段的消息字段