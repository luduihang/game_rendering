import random


class Cards:
    def __init__(self):
        self.cards = []
        self.reset_deck()

    def reset_deck(self):
        self.cards = []
        for suit in ['黑桃', '红心', '方块', '梅花']:
            for value in range(2, 15):
                self.cards.append({'suit': suit, 'value': value})

    def shuffle_deck(self):
        random.shuffle(self.cards)

    def draw_cards(self, num_cards=3):
        if len(self.cards) < num_cards:
            print("Not enough cards in the deck.")
            return None
        return [self.cards.pop() for _ in range(num_cards)]

    def draw_cards_plus(self,num_cards=3):
        max_probability = 0
        best_cards = None

        for _ in range(3):
            drawn_cards = self.draw_cards(num_cards)
            if drawn_cards is None:
                return None

            cards_probability = Cards_Probability(drawn_cards)
            cards_probability.get_probability()

            if cards_probability.probability > max_probability:
                max_probability = cards_probability.probability
                best_cards = drawn_cards

        return best_cards


class Cards_Value:
    def __init__(self, cards):
        self.cards = cards
        self.value = 0
        self.type = None  #type=0无  type=1对子 type=2拖拉机 type=3假金花  type=4金花 type=5三个一样
        self.probability = None
        # type = 0 无
    def max_consecutive_value(self):
        # 提取每张牌的值
        values = [card['value'] for card in self.cards]
        # 对值进行排序
        values.sort()

        # 判断是否连续
        if values[0] + 1 == values[1] and values[1] + 1 == values[2]:
            # 判断是否为顺子
            return max(values)
        else:
            return None

    def Get_Type(self):
        # 提取每张牌的值和花色
        values = [card['value'] for card in self.cards]
        suits = [card['suit'] for card in self.cards]
        values.sort()

        if len(set(values)) == 1:
            self.type = 5
        elif self.max_consecutive_value() and suits[0] == suits[1] == suits[2]:
            self.type = 4
        elif suits[0] == suits[1] == suits[2] and self.max_consecutive_value() is None:
            self.type = 3
        elif self.max_consecutive_value():
            self.type = 2
        elif len(set(values)) == 2:
            self.type = 1
        else:
            self.type = 0

    def Get_Value(self):
        suit_list = ['黑桃', '红心', '方块', '梅花']  #从左到右依次递减

        self.Get_Type()
        values = [card['value'] for card in self.cards]
        new_values = values
        values.sort()
        suits = [card['suit'] for card in self.cards]

        if self.type == 5:
            self.value = 100000 * self.type +  values[0]
        if self.type == 4:
            self.value = 100000 * self.type + values[2] * 1000 + (3 - suit_list.index(suits[0])) * 10
        if self.type == 3:
            self.value = 100000 * self.type + values[2] * 1000 + (3 - suit_list.index(suits[0])) * 10
        if self.type == 2:
            values = [card['value'] for card in self.cards]
            new_values = [card['value'] for card in self.cards]
            values.sort()
            max_value = values[2]
            max_index = new_values.index(max_value)
            max_suit = suits[max_index]
            self.value = 100000 * self.type + values[2] * 1000 + (3 - suit_list.index(max_suit)) * 10
        if self.type == 1:
            different_value = None
            equal_values = []  # 存储相等卡牌的值
            prev_value = None
            for num in values:
                if num == prev_value:
                    equal_values.append(num)
                prev_value = num
            #获取另一个不相等的牌的大小值
            # print("equal_values", equal_values)
            if equal_values:  # 检查相等卡牌列表是否不为空
                for value in values:
                    if values.count(value) == 1 and value != equal_values[0]:
                        different_value = value
                        break

                new_values = [card['value'] for card in self.cards]
                dif_suit = suits[new_values.index(different_value)]
                self.value = 100000 * self.type + equal_values[0] * 1000 + different_value * 10 + (3 - suit_list.index(dif_suit)) * 1
            else:
                self.value = 0
                print("两张相同的卡片逻辑问题")
            # 处理找不到不相等牌的情况
            # 可以选择设定一个默认值或者处理其他逻辑
        if self.type == 0:
            values = [card['value'] for card in self.cards]
            new_values = [card['value'] for card in self.cards]
            values.sort()
            max_value = values[2]
            max_index = new_values.index(max_value)
            max_suit = suits[max_index]

            self.value = 100000 * self.type + values[2] * 5000 + values[1] * 400 + values[0] * 20 + (3 - suit_list.index(max_suit)) * 1

        return self.value

class Cards_Probability:
    def __init__(self, cards):
        self.deck = Cards()
        self.deck.reset_deck()
        self.deck.shuffle_deck()
        self.cards = cards
        self.value = None
        self.probability = None

    def get_probability(self):
        num = 0
        cards_value = Cards_Value(self.cards)
        self.value = cards_value.Get_Value()

        for i in range(2000):
            self.deck.reset_deck()
            self.deck.shuffle_deck()
            cards_copy = self.deck.draw_cards(3)
            cards_value_copy = Cards_Value(cards_copy)
            cards_value_copy.Get_Value()
            if self.value > cards_value_copy.value:
                num += 1
        self.probability = num / 2000
        return self.probability

cards1 = [{'suit': '黑桃', 'value': 7}, {'suit': '方块', 'value': 7}, {'suit': '红心', 'value': 2}]
cards_probability =  Cards_Probability(cards1)
cards_probability.get_probability()
print("cards_probability:", cards_probability.probability)

# # 创建一个牌堆实例
# deck = Cards()
# print("Initial deck:")
# # 洗牌
# #
# # cards1 = [{'suit': '红心', 'value': 12}, {'suit': '方块', 'value': 2}, {'suit': '黑桃', 'value': 13}]
# array = [0] * 6
# times = 0
# my_times= 0
# for i in range(1000):
#     deck.shuffle_deck()
#     drawn_cards_01 = deck.draw_cards(3)
#     drawn_cards_02 = deck.draw_cards(3)
#     card_value_01 = Cards_Value(drawn_cards_01)
#     card_value_02 = Cards_Value(drawn_cards_02)
#     card_value_01.Get_Value()
#     card_value_02.Get_Value()
#     if(card_value_01.value > card_value_02.value):
#         times += 1
#     if(card_value_01.value < card_value_02.value):
#         my_times += 1
#     if card_value_01.value == card_value_02.value:
#         print(card_value_01.value)
#         values = [card['value'] for card in drawn_cards_01]
#         suits = [card['suit'] for card in drawn_cards_01]
#         for value, suit in zip(values, suits):
#             print(f"牌是{suit}{value},")
#
#         values = [card['value'] for card in drawn_cards_02]
#         suits = [card['suit'] for card in drawn_cards_02]
#         for value, suit in zip(values, suits):
#             print(f"牌是{suit}{value},")
#
#     deck.reset_deck()
#
# print("玩家1次数：", times)
# print("玩家2次数：", my_times)
# #经过测试没有发生平局次数，而且测试1000000次都没有，胜率趋于1：1，随机抽卡公平，大小判定函数正确
#

# deck = Cards()
# deck.shuffle_deck()
# drawn_cards_03 = deck.draw_cards(3)
# print(drawn_cards_03)
# card_value_01 = Cards_Value(drawn_cards_03)
# card_value_01.Get_Value()
# print(card_value_01.value)