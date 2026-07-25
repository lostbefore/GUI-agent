from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from .schema import ActionStep, GUITaskRecord


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _items(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        return (item for item in payload if isinstance(item, dict))
    if isinstance(payload, dict):
        for key in ("tasks", "data", "records", "examples"):
            if isinstance(payload.get(key), list):
                return (item for item in payload[key] if isinstance(item, dict))
        return (payload,)
    return ()


def _first(item: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, "", []):
            return value
    return default


def _split_from_path(path: Path) -> str:
    lowered = [part.lower() for part in path.parts]
    for split in ("test_domain", "test_website", "test_task", "train", "test", "validation"):
        if split in lowered or any(part.startswith(split) for part in lowered):
            return split
    return "unknown"


class DatasetPreprocessor(ABC):
    name: str

    @abstractmethod
    def iter_records(self, source: Path) -> Iterator[GUITaskRecord]: ...

    def process(self, source: Path, output: Path, *, limit: int | None = None) -> int:
        if not source.exists():
            raise FileNotFoundError(f"Dataset source does not exist: {source}")
        output.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with output.open("w", encoding="utf-8") as handle:
            for record in self.iter_records(source):
                handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                count += 1
                if limit is not None and count >= limit:
                    break
        return count


class WebArenaPreprocessor(DatasetPreprocessor):
    name = "webarena"

    def iter_records(self, source: Path) -> Iterator[GUITaskRecord]:
        config_root = source / "config_files" if (source / "config_files").exists() else source
        for path in sorted(config_root.rglob("*.json")):
            for index, item in enumerate(_items(_read_json(path))):
                instruction = str(_first(item, "intent", "instruction", "task"))
                if not instruction:
                    continue
                task_id = str(_first(item, "task_id", "id", default=f"{path.stem}-{index}"))
                metadata = {
                    key: item[key]
                    for key in ("sites", "start_url", "require_login", "eval")
                    if key in item
                }
                yield GUITaskRecord(
                    self.name, task_id, _split_from_path(path), instruction, metadata=metadata
                )


class Mind2WebPreprocessor(DatasetPreprocessor):
    name = "mind2web"

    @staticmethod
    def _step(action: dict[str, Any]) -> ActionStep:
        operation = action.get("operation") or {}
        action_name = _first(operation, "op", "original_op", default="unknown")
        value = _first(operation, "value", "original_value")
        target = _first(action, "target", "element", "element_repr")
        if not target:
            positives = action.get("pos_candidates") or []
            if positives and isinstance(positives[0], dict):
                target = _first(positives[0], "backend_node_id", "tag", "text")
        kept = {
            key: action[key] for key in ("action_uid", "cleaned_html", "raw_html") if key in action
        }
        return ActionStep(str(action_name).lower(), str(target), str(value), metadata=kept)

    def iter_records(self, source: Path) -> Iterator[GUITaskRecord]:
        # 兼容数据目录
        data_root = source / "data" if (source / "data").exists() else source
        for path in sorted(data_root.rglob("*.json")):
            for index, item in enumerate(_items(_read_json(path))):
                instruction = str(_first(item, "confirmed_task", "task", "instruction", "intent"))
                if not instruction:
                    continue
                task_id = str(
                    _first(item, "annotation_id", "task_id", "id", default=f"{path.stem}-{index}")
                )
                actions = _first(item, "actions", "action_reprs", default=[])
                steps = [
                    self._step(action)
                    if isinstance(action, dict)
                    else ActionStep("unknown", value=str(action))
                    for action in actions
                ]
                metadata = {
                    key: item[key] for key in ("website", "domain", "subdomain") if key in item
                }
                yield GUITaskRecord(
                    self.name,
                    task_id,
                    _split_from_path(path),
                    instruction,
                    steps,
                    metadata=metadata,
                )


class ScreenAgentPreprocessor(DatasetPreprocessor):
    name = "screenagent"
    image_suffixes = frozenset({".png", ".jpg", ".jpeg", ".webp"})

    @staticmethod
    def _steps(item: dict[str, Any], base: Path) -> list[ActionStep]:
        raw_steps = _first(item, "steps", "actions", "trajectory", default=[])
        steps: list[ActionStep] = []
        for raw in raw_steps:
            if not isinstance(raw, dict):
                steps.append(ActionStep("unknown", value=str(raw)))
                continue
            image = _first(raw, "image", "screenshot", "image_path", default=None)
            if image:
                image = str((base / str(image)).resolve())
            steps.append(
                ActionStep(
                    str(_first(raw, "action", "action_type", "type", default="unknown")).lower(),
                    str(_first(raw, "target", "position", "coordinate")),
                    str(_first(raw, "value", "text", "input")),
                    image,
                    {key: raw[key] for key in ("reflection", "thought") if key in raw},
                )
            )
        return steps

    def iter_records(self, source: Path) -> Iterator[GUITaskRecord]:
        root = source / "ScreenAgent" if (source / "ScreenAgent").exists() else source
        seen: set[Path] = set()
        session_files: dict[Path, list[Path]] = {}
        for path in sorted(root.rglob("*.json")):
            session_files.setdefault(path.parent, []).append(path)

        for session_dir, paths in session_files.items():
            instruction = ""
            task_id = session_dir.name
            steps: list[ActionStep] = []
            referenced_images: list[str] = []
            for path in paths:
                for item in _items(_read_json(path)):
                    if not instruction:
                        instruction = str(
                            _first(
                                item,
                                "task_prompt_en",
                                "task_prompt",
                                "task_prompt_zh",
                                "instruction",
                                "task",
                                "goal",
                                "query",
                            )
                        )
                    task_id = str(_first(item, "session_id", "task_id", "id", default=task_id))
                    image_name = _first(item, "saved_image_name", default="")
                    if image_name:
                        candidate = session_dir / "images" / str(image_name)
                        referenced_images.append(str(candidate.resolve()))
                    steps.extend(self._steps(item, session_dir))
            if not instruction:
                continue
            seen.add(session_dir)
            discovered_images = [
                str(image.resolve())
                for image in session_dir.rglob("*")
                if image.suffix.lower() in self.image_suffixes
            ]
            images = sorted(set(referenced_images + discovered_images))
            yield GUITaskRecord(
                self.name,
                task_id,
                _split_from_path(session_dir),
                instruction,
                steps,
                images,
                {"source_files": [str(path.resolve()) for path in paths]},
            )

        # 兼容文本任务
        for task_file in sorted(root.rglob("task*.txt")):
            if task_file.parent in seen:
                continue
            instruction = task_file.read_text(encoding="utf-8").strip()
            if not instruction:
                continue
            images = sorted(
                str(image.resolve())
                for image in task_file.parent.rglob("*")
                if image.suffix.lower() in self.image_suffixes
            )
            yield GUITaskRecord(
                self.name,
                task_file.parent.name,
                _split_from_path(task_file),
                instruction,
                images=images,
                metadata={"source_file": str(task_file.resolve())},
            )


PREPROCESSORS: dict[str, type[DatasetPreprocessor]] = {
    "screenagent": ScreenAgentPreprocessor,
    "webarena": WebArenaPreprocessor,
    "mind2web": Mind2WebPreprocessor,
}


def preprocess_dataset(
    dataset: str, source: str | Path, output: str | Path, *, limit: int | None = None
) -> int:
    try:
        processor = PREPROCESSORS[dataset.lower()]()
    except KeyError as error:
        raise ValueError(f"Unsupported dataset: {dataset}") from error
    return processor.process(Path(source), Path(output), limit=limit)
