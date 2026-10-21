"""agents —— 智能体层（DQN 策略 + Robot2 对手策略）。

对外接口见 ``base.BaseAgent``。本层不依赖 pygame，可无头运行。
"""

from agents.base import BaseAgent, Transition
from agents.dqn import DQN, DQNAgent, DQNConfig, StateEncoder, checkpoint_dims
from agents.robot import Robot, RobotConfig

__all__ = [
    "BaseAgent",
    "Transition",
    "DQN",
    "DQNConfig",
    "DQNAgent",
    "StateEncoder",
    "checkpoint_dims",
    "Robot",
    "RobotConfig",
]
