from __future__ import annotations
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor

from ui.theme import PRIMARY, BORDER


class SlimProgressBar(QWidget):
    def __init__(self, color: str = PRIMARY, track: str = BORDER,
                 bar_height: int = 4, parent=None):
        super().__init__(parent)
        self._value = 0
        self._total = 100
        self._color = color
        self._track = track
        self._h = bar_height
        self.setFixedHeight(bar_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, value: int, total: int = 100):
        self._value = value
        self._total = total
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        r = self._h // 2
        p.setBrush(QColor(self._track))
        p.drawRoundedRect(0, 0, self.width(), self._h, r, r)
        if self._total > 0 and self._value > 0:
            w = max(r * 2, int(self.width() * min(1.0, self._value / self._total)))
            p.setBrush(QColor(self._color))
            p.drawRoundedRect(0, 0, w, self._h, r, r)
