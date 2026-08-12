from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = (
    "You are a desktop GUI agent. Return JSON actions only. "
    "Use {\"actions\":[{\"action\":\"...\",\"target\":\"...\",\"value\":\"...\"}]}."
)


@dataclass(slots=True)
class SFTExample:
    example_id: str
    dataset: str
    source_split: str
    instruction: str
    response: str
    image: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _records(paths: Iterable[str | Path]) -> Iterator[dict[str, Any]]:
    for source in paths:
        path = Path(source)
        with path.open("r", encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"Invalid JSONL at {path}:{number}") from error
                if isinstance(record, dict):
                    yield record


def _action(step: dict[str, Any]) -> dict[str, str] | None:
    name = str(step.get("action", "")).strip().lower()
    if not name or name == "unknown":
        return None
    result = {"action": name}
    for key in ("target", "value"):
        value = str(step.get(key, "")).strip()
        if value:
            result[key] = value
    return result


def _image(record: dict[str, Any]) -> str | None:
    for image in record.get("images", []):
        path = Path(str(image))
        if path.is_file():
            return str(path)
    return None


def record_to_example(record: dict[str, Any], *, max_actions: int = 6) -> SFTExample | None:
    instruction = str(record.get("instruction", "")).strip()
    steps = record.get("steps", [])
    if not instruction or not isinstance(steps, list):
        return None
    actions = [_action(step) for step in steps if isinstance(step, dict)]
    actions = [action for action in actions if action]
    if not actions:
        return None
    dataset = str(record.get("dataset", "unknown")).strip() or "unknown"
    task_id = str(record.get("task_id", "unknown")).strip() or "unknown"
    return SFTExample(
        example_id=f"{dataset}:{task_id}",
        dataset=dataset,
        source_split=str(record.get("split", "unknown")).strip() or "unknown",
        instruction=instruction,
        response=json.dumps({"actions": actions[:max_actions]}, ensure_ascii=False),
        image=_image(record),
    )


def _validation(example: SFTExample, ratio: float, seed: int) -> bool:
    digest = hashlib.sha256(f"{seed}:{example.example_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64 < ratio


def build_sft_dataset(
    inputs: Iterable[str | Path],
    output_dir: str | Path,
    *,
    validation_ratio: float = 0.1,
    seed: int = 42,
    limit: int | None = None,
    max_actions: int = 6,
    source_splits: Iterable[str] = ("train",),
) -> dict[str, int]:
    if not 0 < validation_ratio < 1:
        raise ValueError("validation_ratio must be between 0 and 1")
    allowed_splits = frozenset(value.strip().lower() for value in source_splits if value.strip())
    if not allowed_splits:
        raise ValueError("source_splits must not be empty")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    counts = {"train": 0, "validation": 0, "skipped": 0}
    seen: set[str] = set()
    with (output / "train.jsonl").open("w", encoding="utf-8") as train, (
        output / "validation.jsonl"
    ).open("w", encoding="utf-8") as validation:
        for record in _records(inputs):
            source_split = str(record.get("split", "unknown")).strip().lower()
            if source_split not in allowed_splits:
                counts["skipped"] += 1
                continue
            example = record_to_example(record, max_actions=max_actions)
            if example is None or example.example_id in seen:
                counts["skipped"] += 1
                continue
            seen.add(example.example_id)
            key = "validation" if _validation(example, validation_ratio, seed) else "train"
            handle = validation if key == "validation" else train
            handle.write(json.dumps(example.to_dict(), ensure_ascii=False) + "\n")
            counts[key] += 1
            if limit is not None and counts["train"] + counts["validation"] >= limit:
                break
    if counts["train"] + counts["validation"] < 2:
        raise ValueError("Need at least two valid training examples")
    train_path = output / "train.jsonl"
    validation_path = output / "validation.jsonl"
    if not counts["validation"]:
        rows = train_path.read_text(encoding="utf-8").splitlines()
        validation_path.write_text(rows[-1] + "\n", encoding="utf-8")
        train_path.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
        counts["train"] -= 1
        counts["validation"] = 1
    if not counts["train"]:
        rows = validation_path.read_text(encoding="utf-8").splitlines()
        train_path.write_text(rows[-1] + "\n", encoding="utf-8")
        validation_path.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
        counts["train"] = 1
        counts["validation"] -= 1
    return counts


def load_examples(path: str | Path) -> list[SFTExample]:
    try:
        return [SFTExample(**record) for record in _records([path])]
    except TypeError as error:
        raise ValueError(f"Invalid SFT example in {path}") from error