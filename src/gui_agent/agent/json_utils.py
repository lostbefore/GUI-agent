from __future__ import annotations

import json
import re
from typing import Any

from gui_agent.models.base import VisionModel

JSON_REPAIR_PROMPT = """You repair malformed JSON.
Return one valid JSON object only. Preserve the original meaning and values.
Do not add explanations or Markdown fences."""


def is_likely_truncated(text: str) -> bool:
    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.count("```") < 2:
        return True
    start = cleaned.find("{")
    return start >= 0 and not cleaned.rstrip().endswith("}")


def _escape_inner_quotes(text: str) -> str:
    output: list[str] = []
    inside = False
    escaped = False
    for index, character in enumerate(text):
        if character == '"' and not escaped:
            if not inside:
                inside = True
            else:
                following = index + 1
                while following < len(text) and text[following].isspace():
                    following += 1
                if following >= len(text) or text[following] in ",:}]":
                    inside = False
                else:
                    output.append("\\")
            output.append(character)
            escaped = False
            continue
        output.append(character)
        if character == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    return "".join(output)


def _repair_json(text: str) -> str:
    repaired = re.sub(r",\s*([}\]])", r"\1", text)
    value = r'("(?:\\.|[^"\\])*"|true|false|null|-?\d+(?:\.\d+)?|[}\]])'
    next_key = r'("(?:\\.|[^"\\])*"\s*:)'
    repaired = re.sub(
        rf"{value}(\s+)(?={next_key})",
        lambda match: f"{match.group(1)},{match.group(2)}",
        repaired,
    )
    repaired = re.sub(r"}([\s\r\n]+)(?={)", r"},\1", repaired)
    return _escape_inner_quotes(repaired)


def _load_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = _repair_json(text)
        if repaired != text:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass
        raise


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    # 兼容代码块
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        value = _load_json(cleaned)
    except json.JSONDecodeError:
        # 提取最外对象
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model response does not contain a JSON object") from None
        try:
            value = _load_json(cleaned[start : end + 1])
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON model response: {error}") from error
    if not isinstance(value, dict):
        raise TypeError("Model response JSON must be an object")
    return value


def parse_json_response(model: VisionModel, text: str) -> tuple[dict[str, Any], str | None]:
    try:
        return parse_json_object(text), None
    except (TypeError, ValueError):
        corrected = model.generate(
            f"Repair this response:\n{text}",
            system_prompt=JSON_REPAIR_PROMPT,
        )
        return parse_json_object(corrected.text), corrected.text
