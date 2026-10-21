"""智能体统一接口。

约定：
- ``act(observation, legal_actions)`` 返回**一定在** legal_actions 内的动作
- ``observe(transition)`` 接收一条经验（无学习能力的实现可忽略）
- ``reset()`` 清理每局状态
- ``save(path)`` / ``load(path)`` 持久化
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True)
class Transition:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool


class BaseAgent(ABC):
    """所有智能体的基类。子类必须实现 act()，其余有默认实现。"""

    name: str = "agent"

    @abstractmethod
    def act(self, observation: Any, legal_actions: Sequence[int]) -> int:
        raise NotImplementedError

    def observe(self, transition: Transition) -> None:
        """默认：无学习能力，忽略经验。"""

    def reset(self) -> None:
        """默认：无每局状态。"""

    def save(self, path) -> None:
        raise NotImplementedError(f"{type(self).__name__} 不支持 save()")

    def load(self, path) -> None:
        raise NotImplementedError(f"{type(self).__name__} 不支持 load()")

    @staticmethod
    def _pick_legal(action: int, legal_actions: Sequence[int]) -> int:
        legal = list(legal_actions)
        if not legal:
            raise ValueError("legal_actions 为空，无法行动")
        if action in legal:
            return action
        # 兜底：取最接近的合法动作，保证接口不违约
        return min(legal, key=lambda a: abs(a - action))
