from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

DIFFICULTIES = frozenset({"basic", "intermediate", "advanced"})
RESOLUTIONS = frozenset({"1366x768", "1920x1080", "2560x1440"})


@dataclass(frozen=True, slots=True)
class BenchmarkTask:
    task_id: str
    title: str
    goal: str
    application: str
    difficulty: str
    resolution: str
    expected_actions: int
    category: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> BenchmarkTask:
        task = cls(
            task_id=str(value["task_id"]),
            title=str(value["title"]),
            goal=str(value["goal"]),
            application=str(value["application"]),
            difficulty=str(value["difficulty"]),
            resolution=str(value["resolution"]),
            expected_actions=int(value["expected_actions"]),
            category=str(value["category"]),
        )
        if not task.task_id or not task.title or not task.goal:
            raise ValueError("Benchmark task identifiers and text must not be empty")
        if task.difficulty not in DIFFICULTIES:
            raise ValueError(f"Unsupported difficulty: {task.difficulty}")
        if task.resolution not in RESOLUTIONS:
            raise ValueError(f"Unsupported resolution: {task.resolution}")
        if task.expected_actions <= 0:
            raise ValueError("expected_actions must be positive")
        return task


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    task_id: str
    success: bool
    duration_seconds: float
    action_attempts: int
    action_errors: int
    retries: int
    execution_mode: str
    message: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> BenchmarkRecord:
        record = cls(
            task_id=str(value["task_id"]),
            success=bool(value["success"]),
            duration_seconds=float(value["duration_seconds"]),
            action_attempts=int(value["action_attempts"]),
            action_errors=int(value["action_errors"]),
            retries=int(value["retries"]),
            execution_mode=str(value.get("execution_mode", "external")),
            message=str(value.get("message", "")),
        )
        if record.duration_seconds < 0 or record.action_attempts <= 0:
            raise ValueError("Invalid duration or action attempts")
        if record.action_errors < 0 or record.retries < 0:
            raise ValueError("Invalid error or retry count")
        if record.action_errors > record.action_attempts:
            raise ValueError("action_errors cannot exceed action_attempts")
        return record


@dataclass(frozen=True, slots=True)
class MetricRow:
    group: str
    total: int
    success_count: int
    success_rate: float
    average_duration_seconds: float
    action_error_rate: float
    average_retries: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    overall: MetricRow
    by_application: list[MetricRow]
    by_difficulty: list[MetricRow]
    by_resolution: list[MetricRow]
    execution_modes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall.to_dict(),
            "by_application": [row.to_dict() for row in self.by_application],
            "by_difficulty": [row.to_dict() for row in self.by_difficulty],
            "by_resolution": [row.to_dict() for row in self.by_resolution],
            "execution_modes": list(self.execution_modes),
        }


def load_tasks(path: str | Path) -> list[BenchmarkTask]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = payload.get("tasks", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise TypeError("Benchmark task file must contain a task list")
    tasks = [BenchmarkTask.from_dict(row) for row in rows if isinstance(row, dict)]
    if len(tasks) != 20:
        raise ValueError("The week 7 benchmark must contain exactly 20 tasks")
    task_ids = [task.task_id for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("Benchmark task identifiers must be unique")
    return tasks


def load_records(path: str | Path) -> list[BenchmarkRecord]:
    records: list[BenchmarkRecord] = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid benchmark JSONL at line {number}") from error
        if not isinstance(payload, dict):
            raise TypeError(f"Benchmark row {number} must be an object")
        records.append(BenchmarkRecord.from_dict(payload))
    return records


def write_records(records: Iterable[BenchmarkRecord], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    return output


def simulate_controlled_records(tasks: Iterable[BenchmarkTask]) -> list[BenchmarkRecord]:
    """Create deterministic runtime baseline records without operating a real desktop."""
    base_seconds = {"basic": 2.6, "intermediate": 4.7, "advanced": 7.3}
    resolution_cost = {"1366x768": 0.0, "1920x1080": 0.35, "2560x1440": 0.7}
    application_cost = {
        "Browser": 0.55,
        "File Explorer": 0.35,
        "Notepad": 0.15,
        "Calculator": 0.1,
        "Windows Settings": 0.45,
    }
    retry_ids = {"T04", "T09", "T15", "T18"}
    failure_ids = {"T17", "T20"}
    records: list[BenchmarkRecord] = []
    for index, task in enumerate(tasks, start=1):
        retries = 1 if task.task_id in retry_ids else 0
        success = task.task_id not in failure_ids
        errors = retries + (1 if not success else 0)
        attempts = task.expected_actions + errors
        duration = (
            base_seconds[task.difficulty]
            + resolution_cost[task.resolution]
            + application_cost[task.application]
            + task.expected_actions * 0.38
            + retries * 0.8
            + (0.45 if not success else 0.0)
            + (index % 3) * 0.07
        )
        message = "completed" if success else "action limit reached during controlled scenario"
        records.append(
            BenchmarkRecord(
                task.task_id,
                success,
                round(duration, 2),
                attempts,
                errors,
                retries,
                "controlled",
                message,
            )
        )
    return records


def _metric(group: str, records: list[BenchmarkRecord]) -> MetricRow:
    attempts = sum(record.action_attempts for record in records)
    errors = sum(record.action_errors for record in records)
    return MetricRow(
        group=group,
        total=len(records),
        success_count=sum(record.success for record in records),
        success_rate=sum(record.success for record in records) / len(records),
        average_duration_seconds=fmean(record.duration_seconds for record in records),
        action_error_rate=errors / attempts if attempts else 0.0,
        average_retries=fmean(record.retries for record in records),
    )


def summarize(
    tasks: Iterable[BenchmarkTask], records: Iterable[BenchmarkRecord]
) -> EvaluationSummary:
    task_list = list(tasks)
    record_list = list(records)
    task_by_id = {task.task_id: task for task in task_list}
    if not record_list:
        raise ValueError("At least one benchmark record is required")
    unknown = [record.task_id for record in record_list if record.task_id not in task_by_id]
    if unknown:
        raise ValueError(f"Unknown benchmark task identifiers: {', '.join(sorted(set(unknown)))}")
    duplicates = [
        task_id
        for task_id in task_by_id
        if sum(record.task_id == task_id for record in record_list) > 1
    ]
    if duplicates:
        raise ValueError(f"Multiple records for task identifiers: {', '.join(duplicates)}")
    missing = sorted(set(task_by_id) - {record.task_id for record in record_list})
    if missing:
        raise ValueError(f"Missing benchmark records: {', '.join(missing)}")

    def grouped(attribute: str) -> list[MetricRow]:
        buckets: dict[str, list[BenchmarkRecord]] = defaultdict(list)
        for record in record_list:
            buckets[str(getattr(task_by_id[record.task_id], attribute))].append(record)
        return [_metric(name, buckets[name]) for name in sorted(buckets)]

    return EvaluationSummary(
        _metric("Overall", record_list),
        grouped("application"),
        grouped("difficulty"),
        grouped("resolution"),
        tuple(sorted({record.execution_mode for record in record_list})),
    )


def write_summary(summary: EvaluationSummary, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return output
