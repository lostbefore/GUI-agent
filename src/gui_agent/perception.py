from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

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
        min_confidence: float = 0.35,
        region_min_area: int = 400,
        region_max_area_ratio: float = 0.4,
        deduplicate_iou: float = 0.72,
    ) -> None:
        if not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1")
        if region_min_area < 1:
            raise ValueError("region_min_area must be positive")
        if not 0 < region_max_area_ratio <= 1:
            raise ValueError("region_max_area_ratio must be in (0, 1]")
        if not 0 <= deduplicate_iou <= 1:
            raise ValueError("deduplicate_iou must be between 0 and 1")
        self.languages = languages
        self.gpu = gpu
        self.capture_engine = capture
        self._reader = ocr_reader
        self.min_confidence = min_confidence
        self.region_min_area = region_min_area
        self.region_max_area_ratio = region_max_area_ratio
        self.deduplicate_iou = deduplicate_iou
        self.last_metrics: dict[str, float | int] = {}

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

    def recognize_text(self, frame: ScreenFrame, min_confidence: float | None = None) -> list[UIElement]:
        threshold = self.min_confidence if min_confidence is None else min_confidence
        results = self.reader.readtext(frame.image)
        elements: list[UIElement] = []
        for polygon, text, confidence in results:
            if float(confidence) < threshold:
                continue
            points = np.asarray(polygon, dtype=float)
            image_box = Box(round(points[:, 0].min()), round(points[:, 1].min()), round(points[:, 0].max()), round(points[:, 1].max()))
            elements.append(UIElement(frame.mapper.box_to_screen(image_box), "text", str(text), float(confidence)))
        return elements

    def detect_ui_regions(self, frame: ScreenFrame, *, min_area: int | None = None, max_area_ratio: float | None = None) -> list[UIElement]:
        min_area = self.region_min_area if min_area is None else min_area
        max_area_ratio = self.region_max_area_ratio if max_area_ratio is None else max_area_ratio
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
            elements.append(UIElement(frame.mapper.box_to_screen(Box(x, y, x + width, y + height)), "region"))
        return elements

    @staticmethod
    def box_iou(first: Box, second: Box) -> float:
        left, top = max(first.left, second.left), max(first.top, second.top)
        right, bottom = min(first.right, second.right), min(first.bottom, second.bottom)
        overlap = max(0, right - left) * max(0, bottom - top)
        union = first.width * first.height + second.width * second.height - overlap
        return overlap / union if union else 0.0

    def _deduplicate(self, elements: Iterable[UIElement]) -> list[UIElement]:
        kept: list[UIElement] = []
        ordered = sorted(elements, key=lambda item: (item.kind != "text", -item.confidence, -(item.box.width * item.box.height)))
        for item in ordered:
            normalized_text = item.text.strip().casefold()
            duplicate = False
            for existing in kept:
                if item.kind != existing.kind:
                    continue
                if item.kind == "text" and normalized_text != existing.text.strip().casefold():
                    continue
                if self.box_iou(item.box, existing.box) >= self.deduplicate_iou:
                    duplicate = True
                    break
            if not duplicate:
                kept.append(item)
        return kept

    def analyze(self, frame: ScreenFrame) -> list[UIElement]:
        started = perf_counter()
        raw = self.recognize_text(frame) + self.detect_ui_regions(frame)
        elements = self._deduplicate(raw)
        self.last_metrics = {"raw_elements": len(raw), "elements": len(elements), "elapsed_ms": round((perf_counter() - started) * 1000, 3)}
        return elements

    @staticmethod
    def draw_boxes(frame: ScreenFrame, elements: Iterable[UIElement]) -> np.ndarray:
        canvas = frame.image.copy()
        for element in elements:
            mapper = frame.mapper
            left = round((element.box.left - mapper.origin_x) / mapper.scale_x)
            top = round((element.box.top - mapper.origin_y) / mapper.scale_y)
            right = round((element.box.right - mapper.origin_x) / mapper.scale_x)
            bottom = round((element.box.bottom - mapper.origin_y) / mapper.scale_y)
            color = (40, 200, 40) if element.kind == "text" else (255, 150, 30)
            cv2.rectangle(canvas, (left, top), (right, bottom), color, 2)
            cv2.putText(canvas, element.text or element.kind, (left, max(15, top - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        return canvas

    def save_annotated(self, frame: ScreenFrame, elements: Iterable[UIElement], output: str | Path) -> Path:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(path), self.draw_boxes(frame, elements)):
            raise OSError(f"Could not write image to {path}")
        return path