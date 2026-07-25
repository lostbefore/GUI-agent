import json

import pytest

from gui_agent.datasets.preprocessors import preprocess_dataset
from gui_agent.datasets.schema import ActionStep, GUITaskRecord


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_schema_validation_and_serialization() -> None:
    record = GUITaskRecord("demo", "1", "train", "Open file", [ActionStep("click", "File")])
    assert record.to_dict()["steps"][0]["action"] == "click"
    with pytest.raises(ValueError, match="instruction"):
        GUITaskRecord("demo", "2", "train", "").to_dict()


def test_webarena_preprocessor(tmp_path) -> None:
    source = tmp_path / "webarena" / "config_files"
    source.mkdir(parents=True)
    (source / "0.json").write_text(
        json.dumps({"task_id": 7, "intent": "Find an issue", "sites": ["gitlab"]}),
        encoding="utf-8",
    )
    output = tmp_path / "out.jsonl"
    assert preprocess_dataset("webarena", source.parent, output) == 1
    record = read_jsonl(output)[0]
    assert record["task_id"] == "7"
    assert record["metadata"]["sites"] == ["gitlab"]


def test_mind2web_preprocessor_and_limit(tmp_path) -> None:
    source = tmp_path / "mind2web" / "data" / "train"
    source.mkdir(parents=True)
    payload = [
        {
            "annotation_id": "a1",
            "confirmed_task": "Book a room",
            "website": "hotel",
            "actions": [
                {
                    "operation": {"op": "CLICK", "value": ""},
                    "pos_candidates": [{"backend_node_id": "42"}],
                }
            ],
        },
        {"annotation_id": "a2", "confirmed_task": "Second", "actions": []},
    ]
    (source / "train_0.json").write_text(json.dumps(payload), encoding="utf-8")
    output = tmp_path / "out.jsonl"
    assert preprocess_dataset("mind2web", source.parents[1], output, limit=1) == 1
    record = read_jsonl(output)[0]
    assert record["split"] == "train"
    assert record["steps"][0]["action"] == "click"
    assert record["steps"][0]["target"] == "42"


def test_screenagent_json_and_text_sessions(tmp_path) -> None:
    root = tmp_path / "ScreenAgent" / "train"
    json_session = root / "session-json"
    json_session.mkdir(parents=True)
    (json_session / "screen.png").write_bytes(b"image")
    (json_session / "record.json").write_text(
        json.dumps(
            {
                "task": "Open calculator",
                "actions": [{"action_type": "CLICK", "position": [10, 20]}],
            }
        ),
        encoding="utf-8",
    )
    text_session = root / "session-text"
    text_session.mkdir()
    (text_session / "task.txt").write_text("Open browser", encoding="utf-8")
    output = tmp_path / "out.jsonl"
    assert preprocess_dataset("screenagent", tmp_path, output) == 2
    records = read_jsonl(output)
    assert {record["instruction"] for record in records} == {
        "Open calculator",
        "Open browser",
    }


def test_screenagent_official_timestamp_format_is_grouped(tmp_path) -> None:
    session = tmp_path / "ScreenAgent" / "test" / "session-1"
    images = session / "images"
    images.mkdir(parents=True)
    (images / "001.jpg").write_bytes(b"image")
    common = {
        "session_id": "session-1",
        "task_prompt_en": "Create a folder",
        "video_height": 768,
        "video_width": 1024,
    }
    (session / "001.json").write_text(
        json.dumps(
            {
                **common,
                "saved_image_name": "001.jpg",
                "actions": [{"action": "click", "position": [10, 20]}],
            }
        ),
        encoding="utf-8",
    )
    (session / "002.json").write_text(
        json.dumps({**common, "actions": ["type: folder"]}), encoding="utf-8"
    )
    output = tmp_path / "out.jsonl"
    assert preprocess_dataset("screenagent", tmp_path, output) == 1
    record = read_jsonl(output)[0]
    assert record["task_id"] == "session-1"
    assert record["instruction"] == "Create a folder"
    assert len(record["steps"]) == 2
    assert record["split"] == "test"
    assert record["images"][0].endswith("001.jpg")


def test_preprocessor_errors(tmp_path) -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        preprocess_dataset("unknown", tmp_path, tmp_path / "out")
    with pytest.raises(FileNotFoundError):
        preprocess_dataset("webarena", tmp_path / "missing", tmp_path / "out")
