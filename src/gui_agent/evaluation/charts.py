from __future__ import annotations

from pathlib import Path

from .benchmark import EvaluationSummary, MetricRow


def _plot(rows: list[MetricRow], attribute: str, title: str, ylabel: str, path: Path, *, percent: bool = False) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [row.group for row in rows]
    values = [getattr(row, attribute) for row in rows]
    figure, axis = plt.subplots(figsize=(7.4, 4.2), dpi=160)
    bars = axis.bar(labels, values, color="#2563eb")
    axis.set_title(title, fontsize=12, fontweight="bold")
    axis.set_ylabel(ylabel)
    axis.grid(axis="y", color="#d1d5db", linewidth=0.7, alpha=0.8)
    axis.set_axisbelow(True)
    upper = max(values) * 1.22 if values else 1
    axis.set_ylim(0, max(upper, 0.1 if percent else 1))
    if percent:
        axis.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    for bar, value in zip(bars, values):
        label = f"{value:.1%}" if percent else f"{value:.2f}"
        axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + upper * 0.025, label, ha="center", va="bottom", fontsize=9)
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)
    return path


def create_charts(summary: EvaluationSummary, output_dir: str | Path) -> list[Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    return [
        _plot(summary.by_difficulty, "success_rate", "Success Rate by Difficulty", "Success rate", output / "success-by-difficulty.png", percent=True),
        _plot(summary.by_resolution, "average_duration_seconds", "Average Duration by Resolution", "Seconds", output / "duration-by-resolution.png"),
        _plot(summary.by_application, "action_error_rate", "Action Error Rate by Application", "Action error rate", output / "error-rate-by-application.png", percent=True),
    ]