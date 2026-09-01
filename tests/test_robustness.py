import json

import numpy as np

from gui_agent.agent import AgentDecision, Plan, PlanStep
from gui_agent.coordinates import Box, CoordinateMapper
from gui_agent.perception import DesktopPerception, UIElement
from gui_agent.runtime import ActionResult, GUIAgentRuntime, RetryPolicy, ScreenStateChecker
from gui_agent.screen import ScreenFrame


class SequencePerception:
    def __init__(self, values: list[int]) -> None:
        self.values = iter(values)
        self.capture_count = 0
        self.last_metrics = {"raw_elements": 0, "elements": 0, "elapsed_ms": 0.1}

    def capture(self, **kwargs):
        self.capture_count += 1
        value = next(self.values)
        image = np.full((40, 60, 3), value, dtype=np.uint8)
        return ScreenFrame(image, CoordinateMapper(60, 40, 60, 40))

    def analyze(self, frame):
        return []

    def save_annotated(self, frame, elements, output):
        raise AssertionError("no annotations expected")


class QueueAgent:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.last_response = ""
        self.planner = type("Planner", (), {"last_response": "", "used_fallback": False})()
        self.histories = []

    def plan(self, goal, screenshot, context):
        return Plan(goal, "test", [PlanStep(1, "first"), PlanStep(2, "finish")])

    def decide(self, goal, plan, screenshot, *, screen_context, history):
        self.histories.append(list(history))
        return self.decisions.pop(0)


class OutcomeExecutor:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def execute(self, decision, mapper):
        success = next(self.outcomes)
        self.calls.append(decision.action)
        return ActionResult(
            decision.action, success, "ok" if success else "not ready", decision.parameters
        )


def test_retry_policy_limits_failures_and_never_retries_finish() -> None:
    policy = RetryPolicy(max_retries=1, retry_delay=0)
    failure = ActionResult("click", False, "failed")
    assert policy.should_retry(AgentDecision("click"), failure, 1) is True
    assert policy.should_retry(AgentDecision("click"), failure, 2) is False
    assert policy.should_retry(AgentDecision("finish"), failure, 1) is False


def test_screen_state_checker_detects_changed_and_same_frames() -> None:
    mapper = CoordinateMapper(4, 4, 4, 4)
    dark = ScreenFrame(np.zeros((4, 4, 3), dtype=np.uint8), mapper)
    bright = ScreenFrame(np.full((4, 4, 3), 30, dtype=np.uint8), mapper)
    checker = ScreenStateChecker(threshold=5)
    assert checker.compare(dark, dark).changed is False
    changed = checker.compare(dark, bright)
    assert changed.changed is True
    assert changed.score == 30


def test_runtime_recaptures_and_redecides_after_failed_action(tmp_path) -> None:
    agent = QueueAgent(
        [
            AgentDecision("click", parameters={"x": 25, "y": 25, "step_id": 1}),
            AgentDecision("click", parameters={"x": 26, "y": 26, "step_id": 1}),
            AgentDecision("finish", parameters={"step_id": 2}),
        ]
    )
    perception = SequencePerception([0, 12, 12])
    executor = OutcomeExecutor([False, True, True])
    waits = []
    runtime = GUIAgentRuntime(
        agent,
        perception,
        executor,
        artifact_dir=tmp_path,
        action_delay=0,
        max_retries=1,
        retry_delay=0.2,
        sleeper=waits.append,
    )
    report = runtime.run("retry task", execute=True)
    assert report.status == "completed"
    assert [(event.index, event.attempt, event.result.success) for event in report.events] == [
        (1, 1, False),
        (1, 2, True),
        (2, 1, True),
    ]
    assert perception.capture_count == 3
    assert waits == [0.2]
    assert (tmp_path / "step-01-retry-1.png").exists()
    progress = [
        json.loads(line)
        for line in (tmp_path / "progress.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert {"retrying", "state_checked", "perception_finished"}.issubset(
        {item["stage"] for item in progress}
    )
    assert (tmp_path / "progress.log").exists()


def test_perception_removes_overlapping_duplicate_elements(monkeypatch) -> None:
    perception = DesktopPerception(ocr_reader=object(), deduplicate_iou=0.7)
    text = UIElement(Box(0, 0, 20, 20), "text", "Save", 0.9)
    duplicate_text = UIElement(Box(1, 1, 21, 21), "text", " save ", 0.8)
    region = UIElement(Box(30, 0, 60, 20), "region")
    duplicate_region = UIElement(Box(31, 1, 61, 21), "region")
    monkeypatch.setattr(perception, "recognize_text", lambda frame: [text, duplicate_text])
    monkeypatch.setattr(perception, "detect_ui_regions", lambda frame: [region, duplicate_region])
    frame = ScreenFrame(np.zeros((70, 70, 3), dtype=np.uint8), CoordinateMapper(70, 70, 70, 70))
    result = perception.analyze(frame)
    assert result == [text, region]
    assert perception.last_metrics["raw_elements"] == 4
    assert perception.last_metrics["elements"] == 2
