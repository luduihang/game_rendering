# dqn.py
import torch.nn as nn
import torch
import numpy as np

# 测试时的模型定义（必须与训练时一致！）
class DQN(torch.nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.fc1 = torch.nn.Linear(input_dim, 128)  # 保持与训练一致
        self.fc2 = torch.nn.Linear(128, 64)         # 保持与训练一致
        self.fc3 = torch.nn.Linear(64, output_dim)  # 保持与训练一致

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)


def select_action(state):

    state = torch.FloatTensor(state).unsqueeze(0)  # 添加batch维度
    with torch.no_grad():  # 禁用梯度计算
        q_values = model(state)
    return q_values.argmax().item()  # 选择Q值最大的动作

model = DQN(9, 6)  # 替换为你的模型参数
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.load_state_dict(torch.load('dqn_model_ep100.pth', map_location=device))
model.eval()  # 切换到评估模式（关闭dropout等训练专用层）

state = np.array([0.1, 0.105, 0.005, 1., 0., 0., 0., 0., 0.])
action = select_action(state)
print("Action:", action)