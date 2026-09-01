import json
from pathlib import Path

import pytest

from gui_agent.evaluation.benchmark import (
    BenchmarkRecord,
    load_tasks,
    simulate_controlled_records,
    summarize,
    write_records,
)
from gui_agent.evaluation.charts import create_charts
from gui_agent.evaluation.cli import main
from gui_agent.evaluation.report import write_report

TASKS = Path("data/week7/benchmark-tasks.json")


def test_week7_tasks_cover_exactly_twenty_tasks_and_required_dimensions() -> None:
    tasks = load_tasks(TASKS)
    assert len(tasks) == 20
    assert {task.difficulty for task in tasks} == {"basic", "intermediate", "advanced"}
    assert {task.resolution for task in tasks} == {"1366x768", "1920x1080", "2560x1440"}
    assert len({task.application for task in tasks}) == 5


def test_controlled_benchmark_produces_complete_reproducible_summary() -> None:
    tasks = load_tasks(TASKS)
    records = simulate_controlled_records(tasks)
    summary = summarize(tasks, records)
    assert len(records) == 20
    assert summary.overall.success_count == 18
    assert summary.overall.success_rate == 0.9
    assert summary.execution_modes == ("controlled",)
    assert [row.group for row in summary.by_resolution] == ["1366x768", "1920x1080", "2560x1440"]


def test_summary_rejects_missing_or_duplicate_task_results() -> None:
    tasks = load_tasks(TASKS)
    records = simulate_controlled_records(tasks)
    with pytest.raises(ValueError, match="Missing"):
        summarize(tasks, records[:-1])
    with pytest.raises(ValueError, match="Multiple"):
        summarize(tasks, records + [records[0]])


def test_charts_report_and_records_are_created(tmp_path) -> None:
    tasks = load_tasks(TASKS)
    records = simulate_controlled_records(tasks)
    records_path = write_records(records, tmp_path / "records.jsonl")
    assert len(records_path.read_text(encoding="utf-8").splitlines()) == 20
    summary = summarize(tasks, records)
    charts = create_charts(summary, tmp_path / "charts")
    assert len(charts) == 3
    assert all(path.is_file() and path.stat().st_size > 5_000 for path in charts)
    report = write_report(tasks, summary, tmp_path / "charts", tmp_path / "report.md")
    text = report.read_text(encoding="utf-8")
    assert "20 项桌面 GUI 基准任务" in text
    assert "Ui-TARS" in text
    assert "charts/success-by-difficulty.png" in text


def test_cli_run_generates_all_week7_artifacts(tmp_path, capsys) -> None:
    report = tmp_path / "week7-report.md"
    result = main(
        [
            "run",
            "--tasks",
            str(TASKS),
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--report",
            str(report),
        ]
    )
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tasks"] == 20
    assert report.is_file()
    assert (tmp_path / "artifacts" / "summary.json").is_file()


def test_record_validation_rejects_too_many_errors() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        BenchmarkRecord.from_dict(
            {
                "task_id": "T01",
                "success": False,
                "duration_seconds": 1,
                "action_attempts": 1,
                "action_errors": 2,
                "retries": 0,
            }
        )
