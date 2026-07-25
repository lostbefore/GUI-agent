import pytest

from gui_agent.coordinates import Box, CoordinateMapper, Point


def test_scaled_region_mapping() -> None:
    mapper = CoordinateMapper(500, 250, 1000, 500, origin_x=100, origin_y=50)
    assert mapper.image_to_screen(Point(250, 125)) == Point(600, 300)
    assert mapper.box_to_screen(Box(10, 20, 30, 40)) == Box(120, 90, 160, 130)


def test_normalized_mapping_and_validation() -> None:
    mapper = CoordinateMapper(100, 100, 1920, 1080)
    assert mapper.normalized_to_screen(0.5, 0.5) == Point(960, 540)
    with pytest.raises(ValueError):
        mapper.normalized_to_screen(1.1, 0.5)


def test_box_properties_clamp_and_validation() -> None:
    box = Box(-10, -5, 120, 90)
    assert box.width == 130
    assert box.height == 95
    assert box.center == (55, 42)
    assert box.clamp(100, 80) == Box(0, 0, 100, 80)
    with pytest.raises(ValueError, match="Invalid box"):
        Box(10, 0, 5, 10)


@pytest.mark.parametrize("dimensions", [(0, 10, 10, 10), (10, -1, 10, 10)])
def test_mapper_rejects_non_positive_dimensions(dimensions) -> None:
    with pytest.raises(ValueError, match="positive"):
        CoordinateMapper(*dimensions)
