from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ActionStep:
    action: str
    target: str = ""
    value: str = ""
    image: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GUITaskRecord:
    dataset: str
    task_id: str
    split: str
    instruction: str
    steps: list[ActionStep] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.dataset.strip():
            raise ValueError("dataset must not be empty")
        if not self.task_id.strip():
            raise ValueError("task_id must not be empty")
        if not self.instruction.strip():
            raise ValueError(f"instruction must not be empty for {self.task_id}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "dataset": self.dataset,
            "task_id": self.task_id,
            "split": self.split,
            "instruction": self.instruction,
            "steps": [step.to_dict() for step in self.steps],
            "images": self.images,
            "metadata": self.metadata,
        }
