from __future__ import annotations
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt

from ui.theme import FG, FG_MUTED, BG_SUBTLE, TEXT_MD, TEXT_SM, SPACE_8
from ui.components.utils import icon_label


class EmptyState(QWidget):
    def __init__(self, icon_key: str, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 30, 16, 30)
        lay.setSpacing(SPACE_8)
        lay.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        icon_w = QWidget()
        icon_w.setFixedSize(44, 44)
        icon_w.setStyleSheet(f"background:{BG_SUBTLE}; border-radius:8px;")
        i_lay = QHBoxLayout(icon_w)
        i_lay.setContentsMargins(0, 0, 0, 0)
        i_lay.addWidget(icon_label(icon_key, 20, FG_MUTED), alignment=Qt.AlignCenter)
        lay.addWidget(icon_w, alignment=Qt.AlignHCenter)

        t = QLabel(title)
        t.setStyleSheet(f"font-size:{TEXT_MD + 1}px; font-weight:500; color:{FG};")
        t.setAlignment(Qt.AlignHCenter)
        lay.addWidget(t)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"font-size:{TEXT_SM}px; color:{FG_MUTED};")
            sub.setAlignment(Qt.AlignHCenter)
            sub.setWordWrap(True)
            lay.addWidget(sub)
