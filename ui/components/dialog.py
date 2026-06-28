from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.theme import FG, FG_MUTED, BG, BG_SUBTLE, BORDER, DIALOG_RADIUS, DIALOG_BORDER
from ui.components.utils import icon_pixmap


class RoundedDialog(QDialog):
    """Base dialog with rounded corners, translucent background, and X button.

    Usage
    -----
    class MyDialog(RoundedDialog):
        def __init__(self, parent=None):
            super().__init__(title="My Title", width=480, parent=parent)
            # add widgets to self.body_layout (QVBoxLayout)
    """

    def __init__(self, title: str = "", width: int = 480,
                 body_margins: tuple = (20, 16, 20, 20),
                 header_separator: bool = True,
                 header_height: int = 52,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(width)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._card = QWidget()
        self._card.setObjectName("roundedCard")
        self._card.setStyleSheet(
            f"#roundedCard {{ background:{BG}; border-radius:{DIALOG_RADIUS}px;"
            f" border:1px solid {DIALOG_BORDER}; }}"
        )
        outer.addWidget(self._card)

        self._root = QVBoxLayout(self._card)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        hdr = QWidget(); hdr.setFixedHeight(header_height)
        hdr.setStyleSheet("background:transparent;")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(20, 0, 16, 0)
        if title:
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet(f"font-size:14px; font-weight:700; color:{FG};")
            h_lay.addWidget(t_lbl)
        h_lay.addStretch()
        x_btn = QPushButton()
        x_btn.setIcon(QIcon(icon_pixmap("x", 15, FG_MUTED)))
        x_btn.setFixedSize(28, 28)
        x_btn.setCursor(Qt.PointingHandCursor)
        x_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; border-radius:6px; }}"
            f"QPushButton:hover {{ background:{BG_SUBTLE}; }}"
        )
        x_btn.clicked.connect(self.reject)
        h_lay.addWidget(x_btn)
        self._root.addWidget(hdr)

        if header_separator:
            sep = QFrame(); sep.setFixedHeight(1)
            sep.setStyleSheet(f"background:{BORDER}; border:none;")
            self._root.addWidget(sep)

        body = QWidget(); body.setStyleSheet("background:transparent;")
        self.body_layout = QVBoxLayout(body)
        l, t, r, b = body_margins
        self.body_layout.setContentsMargins(l, t, r, b)
        self.body_layout.setSpacing(14)
        self._root.addWidget(body, 1)

    def add_footer(self, height: int = 60) -> QHBoxLayout:
        """Add a standard footer bar and return its QHBoxLayout."""
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER}; border:none;")
        self._root.addWidget(sep)

        footer = QWidget(); footer.setFixedHeight(height)
        footer.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(8)
        self._root.addWidget(footer)
        return lay

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
