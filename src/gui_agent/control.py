from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import Any

from .coordinates import Box


@dataclass(slots=True)
class InputController:
    backend: Any = None
    pause: float = 0.1
    failsafe: bool = True
    clipboard: Any = None
    window_provider: Any = None

    def __post_init__(self) -> None:
        if self.backend is None:
            import pyautogui

            self.backend = pyautogui
        self.backend.PAUSE = self.pause
        self.backend.FAILSAFE = self.failsafe

    def _validate(self, x: int, y: int) -> None:
        width, height = self.backend.size()
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"Point ({x}, {y}) is outside the {width}x{height} screen")

    def click(self, x: int, y: int, *, button: str = "left", clicks: int = 1) -> None:
        self._validate(x, y)
        self.backend.click(x=x, y=y, button=button, clicks=clicks)

    def click_box(self, box: Box, *, button: str = "left") -> None:
        self.click(*box.center, button=button)

    def maximize_active_window(self) -> bool:
        provider = self.window_provider
        if provider is None:
            import pygetwindow

            provider = pygetwindow
        try:
            window = provider.getActiveWindow()
        except Exception as error:
            raise RuntimeError("无法读取活动窗口") from error
        if window is None:
            raise RuntimeError("未找到活动窗口")
        title = str(getattr(window, "title", "")).casefold()
        if "edge" not in title:
            raise RuntimeError("活动窗口不是 Edge")
        screen_width, screen_height = self.backend.size()
        covers_screen = (
            window.left <= 0
            and window.top <= 0
            and window.width >= screen_width - 8
            and window.height >= screen_height - 8
        )
        if bool(getattr(window, "isMaximized", False)) or covers_screen:
            return False
        window.maximize()
        return True

    def open_box_in_new_tab(self, box: Box) -> None:
        self.backend.keyDown("ctrl")
        self.backend.keyDown("shift")
        try:
            self.click_box(box)
        finally:
            self.backend.keyUp("shift")
            self.backend.keyUp("ctrl")

    def move(self, x: int, y: int, *, duration: float = 0.2) -> None:
        self._validate(x, y)
        self.backend.moveTo(x, y, duration=duration)

    def write(self, text: str, *, interval: float = 0.03) -> None:
        if text.isascii():
            self.backend.write(text, interval=interval)
            return
        if self.clipboard is None:
            import pyperclip

            self.clipboard = pyperclip
        try:
            self.clipboard.copy(text)
        except Exception as error:
            raise RuntimeError("无法通过剪贴板输入中文") from error
        modifier = "command" if platform.system() == "Darwin" else "ctrl"
        self.backend.hotkey(modifier, "v")

    def press(self, key: str, *, presses: int = 1) -> None:
        self.backend.press(key, presses=presses)

    def hotkey(self, *keys: str) -> None:
        self.backend.hotkey(*keys)

    def scroll(self, amount: int, *, x: int | None = None, y: int | None = None) -> None:
        if (x is None) != (y is None):
            raise ValueError("x and y must be provided together")
        if x is not None and y is not None:
            self._validate(x, y)
            self.backend.moveTo(x, y)
        self.backend.scroll(amount)

    def drag(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        *,
        duration: float = 0.5,
        button: str = "left",
    ) -> None:
        self._validate(*start)
        self._validate(*end)
        self.backend.moveTo(*start)
        self.backend.dragTo(*end, duration=duration, button=button)
