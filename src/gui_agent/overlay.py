from __future__ import annotations

from collections.abc import Iterable

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QWidget

from .perception import UIElement


class BoundingBoxOverlay(QWidget):
    def __init__(self, elements: Iterable[UIElement] = ()) -> None:
        super().__init__()
        self.elements = list(elements)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setGeometry(QApplication.primaryScreen().virtualGeometry())

    def set_elements(self, elements: Iterable[UIElement]) -> None:
        self.elements = list(elements)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setFont(QFont("Sans Serif", 10))
        origin = self.geometry().topLeft()
        for element in self.elements:
            color = QColor(50, 220, 80) if element.kind == "text" else QColor(255, 160, 30)
            painter.setPen(QPen(color, 2))
            box = element.box
            painter.drawRect(
                box.left - origin.x(),
                box.top - origin.y(),
                box.width,
                box.height,
            )
            if element.text:
                painter.drawText(box.left - origin.x(), box.top - origin.y() - 4, element.text)
