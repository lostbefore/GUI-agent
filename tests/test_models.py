import base64
import json
from urllib.error import URLError

import pytest

from gui_agent.agent.config import build_model, load_config
from gui_agent.models.openai_compatible import OpenAICompatibleVisionModel, _image_url
from gui_agent.models.transformers_local import TransformersVisionModel


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


def test_image_url_supports_remote_and_local(tmp_path) -> None:
    assert _image_url("https://example.com/a.png") == "https://example.com/a.png"
    image = tmp_path / "a.png"
    image.write_bytes(b"abc")
    assert _image_url(image) == "data:image/png;base64," + base64.b64encode(b"abc").decode()


def test_openai_compatible_request(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeHTTPResponse(
            {"model": "vlm", "choices": [{"message": {"content": "done"}}], "usage": {"x": 1}}
        )

    monkeypatch.setattr("gui_agent.models.openai_compatible.urlopen", fake_urlopen)
    image = tmp_path / "screen.jpg"
    image.write_bytes(b"jpeg")
    model = OpenAICompatibleVisionModel("vlm", api_key="secret", timeout=5)
    response = model.generate("inspect", [image], system_prompt="system")
    body = json.loads(captured["request"].data)
    assert response.text == "done"
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["content"][1]["type"] == "image_url"
    assert captured["request"].get_header("Authorization") == "Bearer secret"


def test_openai_compatible_connection_error(monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise URLError("offline")

    monkeypatch.setattr("gui_agent.models.openai_compatible.urlopen", fail)
    with pytest.raises(RuntimeError, match="Could not connect"):
        OpenAICompatibleVisionModel("vlm").generate("test")


def test_config_loads_and_builds_backends(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        '[model]\nbackend="openai_compatible"\nname="vlm"\nbase_url="http://localhost/v1"',
        encoding="utf-8",
    )
    api = build_model(load_config(path))
    assert isinstance(api, OpenAICompatibleVisionModel)
    local = build_model(
        {
            "backend": "transformers",
            "path": "models/vlm",
            "load_in_4bit": True,
            "compute_dtype": "bfloat16",
            "max_image_pixels": 1048576,
        }
    )
    assert isinstance(local, TransformersVisionModel)
    assert local.load_in_4bit is True
    assert local.max_image_pixels == 1048576
    with pytest.raises(ValueError, match="Unsupported"):
        build_model({"backend": "other"})
