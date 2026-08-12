import json

import pytest

from gui_agent.finetune.data import build_sft_dataset, load_examples, record_to_example
from gui_agent.finetune.metrics import compare_results, score_predictions, write_comparison_report


def _record(task_id: str, split: str, action: str = "click") -> dict:
    return {
        "dataset": "mind2web",
        "task_id": task_id,
        "split": split,
        "instruction": "Open settings",
        "steps": [{"action": action, "target": "settings", "value": ""}],
        "images": [],
    }


def test_record_to_example_serializes_actions() -> None:
    example = record_to_example(_record("1", "train"))
    assert example is not None
    assert example.example_id == "mind2web:1"
    assert json.loads(example.response)["actions"][0]["target"] == "settings"


def test_build_sft_dataset_filters_non_training_split(tmp_path) -> None:
    source = tmp_path / "source.jsonl"
    records = [_record("1", "train"), _record("2", "train"), _record("3", "test")]
    source.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    counts = build_sft_dataset([source], tmp_path / "output", validation_ratio=0.01)
    assert counts["train"] == 1
    assert counts["validation"] == 1
    assert counts["skipped"] == 1
    assert load_examples(tmp_path / "output" / "validation.jsonl")[0].source_split == "train"


def test_build_sft_dataset_requires_two_training_examples(tmp_path) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text(json.dumps(_record("1", "test")), encoding="utf-8")
    with pytest.raises(ValueError, match="two valid"):
        build_sft_dataset([source], tmp_path / "output")


def test_scores_and_writes_comparison(tmp_path) -> None:
    baseline = score_predictions(
        [
            {"reference": '{"actions":[{"action":"click"}]}', "prediction": "bad"},
            {"reference": '{"actions":[{"action":"type"}]}', "prediction": '{"actions":[{"action":"click"}]}'},
        ]
    )
    finetuned = score_predictions(
        [
            {"reference": '{"actions":[{"action":"click"}]}', "prediction": '{"actions":[{"action":"click"}]}'},
            {"reference": '{"actions":[{"action":"type"}]}', "prediction": '{"actions":[{"action":"type"}]}'},
        ]
    )
    assert compare_results(baseline, finetuned)["first_action_accuracy_change"] == 1.0
    report = tmp_path / "report.md"
    write_comparison_report(baseline, finetuned, report)
    assert "first" not in report.read_text(encoding="utf-8").lower()