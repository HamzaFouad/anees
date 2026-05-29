from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from ui.theme import PRIMARY, PRIMARY_TINT_8, FG, FG_MUTED, BG, BORDER, ERROR_DARK, ERROR_BG
from ui.widgets import icon_pixmap
from ui.state import AppState
from backend.models import RunState


class TabBar(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setFixedHeight(36)
        self.setStyleSheet(f"background:{BG};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(0)

        self._btns: dict[str, QPushButton] = {}
        tabs = [
            ("queue",   "Queue",   "list",     lambda: 0),
            ("history", "History", "clock",    lambda: 0),
            ("logs",    "Logs",    "terminal", lambda: self._log_errors()),
        ]
        for key, label, icon, count_fn in tabs:
            btn = _TabBtn(key, label, icon, count_fn)
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

    def _log_errors(self) -> int:
        from backend.mock_data import MOCK_LOGS
        return sum(1 for l in MOCK_LOGS if l.lvl == "error")

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
        self._btns["logs"].set_count(self._log_errors())


class _TabBtn(QPushButton):
    def __init__(self, key: str, label: str, icon: str, count_fn, parent=None):
        super().__init__(parent)
        self._key = key
        self._label = label
        self._icon = icon
        self._count_fn = count_fn
        self._active = False
        self._count = 0
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
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
        is_err = self._key == "logs" and self._count_fn() > 0
        color  = PRIMARY if self._active else (ERROR_DARK if is_err else FG_MUTED)
        weight = "600" if self._active else "500"
        border = f"border-bottom:2px solid {PRIMARY};" if self._active else ""
        count  = self._count_fn() if self._key == "logs" else self._count

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
        lay.setContentsMargins(10, 4, 10, 4)
        lay.setSpacing(6)

        dot = QLabel()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background:{PRIMARY}; border-radius:3px;")
        lay.addWidget(dot)

        lbl = QLabel("Queue locked — run in progress")
        lbl.setStyleSheet(f"font-size:11px; font-weight:500; color:{PRIMARY};")
        lay.addWidget(lbl)

        self.setStyleSheet(
            f"background:{PRIMARY_TINT_8}; border-radius:99px;"
        )
