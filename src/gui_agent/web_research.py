from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .control import InputController
from .perception import DesktopPerception, UIElement
from .screen import ScreenFrame
from .web_demo import capture_page

_IGNORED_TEXT = {
    "about",
    "images",
    "maps",
    "news",
    "search",
    "settings",
    "shopping",
    "sign in",
    "videos",
    "图片",
    "地图",
    "新闻",
    "更多",
    "登录",
    "设置",
    "视频",
    "购物",
    "搜索",
}

_AI_SUMMARY_MARKERS = (
    "ai overview",
    "ai 概览",
    "ai 摘要",
    "ai mode",
    "ask a follow-up",
    "提出后续问题",
    "生成式 ai",
)

_BLOCKING_PROMPT_MARKERS = (
    "set microsoft edge as your default browser",
    "设置 microsoft edge 为默认浏览器",
    "设置为默认浏览器",
    "欢迎使用 microsoft edge",
    "welcome to microsoft edge",
)

_SNIPPET_ENDINGS = ("。", "！", "？", ".", "!", "?")

_EXCLUDED_SOURCE_MARKERS = ("youtube", "youtu.be", "bilibili", "tiktok", "抖音", "快手")
_CATEGORY_MARKERS = (
    ("documentation", ("documentation", "docs", "官方", "official", "cloud", "开发者")),
    ("reference", ("wikipedia", "维基", "百科", "baike")),
    ("news", ("news", "新闻")),
    ("guide", ("guide", "tutorial", "教程", "指南", "how to", "如何")),
)


@dataclass(frozen=True, slots=True)
class LinkCandidate:
    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int
    box: object
    category: str


@dataclass(frozen=True, slots=True)
class PageVisit:
    index: int
    candidate: str
    changed: bool
    record: str | None
    category: str = "general"


@dataclass(frozen=True, slots=True)
class ResearchResult:
    visits: list[PageVisit]
    report: str
    blocked: bool = False
    completed: int = 0
    scrolls: int = 0


def _has_blocking_prompt(elements: Iterable[UIElement]) -> bool:
    return any(
        element.kind == "text"
        and any(marker in element.text.casefold() for marker in _BLOCKING_PROMPT_MARKERS)
        for element in elements
    )


def _candidate_category(text: str) -> str:
    key = text.casefold()
    for category, markers in _CATEGORY_MARKERS:
        if any(marker in key for marker in markers):
            return category
    return "general"


def _has_ai_summary(elements: Iterable[UIElement]) -> bool:
    return any(
        element.kind == "text"
        and any(marker in element.text.casefold() for marker in _AI_SUMMARY_MARKERS)
        for element in elements
    )


def _summary_bottom(frame: ScreenFrame, elements: Iterable[UIElement]) -> int:
    header_bottoms = [
        element.box.bottom
        for element in elements
        if element.kind == "text"
        and any(marker in element.text.casefold() for marker in _AI_SUMMARY_MARKERS)
    ]
    if not header_bottoms:
        return frame.mapper.origin_y + max(180, round(frame.mapper.screen_height * 0.30))
    reserve = max(260, round(frame.mapper.screen_height * 0.38))
    return max(header_bottoms) + reserve


def find_link_candidates(frame: ScreenFrame, elements: Iterable[UIElement]) -> list[LinkCandidate]:
    items = tuple(elements)
    if _has_blocking_prompt(items):
        return []
    minimum_top = _summary_bottom(frame, items)
    candidates: list[LinkCandidate] = []
    for element in items:
        text = element.text.strip()
        key = text.casefold()
        if (
            element.kind != "text"
            or len(text) < 5
            or element.confidence < 0.3
            or key in _IGNORED_TEXT
            or len(text) > 100
            or text.endswith(_SNIPPET_ENDINGS)
            or any(marker in key for marker in _EXCLUDED_SOURCE_MARKERS)
            or element.box.top < minimum_top
        ):
            continue
        center_x, center_y = element.box.center
        candidates.append(
            LinkCandidate(
                text,
                element.confidence,
                center_x,
                center_y,
                element.box.width,
                element.box.height,
                element.box,
                _candidate_category(text),
            )
        )
    candidates.sort(key=lambda item: (item.y, item.x))
    kept: list[LinkCandidate] = []
    for candidate in candidates:
        if any(
            abs(candidate.x - existing.x) < 40 and abs(candidate.y - existing.y) < 24
            for existing in kept
        ):
            continue
        kept.append(candidate)
    return kept


def _changed(before: ScreenFrame, after: ScreenFrame) -> bool:
    if before.image.shape != after.image.shape:
        return True
    difference = np.mean(np.abs(before.image.astype(np.int16) - after.image.astype(np.int16)))
    return bool(difference >= 3.0)


def visit_search_results(
    perception: DesktopPerception,
    controller: InputController,
    output_dir: str | Path,
    *,
    page_count: int = 3,
    page_wait: float = 6.0,
    return_wait: float = 1.5,
    sleeper: Callable[[float], None] = time.sleep,
) -> ResearchResult:
    if page_count not in {2, 3}:
        raise ValueError("网页数量只能是 2 或 3")
    if page_wait < 0 or return_wait < 0:
        raise ValueError("等待时间不能为负数")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    seen_titles: set[str] = set()
    seen_categories: set[str] = set()
    visits: list[PageVisit] = []
    blocked = False
    completed = 0
    page_moves = 0
    attempts = 0
    revisited = False

    controller.press("pagedown")
    page_moves += 1
    sleeper(0.8)

    while attempts < page_count * 4:
        before = perception.capture()
        elements = perception.analyze(before)
        if _has_blocking_prompt(elements):
            blocked = True
            break
        if _has_ai_summary(elements):
            if page_moves >= page_count + 4:
                break
            controller.press("pagedown")
            page_moves += 1
            sleeper(0.8)
            continue

        candidates = find_link_candidates(before, elements)
        available = [item for item in candidates if item.text.casefold() not in seen_titles]
        candidate = next(
            (item for item in available if item.category not in seen_categories),
            available[0] if available else None,
        )
        if candidate is None:
            if page_moves < page_count + 4:
                controller.press("pagedown")
                page_moves += 1
                sleeper(0.8)
                continue
            if not revisited:
                controller.press("pageup")
                page_moves += 1
                revisited = True
                sleeper(0.8)
                continue
            break

        attempts += 1
        seen_titles.add(candidate.text.casefold())
        controller.open_box_in_new_tab(candidate.box)
        sleeper(page_wait)
        after = perception.capture()
        changed = _changed(before, after)
        record: str | None = None
        if changed:
            capture = capture_page(output, f"page-{attempts:02d}", perception=perception)
            record = capture.record
            controller.hotkey("ctrl", "w")
            sleeper(return_wait)
            completed += 1
            seen_categories.add(candidate.category)
        visits.append(PageVisit(attempts, candidate.text, changed, record, candidate.category))
        if completed >= page_count:
            break
        if changed:
            controller.press("pagedown")
            page_moves += 1
            sleeper(0.8)

    report = output / "research.json"
    report.write_text(
        json.dumps(
            {
                "blocked": blocked,
                "completed": completed,
                "page_moves": page_moves,
                "visits": [asdict(visit) for visit in visits],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return ResearchResult(visits, str(report), blocked, completed, page_moves)
