import json

import pytest

from gui_agent.agent.core import DesktopAgent
from gui_agent.agent.json_utils import parse_json_object
from gui_agent.agent.planner import TaskPlanner
from gui_agent.models.base import ModelResponse


class QueueModel:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, prompt, images=(), *, system_prompt=None):
        self.calls.append((prompt, list(images), system_prompt))
        return ModelResponse(self.responses.pop(0), "fake")


def test_json_parser_accepts_fences_and_surrounding_text() -> None:
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('result: {"b": 2} done') == {"b": 2}
    with pytest.raises(ValueError, match="does not contain"):
        parse_json_object("nothing")
    with pytest.raises(TypeError, match="must be an object"):
        parse_json_object("[]")


def test_planner_builds_bounded_plan() -> None:
    response = json.dumps(
        {
            "summary": "Open settings",
            "steps": [
                {"id": 1, "description": "Open menu"},
                {"id": 2, "description": "Click settings"},
            ],
        }
    )
    model = QueueModel(response)
    plan = TaskPlanner(model, max_steps=1).plan("Open settings")
    assert plan.summary == "Open settings"
    assert len(plan.steps) == 1
    assert plan.steps[0].status == "pending"


def test_planner_resets_model_supplied_status_to_pending() -> None:
    response = json.dumps(
        {
            "summary": "Open settings",
            "steps": [
                {"id": 1, "description": "Open menu", "status": "completed"},
            ],
        }
    )
    plan = TaskPlanner(QueueModel(response)).plan("Open settings")
    assert plan.steps[0].status == "pending"


def test_planner_rejects_invalid_goal_and_steps() -> None:
    with pytest.raises(ValueError, match="goal"):
        TaskPlanner(QueueModel("{}")).plan(" ")
    with pytest.raises(ValueError, match="steps"):
        TaskPlanner(QueueModel("{}")).plan("task")


def test_agent_plans_and_decides(tmp_path) -> None:
    model = QueueModel(
        '{"summary":"demo","steps":[{"id":1,"description":"click"}]}',
        '{"action":"click","x":20,"y":30,"reason":"button found"}',
    )
    agent = DesktopAgent(model)
    plan = agent.plan("demo")
    decision = agent.decide("demo", plan, tmp_path / "screen.png")
    assert decision.action == "click"
    assert decision.parameters == {"x": 20, "y": 30}
    assert model.calls[-1][1] == [tmp_path / "screen.png"]


def test_agent_rejects_unsupported_action(tmp_path) -> None:
    model = QueueModel('{"action":"delete_system","reason":"bad"}')
    agent = DesktopAgent(model)
    plan = TaskPlanner(QueueModel('{"steps":[{"id":1,"description":"wait"}]}')).plan("demo")
    with pytest.raises(ValueError, match="Unsupported"):
        agent.decide("demo", plan, tmp_path / "screen.png")
