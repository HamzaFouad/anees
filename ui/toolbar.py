from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QPainter, QColor

from ui.theme import (
    PRIMARY, PRIMARY_HOVER, ON_PRIMARY,
    FG, FG_MUTED, BG, BG_MUTED, BORDER,
    DISABLED_BG, DISABLED_FG,
    SUCCESS_DARK, ERROR_DARK, ERROR_BORDER,
    WARN_DARK, TEXT_MD, TEXT_LG,
    EQUALIZER_SVG, fmt_mb,
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
        lay.addSpacing(-4)
        name = QLabel("أنيس")
        name.setStyleSheet("font-size:17px; font-weight:700; color:#0F1729;")
        lay.addWidget(name)
        lay.addWidget(VSep())

        # run controls (swappable)
        self._run_controls = RunControls(state, on_merge=self._on_merge)
        lay.addWidget(self._run_controls)

        lay.addStretch()

        # build card — primary CTA button
        self._add_btn = QPushButton("  Build Card…")
        self._add_btn.setIcon(QIcon(icon_pixmap("merge", 15, PRIMARY)))
        self._add_btn.setFixedHeight(36)
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setToolTip(
            "Assemble all processed playlists into a JOC memory card.\n"
            "Files are numbered 1111, 1112, … with splitter clips between playlists."
        )
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG}; border:1.5px solid {BORDER};
                border-radius:10px; padding:0 18px; font-size:14px; font-weight:600;
            }}
            QPushButton:hover {{ background:{BG_MUTED}; border-color:{PRIMARY}; }}
        """)
        self._add_btn.clicked.connect(self._on_merge)
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
        from ui.api import QueueAPI
        self._queue_api = QueueAPI(state)
        self._search.setToolTip("Filter playlists by name")
        self._search.textChanged.connect(self._queue_api.search)
        lay.addWidget(self._search)

        # settings
        s_btn = QPushButton()
        s_btn.setIcon(QIcon(icon_pixmap("settings", 14, FG_MUTED)))
        s_btn.setFixedSize(28, 28)
        s_btn.setCursor(Qt.PointingHandCursor)
        s_btn.setToolTip("App settings")
        s_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none; border-radius:6px; }}
            QPushButton:hover {{ background:{BG_MUTED}; }}
        """)
        s_btn.clicked.connect(self.settings_clicked)
        lay.addWidget(s_btn)

        state.run_state_changed.connect(self._on_run_state)
        state.playlists_changed.connect(self._on_playlists_changed)
        state.view_changed.connect(self._on_view)
        self._on_run_state(state.run_state)

    def _on_playlists_changed(self):
        # only rebuild run controls when idle — during a run this would recreate
        # _PulseDot (20ms timer) on every progress tick, causing rapid
        # create/delete cycles that segfault
        if self._state.run_state == RunState.IDLE:
            self._run_controls.refresh()

    def _on_run_state(self, rs: RunState):
        self._run_controls.refresh()

    def _on_view(self, view: str):
        self._search.setPlaceholderText("Search history" if view == "history" else "Search queue")

    def _on_merge(self) -> None:
        from ui.dialogs.merge import MergeDialog
        MergeDialog(self._state, self.window()).exec()


class RunControls(QWidget):
    def __init__(self, state: AppState, on_merge=None, parent=None):
        super().__init__(parent)
        self._state = state
        self._on_merge = on_merge or (lambda: None)
        from ui.api import RunAPI
        self._api = RunAPI(state)
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(8)
        self.refresh()

    # ── stable slots ──────────────────────────────────────────────────────────
    def _do_start(self) -> None:
        print("[toolbar] _do_start called", flush=True)
        ok, required_mb, free_mb = self._state.disk_space_ok()
        if not ok:
            msg = QMessageBox(self.window())
            msg.setWindowTitle("Not enough disk space")
            msg.setIcon(QMessageBox.Warning)
            msg.setText(
                f"<b>There isn't enough free space to complete this run.</b><br><br>"
                f"Required (with 20 % margin):&nbsp;&nbsp;<b>{fmt_mb(required_mb)}</b><br>"
                f"Available in download folder:&nbsp;&nbsp;<b>{fmt_mb(free_mb)}</b><br><br>"
                f"Free up space in the download folder, change the destination in "
                f"Settings, or remove some playlists from the queue."
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            return
        self._api.start()
    def _do_pause(self)  -> None: self._api.pause()
    def _do_resume(self) -> None: self._api.resume()
    def _do_stop(self)   -> None: self._api.stop()

    def mousePressEvent(self, event) -> None:
        print(f"[RunControls] mouse press {event.position()}", flush=True)
        super().mousePressEvent(event)

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
            print(f"[toolbar] refresh IDLE queued={c['queued']} can_start={can_start}", flush=True)

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
            start_btn.clicked.connect(self._do_start)
            self._lay.addWidget(start_btn)

            if can_start:
                est = self._state.total_estimate_mb()
                hint_text = (
                    f"{c['queued']} playlist{'s' if c['queued']!=1 else ''} queued"
                    + (f"  ·  ~{fmt_mb(est)}" if est > 0 else "")
                )
            else:
                hint_text = "Add a playlist to begin"

            hint = QLabel(hint_text)
            hint.setStyleSheet(f"font-size:{TEXT_MD}px; color:{FG_MUTED};")
            self._lay.addWidget(hint)

        elif rs == RunState.RUNNING:
            pause_btn = self._ctrl_btn("pause", "Pause", FG, BG, BORDER)
            pause_btn.clicked.connect(self._do_pause)
            self._lay.addWidget(pause_btn)

            stop_btn = self._ctrl_btn("x", "Stop", ERROR_DARK, BG, ERROR_BORDER)
            stop_btn.clicked.connect(self._do_stop)
            self._lay.addWidget(stop_btn)

            pulse = _PulseDot()
            self._lay.addWidget(pulse)
            info = QLabel(
                f"Running · <b style='color:{PRIMARY}'>{c['videos_done']}/{c['videos_total']}</b>"
                f" videos"
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
            resume_btn.clicked.connect(self._do_resume)
            self._lay.addWidget(resume_btn)

            stop_btn = self._ctrl_btn("x", "Stop", ERROR_DARK, BG, ERROR_BORDER)
            stop_btn.clicked.connect(self._do_stop)
            self._lay.addWidget(stop_btn)

            paused_lbl = QLabel(f"Paused · {c['videos_done']}/{c['videos_total']} done")
            paused_lbl.setStyleSheet(f"font-size:{TEXT_MD}px; color:{WARN_DARK};")
            self._lay.addWidget(paused_lbl)

        elif rs == RunState.COMPLETE:
            new_btn = self._ctrl_btn("refresh", "New run", FG, BG, BORDER)
            new_btn.clicked.connect(self._do_stop)
            self._lay.addWidget(new_btn)

            done_lbl = QLabel(f"✓  Complete · {c['videos_total']} videos downloaded")
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


