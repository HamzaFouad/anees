from __future__ import annotations
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QParallelAnimationGroup,
    QEasingCurve, Property, QByteArray,
)
from PySide6.QtGui import QPainter, QColor, QBrush


class PulseDot(QWidget):
    """6 px animated dot — breathes opacity + scale on an InOutSine curve.

    Use start_pulse() / stop_pulse() to toggle animation.
    Only the Running state should animate; all others are static.
    """

    def __init__(self, color: str | QColor, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._opacity: float = 1.0
        self._scale: float   = 1.0
        self._anim_group: QParallelAnimationGroup | None = None
        self.setFixedSize(10, 10)   # 2 px breathing room around the 6 px dot

    # ── animatable properties ─────────────────────────────────────────────────

    def _get_opacity(self) -> float: return self._opacity
    def _set_opacity(self, v: float):
        self._opacity = v
        self.update()
    dot_opacity = Property(float, _get_opacity, _set_opacity)

    def _get_scale(self) -> float: return self._scale
    def _set_scale(self, v: float):
        self._scale = v
        self.update()
    dot_scale = Property(float, _get_scale, _set_scale)

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        c = QColor(self._color)
        c.setAlphaF(self._opacity)
        p.setBrush(QBrush(c))
        dot_r = 3.0 * self._scale
        cx, cy = self.width() / 2, self.height() / 2
        p.drawEllipse(cx - dot_r, cy - dot_r, dot_r * 2, dot_r * 2)
        p.end()

    # ── animation control ─────────────────────────────────────────────────────

    def start_pulse(self):
        if self._anim_group:
            self._anim_group.stop()

        ease = QEasingCurve.InOutSine

        a_op = QPropertyAnimation(self, QByteArray(b"dot_opacity"))
        a_op.setDuration(1600)
        a_op.setStartValue(0.45)
        a_op.setKeyValueAt(0.5, 1.0)
        a_op.setEndValue(0.45)
        a_op.setEasingCurve(ease)
        a_op.setLoopCount(-1)

        a_sc = QPropertyAnimation(self, QByteArray(b"dot_scale"))
        a_sc.setDuration(1600)
        a_sc.setStartValue(0.82)
        a_sc.setKeyValueAt(0.5, 1.0)
        a_sc.setEndValue(0.82)
        a_sc.setEasingCurve(ease)
        a_sc.setLoopCount(-1)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(a_op)
        self._anim_group.addAnimation(a_sc)
        self._anim_group.start()

    def stop_pulse(self):
        if self._anim_group:
            self._anim_group.stop()
            self._anim_group = None
        self._opacity = 1.0
        self._scale   = 1.0
        self.update()

    def set_color(self, color: str | QColor):
        self._color = QColor(color)
        self.update()

    def hideEvent(self, event):
        if self._anim_group:
            self._anim_group.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        if self._anim_group is not None:
            self._anim_group.start()
        super().showEvent(event)
