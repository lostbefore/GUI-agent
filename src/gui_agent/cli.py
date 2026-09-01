from __future__ import annotations

import argparse
import sys

from PyQt5.QtWidgets import QApplication

from .overlay import BoundingBoxOverlay
from .perception import DesktopPerception


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Desktop GUI perception tools")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect = subparsers.add_parser("inspect", help="Capture, analyze and save an annotated image")
    inspect.add_argument("--output", default="old/artifacts/screen.png")
    inspect.add_argument("--scale", type=float, default=1.0)
    subparsers.add_parser("overlay", help="Analyze the desktop and display click-through boxes")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    perception = DesktopPerception()
    frame = perception.capture(scale=getattr(args, "scale", 1.0))
    elements = perception.analyze(frame)
    if args.command == "inspect":
        path = perception.save_annotated(frame, elements, args.output)
        print(f"Detected {len(elements)} elements; wrote {path}")
        return 0

    app = QApplication(sys.argv)
    overlay = BoundingBoxOverlay(elements)
    overlay.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
