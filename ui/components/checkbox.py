from __future__ import annotations
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen

from ui.theme import PRIMARY, BORDER, RADIUS_SM


class Checkbox(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, color: str = PRIMARY, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._color = color
        self.setFixedSize(16, 16)
        self.setCursor(Qt.PointingHandCursor)

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, v: bool):
        self._checked = v
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._checked:
            p.setBrush(QColor(self._color))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(0, 0, 16, 16, RADIUS_SM, RADIUS_SM)
            p.setPen(QPen(QColor("white"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(3, 8, 6, 11)
            p.drawLine(6, 11, 13, 4)
        else:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(BORDER), 1.5))
            p.drawRoundedRect(1, 1, 14, 14, RADIUS_SM - 1, RADIUS_SM - 1)

    def mousePressEvent(self, _event):
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()
