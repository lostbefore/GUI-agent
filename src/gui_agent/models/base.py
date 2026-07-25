from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True)
class ModelResponse:
    text: str
    model: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    raw: Any = None


class VisionModel(Protocol):
    def generate(
        self,
        prompt: str,
        images: Sequence[str | Path] = (),
        *,
        system_prompt: str | None = None,
    ) -> ModelResponse: ...
