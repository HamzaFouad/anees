from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QColor

from ui.theme import (
    PRIMARY, FG, FG_MUTED, FG_SUBTLE, BG, BG_MUTED, BG_SUBTLE, BG_ACCENT, BORDER,
    SUCCESS, SUCCESS_DARK, SUCCESS_BG, ERROR, ERROR_DARK, ERROR_BG, ERROR_BORDER,
    SURFACE_ALT, ERROR_TINT_10,
    WARN_DARK,
    PIPELINE_STAGES, fmt_dur, fmt_mb,
)
from ui.widgets import Badge, Btn, PipelineStrip, SlimProgressBar, Spinner, BreathingDot, icon_pixmap, icon_label
from ui.state import AppState
from backend.models import Playlist, Video


class DetailPanel(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._videos: list[Video] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QWidget()
        self._stack_lay = QVBoxLayout(self._stack)
        self._stack_lay.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._stack)

        self._empty = _NoSelection()
        self._detail = _Detail(self._on_retry, self._on_retry_all)

        self._stack_lay.addWidget(self._empty)
        self._stack_lay.addWidget(self._detail)

        # playlists_changed is intentionally NOT connected here —
        # connecting it would rebuild all video rows on every throttle tick
        # (via _on_select_current) causing deleteLater/Spinner-timer segfaults.
        # The detail panel refreshes only on explicit selection_changed events.
        state.selection_changed.connect(self._on_select)
        state.video_row_changed.connect(self._on_video_row_changed)
        self._on_select(state.selected_id)

    def _on_select(self, pid: str):
        pl = next((p for p in self._state.playlists if p.id == pid), None)
        if pl:
            self._videos = list(pl.videos)
            self._detail.set_playlist(pl, self._videos)
            self._empty.setVisible(False)
            self._detail.setVisible(True)
        else:
            self._empty.setVisible(True)
            self._detail.setVisible(False)

    def _on_select_current(self):
        self._on_select(self._state.selected_id)

    def _on_video_row_changed(self, pid: str, idx: int):
        if pid != self._state.selected_id or not self._detail.isVisible():
            return
        pl = self._state.selected_playlist()
        if not pl or idx < 0 or idx >= len(pl.videos):
            return
        self._detail.update_row(idx, pl.videos[idx])
        self._detail.update_pipeline_counts(pl, pl.videos)

    def _on_retry(self, idx: int):
        v = self._videos[idx]
        v.stage = v.failed_at or "download"
        v.progress = 0.0
        v.retry_count += 1
        v.error = None
        pl = self._state.selected_playlist()
        if pl:
            self._detail.set_playlist(pl, self._videos)

    def _on_retry_all(self):
        for v in self._videos:
            if v.stage == "failed":
                v.stage = v.failed_at or "download"
                v.progress = 0.0
                v.retry_count += 1
                v.error = None
        pl = self._state.selected_playlist()
        if pl:
            self._detail.set_playlist(pl, self._videos)


class _Detail(QWidget):
    def __init__(self, on_retry, on_retry_all, parent=None):
        super().__init__(parent)
        self._on_retry = on_retry
        self._on_retry_all = on_retry_all
        self._video_rows: dict[int, VideoRow] = {}
        self.setStyleSheet(f"background:{BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = _DetailHeader(on_retry_all)
        root.addWidget(self._header)

        # table header (sticky)
        self._col_header = _ColHeader()
        root.addWidget(self._col_header)

        # scrollable video rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        # hide the vertical scrollbar so the viewport is always the same width
        # as _ColHeader above it — prevents column misalignment when content
        # overflows; wheel/touch scrolling still works without a visible bar
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background:{BG}; border:none; }}")
        self._rows_widget = QWidget()
        self._rows_widget.setStyleSheet(f"background:{BG};")
        self._rows_lay = QVBoxLayout(self._rows_widget)
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(0)
        self._rows_lay.addStretch()
        scroll.setWidget(self._rows_widget)
        scroll.viewport().setStyleSheet(f"background:{BG};")
        root.addWidget(scroll, 1)

    def set_playlist(self, pl: Playlist, videos: list[Video]):
        self._header.refresh(pl, videos)
        self._col_header.update(pl)
        self._video_rows.clear()

        # stop all active spinners before destroying their parent rows —
        # the Spinner QTimer fires every 16ms and will paint on a deleted
        # widget if we only use deleteLater() without stopping it first
        for sp in self._rows_widget.findChildren(Spinner):
            sp.stop()
        # BreathingDot timers are owned by the widget and die with deleteLater

        while self._rows_lay.count() > 1:
            item = self._rows_lay.takeAt(0)
            if item.widget():
                w = item.widget()
                w.hide()          # suppress any pending paint events
                w.deleteLater()

        rows = []
        for i, v in enumerate(videos):
            row = VideoRow(i, v, pl.split_enabled, self._on_retry)
            rows.append(row)
            self._rows_lay.insertWidget(i * 2, row)
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background:{BORDER};")
            self._rows_lay.insertWidget(i * 2 + 1, sep)
        self._video_rows = {i: row for i, row in enumerate(rows)}

    def update_row(self, idx: int, video: Video) -> None:
        if idx in self._video_rows:
            self._video_rows[idx].refresh(video)

    def update_pipeline_counts(self, pl: "Playlist", videos: list[Video]) -> None:
        self._header.refresh_pipeline(pl, videos)


class _DetailHeader(QWidget):
    def __init__(self, on_retry_all, parent=None):
        super().__init__(parent)
        self._on_retry_all = on_retry_all
        self.setObjectName("detailHeader")
        self.setStyleSheet(f"#detailHeader {{ background:{BG}; border-bottom:1px solid {BORDER}; }}")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(18, 14, 18, 12)
        self._lay.setSpacing(0)

    def _clear(self):
        # Only QWidget children are added to self._lay (wrapped rows),
        # so deleteLater() on each properly destroys all nested children.
        while self._lay.count():
            item = self._lay.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

    def refresh(self, pl: Playlist, videos: list[Video]):
        self._clear()

        from backend.api import playlist_size_estimate
        failed_count = sum(1 for v in videos if v.stage == "failed")
        pct = int(pl.completed / pl.video_count * 100) if pl.video_count else 0
        est_mb = playlist_size_estimate(pl)

        # ── top row (QWidget container so _clear can deleteLater it) ──────────
        top_w = QWidget(); top_w.setStyleSheet("background:transparent;")
        top = QHBoxLayout(top_w)
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)

        pfx = QLabel(pl.prefix)
        pfx.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        pfx.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:600; "
            f"color:{FG_SUBTLE}; background:{BG_ACCENT}; border-radius:6px; padding:4px 10px;"
        )
        top.addWidget(pfx)

        title_w = QWidget(); title_w.setStyleSheet("background:transparent;")
        title_col = QVBoxLayout(title_w)
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)
        t = QLabel(pl.title)
        t.setTextFormat(Qt.PlainText)
        t.setStyleSheet(f"font-size:16px; font-weight:600; letter-spacing:-0.01em; color:{FG};")
        title_col.addWidget(t)
        url_lbl = QLabel(pl.url)
        url_lbl.setTextFormat(Qt.PlainText)
        url_lbl.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; font-family:'JetBrains Mono',monospace;"
        )
        url_lbl.setMaximumWidth(500)
        title_col.addWidget(url_lbl)
        top.addWidget(title_w, 1)

        if failed_count > 0:
            retry_all_btn = QPushButton(f"  Retry {failed_count} failed")
            retry_all_btn.setIcon(QIcon(icon_pixmap("refresh", 12, ERROR_DARK)))
            retry_all_btn.setFixedHeight(28)
            retry_all_btn.setCursor(Qt.PointingHandCursor)
            retry_all_btn.setStyleSheet(f"""
                QPushButton {{ background:{BG}; color:{ERROR_DARK};
                    border:1px solid {ERROR_BORDER}; border-radius:6px;
                    padding:0 10px; font-size:12px; font-weight:600; }}
                QPushButton:hover {{ background:{ERROR_BG}; }}
            """)
            retry_all_btn.clicked.connect(self._on_retry_all)
            top.addWidget(retry_all_btn)

        more_btn = QPushButton()
        more_btn.setIcon(QIcon(icon_pixmap("more", 14, FG_MUTED)))
        more_btn.setFixedSize(28, 28)
        more_btn.setCursor(Qt.PointingHandCursor)
        more_btn.setStyleSheet(f"""
            QPushButton {{ background:{BG}; border:1px solid {BORDER}; border-radius:6px; }}
            QPushButton:hover {{ background:{BG_MUTED}; }}
        """)
        top.addWidget(more_btn)
        self._lay.addWidget(top_w)
        self._lay.addSpacing(14)

        # ── stats row (QWidget container) ─────────────────────────────────────
        stats_w = QWidget(); stats_w.setStyleSheet("background:transparent;")
        stats_row = QHBoxLayout(stats_w)
        stats_row.setContentsMargins(0, 0, 0, 0)
        stats_row.setSpacing(0)
        stats = [
            ("Progress", f"{pl.completed}/{pl.video_count}", f"{pct}%", False),
            ("Speed",    f"{pl.speed}×", "override" if pl.speed != 1.5 else "default", False),
            ("Split",    f"{pl.split_min}m" if pl.split_enabled else "off",
             "enabled" if pl.split_enabled else "—", False),
            ("Size",
             fmt_mb(pl.size_mb) if pl.size_mb else (f"~{est_mb} MB" if est_mb else "—"),
             pl.added_at, False),
            ("Failed",   str(failed_count), "none" if failed_count == 0 else "see below", True),
        ]
        for label, val, sub, is_fail in stats:
            lc = ERROR_DARK if is_fail and failed_count > 0 else FG_MUTED
            vc = ERROR_DARK if is_fail and failed_count > 0 else FG
            sc = ERROR_DARK if is_fail and failed_count > 0 else FG_MUTED
            col_w = QWidget(); col_w.setStyleSheet("background:transparent;")
            col = QVBoxLayout(col_w)
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(1)
            lbl = QLabel(label.upper())
            lbl.setTextFormat(Qt.PlainText)
            lbl.setStyleSheet(f"font-size:10px; color:{lc}; font-weight:500; letter-spacing:0.04em;")
            col.addWidget(lbl)
            val_lbl = QLabel(val)
            val_lbl.setTextFormat(Qt.PlainText)
            val_lbl.setStyleSheet(f"font-size:14px; font-weight:600; color:{vc};")
            col.addWidget(val_lbl)
            sub_lbl = QLabel(sub)
            sub_lbl.setTextFormat(Qt.PlainText)
            sub_lbl.setStyleSheet(f"font-size:10px; color:{sc};")
            col.addWidget(sub_lbl)
            stats_row.addWidget(col_w)
            stats_row.addSpacing(24)
        stats_row.addStretch()
        self._lay.addWidget(stats_w)
        self._lay.addSpacing(14)

        # ── pipeline strip (QWidget container) ────────────────────────────────
        pipe_w = QWidget(); pipe_w.setStyleSheet("background:transparent;")
        pipe_row = QHBoxLayout(pipe_w)
        pipe_row.setContentsMargins(0, 0, 0, 0)
        pipe_row.setSpacing(10)
        pl_lbl = QLabel("Pipeline")
        pl_lbl.setTextFormat(Qt.PlainText)
        pl_lbl.setStyleSheet(
            f"font-size:10px; color:{FG_MUTED}; font-weight:500; letter-spacing:0.04em;"
        )
        pipe_row.addWidget(pl_lbl)
        # count videos that have completed each stage (moved past it)
        _past = {
            "download": {"mp3", "split", "speed", "done"},
            "mp3":      {"split", "speed", "done"},
            "split":    {"speed", "done"},
            "speed":    {"done"},
        }
        total = len(pl.videos)
        stage_counts = {
            k: (sum(1 for v in pl.videos if v.stage in past), total)
            for k, past in _past.items()
        } if total else {}

        self._pipe = PipelineStrip(pl.active_stage, pl.split_enabled,
                                   running=(pl.status == "active"),
                                   stage_counts=stage_counts)
        pipe_row.addWidget(self._pipe)
        pipe_row.addStretch()
        self._lay.addWidget(pipe_w)

    def refresh_pipeline(self, pl: "Playlist", videos: list[Video]) -> None:
        if not hasattr(self, "_pipe"):
            return
        _past = {
            "download": {"mp3", "split", "speed", "done"},
            "mp3":      {"split", "speed", "done"},
            "split":    {"speed", "done"},
            "speed":    {"done"},
        }
        total = len(videos)
        stage_counts = {
            k: (sum(1 for v in videos if v.stage in past), total)
            for k, past in _past.items()
        } if total else {}
        self._pipe.update_stage(pl.active_stage, pl.split_enabled,
                                running=(pl.status == "active"),
                                stage_counts=stage_counts)


class _ColHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            background:{BG_ACCENT};
            border-top:1px solid {BORDER};
            border-bottom:1px solid {BORDER};
        """)
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(10, 0, 10, 0)
        self._lay.setSpacing(8)
        self._build(None)

    def _build(self, pl):
        while self._lay.count():
            item = self._lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def h(text, align=Qt.AlignLeft, width=None):
            lbl = QLabel(text)
            lbl.setTextFormat(Qt.PlainText)
            lbl.setStyleSheet(
                f"font-size:10px; color:{FG_MUTED}; font-weight:500; "
                f"letter-spacing:0.04em; text-transform:uppercase; "
                "background:transparent; border:none; text-decoration:none;"
            )
            lbl.setAlignment(align | Qt.AlignVCenter)
            if width:
                lbl.setFixedWidth(width)
            return lbl

        self._lay.addWidget(h("#", Qt.AlignRight, 28))
        self._lay.addWidget(h("Title"), 1)
        self._lay.addWidget(h("Dur", Qt.AlignRight, 50))
        self._lay.addWidget(h("DL",  Qt.AlignHCenter, 28))
        self._lay.addWidget(h("MP3", Qt.AlignHCenter, 28))
        split_val = f"/{pl.split_min}m" if (pl and pl.split_enabled) else "/–"
        self._lay.addWidget(h(split_val, Qt.AlignHCenter, 28))
        spd = f"×{pl.speed}" if pl else "×"
        self._lay.addWidget(h(spd, Qt.AlignHCenter, 28))
        self._lay.addWidget(h("State", Qt.AlignRight, 92))

    def update(self, pl):
        self._build(pl)


class VideoRow(QWidget):
    STAGE_ORDER = [s[0] for s in PIPELINE_STAGES]

    def __init__(self, idx: int, video: Video, split_enabled: bool,
                 on_retry, parent=None):
        super().__init__(parent)
        self._idx = idx
        self._v = video
        self._split = split_enabled
        self._on_retry_cb = on_retry

        is_failed = video.stage == "failed"
        self.setAttribute(Qt.WA_StyledBackground, True)
        if is_failed:
            self.setObjectName("videoRowFailed")
            self.setStyleSheet(
                f"#videoRowFailed {{ background: {ERROR_TINT_10}; }}"
            )
        else:
            self.setObjectName("videoRow")
            self.setStyleSheet(
                f"#videoRow {{ background: transparent; border-bottom:1px solid {BORDER}; }}"
            )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)

        # index
        num = QLabel(str(idx + 1).zfill(2))
        num.setFixedWidth(28)
        num.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        num.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace; font-size:11px; "
            f"color:{ERROR_DARK if is_failed else FG_MUTED}; "
            "background:transparent; border:none;"
        )
        lay.addWidget(num)

        # title + error
        col_w = QWidget()
        col_w.setStyleSheet("background:transparent;")
        col_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title_col = QVBoxLayout(col_w)
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)
        self._title_lbl = QLabel(video.title)
        self._title_lbl.setWordWrap(True)
        self._title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._title_lbl.setStyleSheet(f"font-size:12px; color:{FG};")
        title_col.addWidget(self._title_lbl)
        if is_failed and video.error:
            err_row = QHBoxLayout()
            err_row.setContentsMargins(0, 0, 0, 0)
            err_row.setSpacing(5)
            err_icon = icon_label("alert", 11, ERROR_DARK)
            err_row.addWidget(err_icon)
            err_lbl = QLabel(video.error)
            err_lbl.setStyleSheet(f"font-size:10.5px; color:{ERROR_DARK};")
            err_row.addWidget(err_lbl, 1)
            if video.retry_count > 0:
                rc = QLabel(f"· retried {video.retry_count}×")
                rc.setStyleSheet(f"font-size:10.5px; color:{FG_MUTED};")
                err_row.addWidget(rc)
            err_row.addStretch()
            err_w = QWidget()
            err_w.setLayout(err_row)
            title_col.addWidget(err_w)
        lay.addWidget(col_w, 1)

        # duration
        self._dur_lbl = QLabel(fmt_dur(video.duration_sec))
        self._dur_lbl.setFixedWidth(50)
        self._dur_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._dur_lbl.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace; font-size:11px; color:{FG_MUTED}; "
            "background:transparent; border:none;"
        )
        lay.addWidget(self._dur_lbl)

        # stage cells
        self._stage_cells: list[QWidget] = []
        stage_idx = self.STAGE_ORDER.index(video.stage) if video.stage in self.STAGE_ORDER else -1
        failed_idx = self.STAGE_ORDER.index(video.failed_at) if (is_failed and video.failed_at in self.STAGE_ORDER) else -1

        for i, (key, label, short, _) in enumerate(PIPELINE_STAGES):
            cell = QWidget()
            cell.setFixedSize(28, 28)
            cell.setStyleSheet("background:transparent;")
            c_lay = QHBoxLayout(cell)
            c_lay.setContentsMargins(0, 0, 0, 0)
            c_lay.setAlignment(Qt.AlignCenter)

            if key == "split" and not split_enabled:
                lbl = QLabel("—")
                lbl.setStyleSheet(f"color:{SURFACE_ALT}; font-size:12px;")
                c_lay.addWidget(lbl)
            elif is_failed and i == failed_idx:
                c_lay.addWidget(icon_label("alert", 13, ERROR))
            elif (not is_failed and (video.stage == "done" or stage_idx > i)) or \
                 (is_failed and i < failed_idx):
                c_lay.addWidget(icon_label("check", 12, SUCCESS))
            elif is_failed and i > failed_idx:
                lbl = QLabel("—")
                lbl.setStyleSheet(f"color:{SURFACE_ALT}; font-size:12px;")
                c_lay.addWidget(lbl)
            elif not is_failed and stage_idx == i:
                sp = Spinner(16, PRIMARY)
                c_lay.addWidget(sp)
            else:
                dot = QLabel()
                dot.setFixedSize(6, 6)
                dot.setStyleSheet(f"background:{SURFACE_ALT}; border-radius:3px;")
                c_lay.addWidget(dot)

            cell.setToolTip(label)
            lay.addWidget(cell)
            self._stage_cells.append(cell)

        # state / retry
        self._status_w = QWidget()
        self._status_w.setFixedWidth(92)
        self._status_w.setStyleSheet("background:transparent;")
        s_lay = QHBoxLayout(self._status_w)
        s_lay.setContentsMargins(0, 0, 0, 0)
        s_lay.setSpacing(0)
        s_lay.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._build_status(video, s_lay)

        lay.addWidget(self._status_w)

    def _build_status(self, video: Video, s_lay: QHBoxLayout) -> None:
        is_failed = video.stage == "failed"
        if video.stage == "done":
            b = Badge("Done", "success")
            b.setStyleSheet(b.styleSheet() + "font-size:10px; padding:1px 6px;")
            s_lay.addWidget(b)
        elif video.stage == "queued":
            ql = QLabel("Queued")
            ql.setStyleSheet(f"font-size:11px; color:{FG_MUTED};")
            s_lay.addWidget(ql)
        elif is_failed:
            r_btn = QPushButton("  Retry")
            r_btn.setIcon(QIcon(icon_pixmap("refresh", 11, ERROR_DARK)))
            r_btn.setFixedHeight(24)
            r_btn.setCursor(Qt.PointingHandCursor)
            r_btn.setStyleSheet(f"""
                QPushButton {{ background:{BG}; color:{ERROR_DARK};
                    border:1px solid #FCA5A5; border-radius:5px;
                    padding:0 8px; font-size:11px; font-weight:600; }}
                QPushButton:hover {{ background:{ERROR_BG}; }}
            """)
            idx = self._idx
            r_btn.clicked.connect(lambda _=False, i=idx: self._on_retry_cb(i))
            s_lay.addWidget(r_btn)
        else:
            pct_lbl = QLabel(f"{int((video.progress or 0) * 100)}%")
            pct_lbl.setStyleSheet(
                f"font-size:11px; color:{PRIMARY}; font-weight:500; "
                f"font-family:'JetBrains Mono',monospace;"
            )
            s_lay.addWidget(pct_lbl)

    def refresh(self, video: Video) -> None:
        self._v = video
        is_failed = video.stage == "failed"

        # update title and duration in place (no widget rebuild needed)
        self._title_lbl.setText(video.title)
        if video.duration_sec > 0:
            self._dur_lbl.setText(fmt_dur(video.duration_sec))

        # update row background style for failed state change
        if is_failed:
            self.setObjectName("videoRowFailed")
            self.setStyleSheet(f"#videoRowFailed {{ background: {ERROR_TINT_10}; }}")
        else:
            self.setObjectName("videoRow")
            self.setStyleSheet(f"#videoRow {{ background: transparent; border-bottom:1px solid {BORDER}; }}")

        stage_idx = self.STAGE_ORDER.index(video.stage) if video.stage in self.STAGE_ORDER else -1
        failed_idx = self.STAGE_ORDER.index(video.failed_at) if (is_failed and video.failed_at in self.STAGE_ORDER) else -1

        for i, (key, label, short, _) in enumerate(PIPELINE_STAGES):
            cell = self._stage_cells[i]
            c_lay = cell.layout()

            # stop and remove any active spinners before replacing cell content
            for j in range(c_lay.count() - 1, -1, -1):
                w = c_lay.itemAt(j).widget()
                if w is not None:
                    if isinstance(w, Spinner):
                        w.stop()
                    # BreathingDot: QTimer dies automatically with the widget
                    w.hide()
                    w.deleteLater()
                    c_lay.takeAt(j)

            if key == "split" and not self._split:
                lbl = QLabel("—")
                lbl.setStyleSheet(f"color:{SURFACE_ALT}; font-size:12px;")
                c_lay.addWidget(lbl)
            elif is_failed and i == failed_idx:
                c_lay.addWidget(icon_label("alert", 13, ERROR))
            elif (not is_failed and (video.stage == "done" or stage_idx > i)) or \
                 (is_failed and i < failed_idx):
                c_lay.addWidget(icon_label("check", 12, SUCCESS))
            elif is_failed and i > failed_idx:
                lbl = QLabel("—")
                lbl.setStyleSheet(f"color:{SURFACE_ALT}; font-size:12px;")
                c_lay.addWidget(lbl)
            elif not is_failed and stage_idx == i:
                sp = Spinner(16, PRIMARY)
                c_lay.addWidget(sp)
            else:
                dot = QLabel()
                dot.setFixedSize(6, 6)
                dot.setStyleSheet(f"background:{SURFACE_ALT}; border-radius:3px;")
                c_lay.addWidget(dot)

        # rebuild status widget content
        s_lay = self._status_w.layout()
        for j in range(s_lay.count() - 1, -1, -1):
            w = s_lay.itemAt(j).widget()
            if w is not None:
                w.hide()
                w.deleteLater()
                s_lay.takeAt(j)
        self._build_status(video, s_lay)


class _NoSelection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(12)

        icon_w = QWidget()
        icon_w.setFixedSize(60, 60)
        icon_w.setStyleSheet(f"background:{BG}; border:1px solid {BORDER}; border-radius:12px;")
        i_lay = QHBoxLayout(icon_w)
        i_lay.setContentsMargins(0, 0, 0, 0)
        i_lay.addWidget(icon_label("music", 28, FG_MUTED), alignment=Qt.AlignCenter)
        lay.addWidget(icon_w, alignment=Qt.AlignHCenter)

        t = QLabel("Nothing to show")
        t.setStyleSheet(f"font-size:14px; font-weight:600; color:{FG};")
        t.setAlignment(Qt.AlignHCenter)
        lay.addWidget(t)

        sub = QLabel("Add a YouTube playlist on the left to see its\nvideos and pipeline progress here.")
        sub.setStyleSheet(f"font-size:12px; color:{FG_MUTED};")
        sub.setAlignment(Qt.AlignHCenter)
        lay.addWidget(sub)
