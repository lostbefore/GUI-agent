from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


class ProgressRecorder:
    """Structured progress and runtime log writer."""

    def __init__(self, path: str | Path, log_path: str | Path | None = None) -> None:
        self.path = Path(path)
        self.log_path = Path(log_path) if log_path else self.path.with_suffix(".log")
        self._logger: logging.Logger | None = None

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            logger = logging.getLogger(f"gui_agent.runtime.{self.log_path.resolve()}")
            logger.setLevel(logging.INFO)
            logger.propagate = False
            if not logger.handlers:
                handler = logging.FileHandler(self.log_path, encoding="utf-8")
                handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
                logger.addHandler(handler)
            self._logger = logger
        return self._logger

    def record(self, stage: str, **details: Any) -> dict[str, Any]:
        event = {
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "stage": stage,
            **details,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(event, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")
        self.logger.info(serialized)
        return event


def read_latest_progress(path: str | Path) -> dict[str, Any] | None:
    source = Path(path)
    if not source.is_file():
        return None
    for line in reversed(source.read_text(encoding="utf-8").splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def format_progress(event: dict[str, Any] | None) -> str:
    if not event:
        return "GUI Agent\n\u7b49\u5f85\u8fd0\u884c"
    labels = {
        "starting": "Starting",
        "observing": "Capturing screen",
        "observed": "Screen captured",
        "perception_finished": "Perception complete",
        "planning": "Planning task",
        "planned": "Plan ready",
        "deciding": "Choosing action",
        "decision_ready": "Action ready",
        "action_finished": "Action complete",
        "retrying": "Retrying after failure",
        "state_checked": "Screen state checked",
        "finished": "Run finished",
        "error": "Run failed",
        "interrupted": "Run interrupted",
    }
    stage = str(event.get("stage", ""))
    parts = ["GUI Agent", labels.get(stage, stage or "Running")]
    if event.get("index") is not None:
        parts[-1] += f"  \u7b2c{event['index']}\u6b65"
    if event.get("attempt", 0):
        parts[-1] += f"  \u5c1d\u8bd5{event['attempt']}"
    if event.get("action"):
        parts.append(f"action: {event['action']}")
    if event.get("status"):
        parts.append(f"status: {event['status']}")
    if event.get("message"):
        parts.append(str(event["message"]))
    return "\n".join(parts)
