from __future__ import annotations

import re
from dataclasses import dataclass

from gui_agent.agent import AgentDecision


class UnsafeActionError(ValueError):
    """动作风险异常"""


@dataclass(frozen=True, slots=True)
class ActionPolicy:
    """动作安全策略"""

    block_terminal_text: bool = True
    max_text_length: int = 2000

    _terminal_patterns = (
        re.compile(r"\bpowershell(?:\.exe)?\b", re.IGNORECASE),
        re.compile(r"\bcmd(?:\.exe)?\b", re.IGNORECASE),
        re.compile(r"\bpython(?:\.exe)?\s+--?m\b", re.IGNORECASE),
        re.compile(r"\bgui_agent\.runtime\.cli\b", re.IGNORECASE),
        re.compile(r"\bgui-agent-v1\b", re.IGNORECASE),
        re.compile(r"\bstart-process\b", re.IGNORECASE),
    )

    def __post_init__(self) -> None:
        if self.max_text_length <= 0:
            raise ValueError("max_text_length must be positive")

    def validate(self, decision: AgentDecision) -> None:
        parameters = decision.parameters or {}
        if decision.action in {"click", "double_click", "context_open"}:
            x = parameters.get("x")
            y = parameters.get("y")
            if isinstance(x, (int, float)) and isinstance(y, (int, float)) and x <= 20 and y <= 20:
                raise UnsafeActionError("动作位于左上角保护区")
        if decision.action != "type":
            return
        text = parameters.get("text")
        if not isinstance(text, str) or not text:
            return
        if len(text) > self.max_text_length:
            raise UnsafeActionError("输入文本超过安全长度")
        if self.block_terminal_text and any(
            pattern.search(text) for pattern in self._terminal_patterns
        ):
            raise UnsafeActionError("检测到终端或项目自调用文本")
