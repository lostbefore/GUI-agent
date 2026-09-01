from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from gui_agent.agent import AgentDecision
from gui_agent.screen import ScreenFrame

from .executor import ActionResult


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """失败后的安全重试规则"""

    max_retries: int = 2
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must not be negative")

    def should_retry(self, decision: AgentDecision, result: ActionResult, attempt: int) -> bool:
        """只对未执行成功的普通动作重新感知并决策"""
        return not result.success and decision.action != "finish" and attempt <= self.max_retries


@dataclass(frozen=True, slots=True)
class ScreenChange:
    changed: bool
    score: float


class ScreenStateChecker:
    """比较连续截图的视觉变化"""

    def __init__(self, *, threshold: float = 3.0) -> None:
        if threshold < 0:
            raise ValueError("threshold must not be negative")
        self.threshold = threshold

    def compare(self, before: ScreenFrame, after: ScreenFrame) -> ScreenChange:
        before_image = before.image
        after_image = after.image
        if before_image.shape[:2] != after_image.shape[:2]:
            return ScreenChange(True, 255.0)
        first = cv2.cvtColor(before_image, cv2.COLOR_BGR2GRAY)
        second = cv2.cvtColor(after_image, cv2.COLOR_BGR2GRAY)
        score = float(np.mean(cv2.absdiff(first, second)))
        return ScreenChange(score >= self.threshold, score)
