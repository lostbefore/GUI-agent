from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

from .coordinates import Box, CoordinateMapper


class ScreenshotBackend(Protocol):
    def screenshot(self, region: tuple[int, int, int, int] | None = None): ...

    def size(self): ...


@dataclass(slots=True)
class ScreenFrame:
    image: np.ndarray
    mapper: CoordinateMapper


class ScreenCapture:
    def __init__(self, backend: ScreenshotBackend | None = None) -> None:
        if backend is None:
            import pyautogui

            backend = pyautogui
        self.backend = backend

    def capture(
        self,
        region: Box | None = None,
        *,
        scale: float = 1.0,
        target_size: tuple[int, int] | None = None,
    ) -> ScreenFrame:
        if scale <= 0:
            raise ValueError("scale must be positive")
        screen_width, screen_height = map(int, self.backend.size())
        if region is None:
            origin_x = origin_y = 0
            source_width, source_height = screen_width, screen_height
            raw_region = None
        else:
            clipped = region.clamp(screen_width, screen_height)
            origin_x, origin_y = clipped.left, clipped.top
            source_width, source_height = clipped.width, clipped.height
            if source_width == 0 or source_height == 0:
                raise ValueError("Capture region is empty")
            raw_region = (origin_x, origin_y, source_width, source_height)

        rgb = np.asarray(self.backend.screenshot(region=raw_region))
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        if target_size is not None:
            out_width, out_height = target_size
        else:
            out_width = max(1, round(source_width * scale))
            out_height = max(1, round(source_height * scale))
        if out_width <= 0 or out_height <= 0:
            raise ValueError("target_size dimensions must be positive")
        if (out_width, out_height) != (source_width, source_height):
            interpolation = cv2.INTER_AREA if out_width < source_width else cv2.INTER_CUBIC
            bgr = cv2.resize(bgr, (out_width, out_height), interpolation=interpolation)

        mapper = CoordinateMapper(
            out_width, out_height, source_width, source_height, origin_x, origin_y
        )
        return ScreenFrame(bgr, mapper)
