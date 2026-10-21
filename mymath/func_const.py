import numpy as np

weight_plus = [2,3,8,12]
class conv_func:
    def __init__(self):
        self.arr_10 = [0.8, 3.5, 3.9, 3.9, 3.9]
        self.arr_10_index = 0

        self.arr_20 = [3.75, 3.8, 3.9, 3.9, 3.9]
        self.arr_20_index = 0

        self.arr_50 = [3.85, 3.95, 3.97, 3.97, 3.97]
        self.arr_50_index = 0

        self.arr_100 = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        self.arr_100_index = 0

        self.all_index = 0

        self.circle_turn = [0, 0, 0, 0]
        self._sum_circle_turn_cache = None  # 缓存 sum_circle_turn 的结果

    def func_init(self, x):
        condition1 = (x < 0)
        condition2 = (x >= 0) & (x < 1)
        y1 = 0  # 当x < 0时
        y2 = 1  # 当0 <= x < 1时
        y3 = 0  # 当x >= 1时
        y = np.where(condition1, y1, np.where(condition2, y2, y3))
        return y

    def update_all_index(self):
        if self.all_index < len(self.arr_10):
            self.all_index += 1
            self.arr_10_index = self.all_index
            self.arr_20_index = self.all_index
            self.arr_50_index = self.all_index
            self.arr_100_index = self.all_index
        else:
            pass

    def sum_circle_turn(self):
        # 直接在每次调用时计算（4 次乘法，极小开销）。
        # 旧版做了缓存但从不失效，导致 circle_turn 变化后仍返回旧值（陈旧缓存 bug）。
        return sum(self.circle_turn[i] * weight_plus[i] for i in range(len(self.circle_turn)))

    def weight_conv(self, x):
        weight = self.sum_circle_turn()
        if 0 <= weight <= 5:
            if 0 <= weight <= 2:
                self.arr_10_index = 0
            else:
                self.arr_10_index = 1
            return self.f10(x)
        elif 5 < weight <= 10:
            if 5 < weight <= 6:
                self.arr_20_index = 0
            elif 6 < weight <= 8:
                self.arr_20_index = 1
            else:
                self.arr_20_index = 2
            return self.f20(x)
        elif 10 < weight <= 20:
            if 10 < weight <= 13:
                self.arr_50_index = 0
            elif 13 < weight <= 17:
                self.arr_50_index = 1
            else:
                self.arr_50_index = 2
            return self.f50(x)
        elif 20 < weight:
            return self.f100(x)

    def f10(self,x):
            condition1 = (x < 0)
            condition2 = (x >= 0) & (x < self.arr_10[self.arr_10_index])
            condition3 = (x >= self.arr_10[self.arr_10_index]) & (x < 4)
            y1 = 0  # 当x < 0时
            y2 = (x / self.arr_10[self.arr_10_index]) ** 6
            y3 = ((x - 4) / (self.arr_10[self.arr_10_index] - 4)) ** 6
            y4 = 0

            y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
            # print('使用了一级函数')
            return y

    def f20(self,x):
        # print('使用了二级函数')
        condition1 = (x < 0)
        condition2 = (x >= 0) & (x < self.arr_20[self.arr_20_index])
        condition3 = (x >= self.arr_20[self.arr_20_index]) & (x < 4)
        y1 = 0  # 当x < 0时
        y2 = 1 / (4 - x) - 1/4    # 当0 <= x < 1时
        y3 = (
            (1 / (4 - self.arr_20[self.arr_20_index]) - 1 / 4)
            / (self.arr_20[self.arr_20_index] - 4)
            * (x - 4)
        )  # 当x >= 1时
        y4 = 0
        y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
        return y

    def f50(self,x):
        condition1 = (x < 0)
        condition2 = (x >= 0) & (x < self.arr_50[self.arr_50_index])
        condition3 = (x >= self.arr_50[self.arr_50_index]) & (x < 4)
        y1 = 0  # 当x < 0时
        y2 = 1/(4.0 - x)**2 - 1/4 ** 2  # 当0 <= x < 1时
        y3 = (
            -(1 / (4 - self.arr_50[self.arr_50_index]))
            * (1 / (4.0 - self.arr_50[self.arr_50_index]) - 1 / 4 ** 2) ** 2
            * (x - 4)
        )  # 当x >= 1时
        y4 = 0
        y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
        # print('使用了三级函数')
        return y

    def f100(self,x):
        condition1 = (x < 0)
        condition2 = (x >= 0) & (x < 3.90)
        condition3 = (x >= 3.90) & (x < 4)
        y1 = 0  # 当x < 0时
        y2 = np.exp(x ** 3) - 1
        y3 = ((np.exp(3.90 ** 3) - 1)/(3.90 - 4)) * (x - 4)
        y4 = 0  # 当x >= 1时
        y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
        # print('使用了四 级函数')
        return y
