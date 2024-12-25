import pygame
import time

# 初始化 Pygame
pygame.init()

# 设置窗口大小
screen_width, screen_height = 400, 300
screen = pygame.display.set_mode((screen_width, screen_height))
font = pygame.font.Font(None, 36)  # 使用默认字体，字号为36
# 颜色定义
black = (0, 0, 0)
white = (255, 255, 255)
gray = (200, 200, 200)

# 输入框的属性
input_box = {
    'username': {'rect': pygame.Rect(100, 100, 140, 32), 'text': '', 'active': False, 'cursor_visible': False,'cursor_position': 0},
    'password': {'rect': pygame.Rect(100, 200, 140, 32), 'text': '', 'active': False, 'cursor_visible': False,'cursor_position': 0}
}

# 光标形状
cursor = pygame.Surface((2, 20))
cursor.fill(black)
last_time = 0
# 主循环
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            for box in input_box.values():
                if box['rect'].collidepoint(event.pos):
                    box['active'] = True
                    box['cursor_visible'] = True
                else:
                    box['active'] = False
                    box['cursor_visible'] = False
        if event.type == pygame.KEYDOWN:
            for box in input_box.values():
                if box['active']:
                    if event.key == pygame.K_BACKSPACE:
                        box['text'] = box['text'][:-1]
                        if box['cursor_position'] > 0:
                            box['cursor_position'] -= 1
                    elif event.key == pygame.K_RETURN:
                        print(f"Username: {box['text']}")
                        box['text'] = ''
                        box['cursor_position'] = 0
                    else:
                        box['text'] += event.unicode
                        box['cursor_position'] += 1

    # 绘制背景
    screen.fill(gray)

    # 绘制输入框
    for box in input_box.values():
        if box['active']:
            pygame.draw.rect(screen, white, box['rect'], 2)
            # 绘制文本
            text_surface = font.render(box['text'], True, black)
            screen.blit(text_surface, (box['rect'].x + 5, box['rect'].y + 5))
            # 绘制光标
            if box['cursor_visible']:
                screen.blit(cursor, (box['rect'].x + 5 + box['cursor_position'] * 14, box['rect'].y + 5))
                # screen.blit(cursor, (box['rect'].x + 5 , box['rect'].y + 5))
        else:
            pygame.draw.rect(screen, black, box['rect'], 2)
            # 绘制文本
            text_surface = font.render(box['text'], True, white)
            screen.blit(text_surface, (box['rect'].x + 5, box['rect'].y + 5))

    # 更新屏幕
    pygame.display.flip()

    # 控制光标闪烁的计时器
    if time.time() - last_time >= 0.6:
        for box in input_box.values():
            box['cursor_visible'] = not box['cursor_visible']
        last_time = time.time()

# 退出 Pygame
pygame.quit()
