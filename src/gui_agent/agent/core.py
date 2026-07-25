from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from gui_agent.models.base import VisionModel

from .json_utils import parse_json_object
from .planner import Plan, TaskPlanner

ACTION_SYSTEM_PROMPT = """You are a multimodal desktop GUI agent.
Inspect the screenshot and choose one safe atomic action. Return JSON only.
Allowed actions: click, double_click, type, press, hotkey, scroll, drag, wait, finish.
Schema: {"action":"click","x":0,"y":0,"text":"","keys":[],
"start":[0,0],"end":[0,0],"amount":0,"reason":"..."}.
Coordinates must refer to the supplied screenshot. If uncertain, choose wait."""


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

    def plan(self, goal: str) -> Plan:
        return self.planner.plan(goal)

    def decide(self, goal: str, plan: Plan, screenshot: str | Path) -> AgentDecision:
        context = json.dumps(
            {"goal": goal, "plan": [asdict(step) for step in plan.steps]}, ensure_ascii=False
        )
        response = self.model.generate(
            f"Current task state:\n{context}", [screenshot], system_prompt=ACTION_SYSTEM_PROMPT
        )
        payload = parse_json_object(response.text)
        action = str(payload.pop("action", "")).lower()
        reason = str(payload.pop("reason", ""))
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
