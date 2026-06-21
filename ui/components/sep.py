from __future__ import annotations
from PySide6.QtWidgets import QFrame

from ui.theme import BORDER


class VSep(QFrame):
    """1px vertical divider for toolbars."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.VLine)
        self.setFixedWidth(1)
        self.setStyleSheet(f"background:{BORDER}; border:none;")
