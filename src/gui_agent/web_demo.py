from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .perception import DesktopPerception


@dataclass(frozen=True, slots=True)
class WebCapture:
    label: str
    image: str
    record: str
    report: str
    text_count: int


def _safe_label(label: str) -> str:
    if not label or Path(label).name != label or label in {".", ".."}:
        raise ValueError("标签必须是文件名")
    return label


def capture_page(
    output_dir: str | Path,
    label: str,
    *,
    perception: DesktopPerception | None = None,
) -> WebCapture:
    label = _safe_label(label)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    perception = perception or DesktopPerception()
    frame = perception.capture()
    elements = perception.analyze(frame)
    texts = []
    seen: set[str] = set()
    for element in elements:
        text = element.text.strip()
        key = text.casefold()
        if element.kind == "text" and text and key not in seen:
            seen.add(key)
            texts.append(text)
    texts = texts[:50]
    image = perception.save_annotated(frame, elements, output / f"{label}.png")
    record = output / f"{label}.json"
    report = output / f"{label}.md"
    payload = {
        "label": label,
        "image": str(image),
        "text_count": len(texts),
        "visible_text": texts,
    }
    record.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report.write_text(
        "\n".join(
            [
                f"# 网页摘取 {label}",
                "",
                f"- 可见文字数量：{len(texts)}",
                f"- 标注图片：{image.name}",
                "",
                "## 可见文字",
                "",
                *[f"- {text}" for text in texts],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return WebCapture(label, str(image), str(record), str(report), len(texts))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="网页可见文字摘取")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--label", default="page")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    capture = capture_page(args.output_dir, args.label)
    print(json.dumps(asdict(capture), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
