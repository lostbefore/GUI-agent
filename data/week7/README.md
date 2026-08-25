# Week 7 benchmark data

`benchmark-tasks.json` defines the 20-task desktop GUI evaluation set.

Each task includes a stable ID, application, category, difficulty, resolution profile, and expected action count. The benchmark is intentionally non-destructive: file and text operations refer to prepared test copies and test locations.

Run the controlled baseline:

```powershell
$env:PYTHONPATH='src'
python -m gui_agent.evaluation.cli run --tasks data/week7/benchmark-tasks.json --output-dir artifacts/week7 --report week7-system-evaluation-report.md
```

Use `summarize --records <path>` to aggregate a complete JSONL file of real or externally collected records following the `BenchmarkRecord` schema in `src/gui_agent/evaluation/benchmark.py`.