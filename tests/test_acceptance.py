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
    result = acceptance.main(["--task", "send-message", "--execute", "--yes", "--start-delay", "0"])
    assert result == 1
    assert "--confirm-send" in capsys.readouterr().out


def test_acceptance_execute_uses_runtime(monkeypatch, capsys) -> None:
    captured = {}

    class Runtime:
        def __init__(self, agent, perception, executor, **kwargs):
            captured.update(agent=agent, options=kwargs)

        def run(self, goal, *, execute=False):
            captured.update(goal=goal, execute=execute)
            return ExecutionReport(
                goal, "execute", "completed", Plan(goal, "完成", [PlanStep(1, "完成")])
            )

    monkeypatch.setattr(acceptance, "DesktopPerception", lambda **kwargs: "perception")
    monkeypatch.setattr(acceptance, "InputController", lambda **kwargs: "controller")
    monkeypatch.setattr(acceptance, "ActionExecutor", lambda controller: "executor")
    monkeypatch.setattr(acceptance, "GUIAgentRuntime", Runtime)
    result = acceptance.main(["--task", "close-app", "--execute", "--yes", "--start-delay", "0"])
    assert result == 0
    assert captured["execute"] is True
    assert captured["options"]["analyze_screen"] is False
    assert '"status": "completed"' in capsys.readouterr().out


def test_acceptance_cancel_and_invalid_delay(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "no")
    cancelled = acceptance.main(["--task", "close-app", "--execute"])
    assert cancelled == 2
    assert '"status": "cancelled"' in capsys.readouterr().out

    invalid = acceptance.main(["--task", "close-app", "--execute", "--yes", "--start-delay", "-1"])
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
    result = acceptance.main(["--task", "close-app", "--execute", "--yes", "--start-delay", "1.5"])
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
    result = acceptance.main(["--task", "close-app", "--execute", "--yes", "--start-delay", "0"])
    assert result == 130
    assert '"status": "interrupted"' in capsys.readouterr().out


def test_scripted_agent_returns_actions_in_order() -> None:
    task = acceptance.build_task("close-app")
    agent = acceptance.ScriptedAgent(task)
    plan = agent.plan(task.goal)
    actions = [
        agent.decide(task.goal, plan, "screen.png").action for _ in range(len(task.decisions))
    ]
    assert actions == [decision.action for decision in task.decisions]
    assert agent.decide(task.goal, plan, "screen.png").action == "finish"


def test_unknown_task_is_rejected() -> None:
    with pytest.raises(ValueError, match="不支持"):
        acceptance.build_task("unknown")


def test_missing_file_is_rejected(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="不存在"):
        acceptance.build_task("open-file", file_path=tmp_path / "missing.txt")


def test_search_task_uses_browser_gui_navigation() -> None:
    task = acceptance.build_task("search-content", query="必应")
    assert [decision.action for decision in task.decisions] == [
        "hotkey",
        "type",
        "press",
        "wait",
        "maximize_window",
        "wait",
        "press",
        "wait",
        "hotkey",
        "wait",
        "type",
        "wait",
        "press",
        "wait",
        "finish",
    ]
    assert task.decisions[0].parameters == {"keys": ["win", "r"]}
    assert task.decisions[1].parameters == {"text": "msedge"}
    assert task.decisions[4].parameters == {}
    assert task.decisions[6].parameters == {"key": "esc"}
    assert task.decisions[8].parameters == {"keys": ["ctrl", "l"]}
    assert task.decisions[10].parameters == {
        "text": "https://www.google.com/search?q=%E5%BF%85%E5%BA%94"
    }
    assert task.decisions[12].parameters == {"key": "enter", "step_id": 1}


def test_browse_pages_requires_search_task(capsys) -> None:
    result = acceptance.main(["--task", "open-browser", "--browse-pages"])
    assert result == 1
    assert "只能用于搜索任务" in capsys.readouterr().out


def test_browse_pages_validates_page_count(capsys) -> None:
    result = acceptance.main(["--task", "search-content", "--browse-pages", "--page-count", "4"])
    assert result == 1
    assert "网页数量只能是 2 或 3" in capsys.readouterr().out


def test_browse_pages_runs_after_search(monkeypatch, capsys, tmp_path) -> None:
    from gui_agent.web_research import PageVisit, ResearchResult

    captured = {}

    class Runtime:
        def __init__(self, agent, perception, executor, **kwargs):
            self.perception = perception
            self.executor = executor
            self.artifact_dir = kwargs["artifact_dir"]

        def run(self, goal, *, execute=False):
            return ExecutionReport(goal, "execute", "completed", Plan(goal, "完成"))

    def research(perception, controller, output_dir, **kwargs):
        captured.update(
            perception=perception,
            controller=controller,
            output_dir=output_dir,
            options=kwargs,
        )
        return ResearchResult(
            [PageVisit(1, "页面一", True, "one.md"), PageVisit(2, "页面二", True, "two.md")],
            str(tmp_path / "research.json"),
        )

    monkeypatch.setattr(acceptance, "DesktopPerception", lambda **kwargs: "perception")
    monkeypatch.setattr(acceptance, "InputController", lambda **kwargs: "controller")
    monkeypatch.setattr(
        acceptance,
        "ActionExecutor",
        lambda controller: type("Executor", (), {"controller": controller})(),
    )
    monkeypatch.setattr(acceptance, "GUIAgentRuntime", Runtime)
    monkeypatch.setattr(acceptance, "visit_search_results", research)
    result = acceptance.main(
        [
            "--task",
            "search-content",
            "--execute",
            "--yes",
            "--start-delay",
            "0",
            "--artifact-dir",
            str(tmp_path),
            "--browse-pages",
            "--page-count",
            "2",
            "--page-wait",
            "7",
        ]
    )
    assert result == 0
    assert captured["options"] == {"page_count": 2, "page_wait": 7.0}
    assert captured["output_dir"].name == "web-pages"
    assert '"web_research"' in capsys.readouterr().out


def test_acceptance_defaults_to_immediate_start() -> None:
    args = acceptance.build_parser().parse_args(["--task", "search-content"])
    assert args.start_delay == 0.0
