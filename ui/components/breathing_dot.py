from __future__ import annotations
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor

from ui.theme import PRIMARY


class BreathingDot(QWidget):
    """Pulsing status dot with a soft halo ring.

    The dot and its halo breathe together — scale 1.0↔0.8, opacity 1.0↔0.55 —
    over a 1.4 s cosine cycle.
    """

    def __init__(self, color: str = PRIMARY, size: int = 14,
                 running: bool = True, parent=None):
        super().__init__(parent)
        self._color   = QColor(color)
        self._size    = size
        self._phase   = 0.0
        self._running = running
        self.setFixedSize(size, size)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        if running:
            self._timer.start(20)

    def set_running(self, running: bool) -> None:
        self._running = running
        if running:
            self._timer.start(20)
        else:
            self._timer.stop()
            self._phase = 0.0
            self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 1 / 70) % 1.0
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)

        cx = cy = self._size / 2

        if self._running:
            cos_t   = (math.cos(self._phase * 2 * math.pi) + 1) / 2
            scale   = 0.8 + cos_t * 0.2
            opacity = 0.55 + cos_t * 0.45
        else:
            scale, opacity = 1.0, 1.0

        dot_r  = self._size * 0.22 * scale
        ring_r = dot_r + self._size * 0.21

        halo = QColor(self._color)
        halo.setAlphaF(0.18 * opacity)
        p.setBrush(halo)
        p.drawEllipse(int(cx - ring_r), int(cy - ring_r),
                      int(ring_r * 2),  int(ring_r * 2))

        dot = QColor(self._color)
        dot.setAlphaF(opacity)
        p.setBrush(dot)
        p.drawEllipse(int(cx - dot_r), int(cy - dot_r),
                      int(dot_r * 2),  int(dot_r * 2))
