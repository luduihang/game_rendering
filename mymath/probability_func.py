import numpy as np
import math
from .func_const import *
import matplotlib.pyplot as plt

from scipy.signal import convolve

def convolution_of_functions(f1, f2):
    # 减少采样点
    x = np.linspace(-5, 5, 1000)

    # 计算两个函数的样本点
    f1_samples = f1(x)
    f2_samples = f2(x)

    # 使用 scipy.signal.convolve 计算卷积
    convolved_samples = convolve(f2_samples, f1_samples, mode='same') * (x[1] - x[0])

    # 线性变换
    nonzero_indices = np.nonzero(convolved_samples)[0]
    min_x = x[nonzero_indices[0]]
    max_x = x[nonzero_indices[-1]]

    convolved_samples_normalized = (x - min_x) / (max_x - min_x)

    # 归一化卷积结果为概率密度函数
    normalization_factor = np.trapezoid(convolved_samples, convolved_samples_normalized)
    pdf_final = convolved_samples / normalization_factor

    # 计算均值
    mean_value = np.trapezoid(convolved_samples_normalized * pdf_final, convolved_samples_normalized)

    def pdf_function(x_values):
        return np.interp(x_values, convolved_samples_normalized, pdf_final)

    return pdf_function

def circle_convolution(func1, func2, num):
    # 缓存卷积结果
    func_buffer = convolution_of_functions(func1, func2)
    for _ in range(num - 1):
        func_buffer = convolution_of_functions(func_buffer, func2)
    return func_buffer

def integral_func(pdf,up_limit):
    x_values = np.linspace(0, up_limit, 1000)  # 在0到0.8之间创建更密集的点
    pdf_values = pdf(x_values)
    integral_value = np.trapezoid(pdf_values, x_values)
    # print("积分的返回值是:",integral_value)
    return integral_value

def mean_func(pdf):
    x_values = np.linspace(0,1,2000)
    pdf_values = pdf(x_values)
    mean_value = np.trapezoid(x_values * pdf_values, x_values)
    return mean_value

def switch_func(func1, conv):
    convolved = circle_convolution(func1, conv.weight_conv, 1)
    x = np.linspace(0, 1, 1000)
    integral = np.trapezoid(convolved(x), x)
    return lambda x: convolved(x) / integral if integral !=0 else convolved(x)

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
    # print(mapping_dict)  # array1到array2的映射
    # print(reverse_mapping_dict)  # array2到array1的反向映射

    mapping_dict_arr[0] = mapping_dict
    mapping_dict_arr[1] = reverse_mapping_dict
    # 使用反向映射字典查找array1中的元素
    element_in_array2 = '1'
    corresponding_element_in_array1 = reverse_mapping_dict.get(element_in_array2, None)
    # print(f"Element in array1 corresponding to '{element_in_array2}' in array2 is: {corresponding_element_in_array1}")
    return mapping_dict_arr




