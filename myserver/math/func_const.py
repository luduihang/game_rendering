import numpy as np

weight_plus = [2,3,8,12]
class conv_func:
    def __init__(self):
        self.arr_10 = [0.8,3.5, 3.9, 3.9,3.9]
        self.arr_10_index = 0

        self.arr_20 = [3.75, 3.8,3.9,3.9,3.9]
        self.arr_20_index = 0

        self.arr_50 = [3.85, 3.95, 3.97,3.97,3.97]
        self.arr_50_index = 0

        self.arr_100 = [1.0 ,1.0 ,1.0,1.0 ,1.0 ,1.0,1.0]
        self.arr_100_index = 0

        self.all_index = 0

        self.circle_turn = [0,0,0,0]
        #记录每一个押注所压的次数，如果次数非常高，概率密度函数就会升级
    # 最初的概率密度函数，0-1之间的均匀分布
    def update_all_index(self):
        if self.all_index < len(self.arr_10):
            self.all_index += 1
            self.arr_10_index = self.all_index
            self.arr_20_index = self.all_index
            self.arr_50_index = self.all_index
            self.arr_100_index = self.all_index
        else:
            pass

    def func_init(self,x):
        condition1 = (x < 0)
        condition2 = (x >= 0) & (x < 1)
        condition3 = (x >= 1)
        y1 = 0  # 当x < 0时
        y2 = 1  # 当0 <= x < 1时
        y3 = 0  # 当x >= 1时
        y = np.where(condition1, y1, np.where(condition2, y2, y3))
        return y

    def sum_circle_turn(self):
        sum = 0
        for i in range(len(self.circle_turn)):
            sum += self.circle_turn[i] * weight_plus[i]
        print("sum的权重是:",sum)
        return sum

    def weight_conv(self,x):
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

    # 双二次函数型(左凹右凹) 效果优秀
    # symmetry = 0.8 1.8 2.8 3.8 3.8 3.8 迭代
    # 效果 0.66  0.75  0.84  0.92  0.93  0.93趋于稳定
    # 10块钱押注
    def f10(self,x):
            condition1 = (x < 0)
            condition2 = (x >= 0) & (x < self.arr_10[self.arr_10_index])
            condition3 = (x >= self.arr_10[self.arr_10_index]) & (x < 4)
            condition4 = (x >= 4)
            y1 = 0  # 当x < 0时
            y2 = (x / self.arr_10[self.arr_10_index]) ** 6
            y3 = ((x - 4)/(self.arr_10[self.arr_10_index] - 4)) ** 6
            y4 = 0

            y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
            print('使用了一级函数')
            return y

    # 反比例函数
    # index = 0  1  2  3
    # 效果 0.76  0.84  0.90  0.93 趋于稳定
    # 20块钱押注
    def f20(self,x):
        print('使用了二级函数')
        condition1 = (x < 0)
        condition2 = (x >= 0) & (x < self.arr_20[self.arr_20_index])
        condition3 = (x >= self.arr_20[self.arr_20_index]) & (x < 4)
        condition4 = (x >= 4)
        y1 = 0  # 当x < 0时
        y2 = 1 / (4 - x) - 1/4    # 当0 <= x < 1时
        y3 = (1 / (4 - self.arr_20[self.arr_20_index]) - 1/4)/(self.arr_20[self.arr_20_index] - 4) * (x - 4)  # 当x >= 1时
        y4 = 0
        y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
        return y


    #反比例幂(连续)
    # index = 0  1  2  3
    # 效果 0.87 0.94 0.98 0.99 趋于稳定
    # 50块钱押注
    def f50(self,x):
        condition1 = (x < 0)
        condition2 = (x >= 0) & (x < self.arr_50[self.arr_50_index])
        condition3 = (x >= self.arr_50[self.arr_50_index]) & (x < 4)
        condition4 = (x >= 4)
        y1 = 0  # 当x < 0时
        y2 = 1/(4.0 - x)**2 - 1/4 ** 2  # 当0 <= x < 1时
        y3 = -(1/(4 - self.arr_50[self.arr_50_index]))*(1/(4.0 - self.arr_50[self.arr_50_index]) - 1/4 ** 2)**2 * (x-4)  # 当x >= 1时
        y4 = 0
        y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
        print('使用了三级函数')
        return y


    # 终极奥义，指数函数
    # 效果 0.88 0.98 0.99 0.99 趋于稳定
    # 100块钱押注
    def f100(self,x):
        condition1 = (x < 0)
        condition2 = (x >= 0) & (x < 3.90)
        condition3 = (x >= 3.90) & (x < 4)
        condition4 = (x >= 4)
        y1 = 0  # 当x < 0时
        y2 = np.exp(x ** 3) - 1
        y3 = ((np.exp(3.90 ** 3) - 1)/(3.90 - 4)) * (x - 4)
        y4 = 0  # 当x >= 1时
        y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
        print('使用了四级函数')
        return y

