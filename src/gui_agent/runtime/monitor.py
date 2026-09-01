from __future__ import annotations

import argparse
import ctypes
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QLabel

from .progress import format_progress, read_latest_progress


def exclude_from_capture(window_id: int) -> bool:
    if sys.platform != "win32":
        return False
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    return bool(user32.SetWindowDisplayAffinity(window_id, 0x11))


class ProgressOverlay(QLabel):
    """进度悬浮窗"""

    def __init__(self, progress_file: str | Path, auto_close: float = 5.0) -> None:
        super().__init__(format_progress(None))
        self.progress_file = Path(progress_file)
        self.auto_close = auto_close
        self._closing = False
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWordWrap(True)
        self.setFixedSize(390, 118)
        self.setStyleSheet(
            "QLabel { background: rgba(18, 22, 30, 220); color: #e8f5e9; "
            "border: 1px solid #4caf50; border-radius: 10px; "
            "padding: 12px; font-size: 14px; }"
        )
        timer = QTimer(self)
        timer.timeout.connect(self.refresh)
        timer.start(400)
        self._timer = timer

    def showEvent(self, event) -> None:
        super().showEvent(event)
        geometry = QApplication.primaryScreen().availableGeometry()
        self.move(geometry.right() - self.width() - 16, geometry.top() + 16)
        if not exclude_from_capture(int(self.winId())):
            QTimer.singleShot(0, QApplication.instance().quit)

    def refresh(self) -> None:
        event = read_latest_progress(self.progress_file)
        self.setText(format_progress(event))
        if not event or self._closing:
            return
        if event.get("stage") in {"finished", "error", "interrupted"}:
            self._closing = True
            QTimer.singleShot(round(self.auto_close * 1000), QApplication.instance().quit)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="桌面任务进度悬浮窗")
    parser.add_argument("--file", required=True, help="进度文件")
    parser.add_argument("--auto-close", type=float, default=5.0, help="结束后关闭秒数")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.auto_close < 0:
        raise ValueError("auto_close must not be negative")
    app = QApplication.instance() or QApplication([])
    overlay = ProgressOverlay(args.file, args.auto_close)
    overlay.show()
    return int(app.exec_())


if __name__ == "__main__":
    raise SystemExit(main())
