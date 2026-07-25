from gui_agent.agent import cli as agent_cli
from gui_agent.agent.core import AgentDecision
from gui_agent.agent.planner import Plan, PlanStep
from gui_agent.datasets import cli as dataset_cli


def test_dataset_cli_runs_preprocessor(monkeypatch, capsys) -> None:
    captured = {}

    def preprocess(dataset, source, output, *, limit=None):
        captured.update(dataset=dataset, source=source, output=output, limit=limit)
        return 3

    monkeypatch.setattr(dataset_cli, "preprocess_dataset", preprocess)
    result = dataset_cli.main(
        ["webarena", "--input", "raw", "--output", "processed.jsonl", "--limit", "3"]
    )
    assert result == 0
    assert captured == {
        "dataset": "webarena",
        "source": "raw",
        "output": "processed.jsonl",
        "limit": 3,
    }
    assert "Wrote 3 webarena records" in capsys.readouterr().out


def test_agent_cli_prints_plan(monkeypatch, capsys) -> None:
    class Agent:
        def __init__(self, model):
            assert model == "model"

        def plan(self, goal):
            return Plan(goal, "summary", [PlanStep(1, "step")])

    monkeypatch.setattr(agent_cli, "load_config", lambda path: {"path": path})
    monkeypatch.setattr(agent_cli, "build_model", lambda config: "model")
    monkeypatch.setattr(agent_cli, "DesktopAgent", Agent)
    assert agent_cli.main(["--config", "agent.toml", "--goal", "demo"]) == 0
    output = capsys.readouterr().out
    assert '"goal": "demo"' in output
    assert '"summary": "summary"' in output


def test_agent_cli_includes_screenshot_decision(monkeypatch, capsys) -> None:
    class Agent:
        def __init__(self, model):
            pass

        def plan(self, goal):
            return Plan(goal, "summary", [PlanStep(1, "step")])

        def decide(self, goal, plan, screenshot):
            assert screenshot == "screen.png"
            return AgentDecision("wait", "loading", {})

    monkeypatch.setattr(agent_cli, "load_config", lambda path: {})
    monkeypatch.setattr(agent_cli, "build_model", lambda config: object())
    monkeypatch.setattr(agent_cli, "DesktopAgent", Agent)
    assert (
        agent_cli.main(["--config", "agent.toml", "--goal", "demo", "--screenshot", "screen.png"])
        == 0
    )
    assert '"action": "wait"' in capsys.readouterr().out
