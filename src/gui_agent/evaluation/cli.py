from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .benchmark import (
    load_records,
    load_tasks,
    simulate_controlled_records,
    summarize,
    write_records,
    write_summary,
)
from .charts import create_charts
from .report import write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Week 7 GUI Agent benchmark evaluator")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("run", "run deterministic controlled benchmark"),
        ("summarize", "summarize existing benchmark records"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--tasks", default="old/data/week7/benchmark-tasks.json")
        command.add_argument("--output-dir", default="old/artifacts/week7")
        command.add_argument("--report", default="old/week7-system-evaluation-report.md")
    commands.choices["summarize"].add_argument("--records", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tasks = load_tasks(args.tasks)
    output_dir = Path(args.output_dir)
    if args.command == "run":
        records = simulate_controlled_records(tasks)
        records_path = write_records(records, output_dir / "benchmark-results.jsonl")
    else:
        records = load_records(args.records)
        records_path = Path(args.records)
    summary = summarize(tasks, records)
    summary_path = write_summary(summary, output_dir / "summary.json")
    chart_paths = create_charts(summary, output_dir / "charts")
    report_path = write_report(tasks, summary, output_dir / "charts", args.report)
    print(
        json.dumps(
            {
                "tasks": len(tasks),
                "records": str(records_path),
                "summary": str(summary_path),
                "charts": [str(path) for path in chart_paths],
                "report": str(report_path),
                "overall": asdict(summary.overall),
                "execution_modes": list(summary.execution_modes),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
