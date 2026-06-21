from __future__ import annotations
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor

from ui.theme import PRIMARY, SURFACE_ALT


class Toggle(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(36, 24)
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
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(PRIMARY if self._checked else SURFACE_ALT))
        p.drawRoundedRect(0, 3, 36, 18, 9, 9)
        p.setBrush(QColor("white"))
        x = 19 if self._checked else 3
        p.drawEllipse(x, 5, 14, 14)

    def mousePressEvent(self, _event):
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()
