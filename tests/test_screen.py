import numpy as np
import pytest

from gui_agent.coordinates import Box, Point
from gui_agent.screen import ScreenCapture


class FakeScreenBackend:
    def __init__(self, width=100, height=60):
        self.width = width
        self.height = height
        self.regions = []

    def size(self):
        return self.width, self.height

    def screenshot(self, region=None):
        self.regions.append(region)
        width, height = (self.width, self.height) if region is None else region[2:]
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[..., 0] = 255
        return image


def test_full_screen_capture_and_color_conversion() -> None:
    backend = FakeScreenBackend()
    frame = ScreenCapture(backend).capture()
    assert frame.image.shape == (60, 100, 3)
    assert tuple(frame.image[0, 0]) == (0, 0, 255)
    assert backend.regions == [None]
    assert frame.mapper.image_to_screen(Point(50, 30)) == Point(50, 30)


def test_scaled_region_capture_maps_to_original_screen() -> None:
    backend = FakeScreenBackend()
    frame = ScreenCapture(backend).capture(Box(10, 5, 90, 45), scale=0.5)
    assert frame.image.shape == (20, 40, 3)
    assert backend.regions == [(10, 5, 80, 40)]
    assert frame.mapper.image_to_screen(Point(20, 10)) == Point(50, 25)


def test_target_size_and_region_clipping() -> None:
    backend = FakeScreenBackend()
    frame = ScreenCapture(backend).capture(Box(-10, -10, 30, 20), target_size=(60, 40))
    assert backend.regions == [(0, 0, 30, 20)]
    assert frame.image.shape == (40, 60, 3)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"scale": 0}, "scale must be positive"),
        ({"target_size": (0, 10)}, "dimensions must be positive"),
        ({"region": Box(200, 100, 300, 200)}, "region is empty"),
    ],
)
def test_capture_rejects_invalid_arguments(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        ScreenCapture(FakeScreenBackend()).capture(**kwargs)


def test_default_backend_is_pyautogui() -> None:
    import pyautogui

    assert ScreenCapture().backend is pyautogui
