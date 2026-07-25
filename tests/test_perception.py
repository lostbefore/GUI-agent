import sys
import types

import cv2
import numpy as np
import pytest

from gui_agent.coordinates import Box, CoordinateMapper
from gui_agent.perception import DesktopPerception, UIElement
from gui_agent.screen import ScreenFrame


class FakeReader:
    def readtext(self, image):
        return [([[10, 10], [50, 10], [50, 30], [10, 30]], "OK", 0.95)]


def test_ocr_boxes_map_back_to_screen() -> None:
    frame = ScreenFrame(
        np.zeros((100, 200, 3), dtype=np.uint8),
        CoordinateMapper(200, 100, 400, 200, 20, 30),
    )
    perception = DesktopPerception(ocr_reader=FakeReader())
    result = perception.recognize_text(frame)
    assert result[0].text == "OK"
    assert result[0].box == Box(40, 50, 120, 90)


def make_frame(width=200, height=100) -> ScreenFrame:
    return ScreenFrame(
        np.zeros((height, width, 3), dtype=np.uint8),
        CoordinateMapper(width, height, width, height),
    )


def test_ocr_filters_low_confidence_results() -> None:
    class Reader:
        def readtext(self, image):
            return [
                ([[0, 0], [10, 0], [10, 10], [0, 10]], "low", 0.2),
                ([[10, 10], [20, 10], [20, 20], [10, 20]], 123, 0.8),
            ]

    result = DesktopPerception(ocr_reader=Reader()).recognize_text(make_frame())
    assert [(item.text, item.confidence) for item in result] == [("123", 0.8)]


def test_reader_is_initialized_once(monkeypatch) -> None:
    calls = []

    class Reader:
        def __init__(self, languages, gpu):
            calls.append((languages, gpu))

    monkeypatch.setitem(sys.modules, "easyocr", types.SimpleNamespace(Reader=Reader))
    perception = DesktopPerception(("en",), gpu=True)
    assert perception.reader is perception.reader
    assert calls == [(["en"], True)]


def test_capture_delegates_to_injected_engine() -> None:
    expected = make_frame()

    class Capture:
        def capture(self, **kwargs):
            assert kwargs == {"scale": 0.5}
            return expected

    assert DesktopPerception(capture=Capture()).capture(scale=0.5) is expected


def test_capture_engine_is_created_lazily(monkeypatch) -> None:
    expected = make_frame()
    created = []

    class Capture:
        def __init__(self):
            created.append(True)

        def capture(self, **kwargs):
            return expected

    monkeypatch.setattr("gui_agent.perception.ScreenCapture", Capture)
    perception = DesktopPerception()
    assert perception.capture() is expected
    assert created == [True]


def test_detect_ui_regions_filters_small_and_oversized_shapes() -> None:
    frame = make_frame(200, 120)
    cv2.rectangle(frame.image, (20, 20), (80, 60), (255, 255, 255), 2)
    result = DesktopPerception(ocr_reader=FakeReader()).detect_ui_regions(
        frame, min_area=100, max_area_ratio=0.5
    )
    assert result
    assert all(item.kind == "region" for item in result)
    assert any(item.box.left <= 20 and item.box.right >= 80 for item in result)


def test_analyze_combines_text_and_regions(monkeypatch) -> None:
    perception = DesktopPerception(ocr_reader=FakeReader())
    text = UIElement(Box(0, 0, 10, 10), "text", "OK", 0.9)
    region = UIElement(Box(20, 20, 40, 40), "region")
    monkeypatch.setattr(perception, "recognize_text", lambda frame: [text])
    monkeypatch.setattr(perception, "detect_ui_regions", lambda frame: [region])
    assert perception.analyze(make_frame()) == [text, region]


def test_draw_boxes_returns_annotated_copy() -> None:
    frame = make_frame()
    elements = [
        UIElement(Box(10, 20, 60, 50), "text", "OK", 0.9),
        UIElement(Box(80, 30, 130, 70), "region"),
    ]
    result = DesktopPerception.draw_boxes(frame, elements)
    assert np.any(result != frame.image)
    assert not np.any(frame.image)


def test_save_annotated_creates_parent_and_image(tmp_path) -> None:
    output = tmp_path / "nested" / "result.png"
    result = DesktopPerception(ocr_reader=FakeReader()).save_annotated(
        make_frame(), [UIElement(Box(5, 5, 30, 20), "text", "OK")], output
    )
    assert result == output
    assert output.exists()
    assert cv2.imread(str(output)).shape == (100, 200, 3)


def test_save_annotated_raises_when_encoder_fails(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cv2, "imwrite", lambda *args: False)
    with pytest.raises(OSError, match="Could not write"):
        DesktopPerception(ocr_reader=FakeReader()).save_annotated(
            make_frame(), [], tmp_path / "failed.png"
        )
