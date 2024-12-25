import numpy as np
import math
from  myserver.math.func_const import *
import matplotlib.pyplot as plt

from scipy.signal import convolve

def convolution_of_functions(f1, f2):
    """
    This function takes two piecewise continuous functions, computes their convolution,
    normalizes it to be a probability density function over the interval [0, 1], and plots the results.
    """
    # 创建一个更密集的x值的范围
    x = np.linspace(-5, 5, 3000)  # 更密集的采样点和更大的范围

    # 计算两个函数的样本点
    f1_samples = f1(x)
    f2_samples = f2(x)

    # 使用 scipy.signal.convolve 计算卷积
    convolved_samples = convolve(f2_samples, f1_samples, mode='same') * (x[1]-x[0])

    # 线性变换
    nonzero_indices = np.nonzero(convolved_samples)[0]  # 找到非零元素的索引
    min_x = x[nonzero_indices[0]]  # 有值部分的最小横坐标
    max_x = x[nonzero_indices[-1]]  # 有值部分的最大横坐标

    convolved_samples_normalized = (x - min_x) / (max_x - min_x)

    # 归一化卷积结果为概率密度函数
    new_normalization_factor = np.trapz(convolved_samples, convolved_samples_normalized)
    pdf_final = convolved_samples / new_normalization_factor

    max_index = np.argmax(pdf_final)
    max_value = pdf_final[max_index]
    max_x_value = convolved_samples_normalized[max_index]
    # 计算概率密度函数的均值
    mean_value = np.trapz(convolved_samples_normalized * pdf_final, convolved_samples_normalized)

    # 绘制图像
    # plt.figure(figsize=(12, 8))
    #
    # # 绘制第一个函数的样本
    # plt.plot(x, f1_samples, label='Function 1 (Sampled)')
    #
    # # 绘制第二个函数的样本
    # plt.plot(x, f2_samples, label='Function 2 (Sampled)')
    #
    # # 绘制卷积结果的样本
    # plt.plot(x, convolved_samples, label='Normalized Convolution (PDF)', linestyle='--')
    #
    # plt.plot(convolved_samples_normalized, pdf_final, label='Normalized Convolution2 (PDF)', linestyle='--')
    #
    # plt.scatter(max_x_value, max_value, color='red', label='Max Value: ({:.2f}, {:.2f})'.format(max_x_value, max_value))
    # plt.title('Sampled Functions and Their Normalized Convolution (PDF)')
    # plt.xlabel('x')
    # plt.ylabel('y')
    # plt.legend()
    # plt.grid(True)
    # plt.show()

    # 打印均值到控制台
    print("概率密度函数的均值: {:.2f}".format(mean_value))

    def pdf_function(x_values):
        # 使用线性插值来找到x_values对应的概率密度函数值
        return np.interp(x_values, convolved_samples_normalized, pdf_final)

    return pdf_function

def circle_convolution(func1,func2,num):#第一个是被卷积函数，第二个是重复卷积函数
    func_buffer = convolution_of_functions(func1, func2)
    for i in range(num -1):
        func_buffer = convolution_of_functions(func_buffer, func2)
    return func_buffer

def integral_func(pdf,up_limit):
    x_values = np.linspace(0, up_limit, 1000)  # 在0到0.8之间创建更密集的点
    pdf_values = pdf(x_values)
    integral_value = np.trapz(pdf_values, x_values)
    # print("积分的返回值是:",integral_value)
    return integral_value

def mean_func(pdf):
    x_values = np.linspace(0,1,2000)
    pdf_values = pdf(x_values)
    mean_value = np.trapz(x_values * pdf_values, x_values)
    return mean_value

def switch_func(func1,conv):
    return circle_convolution(func1, conv.weight_conv, 1)


# # 已知的两个数组
# array1 = ['0', '3', '7']
# array2 = ['0', '1', '2']
#
# # 已知的映射关系
# known_mapping = {'3': '0'}

def mapping_dict(array1, array2, known_mapping):
    # 创建一个映射字典，用于从array1到array2的映射
    mapping_dict = {}
    mapping_dict_arr = [None,None]
    # 首先处理已知的映射关系
    for key, value in known_mapping.items():
        mapping_dict[key] = value

    # 处理剩余的元素，这里使用一个简单的方法，即按照array1的顺序映射到array2的剩余位置
    # 注意：这个方法依赖于array1和array2的元素数量相同，且已知映射不会与剩余映射冲突
    remaining_elements = [x for x in array1 if x not in mapping_dict]
    remaining_targets = [x for x in array2 if x not in mapping_dict.values()]

    for source, target in zip(remaining_elements, remaining_targets):
        mapping_dict[source] = target

    # 现在创建一个反向映射字典，用于从array2找到array1的元素
    reverse_mapping_dict = {v: k for k, v in mapping_dict.items()}

    # 现在你可以使用映射字典和反向映射字典来查找元素
    print(mapping_dict)  # array1到array2的映射
    print(reverse_mapping_dict)  # array2到array1的反向映射

    mapping_dict_arr[0] = mapping_dict
    mapping_dict_arr[1] = reverse_mapping_dict
    # 使用反向映射字典查找array1中的元素
    element_in_array2 = '1'
    corresponding_element_in_array1 = reverse_mapping_dict.get(element_in_array2, None)
    print(f"Element in array1 corresponding to '{element_in_array2}' in array2 is: {corresponding_element_in_array1}")
    return mapping_dict_arr


# 定义两个分段函数
# 初始类型
# def f1(x):
#     condition1 = (x < 0)
#     condition2 = (x >= 0) & (x < 1)
#     condition3 = (x >= 1)
#     y1 = 0  # 当x < 0时
#     y2 = 1  # 当0 <= x < 1时
#     y3 = 0  # 当x >= 1时
#     y = np.where(condition1, y1, np.where(condition2, y2, y3))
#     return y
#
# # 直线型
# def f2(x):
#
#     condition1 = (x <= 0)
#     condition2 = (x > 0) & (x < 3.5)
#     condition3 = (x >= 3.5) & (x < 4)
#     condition4 = (x >= 4)
#     y1 = 0  # 当x < 3时
#     y2 = (1/3.5) * x  # 当3 <= x < 4时
#     y3 = 1/(3.5 - 4) * (x - 4) # 当x >= 4时
#     y4 = 0
#     y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
#     return y
#
# # 幂函数型
# def f3(x):
#     condition1 = (x < 0)
#     condition2 = (x >= 0) & (x < 3.8)
#     condition3 = (x >= 3.8) & (x < 4)
#     condition4 = (x >= 4)
#     y1 = 0  # 当x < 0时
#     y2 = (x/3.8)**6
#     y3 = 1
#     y4 = 0  # 当x >= 3时
#     y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
#     return y
#
# # 反比例函数型
# def f4(x):
#     condition1 = (x < 0)
#     condition2 = (x >= 0) & (x < 4)
#     condition3 = (x >= 4)
#     y1 = 0  # 当x < 0时
#     y2 = 1/(4.01 - x) - 1/(4.01)    # 当0 <= x < 1时
#     y3 = 0  # 当x >= 1时
#     y = np.where(condition1, y1, np.where(condition2, y2, y3))
#     return y
#
# # 双二次函数型
# def f5(x):
#
#     global symmetry
#     condition1 = (x < 0)
#     condition2 = (x >= 0) & (x < symmetry)
#     condition3 = (x >= symmetry) & (x < 4)
#     condition4 = (x >= 4)
#     y1 = 0  # 当x < 0时
#     y2 = (x / symmetry) ** 6
#     y3 = ((x - 4)/(symmetry - 4)) ** 6
#     y4 = 0
#
#     y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
#     return y
# #双二次函数型
# def f6(x):
#     condition1 = (x < 0)
#     condition2 = (x >= 0) & (x < 2.5)
#     condition3 = (x >= 2.5) & (x < 4)
#     condition4 = (x >= 4)
#     y1 = 0  # 当x < 0时
#     y2 = (x / 2.5) ** 6
#     y3 = (-4/9)*(x-1)*(x-4)
#     y4 = 0
#
#     y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
#     return y
#
# #奥义，反比例幂(连续)
# def f7(x):
#     global index
#     arr = [3.5,3.75,3.95,3.97]
#     condition1 = (x < 0)
#     condition2 = (x >= 0) & (x < arr[index])
#     condition3 = (x >= arr[index]) & (x < 4)
#     condition4 = (x >= 4)
#     y1 = 0  # 当x < 0时
#     y2 = 1/(4.0 - x)**2 - 1/4 ** 2  # 当0 <= x < 1时
#     y3 = -(1/(4 - arr[index]))*(1/(4.0 - arr[index]) - 1/4 ** 2)**2 * (x-4)  # 当x >= 1时
#     y4 = 0
#     y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
#     return y
#
# # 什么都不是函数
# def f8(x):
#     condition1 = (x < 2.7)
#     condition2 = (x >= 2.7) & (x < 2.9)
#     condition3 = (x >= 2.9) & (x < 3.9)
#     condition4 = (x >= 3.9) & (x < 4)
#     condition5 = (x >= 4)
#     y1 = 0  # 当x < 0时
#     y2 = (x - 2.7) * 5   # 当0 <= x < 1时
#     y3 = 1  # 当x >= 1时
#     y4 = (-10) * (x - 4)
#     y5 = 0
#
#     y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, np.where(condition4, y4, y5))))
#     return y
#
# #奥义，反比例函数
# def f9(x):
#     arr = [2.0, 3.0, 3.75, 3.9]
#     condition1 = (x < 0)
#     condition2 = (x >= 0) & (x < arr[index])
#     condition3 = (x >= arr[index]) & (x < 4)
#     condition4 = (x >= 4)
#     y1 = 0  # 当x < 0时
#     y2 = 1 / (4 - x) - 1/4    # 当0 <= x < 1时
#     y3 = (1 / (4 - arr[index]) - 1/4)/(arr[index] - 4) * (x - 4)  # 当x >= 1时
#     y4 = 0
#     y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
#     return y
#
# #终极奥义，指数函数
# def f10(x):
#     condition1 = (x < 0)
#     condition2 = (x >= 0) & (x < 3.90)
#     condition3 = (x >= 3.90) & (x < 4)
#     condition4 = (x >= 4)
#     y1 = 0  # 当x < 0时
#     y2 = np.exp(x ** 3) - 1
#     y3 = ((np.exp(3.90 ** 3) - 1)/(3.90 - 4)) * (x - 4)
#     y4 = 0  # 当x >= 1时
#     y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
#     return y
#
# def f11(x):
#     condition1 = (x < 0)
#     condition2 = (x >= 0) & (x < 4)
#     condition3 = (x >= 4)
#     y1 = 0  # 当x < 0时
#     y2 = np.exp(x * 4) - 1
#     y3 = 0  # 当x >= 1时
#     y = np.where(condition1, y1, np.where(condition2, y2, y3))
#     return y
#
# #指数连续函数(连续)
# def f12(x):
#     condition1 = (x < 0)
#     condition2 = (x >= 0) & (x < 3.9)
#     condition3 = (x >= 3.9) & (x < 4)
#     condition4 = (x >= 4)
#     y1 = 0  # 当x < 0时
#     y2 = np.exp(x * 4) - 1
#     y3 = (-10) * (np.exp(3.9 * 4) - 1) * (x - 4)
#     y4 = 0  # 当x >= 1时
#     y = np.where(condition1, y1, np.where(condition2, y2, np.where(condition3, y3, y4)))
#     return y
#



# 调用函数并传入两个分段函数

# myfunc= circle_convolution(f1,f3,1)
# circle_convolution(myfunc,f4,1)

# myfunc= circle_convolution(f1,f3,1)
# circle_convolution(myfunc,f7,1)
#
# myfunc = circle_convolution(f1,f10,3)
# circle_convolution(myfunc,f11,3)

# circle_convolution(f1,f10,4)

# index = 0
# myfunc = circle_convolution(f1,f7,1)
# index = 1
# myfunc = circle_convolution(myfunc,f7,1)
# index = 2
# myfunc = circle_convolution(myfunc,f7,1)
# index = 3
# myfunc = circle_convolution(myfunc,f7,1)
# index = 3
# myfunc = circle_convolution(myfunc,f7,1)

# symmetry = 0.8
# myfunc = circle_convolution(f1,f5,1)
# symmetry = 1.8
# myfunc = circle_convolution(myfunc,f5,1)
# symmetry = 2.8
# myfunc = circle_convolution(myfunc,f5,1)
# symmetry = 3.8
# myfunc = circle_convolution(myfunc,f5,1)
# symmetry = 3.8
# myfunc = circle_convolution(myfunc,f5,1)
# myfunc = circle_convolution(myfunc,f5,1)
# symmetry = 3.8
# myfunc = circle_convolution(myfunc,f5,1)
# symmetry = 3.8
# myfunc = circle_convolution(myfunc,f5,1)


