from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .coordinates import Box


@dataclass(slots=True)
class InputController:
    backend: Any = None
    pause: float = 0.1
    failsafe: bool = True

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

    def move(self, x: int, y: int, *, duration: float = 0.2) -> None:
        self._validate(x, y)
        self.backend.moveTo(x, y, duration=duration)

    def write(self, text: str, *, interval: float = 0.03) -> None:
        self.backend.write(text, interval=interval)

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
