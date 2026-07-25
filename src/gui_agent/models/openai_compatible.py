from __future__ import annotations

import base64
import json
import mimetypes
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import ModelResponse


def _image_url(image: str | Path) -> str:
    value = str(image)
    if value.startswith(("http://", "https://", "data:")):
        return value
    # 编码本地图片
    path = Path(value)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class OpenAICompatibleVisionModel:
    """接口模型后端"""

    def __init__(
        self,
        model: str,
        *,
        base_url: str = "http://127.0.0.1:8000/v1",
        api_key: str | None = None,
        api_key_env: str = "GUI_AGENT_API_KEY",
        timeout: float = 120,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv(api_key_env, "")
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(
        self,
        prompt: str,
        images: Sequence[str | Path] = (),
        *,
        system_prompt: str | None = None,
    ) -> ModelResponse:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        content.extend(
            {"type": "image_url", "image_url": {"url": _image_url(image)}} for image in images
        )
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(f"{self.base_url}/chat/completions", payload, headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Model API returned HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise RuntimeError(f"Could not connect to model API: {error.reason}") from error
        try:
            text = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Invalid model API response: {raw}") from error
        return ModelResponse(
            str(text), str(raw.get("model", self.model)), raw.get("usage", {}), raw
        )
