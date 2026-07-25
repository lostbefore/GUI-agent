from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Box:
    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        if self.right < self.left or self.bottom < self.top:
            raise ValueError("Invalid box: right/bottom must not precede left/top")

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> tuple[int, int]:
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)

    def clamp(self, width: int, height: int) -> Box:
        return Box(
            max(0, min(self.left, width)),
            max(0, min(self.top, height)),
            max(0, min(self.right, width)),
            max(0, min(self.bottom, height)),
        )


@dataclass(frozen=True, slots=True)
class CoordinateMapper:
    """屏幕坐标映射"""

    image_width: int
    image_height: int
    screen_width: int
    screen_height: int
    origin_x: int = 0
    origin_y: int = 0

    def __post_init__(self) -> None:
        if min(self.image_width, self.image_height, self.screen_width, self.screen_height) <= 0:
            raise ValueError("Image and screen dimensions must be positive")

    @property
    def scale_x(self) -> float:
        return self.screen_width / self.image_width

    @property
    def scale_y(self) -> float:
        return self.screen_height / self.image_height

    def image_to_screen(self, point: Point) -> Point:
        return Point(
            self.origin_x + round(point.x * self.scale_x),
            self.origin_y + round(point.y * self.scale_y),
        )

    def box_to_screen(self, box: Box) -> Box:
        start = self.image_to_screen(Point(box.left, box.top))
        end = self.image_to_screen(Point(box.right, box.bottom))
        return Box(start.x, start.y, end.x, end.y)

    def normalized_to_screen(self, x: float, y: float) -> Point:
        if not 0 <= x <= 1 or not 0 <= y <= 1:
            raise ValueError("Normalized coordinates must be between 0 and 1")
        return Point(
            self.origin_x + round(x * self.screen_width),
            self.origin_y + round(y * self.screen_height),
        )
