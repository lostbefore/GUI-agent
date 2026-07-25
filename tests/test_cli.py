from pathlib import Path

import pytest

from gui_agent import cli


def test_parser_supports_inspect_and_overlay() -> None:
    inspect = cli.build_parser().parse_args(["inspect", "--output", "x.png", "--scale", "0.5"])
    overlay = cli.build_parser().parse_args(["overlay"])
    assert (inspect.command, inspect.output, inspect.scale) == ("inspect", "x.png", 0.5)
    assert overlay.command == "overlay"


def test_parser_requires_command() -> None:
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([])


def test_inspect_command_saves_result(monkeypatch, capsys) -> None:
    class Perception:
        def capture(self, **kwargs):
            assert kwargs == {"scale": 0.75}
            return "frame"

        def analyze(self, frame):
            return ["one", "two"]

        def save_annotated(self, frame, elements, output):
            return Path(output)

    monkeypatch.setattr(cli, "DesktopPerception", Perception)
    assert cli.main(["inspect", "--scale", "0.75", "--output", "out.png"]) == 0
    assert "Detected 2 elements; wrote out.png" in capsys.readouterr().out


def test_overlay_command_runs_application(monkeypatch) -> None:
    events = []

    class Perception:
        def capture(self, **kwargs):
            return "frame"

        def analyze(self, frame):
            return ["box"]

    class App:
        def __init__(self, argv):
            events.append("app")

        def exec_(self):
            return 7

    class Overlay:
        def __init__(self, elements):
            events.append(elements)

        def show(self):
            events.append("show")

    monkeypatch.setattr(cli, "DesktopPerception", Perception)
    monkeypatch.setattr(cli, "QApplication", App)
    monkeypatch.setattr(cli, "BoundingBoxOverlay", Overlay)
    assert cli.main(["overlay"]) == 7
    assert events == ["app", ["box"], "show"]
