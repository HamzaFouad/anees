from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFileDialog, QTextEdit, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt, QThread, Signal as _Signal
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, PRIMARY_HOVER, ON_PRIMARY, PRIMARY_TINT_3,
    FG, FG_MUTED, BG, BG_SUBTLE, BORDER,
    SUCCESS, SUCCESS_BG, SUCCESS_DARK,
)
from ui.widgets import (
    icon_pixmap, icon_label, Checkbox, StyledInput,
    section_card_qss,
)
from ui.state import AppState
from backend.models import Playlist, Video
from backend.api.config import get_output_root


def _scan_output_root(output_root: str) -> list[Playlist]:
    """Discover playlist folders on disk and build minimal Playlist stubs.

    Used when the in-memory queue is empty (e.g. after a crash/restart).
    A valid folder looks like ``{prefix}_{title}/`` and contains *.mp3 files.
    """
    import os, re, uuid
    from pathlib import Path

    root = Path(output_root)
    if not root.is_dir():
        return []

    playlists: list[Playlist] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        m = re.match(r'^(\w+)_(.+)$', entry.name)
        if not m:
            continue
        prefix, title_slug = m.group(1), m.group(2)
        mp3s = sorted(entry.glob("*.mp3"))
        if not mp3s:
            continue
        size_mb = sum(f.stat().st_size for f in mp3s) / 1024 / 1024
        pl = Playlist(
            id           = str(uuid.uuid5(uuid.NAMESPACE_URL, str(entry))),
            prefix       = prefix,
            title        = title_slug.replace("_", " "),
            url          = "",
            video_count  = len(mp3s),
            completed    = len(mp3s),
            status       = "done",
            active_stage = "done",
            speed        = 1.0,
            split_enabled= False,
            split_min    = 30,
            size_mb      = round(size_mb, 1),
            added_at     = "",
            videos       = [Video(f.stem, 0, "done") for f in mp3s],
        )
        playlists.append(pl)
    return playlists


def _sep(layout) -> None:
    f = QFrame(); f.setFixedHeight(1)
    f.setStyleSheet(f"background:{BORDER}; border:none;")
    layout.addWidget(f)


def _section_lbl(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        f"font-size:10px; font-weight:600; color:{FG_MUTED}; "
        "letter-spacing:0.05em; background:transparent; border:none;"
    )
    return l


class MergeDialog(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state

        # merge from in-memory queue; fall back to scanning the output folder
        # so the dialog works after a crash/restart with no queue loaded
        mem_pls = [p for p in state.playlists if p.completed > 0]
        disk_pls = _scan_output_root(get_output_root()) if not mem_pls else []
        self._playlists: list[Playlist] = mem_pls or disk_pls

        self._selected: set[str] = {p.id for p in self._playlists}
        self._worker = None

        self.setWindowTitle("Merge to single folder")
        self.setFixedWidth(620)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("mergeCard")
        card.setStyleSheet(
            f"#mergeCard {{ background:{BG}; border-radius:12px; "
            f"border:1px solid {BORDER}; }}"
        )
        outer.addWidget(card)

        root = QVBoxLayout(card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        _sep(root)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background:{BG}; border:none; }}")
        scroll.setWidget(self._build_body())
        scroll.viewport().setStyleSheet(f"background:{BG};")
        root.addWidget(scroll, 1)

        _sep(root)
        root.addWidget(self._build_footer())

    # ── header ────────────────────────────────────────────────────────────────
    def _build_header(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 16, 16, 16)
        lay.setSpacing(12)

        text_col = QWidget(); text_col.setStyleSheet("background:transparent;")
        text_lay = QVBoxLayout(text_col)
        text_lay.setContentsMargins(0, 0, 0, 0)
        text_lay.setSpacing(6)

        title_row = QWidget(); title_row.setStyleSheet("background:transparent;")
        title_lay = QHBoxLayout(title_row)
        title_lay.setContentsMargins(0, 0, 0, 0)
        title_lay.setSpacing(8)
        title_lay.addWidget(icon_label("merge", 15, FG))
        title_lbl = QLabel("Build JOC Card")
        title_lbl.setStyleSheet(f"font-size:15px; font-weight:700; color:{FG};")
        title_lay.addWidget(title_lbl)
        text_lay.addWidget(title_row)

        desc = QLabel(
            "Assembles your playlists into a single memory card folder ready for a JOC device. "
            "Files are numbered sequentially (1111, 1112, …) with a splitter clip before each playlist."
        )
        desc.setStyleSheet(f"font-size:12px; color:{FG_MUTED};")
        desc.setWordWrap(True)
        text_lay.addWidget(desc)
        lay.addWidget(text_col, 1)

        x_btn = QPushButton()
        x_btn.setIcon(QIcon(icon_pixmap("x", 14, FG_MUTED)))
        x_btn.setFixedSize(28, 28)
        x_btn.setCursor(Qt.PointingHandCursor)
        x_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; border-radius:5px; }}"
            f"QPushButton:hover {{ background:{BG_SUBTLE}; }}"
        )
        x_btn.clicked.connect(self.reject)
        lay.addWidget(x_btn)
        return w

    # ── body ──────────────────────────────────────────────────────────────────
    def _build_body(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        # DESTINATION FOLDER
        dest_sec = QWidget(); dest_sec.setStyleSheet("background:transparent;")
        dest_lay = QVBoxLayout(dest_sec)
        dest_lay.setContentsMargins(0, 0, 0, 0); dest_lay.setSpacing(6)
        dest_lay.addWidget(_section_lbl("Destination Folder"))
        dest_row = QWidget(); dest_row.setStyleSheet("background:transparent;")
        dest_r = QHBoxLayout(dest_row)
        dest_r.setContentsMargins(0, 0, 0, 0); dest_r.setSpacing(8)
        default_dest = get_output_root().rstrip("/\\")
        self._dest_input = StyledInput(default_dest, mono=True)
        self._dest_input.setText(default_dest)
        dest_r.addWidget(self._dest_input, 1)
        browse_btn = QPushButton("  Browse")
        browse_btn.setIcon(QIcon(icon_pixmap("folder", 13, FG_MUTED)))
        browse_btn.setFixedHeight(32)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG}; border:1px solid {BORDER};
                border-radius:8px; font-size:12px; padding:0 12px;
            }}
            QPushButton:hover {{ background:{BG_SUBTLE}; }}
        """)
        browse_btn.clicked.connect(self._on_browse)
        dest_r.addWidget(browse_btn)
        dest_lay.addWidget(dest_row)
        lay.addWidget(dest_sec)

        # PLAYLISTS TO INCLUDE
        eligible = list(self._playlists)
        n_sel = sum(1 for p in eligible if p.id in self._selected)
        self._pl_label = _section_lbl(
            f"Playlists to Include ({n_sel}/{len(eligible)} selected)"
        )
        lay.addWidget(self._pl_label)
        self._pl_list = _PlaylistChecklist(eligible, self._selected)
        self._pl_list.selection_changed.connect(self._on_selection_changed)
        lay.addWidget(self._pl_list)

        # SPLITTER CLIPS (always on — fixed playlist)
        self._splitter_section = _SplitterSection()
        self._splitter_section.update_count(len(self._selected))  # seed before fetch completes
        lay.addWidget(self._splitter_section)

        self._update_preview()
        return w

    # ── footer ────────────────────────────────────────────────────────────────
    def _build_footer(self) -> QWidget:
        w = QWidget(); w.setFixedHeight(56)
        w.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(8)

        self._footer_info = QLabel("")
        self._footer_info.setStyleSheet(f"font-size:11px; color:{FG_MUTED};")
        lay.addWidget(self._footer_info)
        lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG}; border:1px solid {BORDER};
                border-radius:8px; padding:0 20px; font-size:13px;
            }}
            QPushButton:hover {{ background:{BG_SUBTLE}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        lay.addWidget(cancel_btn)

        self._merge_btn = QPushButton("  Merge playlists")
        self._merge_btn.setIcon(QIcon(icon_pixmap("merge", 13, ON_PRIMARY)))
        self._merge_btn.setFixedHeight(36)
        self._merge_btn.setCursor(Qt.PointingHandCursor)
        self._merge_btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:{ON_PRIMARY}; border:none;
                border-radius:8px; padding:0 20px; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
        """)
        self._merge_btn.clicked.connect(self._on_merge)
        lay.addWidget(self._merge_btn)

        self._update_footer()
        return w

    # ── handlers ──────────────────────────────────────────────────────────────
    def _on_browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select destination folder",
            self._dest_input.text() or get_output_root(),
        )
        if path:
            self._dest_input.setText(path)

    def _on_selection_changed(self) -> None:
        eligible = list(self._playlists)
        n_sel = len(self._selected)
        self._pl_label.setText(
            f"Playlists to Include ({n_sel}/{len(eligible)} selected)"
        )
        self._splitter_section.update_count(n_sel)
        self._update_footer()
        self._update_preview()

    def _update_footer(self) -> None:
        selected_pls = [p for p in self._playlists if p.id in self._selected]
        total_files = sum(p.completed for p in selected_pls)
        total_mb = sum(p.size_mb or 0 for p in selected_pls)
        n_sel = len(selected_pls)
        n_splitters = n_sel  # one splitter before each playlist

        files_str = f"{total_files} + {n_splitters} splitter files" if n_splitters else f"{total_files} files"
        self._footer_info.setText(
            f"{files_str} · {total_mb:.1f} MB · moves files"
        )
        self._merge_btn.setText(f"  Merge {n_sel} playlist{'s' if n_sel != 1 else ''}")
        self._merge_btn.setEnabled(bool(n_sel))

    def _update_preview(self) -> None:
        from backend.services.merge_service import JOC_BASE
        selected_pls = sorted(
            (p for p in self._playlists if p.id in self._selected),
            key=lambda p: p.prefix,
        )
        lines: list[str] = []
        joc = JOC_BASE
        for idx, pl in enumerate(selected_pls):
            lines.append(f"{joc}.mp3  ← splitter")
            joc += 1
            count = pl.video_count or len(pl.videos) or 1
            shown = min(count, 3)
            for _ in range(shown):
                lines.append(f"{joc}.mp3")
                joc += 1
            if count > shown:
                lines.append(f"  … ({count - shown} more, up to {joc + count - shown - 1}.mp3)")
                joc += count - shown
        self._splitter_section.update_preview("\n".join(lines[:12]))

    def _on_merge(self) -> None:
        dest = self._dest_input.text().strip()
        if not dest:
            self._footer_info.setText("Please enter a destination folder.")
            return

        selected_pls = [p for p in self._playlists if p.id in self._selected]
        if not selected_pls:
            return

        splitter_urls = self._splitter_section.get_urls(len(selected_pls))
        if not splitter_urls:
            self._footer_info.setText("Splitter playlist still loading — please wait.")
            return

        self._merge_btn.setEnabled(False)
        self._merge_btn.setText("  Merging…")
        self._footer_info.setText("Downloading splitter clips…")

        from ui.workers.merge_worker import MergeWorker
        self._worker = MergeWorker(
            selected_pls, get_output_root(), dest, splitter_urls, parent=self
        )
        self._worker.progress.connect(
            lambda c, t: self._footer_info.setText(f"Copying files… ({c}/{t})")
        )
        self._worker.completed.connect(self._on_complete)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_complete(self, n: int) -> None:
        self._footer_info.setText(f"Done — {n} files copied.")
        self._merge_btn.setEnabled(True)
        self._merge_btn.setText("  Done")
        self._merge_btn.setStyleSheet(
            f"QPushButton {{ background:{SUCCESS_BG}; color:{SUCCESS_DARK}; border:none; "
            f"border-radius:8px; padding:0 20px; font-size:13px; font-weight:600; }}"
        )
        self._merge_btn.clicked.disconnect()
        self._merge_btn.clicked.connect(self.accept)

    def _on_failed(self, msg: str) -> None:
        self._footer_info.setText(f"Error: {msg}")
        self._merge_btn.setEnabled(True)
        self._merge_btn.setText("  Retry")

    def reject(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
        super().reject()


# ── Playlist checklist ────────────────────────────────────────────────────────

class _PlaylistChecklist(QWidget):
    selection_changed = _Signal()

    def __init__(self, playlists: list[Playlist], selected: set[str], parent=None):
        super().__init__(parent)
        self._selected = selected
        self._rows: list[_CheckRow] = []
        self.setObjectName("plChecklist")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(section_card_qss("plChecklist", PRIMARY_TINT_3))
        self.setMaximumHeight(200)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(1, 1, 1, 1)
        lay.setSpacing(0)

        for i, p in enumerate(playlists):
            eligible = p.completed > 0
            row = _CheckRow(p, p.id in selected, eligible)
            self._rows.append(row)
            if eligible:
                row.toggled.connect(
                    lambda checked, pid=p.id: self._on_toggle(pid, checked)
                )
            lay.addWidget(row)
            if i < len(playlists) - 1:
                sep = QFrame(); sep.setFixedHeight(1)
                sep.setStyleSheet(f"background:{BORDER}; border:none;")
                lay.addWidget(sep)

    def _on_toggle(self, pid: str, checked: bool) -> None:
        if checked:
            self._selected.add(pid)
        else:
            self._selected.discard(pid)
        for row in self._rows:
            if row._pl.id == pid:
                row._checked = checked
                row.update()
        self.selection_changed.emit()


class _CheckRow(QWidget):
    toggled = _Signal(bool)

    def __init__(self, pl: Playlist, checked: bool, eligible: bool, parent=None):
        super().__init__(parent)
        self._pl = pl
        self._checked = checked
        self._eligible = eligible

        if eligible:
            self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(8)

        self._check = Checkbox(checked)
        lay.addWidget(self._check)

        pfx = QLabel(pl.prefix)
        pfx.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace; font-size:11px; "
            f"font-weight:600; color:{FG_MUTED}; background:transparent; border:none;"
        )
        lay.addWidget(pfx)

        title = QLabel(pl.title)
        title.setStyleSheet(f"font-size:12px; color:{FG}; background:transparent; border:none;")
        lay.addWidget(title, 1)

        stats_text = f"{pl.completed}/{pl.video_count}"
        if pl.size_mb:
            stats_text += f" · {pl.size_mb:.1f} MB"
        stats = QLabel(stats_text)
        stats.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; "
            f"font-family:'JetBrains Mono',monospace; background:transparent; border:none;"
        )
        lay.addWidget(stats)

    def mousePressEvent(self, event):
        if self._eligible:
            self._checked = not self._checked
            self._check.checked = self._checked
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)


SPLITTER_PLAYLIST = "https://www.youtube.com/playlist?list=PLoOpuURvl_OMoX3iDm8WB9uYWFutIG9dj"


# ── Splitter section ──────────────────────────────────────────────────────────

class _SplitterSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # list of (url, title, duration_sec) from the splitter playlist
        self._clips: list[tuple[str, str, int]] = []
        self._count = 0  # how many playlists are selected
        self._fetch_thread: QThread | None = None

        self.setObjectName("splitterSection")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(section_card_qss("splitterSection", PRIMARY_TINT_3))

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        # ── header ──
        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(14, 12, 14, 12)
        top_lay.setSpacing(8)
        top_lay.addWidget(icon_label("scissors", 13, FG))
        title_lbl = QLabel("Splitter clips")
        title_lbl.setStyleSheet(
            f"font-size:12px; font-weight:600; color:{FG}; background:transparent; border:none;"
        )
        top_lay.addWidget(title_lbl)
        top_lay.addStretch()
        self._status_lbl = QLabel("Loading…")
        self._status_lbl.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; background:transparent; border:none;"
        )
        top_lay.addWidget(self._status_lbl)
        self._root.addWidget(top)

        # ── clip list ──
        clips_border = QWidget()
        clips_border.setObjectName("clipsArea")
        clips_border.setStyleSheet(
            f"#clipsArea {{ border-top:1px solid {BORDER}; background:transparent; }}"
        )
        clips_v = QVBoxLayout(clips_border)
        clips_v.setContentsMargins(0, 0, 0, 0)
        clips_v.setSpacing(0)

        self._list_scroll = QScrollArea()
        self._list_scroll.setWidgetResizable(True)
        self._list_scroll.setFrameShape(QFrame.NoFrame)
        self._list_scroll.setFixedHeight(130)
        self._list_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self._list_scroll.viewport().setStyleSheet("background:transparent;")
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background:transparent;")
        self._list_lay = QVBoxLayout(self._list_widget)
        self._list_lay.setContentsMargins(0, 0, 0, 0)
        self._list_lay.setSpacing(0)
        self._list_lay.addStretch()
        self._list_scroll.setWidget(self._list_widget)
        clips_v.addWidget(self._list_scroll)
        self._root.addWidget(clips_border)

        # ── OUTPUT ORDER PREVIEW ──
        prev_row = QWidget()
        prev_row.setObjectName("splitterPreviewRow")
        prev_row.setStyleSheet(
            f"#splitterPreviewRow {{ border-top:1px solid {BORDER}; background:transparent; }}"
        )
        prev_lay = QVBoxLayout(prev_row)
        prev_lay.setContentsMargins(14, 10, 14, 12)
        prev_lay.setSpacing(6)
        prev_lay.addWidget(_section_lbl("Output Order Preview"))
        self._preview_box = QTextEdit()
        self._preview_box.setReadOnly(True)
        self._preview_box.setFixedHeight(72)
        self._preview_box.setStyleSheet(
            f"QTextEdit {{ background:#F3F3F7; border:1px solid {BORDER}; "
            f"border-radius:6px; padding:6px 10px; "
            f"font-family:'JetBrains Mono',monospace; font-size:11px; color:{FG_MUTED}; }}"
        )
        prev_lay.addWidget(self._preview_box)
        self._root.addWidget(prev_row)

        # auto-fetch the fixed splitter playlist
        self._start_fetch()

    # ── public API ────────────────────────────────────────────────────────────

    def get_urls(self, n: int) -> list[str]:
        if not self._clips:
            return []
        return [self._clips[i % len(self._clips)][0] for i in range(n)]

    def update_count(self, n: int) -> None:
        self._count = n
        if self._clips:
            self._status_lbl.setText(f"{n} clips")
        self._refresh_list()

    def update_preview(self, text: str) -> None:
        self._preview_box.setPlainText(text)

    # ── fetch ─────────────────────────────────────────────────────────────────

    def _start_fetch(self) -> None:
        self._fetch_thread = _FetchPlaylistThread(SPLITTER_PLAYLIST, self)
        self._fetch_thread.fetched.connect(self._on_fetched)
        self._fetch_thread.errored.connect(self._on_fetch_error)
        self._fetch_thread.start()

    def _on_fetched(self, clips: list) -> None:
        self._clips = clips
        self._status_lbl.setText(f"{self._count} clips")

        self._refresh_list()

    def _on_fetch_error(self, msg: str) -> None:
        self._status_lbl.setText("Failed to load — retry later")

    # ── list rendering ────────────────────────────────────────────────────────

    def _refresh_list(self) -> None:
        if not self._clips or not self._count:
            return
        while self._list_lay.count() > 1:
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i in range(self._count):
            _, title, dur = self._clips[i % len(self._clips)]
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(14, 6, 14, 6)
            row_lay.setSpacing(8)

            idx_lbl = QLabel(str(i + 1))
            idx_lbl.setFixedWidth(20)
            idx_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            idx_lbl.setStyleSheet(
                f"font-size:11px; font-weight:600; color:{PRIMARY}; background:transparent; border:none;"
            )
            row_lay.addWidget(idx_lbl)

            url, _, _ = self._clips[i % len(self._clips)]
            t_lbl = QLabel(f'<a href="{url}" style="color:{PRIMARY}; text-decoration:none;">{title[:55]}</a>')
            t_lbl.setTextFormat(Qt.RichText)
            t_lbl.setOpenExternalLinks(True)
            t_lbl.setCursor(Qt.PointingHandCursor)
            t_lbl.setStyleSheet("font-size:11px; background:transparent; border:none;")
            t_lbl.setToolTip(url)
            row_lay.addWidget(t_lbl, 1)

            mins, secs = divmod(dur, 60)
            d_lbl = QLabel(f"{mins}:{secs:02d}")
            d_lbl.setStyleSheet(
                f"font-size:11px; color:{FG_MUTED}; "
                f"font-family:'JetBrains Mono',monospace; background:transparent; border:none;"
            )
            row_lay.addWidget(d_lbl)

            self._list_lay.insertWidget(i, row)

            if i < len(self._clips) - 1:
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet(f"background:{BORDER}; border:none;")
                self._list_lay.insertWidget(i * 2 + 1, sep)


class _FetchPlaylistThread(QThread):
    fetched = _Signal(object)   # list[tuple[str, str, int]]
    errored = _Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self) -> None:
        try:
            from backend.api.merge import MergeAPI
            clips = MergeAPI().fetch_splitter_playlist(self._url)
            self.fetched.emit(clips)
        except Exception as exc:
            self.errored.emit(str(exc))
