from __future__ import annotations
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, PRIMARY_HOVER, ON_PRIMARY, SURFACE_ALT,
    DISABLED_BG, DISABLED_FG, FG, FG_SUBTLE,
    BG, BG_MUTED, BG_ACCENT, BORDER,
    ERROR_DARK, ERROR_BG,
)
from ui.components.utils import icon_pixmap

_BTN_STYLES = {
    "primary":   (PRIMARY,        ON_PRIMARY,  PRIMARY_HOVER,   "transparent"),
    "outline":   (BG,             FG,          BG_ACCENT,       BORDER),
    "secondary": (BG_MUTED,       FG_SUBTLE,   SURFACE_ALT,     "transparent"),
    "ghost":     ("transparent",  FG,          BG_ACCENT,       "transparent"),
    "danger":    (ON_PRIMARY,     ERROR_DARK,  ERROR_BG,        BORDER),
}
_BTN_SIZES = {
    "sm": (28, 10, 12),
    "md": (32, 14, 13),
    "lg": (40, 20, 14),
}


class Btn(QPushButton):
    def __init__(self, text: str = "", variant: str = "primary", size: str = "md",
                 icon_key: str = "", parent=None):
        super().__init__(parent)
        bg, fg, hover_bg, border = _BTN_STYLES.get(variant, _BTN_STYLES["primary"])
        h, px, fs = _BTN_SIZES.get(size, _BTN_SIZES["md"])
        self.setFixedHeight(h)
        self.setCursor(Qt.PointingHandCursor)
        border_css = f"1px solid {border}" if border != "transparent" else "none"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg}; color: {fg};
                border: {border_css}; border-radius: 6px;
                padding: 0 {px}px; font-size: {fs}px; font-weight: 500;
                text-align: center;
            }}
            QPushButton:hover {{ background: {hover_bg}; }}
            QPushButton:disabled {{
                background: {DISABLED_BG}; color: {DISABLED_FG};
                border: 1px solid {BORDER}; opacity: 0.6;
            }}
        """)
        if icon_key:
            px_map = icon_pixmap(icon_key, fs, fg)
            self.setIcon(QIcon(px_map))
            self.setIconSize(px_map.size())
        if text:
            self.setText(text)
