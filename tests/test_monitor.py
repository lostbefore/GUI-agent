import importlib
import json

import pytest


@pytest.fixture
def monitor_module(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    return importlib.import_module("gui_agent.runtime.monitor")


def test_monitor_exclusion_returns_false_off_windows(monkeypatch, monitor_module) -> None:
    monkeypatch.setattr(monitor_module.sys, "platform", "linux")
    assert monitor_module.exclude_from_capture(1) is False


def test_monitor_exclusion_calls_windows_api(monkeypatch, monitor_module) -> None:
    calls = []

    class User32:
        @staticmethod
        def SetWindowDisplayAffinity(window_id, affinity):
            calls.append((window_id, affinity))
            return 1

    monkeypatch.setattr(monitor_module.sys, "platform", "win32")
    monkeypatch.setattr(
        monitor_module.ctypes,
        "WinDLL",
        lambda *args, **kwargs: User32(),
    )
    assert monitor_module.exclude_from_capture(12) is True
    assert calls == [(12, 0x11)]


def test_overlay_refreshes_and_marks_completion(tmp_path, monkeypatch, monitor_module) -> None:
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    path = tmp_path / "progress.jsonl"
    path.write_text(
        json.dumps(
            {"stage": "deciding", "index": 2, "action": "click"},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    overlay = monitor_module.ProgressOverlay(path, auto_close=0)
    overlay.refresh()
    assert "第 2 步" in overlay.text()

    path.write_text('{"stage":"finished","status":"completed"}\n', encoding="utf-8")
    callbacks = []
    monkeypatch.setattr(
        monitor_module.QTimer,
        "singleShot",
        lambda delay, callback: callbacks.append((delay, callback)),
    )
    overlay.refresh()
    assert overlay._closing is True
    assert callbacks[0][0] == 0
    overlay.close()
    app.processEvents()


def test_overlay_show_event_uses_capture_exclusion(tmp_path, monkeypatch, monitor_module) -> None:
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    overlay = monitor_module.ProgressOverlay(tmp_path / "progress.jsonl")
    monkeypatch.setattr(monitor_module, "exclude_from_capture", lambda window_id: True)
    overlay.show()
    app.processEvents()
    assert overlay.isVisible()
    overlay.close()


def test_monitor_main_rejects_negative_close_time(monitor_module) -> None:
    with pytest.raises(ValueError, match="auto_close"):
        monitor_module.main(["--file", "progress.jsonl", "--auto-close", "-1"])


def test_monitor_main_starts_application(monkeypatch, monitor_module) -> None:
    shown = []

    class App:
        @staticmethod
        def instance():
            return None

        def __init__(self, args):
            pass

        @staticmethod
        def exec_():
            return 0

    class Overlay:
        def __init__(self, path, auto_close):
            shown.append((path, auto_close))

        @staticmethod
        def show():
            shown.append("shown")

    monkeypatch.setattr(monitor_module, "QApplication", App)
    monkeypatch.setattr(monitor_module, "ProgressOverlay", Overlay)
    assert monitor_module.main(["--file", "progress.jsonl"]) == 0
    assert shown[-1] == "shown"
