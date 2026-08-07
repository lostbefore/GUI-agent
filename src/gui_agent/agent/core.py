from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from gui_agent.models.base import VisionModel

from .json_utils import parse_json_response
from .planner import Plan, TaskPlanner

ACTION_SYSTEM_PROMPT = """You are a multimodal desktop GUI agent.
Inspect the screenshot and choose one safe atomic action. Return JSON only.
Allowed actions: click, double_click, context_open, type, press, hotkey, scroll, drag, wait, finish.
Schema: {"action":"click","step_id":1,"x":0,"y":0,"button":"left","text":"","key":"",
"keys":[],"start":[0,0],"end":[0,0],"amount":0,"duration":0,"reason":"..."}.
Coordinates must refer to the supplied screenshot. Use only visible GUI controls.
Never type shell, PowerShell, CMD, Python, or agent invocation commands.
When the task says Win+R, return hotkey with keys ["win","r"].
Use context_open only when the user explicitly asks to right-click a visible shortcut.
Choose finish only when the screenshot proves the user goal is complete.
If uncertain, choose wait."""


@dataclass(slots=True)
class AgentDecision:
    action: str
    reason: str = ""
    parameters: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {}


class DesktopAgent:
    allowed_actions = frozenset(
        {
            "click",
            "double_click",
            "context_open",
            "type",
            "press",
            "hotkey",
            "scroll",
            "drag",
            "wait",
            "finish",
        }
    )

    def __init__(self, model: VisionModel, planner: TaskPlanner | None = None) -> None:
        self.model = model
        self.planner = planner or TaskPlanner(model)
        self.last_response = ""

    def plan(
        self,
        goal: str,
        screenshot: str | Path | None = None,
        screen_context: str = "",
    ) -> Plan:
        return self.planner.plan(goal, screenshot, screen_context)

    @staticmethod
    def _normalize_action(
        action: str,
        parameters: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        key = parameters.get("key")
        if isinstance(key, str) and "+" in key:
            keys = [part.strip().lower() for part in key.split("+") if part.strip()]
            if len(keys) >= 2:
                normalized = {"keys": keys}
                if "step_id" in parameters:
                    normalized["step_id"] = parameters["step_id"]
                return "hotkey", normalized
        return action, parameters

    def decide(
        self,
        goal: str,
        plan: Plan,
        screenshot: str | Path,
        *,
        screen_context: str = "",
        history: Sequence[dict[str, Any]] = (),
    ) -> AgentDecision:
        try:
            elements: Any = json.loads(screen_context) if screen_context else []
        except json.JSONDecodeError:
            elements = screen_context
        context = json.dumps(
            {
                "goal": goal,
                "plan": [asdict(step) for step in plan.steps],
                "screen_elements": elements,
                "action_history": list(history),
            },
            ensure_ascii=False,
        )
        response = self.model.generate(
            f"Current task state:\n{context}", [screenshot], system_prompt=ACTION_SYSTEM_PROMPT
        )
        self.last_response = response.text
        payload, corrected = parse_json_response(self.model, response.text)
        if corrected is not None:
            self.last_response += f"\n\n--- corrected ---\n{corrected}"
        action = str(payload.pop("action", "")).lower()
        reason = str(payload.pop("reason", ""))
        action, payload = self._normalize_action(action, payload)
        if action not in self.allowed_actions:
            raise ValueError(f"Unsupported model action: {action}")
        return AgentDecision(action, reason, payload)

    def as_langchain_runnable(self):
        """封装规划接口"""
        try:
            from langchain_core.runnables import RunnableLambda
        except ImportError as error:
            raise ImportError(
                'Install agent dependencies with: pip install -e ".[agent]"'
            ) from error
        return RunnableLambda(lambda request: self.plan(str(request["goal"])))
