from pathlib import Path

from gui_agent.coordinates import Box
from gui_agent.perception import UIElement
from gui_agent.web_demo import capture_page


class FakePerception:
    def capture(self):
        return object()

    def analyze(self, frame):
        return [
            UIElement(Box(0, 0, 10, 10), "text", "网页标题", 0.9),
            UIElement(Box(0, 0, 10, 10), "text", "网页标题", 0.8),
            UIElement(Box(0, 0, 10, 10), "region"),
        ]

    def save_annotated(self, frame, elements, path):
        output = Path(path)
        output.write_bytes(b"image")
        return output


def test_capture_page_saves_visible_text_and_artifacts(tmp_path) -> None:
    result = capture_page(tmp_path, "page-01", perception=FakePerception())
    assert result.text_count == 1
    assert Path(result.image).is_file()
    assert '"网页标题"' in Path(result.record).read_text(encoding="utf-8")
    assert "可见文字数量：1" in Path(result.report).read_text(encoding="utf-8")
