from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    total: int
    valid_json: int
    first_action_correct: int
    exact_response_correct: int

    @property
    def valid_json_rate(self) -> float:
        return self.valid_json / self.total if self.total else 0.0

    @property
    def first_action_accuracy(self) -> float:
        return self.first_action_correct / self.total if self.total else 0.0

    @property
    def exact_response_accuracy(self) -> float:
        return self.exact_response_correct / self.total if self.total else 0.0

    def to_dict(self) -> dict[str, float | int]:
        result: dict[str, float | int] = asdict(self)
        result.update(
            valid_json_rate=round(self.valid_json_rate, 4),
            first_action_accuracy=round(self.first_action_accuracy, 4),
            exact_response_accuracy=round(self.exact_response_accuracy, 4),
        )
        return result


def _parse(value: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _first_action(payload: dict[str, Any]) -> str | None:
    actions = payload.get("actions")
    if not isinstance(actions, list) or not actions or not isinstance(actions[0], dict):
        return None
    value = actions[0].get("action")
    return str(value) if value else None


def score_predictions(rows: Iterable[dict[str, str]]) -> EvaluationResult:
    total = valid_json = first = exact = 0
    for row in rows:
        total += 1
        reference = _parse(row.get("reference", ""))
        prediction = _parse(row.get("prediction", ""))
        if prediction is not None:
            valid_json += 1
        if reference is not None and prediction is not None:
            first += _first_action(reference) == _first_action(prediction)
            exact += reference == prediction
    return EvaluationResult(total, valid_json, first, exact)


def load_prediction_rows(path: str | Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip() and isinstance(row := json.loads(line), dict):
                rows.append({key: str(value) for key, value in row.items()})
    return rows


def compare_results(baseline: EvaluationResult, finetuned: EvaluationResult) -> dict[str, float]:
    return {
        "valid_json_rate_change": round(finetuned.valid_json_rate - baseline.valid_json_rate, 4),
        "first_action_accuracy_change": round(
            finetuned.first_action_accuracy - baseline.first_action_accuracy, 4
        ),
        "exact_response_accuracy_change": round(
            finetuned.exact_response_accuracy - baseline.exact_response_accuracy, 4
        ),
    }


def write_comparison_report(
    baseline: EvaluationResult, finetuned: EvaluationResult, output: str | Path
) -> None:
    change = compare_results(baseline, finetuned)
    title = "# \u7b2c\u4e94\u5468\u5fae\u8c03\u6548\u679c\u5bf9\u6bd4\u62a5\u544a"
    results = "## \u8bc4\u6d4b\u7ed3\u679c"
    sample_size = "## \u6837\u672c\u89c4\u6a21"
    conclusion = "## \u7ed3\u8bba"
    rows = [
        "| \u6307\u6807 | \u5fae\u8c03\u524d | \u5fae\u8c03\u540e | \u53d8\u5316 |",
        "|---|---:|---:|---:|",
        f"| JSON \u6709\u6548\u7387 | {baseline.valid_json_rate:.2%} | {finetuned.valid_json_rate:.2%} | {change['valid_json_rate_change']:+.2%} |",
        f"| \u9996\u52a8\u4f5c\u51c6\u786e\u7387 | {baseline.first_action_accuracy:.2%} | {finetuned.first_action_accuracy:.2%} | {change['first_action_accuracy_change']:+.2%} |",
        f"| \u5b8c\u6574\u52a8\u4f5c\u5e8f\u5217\u51c6\u786e\u7387 | {baseline.exact_response_accuracy:.2%} | {finetuned.exact_response_accuracy:.2%} | {change['exact_response_accuracy_change']:+.2%} |",
    ]
    text = "\n".join(
        [
            title,
            "",
            results,
            "",
            *rows,
            "",
            sample_size,
            "",
            f"- \u5fae\u8c03\u524d\u8bc4\u6d4b\u6837\u672c\uff1a{baseline.total}",
            f"- \u5fae\u8c03\u540e\u8bc4\u6d4b\u6837\u672c\uff1a{finetuned.total}",
            "",
            conclusion,
            "",
            (
                "\\u5fae\\u8c03\\u524d\\u540e\\u4f7f\\u7528\\u76f8\\u540c\\u9a8c\\u8bc1\\u96c6\\u3001\\u751f\\u6210\\u53c2\\u6570\\u548c\\u8bc4\\u5206\\u89c4\\u5219\\u3002"
                "\\u4ee5\\u4e0a\\u53d8\\u5316\\u7528\\u4e8e\\u5224\\u65ad LoRA \\u5fae\\u8c03\\u5bf9 GUI \\u52a8\\u4f5c\\u751f\\u6210\\u7684\\u5f71\\u54cd\\u3002"
            ),
            "",
        ]
    )
    Path(output).write_text(text, encoding="utf-8")
