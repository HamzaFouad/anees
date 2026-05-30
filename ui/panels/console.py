from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from ui.theme import (
    BG, BG_MUTED, BORDER, FG, FG_MUTED,
    LOG_BG_DARK, FG_ON_DARK, FONT_MONO, TEXT_SM,
)


_LEVEL_COLOR = {
    "error": "#FF6B6B",
    "warn":  "#FFD93D",
    "info":  FG_ON_DARK,
    "debug": "#4B5563",
}


class ConsolePanel(QWidget):
    """Full-width collapsible output console — lives at the bottom of MainWindow."""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state      = state
        self._last_count = 0
        self.setVisible(False)
        self.setFixedHeight(220)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── toolbar ───────────────────────────────────────────────────────────
        bar = QWidget()
        bar.setFixedHeight(26)
        bar.setStyleSheet(f"background:{LOG_BG_DARK}; border-top:1px solid #1e2a40;")
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(12, 0, 12, 0)
        bar_lay.setSpacing(12)

        lbl = QLabel("OUTPUT")
        lbl.setStyleSheet(
            f"font-size:9px; font-weight:600; letter-spacing:.08em; "
            f"color:#4B5563; font-family:{FONT_MONO};"
        )
        bar_lay.addWidget(lbl)
        bar_lay.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; "
            f"font-size:9px; color:#4B5563; font-family:{FONT_MONO}; }}"
            f"QPushButton:hover {{ color:{FG_ON_DARK}; }}"
        )
        clear_btn.clicked.connect(self._clear)
        bar_lay.addWidget(clear_btn)
        root.addWidget(bar)

        # ── text area ─────────────────────────────────────────────────────────
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFrameShape(QFrame.NoFrame)
        self._text.setStyleSheet(
            f"QTextEdit {{ background:{LOG_BG_DARK}; color:{FG_ON_DARK}; "
            f"font-family:{FONT_MONO}; font-size:{TEXT_SM}px; "
            f"padding:4px 12px; border:none; }}"
        )
        root.addWidget(self._text)

        state.logs_changed.connect(self._on_logs_changed)

    def _on_logs_changed(self) -> None:
        new = self._state.logs[self._last_count:]
        if not new:
            return
        self._last_count = len(self._state.logs)
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.End)
        for entry in new:
            color = _LEVEL_COLOR.get(entry.lvl, FG_ON_DARK)
            cursor.insertHtml(
                f'<span style="color:#4B5563">{entry.t}</span>&nbsp;&nbsp;'
                f'<span style="color:{color}">{entry.msg}</span><br>'
            )
        self._text.verticalScrollBar().setValue(
            self._text.verticalScrollBar().maximum()
        )

    def _clear(self) -> None:
        self._text.clear()
        self._last_count = 0


class ConsoleToggleBar(QWidget):
    """Thin persistent bar that toggles the ConsolePanel above it."""

    def __init__(self, console: ConsolePanel, parent=None):
        super().__init__(parent)
        self._console = console
        self.setFixedHeight(24)
        self.setStyleSheet(f"background:{BG_MUTED}; border-top:1px solid {BORDER};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(0)

        self._btn = QPushButton("▶  Console")
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; "
            f"font-size:{TEXT_SM}px; font-weight:500; color:{FG_MUTED}; "
            f"font-family:{FONT_MONO}; }}"
            f"QPushButton:hover {{ color:{FG}; }}"
        )
        self._btn.clicked.connect(self._toggle)
        lay.addWidget(self._btn)
        lay.addStretch()

    def _toggle(self) -> None:
        visible = not self._console.isVisible()
        self._console.setVisible(visible)
        self._btn.setText("▼  Console" if visible else "▶  Console")
