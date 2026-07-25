from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib

from gui_agent.models import OpenAICompatibleVisionModel, TransformersVisionModel


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("rb") as handle:
        return tomllib.load(handle)


def build_model(config: dict[str, Any]):
    model = config.get("model", config)
    backend = str(model.get("backend", "openai_compatible"))
    if backend == "openai_compatible":
        return OpenAICompatibleVisionModel(
            str(model["name"]),
            base_url=str(model.get("base_url", "http://127.0.0.1:8000/v1")),
            api_key_env=str(model.get("api_key_env", "GUI_AGENT_API_KEY")),
            timeout=float(model.get("timeout", 120)),
            temperature=float(model.get("temperature", 0)),
            max_tokens=int(model.get("max_tokens", 1024)),
        )
    if backend == "transformers":
        return TransformersVisionModel(
            str(model["path"]),
            device_map=str(model.get("device_map", "auto")),
            dtype=str(model.get("dtype", "auto")),
            max_new_tokens=int(model.get("max_new_tokens", 512)),
            trust_remote_code=bool(model.get("trust_remote_code", False)),
            load_in_4bit=bool(model.get("load_in_4bit", False)),
            compute_dtype=str(model.get("compute_dtype", "bfloat16")),
            max_image_pixels=(
                int(model["max_image_pixels"]) if "max_image_pixels" in model else None
            ),
        )
    raise ValueError(f"Unsupported model backend: {backend}")
