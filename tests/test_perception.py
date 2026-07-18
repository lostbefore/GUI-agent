import numpy as np

from gui_agent.coordinates import Box, CoordinateMapper
from gui_agent.perception import DesktopPerception
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
