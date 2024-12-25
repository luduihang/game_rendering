
GAME_WIDTH_SIZE = 1200
GAME_HEIGHT_SIZE = 800

background_directory = '../myclient/src/item_pic/'
character_directory = '../myclient/src/character/'
bgm_directory = '../myclient/src/BGM/'
font_directory = '../myclient/src/Font/'


BACKGROUND_W = 1200
BACKGROUND_H = 900
Background = background_directory + '桌面清晰.jpg'

class ice_spirit:
    CHARACTERS_W = 200
    CHARACTERS_H = 200
    Destination = character_directory + '雪影娃娃第一阶段.png'

class water_spirit:
     CHARACTERS_W = 200
     CHARACTERS_H = 200
     Destination = character_directory + '水蓝蓝.png'

class fire_spirit:
     CHARACTERS_W = 200
     CHARACTERS_H = 200
     Destination = character_directory + '火花.png'

class cat_spirit:
     CHARACTERS_W = 200
     CHARACTERS_H = 200
     Destination = character_directory + '喵喵.png'

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
    CHARACTERS_SIZE = [36,24,24]

class Player_Icon_Location:
    player_loca = [
        (50,610),
        (-40,300),
        (1050,300)
    ]
    gender_loca = [
        (270,700),
        (20,535),
        (1020,535)
    ]
    wallet_loca = [
        (270,750),
        (20,500),
        (1020,500)
    ]
    nickname_loca = [
        (315,700),
        (50,535),
        (1050,535)
    ]
    money_loca = [
        (315,760),
        (50,500),
        (1050,500)
    ]

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