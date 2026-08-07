import json

from gui_agent.runtime.progress import (
    ProgressRecorder,
    format_progress,
    read_latest_progress,
)


def test_progress_recorder_appends_and_reads_latest(tmp_path) -> None:
    path = tmp_path / "progress.jsonl"
    recorder = ProgressRecorder(path)
    recorder.record("starting", goal="打开浏览器")
    recorder.record("deciding", index=2)
    latest = read_latest_progress(path)
    assert latest is not None
    assert latest["stage"] == "deciding"
    assert latest["index"] == 2
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_progress_reader_skips_invalid_last_line(tmp_path) -> None:
    path = tmp_path / "progress.jsonl"
    path.write_text(
        json.dumps({"stage": "planned"}) + "\npartial",
        encoding="utf-8",
    )
    assert read_latest_progress(path) == {"stage": "planned"}
    assert read_latest_progress(tmp_path / "missing.jsonl") is None


def test_progress_formatter_describes_current_step() -> None:
    assert "等待运行" in format_progress(None)
    text = format_progress(
        {
            "stage": "action_finished",
            "index": 3,
            "action": "hotkey",
            "status": "completed",
            "message": "执行成功",
        }
    )
    assert "第 3 步" in text
    assert "hotkey" in text
    assert "completed" in text
    assert "执行成功" in text
