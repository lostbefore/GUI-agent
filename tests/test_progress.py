import json

from gui_agent.runtime.progress import ProgressRecorder, format_progress, read_latest_progress


def test_progress_recorder_appends_and_reads_latest(tmp_path) -> None:
    path = tmp_path / "progress.jsonl"
    recorder = ProgressRecorder(path)
    recorder.record("starting", goal="\u6253\u5f00\u6d4f\u89c8\u5668")
    recorder.record("deciding", index=2)
    latest = read_latest_progress(path)
    assert latest is not None
    assert latest["stage"] == "deciding"
    assert latest["index"] == 2
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
    assert path.with_suffix(".log").exists()


def test_progress_reader_skips_invalid_last_line(tmp_path) -> None:
    path = tmp_path / "progress.jsonl"
    path.write_text(json.dumps({"stage": "planned"}) + "\npartial", encoding="utf-8")
    assert read_latest_progress(path) == {"stage": "planned"}
    assert read_latest_progress(tmp_path / "missing.jsonl") is None


def test_progress_formatter_describes_current_step() -> None:
    assert "\u7b49\u5f85\u8fd0\u884c" in format_progress(None)
    text = format_progress({"stage": "action_finished", "index": 3, "action": "hotkey", "status": "completed", "message": "\u6267\u884c\u6210\u529f"})
    assert "\u7b2c3\u6b65" in text
    assert "hotkey" in text
    assert "completed" in text
    assert "\u6267\u884c\u6210\u529f" in text


def test_progress_formatter_shows_retry_attempt() -> None:
    text = format_progress({"stage": "retrying", "index": 2, "attempt": 2})
    assert "Retrying" in text
    assert "\u5c1d\u8bd52" in text