from __future__ import annotations
from PySide6.QtWidgets import QLabel

from ui.theme import (
    PRIMARY_TINT_8, PRIMARY,
    FG_SUBTLE, BG_MUTED, BG_ACCENT,
    SUCCESS_BG, SUCCESS_DARK,
    ERROR_BG, ERROR_DARK,
    WARN_BG, WARN_DARK,
)

_BADGE_STYLES = {
    "default": (BG_MUTED,       FG_SUBTLE),
    "primary": (PRIMARY_TINT_8, PRIMARY),
    "success": (SUCCESS_BG,     SUCCESS_DARK),
    "active":  (PRIMARY_TINT_8, PRIMARY),
    "queued":  (WARN_BG,        WARN_DARK),
    "error":   (ERROR_BG,       ERROR_DARK),
    "mono":    (BG_ACCENT,      FG_SUBTLE),
}


class Badge(QLabel):
    def __init__(self, text: str = "", kind: str = "default", parent=None):
        super().__init__(text, parent)
        bg, fg = _BADGE_STYLES.get(kind, _BADGE_STYLES["default"])
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg}; color: {fg};
                border-radius: 4px; padding: 2px 8px;
                font-size: 11px; font-weight: 500;
            }}
        """)
        self.setContentsMargins(0, 0, 0, 0)
