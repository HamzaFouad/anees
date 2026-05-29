from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, PRIMARY_HOVER, ON_PRIMARY,
    FG, FG_MUTED, BG, BG_MUTED, BORDER,
    DISABLED_BG, DISABLED_FG,
    SUCCESS_DARK, ERROR_DARK, ERROR_BORDER,
    WARN_DARK, TEXT_MD, TEXT_LG,
    EQUALIZER_SVG,
)
from ui.widgets import Btn, VSep, icon_pixmap
from ui.state import AppState
from backend.models import RunState


class Toolbar(QWidget):
    add_clicked         = Signal()
    settings_clicked    = Signal()

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setFixedHeight(52)
        self.setStyleSheet(f"background:{BG};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(8)

        # logo
        from ui.titlebar import _AppMark
        lay.addWidget(_AppMark())
        name = QLabel("Anees")
        name.setStyleSheet(f"font-size:{TEXT_LG}px; font-weight:700; letter-spacing:-0.01em; color:{FG};")
        lay.addWidget(name)
        lay.addWidget(VSep())

        # run controls (swappable)
        self._run_controls = RunControls(state)
        lay.addWidget(self._run_controls)

        lay.addStretch()

        # add playlist
        self._add_btn = QPushButton("  Add playlist")
        self._add_btn.setIcon(QIcon(icon_pixmap("plus", 13, FG_MUTED)))
        self._add_btn.setFixedHeight(30)
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG}; border:1px solid {BORDER};
                border-radius:6px; padding:0 12px; font-size:12px; font-weight:500;
            }}
            QPushButton:hover {{ background:{BG_MUTED}; }}
            QPushButton:disabled {{ background:{DISABLED_BG}; color:{DISABLED_FG}; opacity:0.7; }}
        """)
        self._add_btn.clicked.connect(self.add_clicked)
        lay.addWidget(self._add_btn)

        # search
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search queue")
        self._search.setFixedSize(180, 28)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background:{BG_MUTED}; border:1px solid {BORDER}; border-radius:6px;
                padding:0 10px 0 28px; font-size:12px; color:{FG};
            }}
            QLineEdit:focus {{ border-color:{PRIMARY}; }}
        """)
        self._search.textChanged.connect(state.set_query)
        lay.addWidget(self._search)

        # settings
        s_btn = QPushButton()
        s_btn.setIcon(QIcon(icon_pixmap("settings", 14, FG_MUTED)))
        s_btn.setFixedSize(28, 28)
        s_btn.setCursor(Qt.PointingHandCursor)
        s_btn.setToolTip("Settings")
        s_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none; border-radius:6px; }}
            QPushButton:hover {{ background:{BG_MUTED}; }}
        """)
        s_btn.clicked.connect(self.settings_clicked)
        lay.addWidget(s_btn)

        state.run_state_changed.connect(self._on_run_state)
        state.playlists_changed.connect(self._run_controls.refresh)
        state.view_changed.connect(self._on_view)
        self._on_run_state(state.run_state)

    def _on_run_state(self, rs: RunState):
        locked = rs in (RunState.RUNNING, RunState.PAUSED)
        self._add_btn.setDisabled(locked)
        self._add_btn.setToolTip(
            "Queue is locked while a run is in progress" if locked else "Add a YouTube playlist to the queue"
        )
        self._run_controls.refresh()

    def _on_view(self, view: str):
        self._search.setPlaceholderText("Search history" if view == "history" else "Search queue")


class RunControls(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(8)
        self.refresh()

    def _clear(self):
        while self._lay.count():
            item = self._lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def refresh(self):
        self._clear()
        rs = self._state.run_state
        c  = self._state.counts()

        if rs == RunState.IDLE:
            can_start = c["queued"] > 0
            start_btn = QPushButton("  Start run")
            start_btn.setIcon(QIcon(icon_pixmap("play", 13, ON_PRIMARY if can_start else FG_MUTED)))
            start_btn.setFixedHeight(32)
            start_btn.setEnabled(can_start)
            start_btn.setCursor(Qt.PointingHandCursor)
            start_btn.setStyleSheet(f"""
                QPushButton {{
                    background:{PRIMARY if can_start else BORDER};
                    color:{ON_PRIMARY if can_start else FG_MUTED};
                    border:none; border-radius:6px;
                    padding:0 16px; font-size:13px; font-weight:600;
                }}
                QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
                QPushButton:disabled {{ color:{DISABLED_FG}; }}
            """)
            start_btn.clicked.connect(lambda: self._state.set_run_state(RunState.RUNNING))
            self._lay.addWidget(start_btn)

            hint = QLabel(
                f"{c['queued']} playlist{'s' if c['queued']!=1 else ''} queued · ~{c['queued']*8} min"
                if c["queued"] > 0 else "Add a playlist to begin"
            )
            hint.setStyleSheet(f"font-size:{TEXT_MD}px; color:{FG_MUTED};")
            self._lay.addWidget(hint)

        elif rs == RunState.RUNNING:
            pause_btn = self._ctrl_btn("pause", "Pause", FG, BG, BORDER)
            pause_btn.clicked.connect(lambda: self._state.set_run_state(RunState.PAUSED))
            self._lay.addWidget(pause_btn)

            stop_btn = self._ctrl_btn("x", "Stop", ERROR_DARK, BG, ERROR_BORDER)
            stop_btn.clicked.connect(lambda: self._state.set_run_state(RunState.IDLE))
            self._lay.addWidget(stop_btn)

            pulse = _PulseDot()
            self._lay.addWidget(pulse)
            info = QLabel(
                f"Running · <b style='color:{PRIMARY}'>{c['videos_done']}/{c['videos_total']}</b>"
                f" videos · ~12 min remaining"
            )
            info.setTextFormat(Qt.RichText)
            info.setStyleSheet(f"font-size:{TEXT_MD}px; color:{FG}; font-weight:500;")
            self._lay.addWidget(info)

        elif rs == RunState.PAUSED:
            resume_btn = QPushButton("  Resume")
            resume_btn.setIcon(QIcon(icon_pixmap("play", 13, ON_PRIMARY)))
            resume_btn.setFixedHeight(32)
            resume_btn.setCursor(Qt.PointingHandCursor)
            resume_btn.setStyleSheet(f"""
                QPushButton {{ background:{PRIMARY}; color:{ON_PRIMARY}; border:none;
                    border-radius:6px; padding:0 16px; font-size:13px; font-weight:600; }}
                QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
            """)
            resume_btn.clicked.connect(lambda: self._state.set_run_state(RunState.RUNNING))
            self._lay.addWidget(resume_btn)

            stop_btn = self._ctrl_btn("x", "Stop", ERROR_DARK, BG, ERROR_BORDER)
            stop_btn.clicked.connect(lambda: self._state.set_run_state(RunState.IDLE))
            self._lay.addWidget(stop_btn)

            paused_lbl = QLabel(f"Paused · {c['videos_done']}/{c['videos_total']} done")
            paused_lbl.setStyleSheet(f"font-size:{TEXT_MD}px; color:{WARN_DARK};")
            self._lay.addWidget(paused_lbl)

        elif rs == RunState.COMPLETE:
            merge_btn = QPushButton("  Merge to folder")
            merge_btn.setIcon(QIcon(icon_pixmap("merge", 13, ON_PRIMARY)))
            merge_btn.setFixedHeight(32)
            merge_btn.setCursor(Qt.PointingHandCursor)
            merge_btn.setStyleSheet(f"""
                QPushButton {{ background:{PRIMARY}; color:{ON_PRIMARY}; border:none;
                    border-radius:6px; padding:0 14px; font-size:13px; font-weight:600; }}
                QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
            """)
            from ui.dialogs.merge import MergeDialog
            merge_btn.clicked.connect(lambda: MergeDialog(self._state, self.window()).exec())
            self._lay.addWidget(merge_btn)

            new_btn = self._ctrl_btn("refresh", "New run", FG, BG, BORDER)
            new_btn.clicked.connect(lambda: self._state.set_run_state(RunState.IDLE))
            self._lay.addWidget(new_btn)

            done_lbl = QLabel(f"✓  Complete · {c['videos_total']} videos · 1.2 GB")
            done_lbl.setStyleSheet(f"font-size:{TEXT_MD}px; color:{SUCCESS_DARK};")
            self._lay.addWidget(done_lbl)

    def _ctrl_btn(self, icon: str, text: str, fg: str, bg: str, border: str) -> QPushButton:
        btn = QPushButton(f"  {text}")
        btn.setIcon(QIcon(icon_pixmap(icon, 12, fg)))
        btn.setFixedHeight(32)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background:{bg}; color:{fg}; border:1px solid {border};
                border-radius:6px; padding:0 14px; font-size:13px; font-weight:500; }}
            QPushButton:hover {{ background:{DISABLED_BG}; }}
        """)
        return btn


class _PulseDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._alpha = 255
        self._growing = False
        from PySide6.QtCore import QTimer
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(20)

    def _tick(self):
        if self._growing:
            self._alpha = min(255, self._alpha + 5)
            if self._alpha == 255:
                self._growing = False
        else:
            self._alpha = max(80, self._alpha - 5)
            if self._alpha == 80:
                self._growing = True
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        c = QColor(PRIMARY)
        c.setAlpha(self._alpha)
        p.setBrush(c)
        p.drawEllipse(0, 0, 8, 8)


from PySide6.QtGui import QPainter
