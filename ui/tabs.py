from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QIcon, QPainter, QColor

from ui.theme import PRIMARY, FG, FG_MUTED, BG, BORDER, H_TABBAR
from ui.widgets import icon_pixmap, Spinner
from ui.state import AppState
from backend.models import RunState


class TabBar(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setFixedHeight(H_TABBAR)
        self.setStyleSheet(f"background:{BG}; border-bottom:1px solid {BORDER};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(0)

        self._btns: dict[str, QPushButton] = {}
        tabs = [
            ("queue",   "Queue",   "list",  lambda: 0, True),
            ("history", "History", "clock", lambda: 0, False),
        ]
        for key, label, icon, count_fn, enabled in tabs:
            btn = _TabBtn(key, label, icon, count_fn, enabled=enabled)
            if enabled:
                btn.clicked.connect(lambda _=False, k=key: state.set_view(k))
            self._btns[key] = btn
            lay.addWidget(btn)

        lay.addStretch()

        self._lock_pill = _LockPill()
        self._lock_pill.setVisible(False)
        lay.addWidget(self._lock_pill)

        state.view_changed.connect(self._on_view)
        state.run_state_changed.connect(self._on_run_state)
        state.playlists_changed.connect(self._refresh_counts)
        self._on_view(state.view)
        self._refresh_counts()

    def _on_view(self, view: str):
        for k, btn in self._btns.items():
            btn.set_active(k == view)

    def _on_run_state(self, rs: RunState):
        locked = rs in (RunState.RUNNING, RunState.PAUSED)
        self._lock_pill.setVisible(locked)
        self._refresh_counts()

    def _refresh_counts(self):
        self._btns["queue"].set_count(len(self._state.playlists))
        from backend.mock_data import MOCK_HISTORY
        self._btns["history"].set_count(len(MOCK_HISTORY))


class _TabBtn(QPushButton):
    def __init__(self, key: str, label: str, icon: str, count_fn,
                 enabled: bool = True, parent=None):
        super().__init__(parent)
        self._key = key
        self._label = label
        self._icon = icon
        self._count_fn = count_fn
        self._enabled = enabled
        self._active = False
        self._count = 0
        self.setFixedHeight(H_TABBAR)
        if enabled:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            self.setToolTip("Coming soon")
        self._refresh_style()

    def set_active(self, active: bool):
        self._active = active
        self._refresh_style()

    def set_count(self, n: int):
        self._count = n
        self._refresh_style()

    def _refresh_style(self):
        from ui.widgets import icon_pixmap
        from PySide6.QtGui import QIcon
        from ui.theme import DISABLED_FG

        if not self._enabled:
            self.setIcon(QIcon(icon_pixmap(self._icon, 12, DISABLED_FG)))
            self.setText(f" {self._label}")
            self.setStyleSheet(f"""
                QPushButton {{
                    background:transparent; color:{DISABLED_FG}; border:none;
                    font-size:12px; font-weight:500; padding:0 14px; opacity:0.5;
                }}
            """)
            return

        color  = PRIMARY if self._active else FG_MUTED
        weight = "600" if self._active else "500"
        border = f"border-bottom:2px solid {PRIMARY};" if self._active else ""
        count  = self._count

        self.setIcon(QIcon(icon_pixmap(self._icon, 12, color)))
        self.setText(f" {self._label}  {count}")
        self.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{color}; border:none; {border}
                font-size:12px; font-weight:{weight};
                padding:0 14px;
            }}
            QPushButton:hover {{ color:{FG}; }}
        """)


class _LockPill(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 10, 4)
        lay.setSpacing(5)

        self._spinner = Spinner(12, PRIMARY)
        self._spinner.stop()
        lay.addWidget(self._spinner)

        lbl = QLabel("Queue locked — run in progress")
        lbl.setStyleSheet(
            f"font-size:11px; font-weight:500; color:{PRIMARY}; "
            "background:transparent; border:none;"
        )
        lay.addWidget(lbl)

    def hideEvent(self, event):
        self._spinner.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        self._spinner.start()
        super().showEvent(event)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 68, 255, 20))   # PRIMARY_TINT_8 (0.08×255≈20) — Qt QPainter needs int alpha
        r = self.height() / 2
        p.drawRoundedRect(QRectF(self.rect()), r, r)
