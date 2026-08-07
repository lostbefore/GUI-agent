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


def test_json_parser_repairs_missing_and_trailing_commas() -> None:
    missing = '{\n"action": "click"\n"x": 20,\n"y": 30\n}'
    trailing = '{"action": "finish",}'
    assert parse_json_object(missing) == {"action": "click", "x": 20, "y": 30}
    assert parse_json_object(trailing) == {"action": "finish"}


def test_json_parser_repairs_inner_quotes() -> None:
    malformed = '{"description":"在搜索框中输入"必应"并搜索","status":"pending"}'
    assert parse_json_object(malformed) == {
        "description": '在搜索框中输入"必应"并搜索',
        "status": "pending",
    }


def test_agent_retries_unrepairable_json(tmp_path) -> None:
    model = QueueModel(
        '{"summary":"demo","steps":[{"id":1,"description":"click"}]}',
        "not json",
        '{"action":"click","x":20,"y":30,"reason":"corrected"}',
    )
    agent = DesktopAgent(model)
    plan = agent.plan("demo")
    decision = agent.decide("demo", plan, tmp_path / "screen.png")
    assert decision.action == "click"
    assert decision.parameters == {"x": 20, "y": 30}
    assert "corrected" in agent.last_response


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


def test_planner_falls_back_when_json_stays_truncated() -> None:
    model = QueueModel('{"summary":"cut', '{"summary":"still cut')
    planner = TaskPlanner(model)
    plan = planner.plan("打开浏览器")
    assert planner.used_fallback is True
    assert plan.summary == "使用用户目标继续执行"
    assert plan.steps[0].description == "打开浏览器"
    assert "fallback" in planner.last_response
    assert len(model.calls) == 1


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


def test_planner_uses_initial_screenshot_context() -> None:
    model = QueueModel('{"summary":"demo","steps":[{"id":1,"description":"click"}]}')
    plan = TaskPlanner(model).plan("demo", "screen.png", '[{"text":"确定"}]')
    assert plan.goal == "demo"
    assert model.calls[0][1] == ["screen.png"]
    assert "确定" in model.calls[0][0]


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
    decision = agent.decide(
        "demo",
        plan,
        tmp_path / "screen.png",
        screen_context='[{"text":"button"}]',
        history=[{"action": "wait", "success": True}],
    )
    assert decision.action == "click"
    assert decision.parameters == {"x": 20, "y": 30}
    assert model.calls[-1][1] == [tmp_path / "screen.png"]
    assert "button" in model.calls[-1][0]
    assert "wait" in model.calls[-1][0]


def test_agent_rejects_unsupported_action(tmp_path) -> None:
    model = QueueModel('{"action":"delete_system","reason":"bad"}')
    agent = DesktopAgent(model)
    plan = TaskPlanner(QueueModel('{"steps":[{"id":1,"description":"wait"}]}')).plan("demo")
    with pytest.raises(ValueError, match="Unsupported"):
        agent.decide("demo", plan, tmp_path / "screen.png")


def test_agent_accepts_context_open(tmp_path) -> None:
    model = QueueModel('{"action":"context_open","x":20,"y":30,"reason":"打开快捷方式"}')
    agent = DesktopAgent(model)
    plan = TaskPlanner(QueueModel('{"steps":[{"id":1,"description":"打开"}]}')).plan(
        "打开 Edge"
    )
    decision = agent.decide("打开 Edge", plan, tmp_path / "screen.png")
    assert decision.action == "context_open"
    assert decision.parameters == {"x": 20, "y": 30}


def test_agent_normalizes_combined_hotkey_field(tmp_path) -> None:
    model = QueueModel(
        '{"action":"context_open","step_id":1,"x":10,"y":10,"key":"win+r"}'
    )
    agent = DesktopAgent(model)
    plan = TaskPlanner(QueueModel('{"steps":[{"id":1,"description":"打开运行"}]}')).plan(
        "按Win+R"
    )
    decision = agent.decide("按Win+R", plan, tmp_path / "screen.png")
    assert decision.action == "hotkey"
    assert decision.parameters == {"keys": ["win", "r"], "step_id": 1}
