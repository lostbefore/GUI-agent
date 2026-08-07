import pytest

from gui_agent.agent import AgentDecision
from gui_agent.coordinates import CoordinateMapper
from gui_agent.runtime import ActionExecutor


class RecordingController:
    def __init__(self) -> None:
        self.calls = []

    def click(self, *args, **kwargs) -> None:
        self.calls.append(("click", args, kwargs))

    def write(self, *args, **kwargs) -> None:
        self.calls.append(("write", args, kwargs))

    def press(self, *args, **kwargs) -> None:
        self.calls.append(("press", args, kwargs))

    def hotkey(self, *args) -> None:
        self.calls.append(("hotkey", args, {}))

    def scroll(self, *args, **kwargs) -> None:
        self.calls.append(("scroll", args, kwargs))

    def drag(self, *args, **kwargs) -> None:
        self.calls.append(("drag", args, kwargs))


def make_executor():
    controller = RecordingController()
    waits = []
    executor = ActionExecutor(controller, sleeper=waits.append, max_wait=5)
    mapper = CoordinateMapper(100, 50, 200, 100, 10, 20)
    return executor, controller, waits, mapper


def test_click_actions_map_screenshot_coordinates() -> None:
    executor, controller, _, mapper = make_executor()
    first = executor.execute(AgentDecision("click", parameters={"x": 25, "y": 10}), mapper)
    second = executor.execute(
        AgentDecision("double_click", parameters={"x": 50, "y": 20, "button": "right"}),
        mapper,
    )
    assert first.success and second.success
    assert controller.calls == [
        ("click", (60, 40), {"button": "left", "clicks": 1}),
        ("click", (110, 60), {"button": "right", "clicks": 2}),
    ]


def test_context_open_uses_right_click_and_enter() -> None:
    executor, controller, _, mapper = make_executor()
    result = executor.execute(
        AgentDecision("context_open", parameters={"x": 25, "y": 10}),
        mapper,
    )
    assert result.success
    assert controller.calls == [
        ("click", (60, 40), {"button": "right", "clicks": 1}),
        ("press", ("enter",), {"presses": 1}),
    ]


def test_context_open_rejects_keyboard_parameters() -> None:
    executor, controller, _, mapper = make_executor()
    result = executor.execute(
        AgentDecision(
            "context_open",
            parameters={"x": 25, "y": 10, "key": "win+r"},
        ),
        mapper,
    )
    assert result.success is False
    assert controller.calls == []


def test_keyboard_actions_are_dispatched() -> None:
    executor, controller, _, mapper = make_executor()
    executor.execute(AgentDecision("type", parameters={"text": "hello", "interval": 0.1}), mapper)
    executor.execute(AgentDecision("press", parameters={"key": "enter", "presses": 2}), mapper)
    executor.execute(AgentDecision("hotkey", parameters={"keys": ["ctrl", "a"]}), mapper)
    assert controller.calls == [
        ("write", ("hello",), {"interval": 0.1}),
        ("press", ("enter",), {"presses": 2}),
        ("hotkey", ("ctrl", "a"), {}),
    ]


def test_scroll_and_drag_are_dispatched() -> None:
    executor, controller, _, mapper = make_executor()
    executor.execute(AgentDecision("scroll", parameters={"amount": -3}), mapper)
    executor.execute(AgentDecision("scroll", parameters={"amount": 2, "x": 10, "y": 5}), mapper)
    executor.execute(
        AgentDecision(
            "drag",
            parameters={"start": [0, 0], "end": [99, 49], "duration": 0.8},
        ),
        mapper,
    )
    assert controller.calls == [
        ("scroll", (-3,), {}),
        ("scroll", (2,), {"x": 30, "y": 30}),
        ("drag", ((10, 20), (208, 118)), {"duration": 0.8, "button": "left"}),
    ]


def test_wait_and_finish_do_not_use_controller() -> None:
    executor, controller, waits, mapper = make_executor()
    waited = executor.execute(AgentDecision("wait", parameters={"duration": 1.5}), mapper)
    finished = executor.execute(AgentDecision("finish"), mapper)
    assert waited.success and finished.success
    assert waits == [1.5]
    assert controller.calls == []


def test_invalid_action_parameters_return_failure() -> None:
    executor, _, _, mapper = make_executor()
    decisions = [
        AgentDecision("click", parameters={"x": 101, "y": 0}),
        AgentDecision("type", parameters={"text": ""}),
        AgentDecision("press", parameters={}),
        AgentDecision("hotkey", parameters={"keys": []}),
        AgentDecision("wait", parameters={"duration": 6}),
        AgentDecision("unknown"),
    ]
    assert all(not executor.execute(decision, mapper).success for decision in decisions)


def test_executor_rejects_invalid_wait_limit() -> None:
    with pytest.raises(ValueError, match="max_wait"):
        ActionExecutor(RecordingController(), max_wait=-1)


def test_executor_rejects_missing_and_malformed_points() -> None:
    executor, _, _, mapper = make_executor()
    decisions = [
        AgentDecision("click", parameters={}),
        AgentDecision("drag", parameters={"start": "bad", "end": [1, 1]}),
    ]
    assert all(not executor.execute(decision, mapper).success for decision in decisions)


def test_executor_converts_pyautogui_failsafe_to_failure() -> None:
    executor, controller, _, mapper = make_executor()
    failsafe = type("FailSafeException", (Exception,), {"__module__": "pyautogui"})

    def fail(*args, **kwargs):
        raise failsafe("failsafe triggered")

    controller.click = fail
    result = executor.execute(
        AgentDecision("click", parameters={"x": 10, "y": 10}),
        mapper,
    )
    assert result.success is False
    assert "failsafe" in result.message


def test_executor_reraises_unexpected_backend_error() -> None:
    executor, controller, _, mapper = make_executor()

    def fail(*args, **kwargs):
        raise KeyError("unexpected")

    controller.click = fail
    with pytest.raises(KeyError, match="unexpected"):
        executor.execute(
            AgentDecision("click", parameters={"x": 10, "y": 10}),
            mapper,
        )
