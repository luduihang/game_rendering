import pygame
import random
import time
import threading
from const import *

# inform_list = ["这是一条消息", "这是另一条消息", "再一条消息", "更多消息", "最后一条消息"]

class UserAllocation:
    def __init__(self, self_id):
        self.self_id = self_id
        self.users = []

    def update_users(self, user_ids):
        # 创建一个新列表来保存更新后的用户ID，初始时包含self_id
        new_users = [self.self_id]
        user_ids_set = set(user_ids)  # 使用集合来提高查找效率

        # 遍历原列表，除了self_id之外的元素，如果在新列表中，则保留其位置
        for user_id in self.users[1:]:
            if user_id in user_ids_set:
                new_users.append(user_id)
            elif len(new_users) < 3:  # 只有当新列表长度小于3时，才添加空字符串
                new_users.append('')

        # 添加新列表中没有的元素，除了self_id
        for user_id in user_ids:
            if user_id != self.self_id and user_id not in new_users:
                # 如果有空字符串，则替换空字符串；否则，添加到列表末尾
                if '' in new_users:
                    new_users[new_users.index('')] = user_id
                else:
                    new_users.append(user_id)

        # 如果新列表长度大于3，则只保留前三个元素
        self.users = new_users[:3]
        return self.users

    def get_allocation(self):
        return self.users

class RepeatedTimer:
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.next_call = time.time()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self.next_call += self.interval
            self._timer = threading.Timer(self.next_call - time.time(), self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

#必要参数  屏幕 内容 位置
def show_font(screen,content,loca,font=font_spirit.Destination['ShangShouHanShuTi'],size=16,color=Color.white):
    myfont = pygame.font.Font(font, size)
    text = myfont.render(content, True, color)  # 白色文本
    screen.blit(text, loca)  # 文本位置

def show_inform(screen,inform,loca):
    myfont = pygame.font.Font(font_spirit.Destination['HeiTi'], 20)
    x, y = loca
    start = 0

    while '[' in inform[start:]:
        open_bracket = inform.find('[', start)
        close_bracket = inform.find(']', open_bracket)
        num = 0  # 初始化num变量
        if open_bracket != -1 and close_bracket != -1:
            if close_bracket > open_bracket + 1 and inform[close_bracket + 1].isdigit():
                num = int(inform[close_bracket + 1])
                # close_bracket += 1
            # 渲染括号前的文本
            if open_bracket > start:
                text = myfont.render(inform[start:open_bracket], True, Color.gray)
                screen.blit(text, (x, y))
                x += text.get_width()
            # 渲染括号内的文本
            highlighted_text = myfont.render(inform[open_bracket + 1:close_bracket], True, Randon_Color[num])
            screen.blit(highlighted_text, (x, y))
            x += highlighted_text.get_width()
            start = close_bracket + 2
        else:
            break
        # 渲染剩余的文本
    remaining_text = myfont.render(inform[start+1:], True, Color.gray)
    screen.blit(remaining_text, (x, y))

def show_font_list(screen,position, max_height,inform_list):
    # 从列表后面开始显示，确保不超过最大高度
    display_strings = []
    current_height = position[0]
    font = pygame.font.Font(font_spirit.Destination['HeiTi'],25)
    for text in reversed(inform_list):
        font_surface = font.render(text, True, Color.white)
        text_width, text_height = font_surface.get_size()
        if current_height + text_height > max_height:
            break
        display_strings.append((text, text_width, text_height))
        current_height += text_height

    # 显示字符串
    i = 0
    for text, text_width, text_height in reversed(display_strings):
        # 确保不超过最大宽度
        # show_font(screen, text, (position[0], position[1] + 25 * i), font_spirit.Destination['ShangShouHanShuTi'], 25, Color.red)
        show_inform(screen,text,(position[0], position[1] + 30 * i))
        i += 1
    # print("已加载登录页面组件！")

def get_spirit(gender,nickname):
    last_char = nickname[-1]  # 获取字符串的最后一个字符
    ascii_value = ord(last_char)  # 获取字符的ASCII值
    if gender == 'male':
        if ascii_value % 2 == 1:
            return "fire_spirit"
        else:
            return "cat_spirit"
    elif gender == 'female':
        if ascii_value % 2 == 1:
            return "ice_spirit"
        else:
            return "water_spirit"
    else:
        print("不符合格式的输入")
        return

def get_voice(gender,nickname):
    last_char = nickname[-1]  # 获取字符串的最后一个字符
    ascii_value = ord(last_char)  # 获取字符的ASCII值
    if gender == 'male':
        if ascii_value % 2 == 1:
            return "man1"
        else:
            return "man2"
    elif gender == 'female':
        if ascii_value % 2 == 1:
            return "woman1"
        else:
            return "woman2"
    else:
        print("不符合格式的输入")
        return

def public_login_pic(arr_icon,screen):
    for icon in arr_icon:
        temp = pygame.image.load(f"{login.Destination[str(icon)]}")
        temp = pygame.transform.scale(temp, login.CHARACTERS_SIZE[str(icon)])
        screen.blit(temp, login.Location[str(icon)])

def public_gaming_pic(arr_icon,screen):
    for icon in arr_icon:
        temp = pygame.image.load(f"{gaming.Destination[str(icon)]}")
        temp = pygame.transform.scale(temp, gaming.CHARACTERS_SIZE[str(icon)])
        if icon == "inform_frame":
            temp.set_alpha(210)
        screen.blit(temp, gaming.Location[str(icon)])

def public_button_pic(arr_icon,screen):
    for icon in arr_icon:
        temp = pygame.image.load(f"{button_spirit.Destination[str(icon)]}")
        temp = pygame.transform.scale(temp, button_spirit.Characters_Size[str(icon)])
        screen.blit(temp, button_spirit.Location[str(icon)])


def choice_button_pic(rest_option,screen):
    for i in range(rest_option,6):
        temp = pygame.image.load(f"{button_spirit.Destination[select_option[i]]}")
        temp = pygame.transform.scale(temp, button_spirit.Characters_Size[select_option[i]])
        screen.blit(temp, button_spirit.Location[select_option[i]])

def inform_choice(json,inform_list):
    option = json["option"]
    whose_turn = json["whose_turn"]
    nickname = json[str(whose_turn)]["nickname"]
    string = ""
    random_number = str(random.randint(0, len(Randon_Color)-1))  # 生成0-6之间的随机数字
    string += str(len(inform_list))
    string += ": "

    if 0 <= option <= 3:
        string += "[" + nickname +"]"+ random_number + "选选择了押注" + select_option[option]
    elif option == 4:
        string += "[" + nickname +"]"+ random_number + "选选择了弃牌"
    elif option == 5:
        target = json["target"]
        target_nickname = json[str(target)]["nickname"]
        string += "[" + nickname +"]"+ random_number + "选择了看" + "[" + target_nickname +"]"+ random_number + "的牌"

    inform_list.append(string)
    if json['game_process'] == 'battle':
        if 'battle_win' in json:
            string = ""
            random_number = str(random.randint(0, len(Randon_Color) - 1))  # 生成0-6之间的随机数字
            string += str(len(inform_list))
            string += ": "
            if json["battle_win"]:
                string += "[" + nickname +"]"+ random_number + '挑挑战成功'
            else:
                string += "[" + nickname + "]" + random_number + '挑挑战失败'
            inform_list.append(string)
    print("1")

def show_help_font(window_surface):
    show_font(window_surface, '游戏规则', (540, 130),
              font_spirit.Destination['ShangShouHanShuTi'], 40)
    show_font(window_surface, '1.每名玩家开局分别由系统发到3张牌，大小如下', (370, 175),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '单张<对子<顺子<金花<顺金<三个。', (350, 205),
              font_spirit.Destination['ShangShouHanShuTi'], 25, Color.red)
    show_font(window_surface, '拿到的牌是相同类型，那么他们的大小由三张牌当中', (350, 235),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '最大的一张作为判别依据(其中A是最大的牌)。', (350, 265),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '2.每局开始，系统自动为三名玩家押注5，然后三名', (370, 295),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '玩家分别按照顺序押注，押注的大小分别是10 20 50', (350, 325),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '100,同时玩家也可以选择弃牌或者看牌。', (350, 355),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '3.押注：每轮玩家可以押注大小的最小选项 是当前', (370, 385),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '所有玩家押注选项的最大值。（如：开始默认的押注', (350, 415),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '10 20 50 100,但是前一名玩家已经押注了20, 那么', (350, 445),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '下一位玩家押注的选项就是20 50 100）', (350, 475),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '弃牌：指玩家自动弃权，本副牌认输且不收回本副牌', (370, 505),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '筹码。', (350, 535),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '看牌：拿自己的牌和其他玩家的牌比大小，同时要支', (370, 565),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '付当前单注大小的比牌费用，加入押注池。', (350, 595),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '4.场上最后一名玩家是胜利者，获得押注池里面的', (370, 625),
              font_spirit.Destination['ShangShouHanShuTi'], 25)
    show_font(window_surface, '所有金币。', (350, 655),
              font_spirit.Destination['ShangShouHanShuTi'], 25)