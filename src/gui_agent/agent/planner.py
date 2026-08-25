from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gui_agent.models.base import VisionModel

from .json_utils import is_likely_truncated, parse_json_response

PLANNER_SYSTEM_PROMPT = """You are a desktop task planner. Return JSON only.
Break the request into safe, observable, atomic GUI steps. Do not invent coordinates.
Use visible GUI controls only. Do not plan shell, terminal, or Python commands.
Preserve explicit keyboard shortcuts and their order exactly.
Do not replace requested hotkeys with icon clicks.
Do not add closing or cleanup steps unless the user requests them.
Keep descriptions concise and obey the requested maximum number of steps.
Schema: {"summary": "...", "steps": [{"id": 1, "description": "..."}]}"""


@dataclass(slots=True)
class PlanStep:
    id: int
    description: str
    status: str = "pending"


@dataclass(slots=True)
class Plan:
    goal: str
    summary: str
    steps: list[PlanStep] = field(default_factory=list)

    def next_pending_step(self) -> PlanStep | None:
        return next((step for step in self.steps if step.status == "pending"), None)


class TaskPlanner:
    def __init__(self, model: VisionModel, *, max_steps: int = 8) -> None:
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        self.model = model
        self.max_steps = max_steps
        self.last_response = ""
        self.used_fallback = False

    def plan(self, goal: str, screenshot: str | Path | None = None, screen_context: str = "") -> Plan:
        if not goal.strip():
            raise ValueError("goal must not be empty")
        prompt = f"User goal: {goal}\nMaximum steps: {self.max_steps}"
        if screen_context:
            prompt += f"\nCurrent screen elements:\n{screen_context}"
        response = self.model.generate(prompt, [screenshot] if screenshot else (), system_prompt=PLANNER_SYSTEM_PROMPT)
        self.last_response = response.text
        self.used_fallback = False
        if is_likely_truncated(response.text):
            self.used_fallback = True
            self.last_response += "\n\n--- fallback ---\ntruncated response"
            return Plan(goal, "\u4f7f\u7528\u7528\u6237\u76ee\u6807\u7ee7\u7eed\u6267\u884c", [PlanStep(1, goal)])
        try:
            payload, corrected = parse_json_response(self.model, response.text)
        except (TypeError, ValueError):
            self.used_fallback = True
            self.last_response += "\n\n--- fallback ---\ninvalid planner response"
            return Plan(goal, "\u4f7f\u7528\u7528\u6237\u76ee\u6807\u7ee7\u7eed\u6267\u884c", [PlanStep(1, goal)])
        if corrected is not None:
            self.last_response += f"\n\n--- corrected ---\n{corrected}"
        raw_steps = payload.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("Planner response must contain a non-empty steps list")
        steps = [
            PlanStep(int(step.get("id", index)), str(step.get("description", "")).strip(), "pending")
            for index, step in enumerate(raw_steps[: self.max_steps], 1)
            if isinstance(step, dict) and str(step.get("description", "")).strip()
        ]
        if not steps:
            raise ValueError("Planner returned no valid steps")
        return Plan(goal, str(payload.get("summary", goal)), steps)