import pygame
from const import *

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
            return "water_spirit"
        else:
            return "ice_spirit"
    else:
        print("不符合格式的输入")
        return

def public_login_pic(arr_icon,screen):
    for icon in arr_icon:
        temp = pygame.image.load(f"{login.Destination[str(icon)]}")
        temp = pygame.transform.scale(temp, login.CHARACTERS_SIZE[str(icon)])
        screen.blit(temp, login.Location[str(icon)])

#必要参数  屏幕 内容 位置
def show_font(screen,content,loca,font=font_spirit.Destination['ShangShouHanShuTi'],size=16,color=Color.white):
    myfont = pygame.font.Font(font, size)
    text = myfont.render(content, True, color)  # 白色文本
    screen.blit(text, loca)  # 文本位置

    # print("已加载登录页面组件！")
