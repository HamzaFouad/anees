from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QTextEdit,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QColor, QTextCursor

from ui.theme import (
    PRIMARY, FG, FG_MUTED, FG_SUBTLE, BG, BG_MUTED, BG_SUBTLE, BG_ACCENT, BORDER,
    SUCCESS, SUCCESS_DARK, SUCCESS_BG, ERROR, ERROR_DARK, ERROR_BG, ERROR_BORDER,
    SURFACE_ALT, ERROR_TINT_10, LOG_BG_DARK, FG_ON_DARK, FONT_MONO, TEXT_SM,
    WARN_DARK,
    PIPELINE_STAGES, fmt_dur, fmt_mb,
)
from ui.widgets import Badge, Btn, PipelineStrip, SlimProgressBar, Spinner, icon_pixmap, icon_label
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
        state.logs_changed.connect(self._detail.console.on_logs_changed)
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

        # ── console toggle bar ────────────────────────────────────────────────
        self._console_bar = QWidget()
        self._console_bar.setFixedHeight(28)
        self._console_bar.setStyleSheet(
            f"background:{BG_MUTED}; border-top:1px solid {BORDER};"
        )
        bar_lay = QHBoxLayout(self._console_bar)
        bar_lay.setContentsMargins(12, 0, 12, 0)
        bar_lay.setSpacing(6)
        self._console_toggle = QPushButton("▶  Console")
        self._console_toggle.setCursor(Qt.PointingHandCursor)
        self._console_toggle.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; "
            f"font-size:{TEXT_SM}px; font-weight:500; color:{FG_MUTED}; "
            f"font-family:{FONT_MONO}; }}"
            f"QPushButton:hover {{ color:{FG}; }}"
        )
        self._console_toggle.clicked.connect(self._toggle_console)
        bar_lay.addWidget(self._console_toggle)
        bar_lay.addStretch()
        root.addWidget(self._console_bar)

        # ── console panel (hidden by default) ────────────────────────────────
        self.console = _Console()
        self.console.setVisible(False)
        root.addWidget(self.console)

    def _toggle_console(self) -> None:
        visible = not self.console.isVisible()
        self.console.setVisible(visible)
        self._console_toggle.setText("▼  Console" if visible else "▶  Console")

    def set_playlist(self, pl: Playlist, videos: list[Video]):
        self._header.refresh(pl, videos)
        self._col_header.update(pl)
        self._video_rows.clear()

        # stop all active spinners before destroying their parent rows —
        # the Spinner QTimer fires every 16ms and will paint on a deleted
        # widget if we only use deleteLater() without stopping it first
        for sp in self._rows_widget.findChildren(Spinner):
            sp.stop()

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
        pipe = PipelineStrip(pl.active_stage, pl.split_enabled)
        pipe_row.addWidget(pipe)
        pipe_row.addStretch()
        self._lay.addWidget(pipe_w)


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
        spd = f"×{pl.speed}" if pl else "×"
        self._lay.addWidget(h(spd, Qt.AlignHCenter, 28))
        split_val = f"/{pl.split_min}" if (pl and pl.split_enabled) else "/–"
        self._lay.addWidget(h(split_val, Qt.AlignHCenter, 28))
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
        title_col = QVBoxLayout(col_w)
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)
        self._title_lbl = QLabel(video.title)
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


class _Console(QWidget):
    """Collapsible terminal panel — shows live yt-dlp / ffmpeg log output."""

    _LEVEL_COLOR = {
        "error": "#FF6B6B",
        "warn":  "#FFD93D",
        "info":  FG_ON_DARK,
        "debug": "#6B7280",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(200)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(26)
        toolbar.setStyleSheet(f"background:{LOG_BG_DARK}; border-bottom:1px solid #1e2a40;")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(10, 0, 10, 0)
        tb_lay.setSpacing(10)
        lbl = QLabel("OUTPUT")
        lbl.setStyleSheet(
            f"font-size:9px; font-weight:600; letter-spacing:.08em; "
            f"color:#4B5563; font-family:{FONT_MONO};"
        )
        tb_lay.addWidget(lbl)
        tb_lay.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; "
            f"font-size:9px; color:#4B5563; font-family:{FONT_MONO}; }}"
            f"QPushButton:hover {{ color:{FG_ON_DARK}; }}"
        )
        clear_btn.clicked.connect(self._clear)
        tb_lay.addWidget(clear_btn)
        root.addWidget(toolbar)

        # text area
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFrameShape(QFrame.NoFrame)
        self._text.setStyleSheet(
            f"QTextEdit {{ background:{LOG_BG_DARK}; color:{FG_ON_DARK}; "
            f"font-family:{FONT_MONO}; font-size:{TEXT_SM}px; "
            f"padding:6px 10px; border:none; }}"
        )
        root.addWidget(self._text)

        self._auto_scroll = True
        self._last_count  = 0

    def on_logs_changed(self) -> None:
        """Called by state.logs_changed — append only new entries."""
        from ui.state import AppState
        # access state via parent chain
        state = self._find_state()
        if not state:
            return
        logs = state.logs
        new_entries = logs[self._last_count:]
        if not new_entries:
            return
        self._last_count = len(logs)
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.End)
        for entry in new_entries:
            color = self._LEVEL_COLOR.get(entry.lvl, FG_ON_DARK)
            line = f'<span style="color:#4B5563">{entry.t}</span> ' \
                   f'<span style="color:{color}">{entry.msg}</span><br>'
            cursor.insertHtml(line)
        if self._auto_scroll:
            self._text.verticalScrollBar().setValue(
                self._text.verticalScrollBar().maximum()
            )

    def _clear(self) -> None:
        self._text.clear()
        self._last_count = 0

    def _find_state(self):
        """Walk up the widget tree to find DetailPanel which holds state."""
        w = self.parent()
        while w:
            if hasattr(w, '_state'):
                return w._state
            w = w.parent() if hasattr(w, 'parent') else None
        return None


class _NoSelection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_SUBTLE};")
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
