import pytest

from gui_agent.agent import Plan, PlanStep
from gui_agent.runtime import ExecutionReport
from gui_agent.runtime import cli as runtime_cli


def install_fakes(monkeypatch, status="preview"):
    captured = {}

    monkeypatch.setattr(runtime_cli, "load_config", lambda path: {"runtime": {"max_actions": 4}})
    monkeypatch.setattr(runtime_cli, "build_model", lambda config: "model")
    monkeypatch.setattr(runtime_cli, "DesktopAgent", lambda model: "agent")
    monkeypatch.setattr(runtime_cli, "DesktopPerception", lambda **kwargs: "perception")
    monkeypatch.setattr(runtime_cli, "InputController", lambda **kwargs: "controller")
    monkeypatch.setattr(runtime_cli, "ActionExecutor", lambda controller, **kwargs: "executor")

    class Runtime:
        def __init__(self, agent, perception, executor, **kwargs):
            captured.update(agent=agent, perception=perception, executor=executor, options=kwargs)

        def run(self, goal, *, execute=False):
            captured.update(goal=goal, execute=execute)
            plan = Plan(goal, "摘要", [PlanStep(1, "步骤")])
            return ExecutionReport(goal, "execute" if execute else "preview", status, plan)

    monkeypatch.setattr(runtime_cli, "GUIAgentRuntime", Runtime)
    return captured


def test_runtime_cli_preview(monkeypatch, capsys) -> None:
    captured = install_fakes(monkeypatch)
    result = runtime_cli.main(["--config", "agent.toml", "--goal", "打开浏览器"])
    assert result == 0
    assert captured["execute"] is False
    assert captured["options"]["max_actions"] == 4
    assert '"status": "preview"' in capsys.readouterr().out


def test_runtime_cli_execute_with_confirmation_flag(monkeypatch, capsys) -> None:
    captured = install_fakes(monkeypatch, status="completed")
    result = runtime_cli.main(
        [
            "--config",
            "agent.toml",
            "--goal",
            "关闭应用",
            "--execute",
            "--yes",
            "--start-delay",
            "0",
        ]
    )
    assert result == 0
    assert captured["execute"] is True
    assert '"status": "completed"' in capsys.readouterr().out


def test_runtime_cli_cancels_unconfirmed_execution(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "no")
    result = runtime_cli.main(["--config", "agent.toml", "--goal", "发送消息", "--execute"])
    assert result == 2
    assert '"status": "cancelled"' in capsys.readouterr().out


def test_runtime_cli_reads_interactive_goal(monkeypatch, capsys) -> None:
    captured = install_fakes(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda prompt: "打开文件")
    assert runtime_cli.main(["--config", "agent.toml"]) == 0
    assert captured["goal"] == "打开文件"
    assert '"goal": "打开文件"' in capsys.readouterr().out


def test_runtime_cli_reports_runtime_error(monkeypatch, capsys) -> None:
    install_fakes(monkeypatch)

    class BrokenRuntime:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, goal, *, execute=False):
            raise RuntimeError("capture failed")

    monkeypatch.setattr(runtime_cli, "GUIAgentRuntime", BrokenRuntime)
    assert runtime_cli.main(["--config", "agent.toml", "--goal", "打开浏览器"]) == 1
    output = capsys.readouterr().out
    assert '"status": "error"' in output
    assert "capture failed" in output


def test_runtime_cli_rejects_empty_interactive_goal(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: " ")
    with pytest.raises(ValueError, match="goal"):
        runtime_cli.main(["--config", "agent.toml"])


def test_runtime_cli_rejects_nested_run_name() -> None:
    with pytest.raises(ValueError, match="run_name"):
        runtime_cli._artifact_dir("artifacts/runtime", "nested/run")


def test_runtime_cli_waits_for_target_window(monkeypatch, capsys) -> None:
    waits = []
    monkeypatch.setattr(runtime_cli.time, "sleep", waits.append)
    runtime_cli._wait_for_desktop(1.5)
    assert waits == [1.5]
    assert "切换到目标窗口" in capsys.readouterr().err
    with pytest.raises(ValueError, match="start_delay"):
        runtime_cli._wait_for_desktop(-1)


def test_runtime_cli_reports_missing_config(capsys) -> None:
    result = runtime_cli.main(
        ["--config", "missing-agent.toml", "--goal", "打开浏览器"]
    )
    assert result == 1
    assert '"status": "error"' in capsys.readouterr().out


def test_runtime_cli_handles_keyboard_interrupt(monkeypatch, capsys) -> None:
    install_fakes(monkeypatch)

    class InterruptedRuntime:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, goal, *, execute=False):
            raise KeyboardInterrupt

    monkeypatch.setattr(runtime_cli, "GUIAgentRuntime", InterruptedRuntime)
    result = runtime_cli.main(["--config", "agent.toml", "--goal", "打开浏览器"])
    assert result == 130
    assert '"status": "interrupted"' in capsys.readouterr().out


def test_runtime_cli_starts_progress_overlay(monkeypatch) -> None:
    captured = install_fakes(monkeypatch)
    monitors = []
    monkeypatch.setattr(
        runtime_cli,
        "_start_progress_monitor",
        lambda path: monitors.append(path),
    )
    result = runtime_cli.main(
        [
            "--config",
            "agent.toml",
            "--goal",
            "打开浏览器",
            "--show-progress",
            "--run-name",
            "monitor-test",
        ]
    )
    assert result == 0
    assert len(monitors) == 1
    assert monitors[0].name == "progress.jsonl"
    assert captured["options"]["progress"].path == monitors[0]
