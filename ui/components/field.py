from __future__ import annotations
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QVBoxLayout

from ui.theme import (
    FG, FG_MUTED, BG, BORDER, PRIMARY,
    TEXT_XS, TEXT_SM,
)


class Field(QWidget):
    def __init__(self, label: str, hint: str = "", inline: bool = False, parent=None):
        from PySide6.QtWidgets import QHBoxLayout
        super().__init__(parent)
        if inline:
            lay = QHBoxLayout(self)
        else:
            lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"font-size:{TEXT_XS}px; font-weight:500; color:{FG_MUTED}; letter-spacing:0.04em;"
        )
        if inline:
            lbl.setFixedWidth(100)
        lay.addWidget(lbl)

        self._content_area = QWidget()
        clay = QVBoxLayout(self._content_area)
        clay.setContentsMargins(0, 0, 0, 0)
        clay.setSpacing(2)
        lay.addWidget(self._content_area)

        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setStyleSheet(f"font-size:{TEXT_SM}px; color:{FG_MUTED};")
            clay.addWidget(hint_lbl)

    def content_layout(self):
        return self._content_area.layout()


class StyledInput(QLineEdit):
    def __init__(self, placeholder: str = "", mono: bool = False, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        font_family = "'JetBrains Mono', monospace" if mono else "inherit"
        self.setStyleSheet(f"""
            QLineEdit {{
                height: 32px; padding: 0 10px;
                border: 1px solid {BORDER}; border-radius: 6px;
                font-size: 13px; font-family: {font_family};
                background: {BG}; color: {FG};
            }}
            QLineEdit:focus {{
                border-color: {PRIMARY};
            }}
        """)
