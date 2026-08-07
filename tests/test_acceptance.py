import pytest

from gui_agent.agent import Plan, PlanStep
from gui_agent.runtime import ExecutionReport, acceptance


def test_builds_five_acceptance_tasks(tmp_path) -> None:
    test_file = tmp_path / "demo.txt"
    test_file.write_text("demo", encoding="utf-8")
    tasks = [
        acceptance.build_task("open-browser"),
        acceptance.build_task("search-content", query="GUI Agent"),
        acceptance.build_task("open-file", file_path=test_file),
        acceptance.build_task("send-message", message="测试消息"),
        acceptance.build_task("close-app"),
    ]
    assert [task.name for task in tasks] == list(acceptance.TASK_NAMES)
    assert all(task.decisions[-1].action == "finish" for task in tasks)


def test_acceptance_preview_lists_actions(capsys) -> None:
    result = acceptance.main(["--task", "open-browser"])
    output = capsys.readouterr().out
    assert result == 0
    assert '"mode": "preview"' in output
    assert '"hotkey"' in output
    assert '"msedge"' in output


def test_send_message_requires_extra_confirmation(capsys) -> None:
    result = acceptance.main(
        ["--task", "send-message", "--execute", "--yes", "--start-delay", "0"]
    )
    assert result == 1
    assert "--confirm-send" in capsys.readouterr().out


def test_acceptance_execute_uses_runtime(monkeypatch, capsys) -> None:
    captured = {}

    class Runtime:
        def __init__(self, agent, perception, executor, **kwargs):
            captured.update(agent=agent, options=kwargs)

        def run(self, goal, *, execute=False):
            captured.update(goal=goal, execute=execute)
            return ExecutionReport(goal, "execute", "completed", Plan(goal, "完成", [PlanStep(1, "完成")]))

    monkeypatch.setattr(acceptance, "DesktopPerception", lambda **kwargs: "perception")
    monkeypatch.setattr(acceptance, "InputController", lambda **kwargs: "controller")
    monkeypatch.setattr(acceptance, "ActionExecutor", lambda controller: "executor")
    monkeypatch.setattr(acceptance, "GUIAgentRuntime", Runtime)
    result = acceptance.main(
        ["--task", "close-app", "--execute", "--yes", "--start-delay", "0"]
    )
    assert result == 0
    assert captured["execute"] is True
    assert captured["options"]["analyze_screen"] is False
    assert '"status": "completed"' in capsys.readouterr().out


def test_acceptance_cancel_and_invalid_delay(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "no")
    cancelled = acceptance.main(["--task", "close-app", "--execute"])
    assert cancelled == 2
    assert '"status": "cancelled"' in capsys.readouterr().out

    invalid = acceptance.main(
        ["--task", "close-app", "--execute", "--yes", "--start-delay", "-1"]
    )
    assert invalid == 1
    assert "start_delay" in capsys.readouterr().out


def test_acceptance_countdown_runs_before_runtime(monkeypatch, capsys) -> None:
    waits = []

    class Runtime:
        def __init__(self, agent, perception, executor, **kwargs):
            pass

        def run(self, goal, *, execute=False):
            return ExecutionReport(goal, "execute", "completed", Plan(goal, "完成"))

    monkeypatch.setattr(acceptance.time, "sleep", waits.append)
    monkeypatch.setattr(acceptance, "DesktopPerception", lambda **kwargs: "perception")
    monkeypatch.setattr(acceptance, "InputController", lambda **kwargs: "controller")
    monkeypatch.setattr(acceptance, "ActionExecutor", lambda controller: "executor")
    monkeypatch.setattr(acceptance, "GUIAgentRuntime", Runtime)
    result = acceptance.main(
        ["--task", "close-app", "--execute", "--yes", "--start-delay", "1.5"]
    )
    assert result == 0
    assert waits == [1.5]
    assert "完成准备" in capsys.readouterr().err


def test_acceptance_handles_keyboard_interrupt(monkeypatch, capsys) -> None:
    class Runtime:
        def __init__(self, agent, perception, executor, **kwargs):
            pass

        def run(self, goal, *, execute=False):
            raise KeyboardInterrupt

    monkeypatch.setattr(acceptance, "DesktopPerception", lambda **kwargs: "perception")
    monkeypatch.setattr(acceptance, "InputController", lambda **kwargs: "controller")
    monkeypatch.setattr(acceptance, "ActionExecutor", lambda controller: "executor")
    monkeypatch.setattr(acceptance, "GUIAgentRuntime", Runtime)
    result = acceptance.main(
        ["--task", "close-app", "--execute", "--yes", "--start-delay", "0"]
    )
    assert result == 130
    assert '"status": "interrupted"' in capsys.readouterr().out


def test_scripted_agent_returns_actions_in_order() -> None:
    task = acceptance.build_task("close-app")
    agent = acceptance.ScriptedAgent(task)
    plan = agent.plan(task.goal)
    actions = [
        agent.decide(task.goal, plan, "screen.png").action
        for _ in range(len(task.decisions))
    ]
    assert actions == [decision.action for decision in task.decisions]
    assert agent.decide(task.goal, plan, "screen.png").action == "finish"


def test_unknown_task_is_rejected() -> None:
    with pytest.raises(ValueError, match="不支持"):
        acceptance.build_task("unknown")


def test_missing_file_is_rejected(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="不存在"):
        acceptance.build_task("open-file", file_path=tmp_path / "missing.txt")
