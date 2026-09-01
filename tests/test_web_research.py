import numpy as np

from gui_agent.coordinates import Box, CoordinateMapper
from gui_agent.perception import UIElement
from gui_agent.screen import ScreenFrame
from gui_agent.web_research import find_link_candidates


def test_find_link_candidates_filters_navigation_and_deduplicates() -> None:
    frame = ScreenFrame(
        np.zeros((600, 800, 3), dtype=np.uint8),
        CoordinateMapper(800, 600, 800, 600),
    )
    elements = [
        UIElement(Box(20, 40, 160, 70), "text", "Google Search", 0.9),
        UIElement(Box(80, 180, 300, 210), "text", "GUI Agent Introduction", 0.9),
        UIElement(Box(82, 182, 302, 212), "text", "GUI Agent Introduction", 0.8),
        UIElement(Box(80, 260, 300, 290), "text", "Desktop Automation Guide", 0.8),
    ]
    candidates = find_link_candidates(frame, elements)
    assert [item.text for item in candidates] == [
        "GUI Agent Introduction",
        "Desktop Automation Guide",
    ]


def test_find_link_candidates_skips_ai_summary_region() -> None:
    frame = ScreenFrame(
        np.zeros((600, 800, 3), dtype=np.uint8),
        CoordinateMapper(800, 600, 800, 600),
    )
    elements = [
        UIElement(Box(80, 140, 240, 170), "text", "AI Overview", 0.9),
        UIElement(Box(80, 240, 420, 270), "text", "AI summary content", 0.9),
        UIElement(Box(80, 460, 420, 490), "text", "Reliable Desktop Agent Guide", 0.9),
    ]
    candidates = find_link_candidates(frame, elements)
    assert [item.text for item in candidates] == ["Reliable Desktop Agent Guide"]


def test_find_link_candidates_blocks_browser_prompt() -> None:
    frame = ScreenFrame(
        np.zeros((600, 800, 3), dtype=np.uint8),
        CoordinateMapper(800, 600, 800, 600),
    )
    elements = [
        UIElement(
            Box(180, 180, 600, 220), "text", "Set Microsoft Edge as your default browser", 0.9
        ),
        UIElement(Box(80, 460, 420, 490), "text", "Reliable Desktop Agent Guide", 0.9),
    ]
    assert find_link_candidates(frame, elements) == []


def test_find_link_candidates_skips_sentence_snippets() -> None:
    frame = ScreenFrame(
        np.zeros((600, 800, 3), dtype=np.uint8),
        CoordinateMapper(800, 600, 800, 600),
    )
    elements = [
        UIElement(Box(80, 180, 480, 210), "text", "步骤任务以达成目标的智能软件系统。", 0.9),
        UIElement(Box(80, 260, 420, 290), "text", "Desktop Agent Documentation", 0.9),
    ]
    candidates = find_link_candidates(frame, elements)
    assert [item.text for item in candidates] == ["Desktop Agent Documentation"]


def test_visit_search_results_retries_after_unchanged_candidate(monkeypatch, tmp_path) -> None:
    from gui_agent import web_research

    mapper = CoordinateMapper(800, 600, 800, 600)
    unchanged = ScreenFrame(np.zeros((600, 800, 3), dtype=np.uint8), mapper)
    changed = ScreenFrame(np.full((600, 800, 3), 10, dtype=np.uint8), mapper)
    elements = [
        UIElement(Box(80, 180, 320, 210), "text", "First Result", 0.9),
        UIElement(Box(80, 260, 320, 290), "text", "Second Result", 0.9),
        UIElement(Box(80, 340, 320, 370), "text", "Third Result", 0.9),
    ]

    class Perception:
        def __init__(self) -> None:
            self.frames = iter([unchanged, unchanged, unchanged, changed, unchanged, changed])

        def capture(self):
            return next(self.frames)

        def analyze(self, frame):
            return elements

    class Controller:
        def __init__(self) -> None:
            self.opened = []
            self.hotkeys = []
            self.presses = []

        def open_box_in_new_tab(self, box) -> None:
            self.opened.append(box)

        def hotkey(self, *keys) -> None:
            self.hotkeys.append(keys)

        def press(self, key, *, presses=1) -> None:
            self.presses.append((key, presses))

    monkeypatch.setattr(
        web_research,
        "capture_page",
        lambda output, label, *, perception: type("Capture", (), {"record": f"{label}.json"})(),
    )
    controller = Controller()
    result = web_research.visit_search_results(
        Perception(),
        controller,
        tmp_path,
        page_count=2,
        page_wait=0,
        return_wait=0,
        sleeper=lambda seconds: None,
    )

    assert [visit.changed for visit in result.visits] == [False, True, True]
    assert [visit.candidate for visit in result.visits] == [
        "First Result",
        "Second Result",
        "Third Result",
    ]
    assert len(controller.opened) == 3
    assert controller.hotkeys == [("ctrl", "w"), ("ctrl", "w")]
    assert controller.presses == [("pagedown", 1), ("pagedown", 1)]


def test_find_link_candidates_excludes_video_sources() -> None:
    frame = ScreenFrame(
        np.zeros((600, 800, 3), dtype=np.uint8),
        CoordinateMapper(800, 600, 800, 600),
    )
    elements = [
        UIElement(Box(80, 180, 320, 210), "text", "YouTube 智能体教程", 0.9),
        UIElement(Box(80, 260, 360, 290), "text", "智能体官方文档", 0.9),
        UIElement(Box(80, 340, 360, 370), "text", "智能体维基百科", 0.9),
    ]
    candidates = find_link_candidates(frame, elements)
    assert [(item.text, item.category) for item in candidates] == [
        ("智能体官方文档", "documentation"),
        ("智能体维基百科", "reference"),
    ]
