import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from gui_agent.agent import AgentDecision, Plan, PlanStep
from gui_agent.coordinates import Box, CoordinateMapper
from gui_agent.perception import UIElement
from gui_agent.runtime import ActionResult, GUIAgentRuntime
from gui_agent.screen import ScreenFrame


class FakePerception:
    def __init__(self, width=200, height=100) -> None:
        self.width = width
        self.height = height
        self.capture_calls = []

    def capture(self, **kwargs):
        self.capture_calls.append(kwargs)
        image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        mapper = CoordinateMapper(self.width, self.height, self.width * 2, self.height * 2)
        return ScreenFrame(image, mapper)

    def analyze(self, frame):
        return [UIElement(Box(20, 20, 60, 50), "text", "按钮", 0.95)]

    def save_annotated(self, frame, elements, output):
        assert elements
        cv2.imwrite(str(output), frame.image)
        return output


class FakeAgent:
    def __init__(self, decisions) -> None:
        self.decisions = list(decisions)
        self.plan_calls = []
        self.decide_calls = []
        self.last_response = ""

    def plan(self, goal, screenshot=None, screen_context=""):
        self.plan_calls.append((goal, screenshot, screen_context))
        return Plan(goal, "测试计划", [PlanStep(1, "执行任务")])

    def decide(self, goal, plan, screenshot, *, screen_context="", history=()):
        self.decide_calls.append((goal, screenshot, screen_context, list(history)))
        return self.decisions.pop(0)


class FakeExecutor:
    def __init__(self, *, fail=False) -> None:
        self.fail = fail
        self.calls = []

    def execute(self, decision, mapper):
        self.calls.append((decision, mapper))
        return ActionResult(
            decision.action,
            not self.fail,
            "失败" if self.fail else "成功",
            decision.parameters or {},
        )


def make_runtime(tmp_path, decisions, **kwargs):
    agent = FakeAgent(decisions)
    perception = FakePerception()
    executor = FakeExecutor(fail=kwargs.pop("fail", False))
    waits = []
    runtime = GUIAgentRuntime(
        agent,
        perception,
        executor,
        artifact_dir=tmp_path,
        action_delay=kwargs.pop("action_delay", 0),
        sleeper=waits.append,
        **kwargs,
    )
    return runtime, agent, perception, executor, waits


def test_preview_captures_and_decides_without_execution(tmp_path) -> None:
    runtime, agent, perception, executor, _ = make_runtime(
        tmp_path, [AgentDecision("click", parameters={"x": 30, "y": 30})]
    )
    report = runtime.run("打开浏览器")
    assert report.status == "preview"
    assert report.mode == "preview"
    assert len(report.events) == 1
    assert executor.calls == []
    assert perception.capture_calls == [{"scale": 1.0}]
    assert agent.plan_calls[0][1].endswith("step-00.png")
    assert (tmp_path / "step-00.png").exists()
    assert (tmp_path / "step-00-annotated.png").exists()
    assert (tmp_path / "report.json").exists()


def test_runtime_saves_model_response(tmp_path) -> None:
    runtime, agent, _, _, _ = make_runtime(
        tmp_path,
        [AgentDecision("finish")],
    )
    agent.last_response = '{"action":"finish"}'
    runtime.run("检查状态")
    assert (tmp_path / "step-01-response.txt").read_text(encoding="utf-8") == agent.last_response


def test_runtime_saves_invalid_decision_response(tmp_path) -> None:
    runtime, agent, _, _, _ = make_runtime(
        tmp_path,
        [AgentDecision("finish")],
    )
    agent.last_response = "invalid json"

    def fail(*args, **kwargs):
        raise ValueError("invalid response")

    agent.decide = fail
    with pytest.raises(ValueError, match="invalid response"):
        runtime.run("检查状态")
    assert (tmp_path / "step-01-response.txt").read_text(encoding="utf-8") == "invalid json"


def test_runtime_saves_invalid_plan_response(tmp_path) -> None:
    runtime, agent, _, _, _ = make_runtime(
        tmp_path,
        [AgentDecision("finish")],
    )
    agent.planner = SimpleNamespace(last_response="invalid plan")

    def fail(*args, **kwargs):
        raise ValueError("invalid plan")

    agent.plan = fail
    with pytest.raises(ValueError, match="invalid plan"):
        runtime.run("检查状态")
    assert (tmp_path / "plan-response.txt").read_text(encoding="utf-8") == "invalid plan"


def test_runtime_saves_invalid_execute_response(tmp_path) -> None:
    runtime, agent, _, _, _ = make_runtime(
        tmp_path,
        [AgentDecision("finish")],
    )
    agent.last_response = "invalid action"

    def fail(*args, **kwargs):
        raise ValueError("invalid action")

    agent.decide = fail
    with pytest.raises(ValueError, match="invalid action"):
        runtime.run("检查状态", execute=True)
    assert (tmp_path / "step-01-response.txt").read_text(encoding="utf-8") == "invalid action"


def test_execute_closes_loop_and_returns_feedback(tmp_path) -> None:
    decisions = [
        AgentDecision("click", parameters={"x": 30, "y": 30, "step_id": 1}),
        AgentDecision("finish", "已完成"),
    ]
    runtime, agent, perception, executor, _ = make_runtime(tmp_path, decisions)
    report = runtime.run("搜索内容", execute=True)
    assert report.status == "completed"
    assert [event.decision.action for event in report.events] == ["click", "finish"]
    assert len(executor.calls) == 2
    assert len(perception.capture_calls) == 2
    assert agent.decide_calls[1][3][0]["action"] == "click"
    assert report.plan.steps[0].status == "completed"
    progress = [
        json.loads(line)
        for line in (tmp_path / "progress.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    stages = [event["stage"] for event in progress]
    assert stages[0] == "starting"
    assert "planning" in stages
    assert "action_finished" in stages
    assert stages[-1] == "finished"


def test_execute_stops_after_action_failure(tmp_path) -> None:
    runtime, _, perception, executor, _ = make_runtime(
        tmp_path,
        [AgentDecision("click", parameters={"x": 30, "y": 30})],
        fail=True,
    )
    report = runtime.run("打开文件", execute=True)
    assert report.status == "failed"
    assert len(report.events) == 1
    assert len(perception.capture_calls) == 1
    assert len(executor.calls) == 1


def test_execute_stops_at_action_limit(tmp_path) -> None:
    runtime, _, _, _, _ = make_runtime(
        tmp_path,
        [AgentDecision("wait"), AgentDecision("wait")],
        max_actions=2,
    )
    report = runtime.run("等待页面", execute=True)
    assert report.status == "limit_reached"
    assert len(report.events) == 2


def test_execute_applies_action_delay(tmp_path) -> None:
    runtime, _, _, _, waits = make_runtime(
        tmp_path,
        [AgentDecision("click"), AgentDecision("finish")],
        action_delay=0.25,
    )
    report = runtime.run("打开浏览器", execute=True)
    assert report.status == "completed"
    assert waits == [0.25]


def test_observation_resizes_screen_and_serializes_elements(tmp_path) -> None:
    runtime, agent, _, _, _ = make_runtime(
        tmp_path,
        [AgentDecision("finish")],
        max_screen_pixels=5_000,
    )
    report = runtime.run("查看屏幕")
    image = cv2.imread(report.events[0].screenshot)
    context = json.loads(agent.plan_calls[0][2])
    assert image.shape[:2] == (50, 100)
    assert context == [{"kind": "text", "text": "按钮", "confidence": 0.95, "box": [5, 5, 15, 12]}]


def test_observation_reports_screenshot_write_failure(tmp_path, monkeypatch) -> None:
    runtime, _, _, _, _ = make_runtime(tmp_path, [AgentDecision("finish")])
    monkeypatch.setattr(cv2, "imwrite", lambda *args: False)
    with pytest.raises(OSError, match="screenshot"):
        runtime.run("查看屏幕")


@pytest.mark.parametrize(
    ("goal", "decisions", "actions"),
    [
        (
            "打开浏览器",
            [
                AgentDecision("hotkey", parameters={"keys": ["win", "r"]}),
                AgentDecision("type", parameters={"text": "msedge"}),
                AgentDecision("press", parameters={"key": "enter"}),
                AgentDecision("finish"),
            ],
            ["hotkey", "type", "press", "finish"],
        ),
        (
            "搜索指定内容",
            [
                AgentDecision("click", parameters={"x": 50, "y": 20}),
                AgentDecision("type", parameters={"text": "GUI Agent"}),
                AgentDecision("press", parameters={"key": "enter"}),
                AgentDecision("finish"),
            ],
            ["click", "type", "press", "finish"],
        ),
        (
            "打开指定文件",
            [
                AgentDecision("hotkey", parameters={"keys": ["ctrl", "o"]}),
                AgentDecision("type", parameters={"text": "C:/demo.txt"}),
                AgentDecision("press", parameters={"key": "enter"}),
                AgentDecision("finish"),
            ],
            ["hotkey", "type", "press", "finish"],
        ),
        (
            "发送消息",
            [
                AgentDecision("click", parameters={"x": 50, "y": 40}),
                AgentDecision("type", parameters={"text": "hello"}),
                AgentDecision("press", parameters={"key": "enter"}),
                AgentDecision("finish"),
            ],
            ["click", "type", "press", "finish"],
        ),
        (
            "关闭应用",
            [
                AgentDecision("hotkey", parameters={"keys": ["alt", "f4"]}),
                AgentDecision("finish"),
            ],
            ["hotkey", "finish"],
        ),
    ],
)
def test_five_basic_desktop_tasks_complete(tmp_path, goal, decisions, actions) -> None:
    runtime, _, _, _, _ = make_runtime(
        tmp_path / str(len(goal)),
        decisions,
    )
    report = runtime.run(goal, execute=True)
    assert report.status == "completed"
    assert [event.decision.action for event in report.events] == actions


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_actions": 0},
        {"capture_scale": 0},
        {"max_screen_pixels": 0},
        {"max_elements": -1},
        {"action_delay": -1},
    ],
)
def test_runtime_rejects_invalid_configuration(tmp_path, kwargs) -> None:
    with pytest.raises(ValueError):
        make_runtime(tmp_path, [AgentDecision("finish")], **kwargs)


def test_runtime_rejects_empty_goal(tmp_path) -> None:
    runtime, _, _, _, _ = make_runtime(tmp_path, [AgentDecision("finish")])
    with pytest.raises(ValueError, match="goal"):
        runtime.run(" ")


def test_preview_blocks_terminal_command_text(tmp_path) -> None:
    runtime, _, _, executor, _ = make_runtime(
        tmp_path,
        [
            AgentDecision(
                "type",
                parameters={"text": "powershell\npython -m gui_agent.runtime.cli"},
            )
        ],
    )
    report = runtime.run("打开浏览器")
    assert report.status == "blocked"
    assert report.events[0].result.success is False
    assert "安全策略" in report.events[0].result.message
    assert executor.calls == []


def test_execute_blocks_terminal_command_before_controller(tmp_path) -> None:
    runtime, _, _, executor, _ = make_runtime(
        tmp_path,
        [AgentDecision("type", parameters={"text": "cmd.exe /c calc"})],
    )
    report = runtime.run("打开计算器", execute=True)
    assert report.status == "blocked"
    assert executor.calls == []
