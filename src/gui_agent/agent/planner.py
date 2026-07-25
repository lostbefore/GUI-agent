from __future__ import annotations

from dataclasses import dataclass, field

from gui_agent.models.base import VisionModel

from .json_utils import parse_json_object

PLANNER_SYSTEM_PROMPT = """You are a desktop task planner. Return JSON only.
Break the request into safe, observable, atomic GUI steps. Do not invent coordinates.
Schema: {"summary": "...", "steps": [{"id": 1, "description": "...", "status": "pending"}]}"""


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


class TaskPlanner:
    def __init__(self, model: VisionModel, *, max_steps: int = 6) -> None:
        self.model = model
        self.max_steps = max_steps

    def plan(self, goal: str) -> Plan:
        if not goal.strip():
            raise ValueError("goal must not be empty")
        response = self.model.generate(
            f"User goal: {goal}\nMaximum steps: {self.max_steps}",
            system_prompt=PLANNER_SYSTEM_PROMPT,
        )
        payload = parse_json_object(response.text)
        raw_steps = payload.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("Planner response must contain a non-empty steps list")
        steps = [
            PlanStep(
                int(step.get("id", index)),
                str(step.get("description", "")).strip(),
                "pending",
            )
            for index, step in enumerate(raw_steps[: self.max_steps], 1)
            if isinstance(step, dict) and str(step.get("description", "")).strip()
        ]
        if not steps:
            raise ValueError("Planner returned no valid steps")
        return Plan(goal, str(payload.get("summary", goal)), steps)
