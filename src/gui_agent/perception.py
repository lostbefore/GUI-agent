from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np

from .coordinates import Box
from .screen import ScreenCapture, ScreenFrame


@dataclass(frozen=True, slots=True)
class UIElement:
    box: Box
    kind: str
    text: str = ""
    confidence: float = 0.0


class DesktopPerception:
    def __init__(
        self,
        languages: tuple[str, ...] = ("ch_sim", "en"),
        *,
        gpu: bool = False,
        capture: ScreenCapture | None = None,
        ocr_reader: Any | None = None,
    ) -> None:
        self.languages = languages
        self.gpu = gpu
        self.capture_engine = capture
        self._reader = ocr_reader

    @property
    def reader(self):
        if self._reader is None:
            import easyocr

            self._reader = easyocr.Reader(list(self.languages), gpu=self.gpu)
        return self._reader

    def capture(self, **kwargs) -> ScreenFrame:
        if self.capture_engine is None:
            self.capture_engine = ScreenCapture()
        return self.capture_engine.capture(**kwargs)

    def recognize_text(self, frame: ScreenFrame, min_confidence: float = 0.35) -> list[UIElement]:
        results = self.reader.readtext(frame.image)
        elements: list[UIElement] = []
        for polygon, text, confidence in results:
            if float(confidence) < min_confidence:
                continue
            points = np.asarray(polygon, dtype=float)
            image_box = Box(
                round(points[:, 0].min()),
                round(points[:, 1].min()),
                round(points[:, 0].max()),
                round(points[:, 1].max()),
            )
            elements.append(
                UIElement(frame.mapper.box_to_screen(image_box), "text", str(text), float(confidence))
            )
        return elements

    def detect_ui_regions(
        self,
        frame: ScreenFrame,
        *,
        min_area: int = 400,
        max_area_ratio: float = 0.4,
    ) -> list[UIElement]:
        gray = cv2.cvtColor(frame.image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 60, 160)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        image_area = frame.image.shape[0] * frame.image.shape[1]
        elements: list[UIElement] = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = width * height
            if area < min_area or area > image_area * max_area_ratio:
                continue
            box = frame.mapper.box_to_screen(Box(x, y, x + width, y + height))
            elements.append(UIElement(box, "region"))
        return elements

    def analyze(self, frame: ScreenFrame) -> list[UIElement]:
        return self.recognize_text(frame) + self.detect_ui_regions(frame)

    @staticmethod
    def draw_boxes(frame: ScreenFrame, elements: Iterable[UIElement]) -> np.ndarray:
        canvas = frame.image.copy()
        for element in elements:
            screen_box = element.box
            mapper = frame.mapper
            left = round((screen_box.left - mapper.origin_x) / mapper.scale_x)
            top = round((screen_box.top - mapper.origin_y) / mapper.scale_y)
            right = round((screen_box.right - mapper.origin_x) / mapper.scale_x)
            bottom = round((screen_box.bottom - mapper.origin_y) / mapper.scale_y)
            color = (40, 200, 40) if element.kind == "text" else (255, 150, 30)
            cv2.rectangle(canvas, (left, top), (right, bottom), color, 2)
            label = element.text or element.kind
            cv2.putText(
                canvas,
                label,
                (left, max(15, top - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )
        return canvas

    def save_annotated(
        self, frame: ScreenFrame, elements: Iterable[UIElement], output: str | Path
    ) -> Path:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(path), self.draw_boxes(frame, elements)):
            raise OSError(f"Could not write image to {path}")
        return path
