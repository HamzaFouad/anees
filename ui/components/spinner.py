from __future__ import annotations
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen

from ui.theme import PRIMARY


class Spinner(QWidget):
    def __init__(self, size: int = 13, color: str = PRIMARY, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._color = color
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        pen = QPen(QColor(self._color), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(2, 2, s - 4, s - 4, self._angle * 16, 270 * 16)

    def stop(self):
        self._timer.stop()

    def start(self):
        if not self._timer.isActive():
            self._timer.start(16)
