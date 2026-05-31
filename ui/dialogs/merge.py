from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QWidget, QFileDialog, QTextEdit, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt, QThread, Signal as _Signal
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, PRIMARY_HOVER, ON_PRIMARY, PRIMARY_TINT_4,
    FG, FG_MUTED, BG, BG_SUBTLE, BG_ACCENT, BORDER,
    SUCCESS, SUCCESS_BG, SUCCESS_DARK,
)
from ui.widgets import Toggle, StyledInput, icon_pixmap, icon_label, Checkbox
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
        title_lbl = QLabel("Merge to single folder")
        title_lbl.setStyleSheet(f"font-size:15px; font-weight:700; color:{FG};")
        title_lay.addWidget(title_lbl)
        text_lay.addWidget(title_row)

        desc = QLabel(
            "Moves the processed <b>.mp3</b> files from every selected playlist "
            "into one flat folder — handy for syncing to a phone, MP3 player, or car."
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
        default_dest = get_output_root().rstrip("/\\") + "/_merged"
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

        # SPLITTER CLIP
        self._splitter_section = _SplitterSection()
        self._splitter_section.toggled.connect(self._update_footer)
        lay.addWidget(self._splitter_section)

        # OUTPUT ORDER PREVIEW
        self._preview_sec = QWidget(); self._preview_sec.setStyleSheet("background:transparent;")
        prev_lay = QVBoxLayout(self._preview_sec)
        prev_lay.setContentsMargins(0, 0, 0, 0); prev_lay.setSpacing(6)
        prev_lay.addWidget(_section_lbl("Output Order Preview"))
        self._preview_box = QTextEdit()
        self._preview_box.setReadOnly(True)
        self._preview_box.setFixedHeight(80)
        self._preview_box.setStyleSheet(
            f"QTextEdit {{ background:{BG_ACCENT}; border:1px solid {BORDER}; "
            f"border-radius:8px; padding:6px 10px; "
            f"font-family:'JetBrains Mono',monospace; font-size:11px; color:{FG_MUTED}; }}"
        )
        prev_lay.addWidget(self._preview_box)
        lay.addWidget(self._preview_sec)

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
        self._update_footer()
        self._update_preview()

    def _update_footer(self) -> None:
        selected_pls = [p for p in self._playlists if p.id in self._selected]
        total_files = sum(p.completed for p in selected_pls)
        total_mb = sum(p.size_mb or 0 for p in selected_pls)
        n_sel = len(selected_pls)
        splitter_on = self._splitter_section._on if hasattr(self, "_splitter_section") else False
        n_splitters = max(0, n_sel - 1) if splitter_on else 0

        files_str = f"{total_files} + {n_splitters} splitter files" if n_splitters else f"{total_files} files"
        self._footer_info.setText(
            f"{files_str} · {total_mb:.1f} MB · moves files"
        )
        self._merge_btn.setText(f"  Merge {n_sel} playlist{'s' if n_sel != 1 else ''}")
        self._merge_btn.setEnabled(bool(n_sel))

    def _update_preview(self) -> None:
        selected_pls = sorted(
            (p for p in self._playlists if p.id in self._selected),
            key=lambda p: p.prefix,
        )
        lines: list[str] = []
        for pl in selected_pls:
            for i, v in enumerate(pl.videos[:3]):
                safe = v.title[:45].replace("/", "_")
                lines.append(f"{pl.prefix}_{i+1:02d}_{safe}.mp3")
            if len(pl.videos) > 3:
                lines.append(f"{pl.prefix}_…")
        self._preview_box.setPlainText("\n".join(lines[:8]))
        self._preview_sec.setVisible(bool(lines))

    def _on_merge(self) -> None:
        dest = self._dest_input.text().strip()
        if not dest:
            self._footer_info.setText("Please enter a destination folder.")
            return
        splitter_url = None
        if self._splitter_section._on:
            splitter_url = self._splitter_section.url()
            if not splitter_url:
                self._footer_info.setText("Enter a splitter clip URL or disable splitter.")
                return

        selected_pls = [p for p in self._playlists if p.id in self._selected]
        if not selected_pls:
            return

        self._merge_btn.setEnabled(False)
        self._merge_btn.setText("  Merging…")
        self._footer_info.setText("Copying files…")

        from ui.workers.merge_worker import MergeWorker
        self._worker = MergeWorker(
            selected_pls, get_output_root(), dest, splitter_url, parent=self
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
        self.setStyleSheet(
            f"#plChecklist {{ border:1px solid {BORDER}; border-radius:6px; background:{BG}; }}"
        )
        self.setMaximumHeight(200)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        for i, p in enumerate(playlists):
            eligible = p.completed > 0
            row = _CheckRow(p, p.id in selected, eligible)
            self._rows.append(row)
            if eligible:
                row.toggled.connect(
                    lambda checked, pid=p.id: self._on_toggle(pid, checked)
                )
            has_border = i < len(playlists) - 1
            self._set_row_style(row, p.id in selected, has_border)
            lay.addWidget(row)

    def _set_row_style(self, row: "_CheckRow", checked: bool, border_bottom: bool) -> None:
        oid = f"chkRow_{id(row)}"
        row.setObjectName(oid)
        bg = BG_ACCENT if checked else BG
        border = f"border-bottom:1px solid {BORDER};" if border_bottom else ""
        row.setStyleSheet(f"#{oid} {{ background:{bg}; {border} }}")

    def _on_toggle(self, pid: str, checked: bool) -> None:
        if checked:
            self._selected.add(pid)
        else:
            self._selected.discard(pid)
        for row in self._rows:
            if row._pl.id == pid:
                has_border = self._rows.index(row) < len(self._rows) - 1
                self._set_row_style(row, checked, has_border)
        self.selection_changed.emit()


class _CheckRow(QWidget):
    toggled = _Signal(bool)

    def __init__(self, pl: Playlist, checked: bool, eligible: bool, parent=None):
        super().__init__(parent)
        self._pl = pl
        self._checked = checked
        self._eligible = eligible
        self.setAttribute(Qt.WA_StyledBackground, True)

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


# ── Splitter section ──────────────────────────────────────────────────────────

class _SplitterSection(QWidget):
    toggled = _Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self._fetch_thread: QThread | None = None

        self.setObjectName("splitterSection")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"#splitterSection {{ border:1px solid {BORDER}; border-radius:8px; background:{BG}; }}"
        )

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        # toggle row
        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(14, 12, 14, 12)
        top_lay.setSpacing(12)

        text = QWidget()
        text_lay = QVBoxLayout(text)
        text_lay.setContentsMargins(0, 0, 0, 0); text_lay.setSpacing(3)

        title_row = QWidget()
        title_lay = QHBoxLayout(title_row)
        title_lay.setContentsMargins(0, 0, 0, 0); title_lay.setSpacing(6)
        title_lay.addWidget(icon_label("scissors", 13, FG))
        title_lbl = QLabel("Splitter clip between playlists")
        title_lbl.setStyleSheet(
            f"font-size:12px; font-weight:600; color:{FG}; background:transparent; border:none;"
        )
        title_lay.addWidget(title_lbl)
        text_lay.addWidget(title_row)

        desc = QLabel(
            'Insert one short YouTube clip in the merged folder between each playlist — '
            'a chime, jingle, or "next up" marker so you hear where one ends and the next begins.'
        )
        desc.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; background:transparent; border:none;"
        )
        desc.setWordWrap(True)
        text_lay.addWidget(desc)
        top_lay.addWidget(text, 1)

        self._toggle = Toggle(False)
        self._toggle.toggled.connect(self._on_toggle)
        top_lay.addWidget(self._toggle)
        self._root.addWidget(top)

        # URL row (hidden initially)
        self._url_row = QWidget()
        self._url_row.setObjectName("splitterUrlRow")
        self._url_row.setStyleSheet(
            f"#splitterUrlRow {{ border-top:1px solid {BORDER}; background:transparent; }}"
        )
        self._url_row.setVisible(False)
        url_lay = QVBoxLayout(self._url_row)
        url_lay.setContentsMargins(14, 10, 14, 12)
        url_lay.setSpacing(8)

        input_row = QWidget()
        input_lay = QHBoxLayout(input_row)
        input_lay.setContentsMargins(0, 0, 0, 0); input_lay.setSpacing(8)
        self._url_input = StyledInput("https://youtube.com/watch?v=…", mono=True)
        input_lay.addWidget(self._url_input, 1)
        self._fetch_btn = QPushButton("Fetch")
        self._fetch_btn.setFixedHeight(32)
        self._fetch_btn.setCursor(Qt.PointingHandCursor)
        self._fetch_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG}; border:1px solid {BORDER};
                border-radius:8px; padding:0 14px; font-size:12px;
            }}
            QPushButton:hover {{ background:{BG_SUBTLE}; }}
            QPushButton:disabled {{ color:{FG_MUTED}; }}
        """)
        self._fetch_btn.clicked.connect(self._on_fetch)
        input_lay.addWidget(self._fetch_btn)
        url_lay.addWidget(input_row)

        # card slot
        self._card_slot = QWidget(); self._card_slot.setStyleSheet("background:transparent;")
        self._card_slot_lay = QVBoxLayout(self._card_slot)
        self._card_slot_lay.setContentsMargins(0, 0, 0, 0)
        url_lay.addWidget(self._card_slot)

        self._root.addWidget(self._url_row)

    def url(self) -> str:
        return self._url_input.text().strip()

    def _on_toggle(self, on: bool) -> None:
        self._on = on
        self._url_row.setVisible(on)
        bg = BG_ACCENT if on else BG
        self.setStyleSheet(
            f"#splitterSection {{ border:1px solid {BORDER}; border-radius:8px; background:{bg}; }}"
        )
        self.toggled.emit(on)

    def _on_fetch(self) -> None:
        url = self._url_input.text().strip()
        if not url:
            return
        self._fetch_btn.setText("Fetching…")
        self._fetch_btn.setEnabled(False)

        self._fetch_thread = _FetchInfoThread(url, self)
        self._fetch_thread.resolved.connect(self._on_resolved)
        self._fetch_thread.errored.connect(self._on_fetch_error)
        self._fetch_thread.start()

    def _on_resolved(self, title: str, dur: int) -> None:
        self._fetch_btn.setText("Re-fetch")
        self._fetch_btn.setEnabled(True)
        self._show_card(title, dur)

    def _on_fetch_error(self, msg: str) -> None:
        self._fetch_btn.setText("Retry")
        self._fetch_btn.setEnabled(True)

    def _show_card(self, title: str, dur: int) -> None:
        while self._card_slot_lay.count():
            item = self._card_slot_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        card = QWidget()
        card_lay = QHBoxLayout(card)
        card_lay.setContentsMargins(10, 8, 10, 8)
        card_lay.setSpacing(10)

        thumb = QWidget()
        thumb.setFixedSize(42, 42)
        thumb.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #1a2547,stop:1 #2a3050); border-radius:6px;"
        )
        thumb_inner = QHBoxLayout(thumb)
        thumb_inner.setContentsMargins(0, 0, 0, 0)
        thumb_inner.addWidget(
            icon_label("music", 16, "rgba(255,255,255,0.7)"), alignment=Qt.AlignCenter
        )
        card_lay.addWidget(thumb)

        info = QWidget()
        info_lay = QVBoxLayout(info)
        info_lay.setContentsMargins(0, 0, 0, 0); info_lay.setSpacing(2)
        t = QLabel(title[:60])
        t.setStyleSheet(
            f"font-size:12px; font-weight:600; color:{FG}; background:transparent; border:none;"
        )
        info_lay.addWidget(t)
        mins, secs = divmod(dur, 60)
        sub = QLabel(f"{mins}:{secs:02d}")
        sub.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; "
            f"font-family:'JetBrains Mono',monospace; background:transparent; border:none;"
        )
        info_lay.addWidget(sub)
        card_lay.addWidget(info, 1)

        card_lay.addWidget(icon_label("check", 14, SUCCESS))

        self._card_slot_lay.addWidget(card)


class _FetchInfoThread(QThread):
    resolved = _Signal(str, int)
    errored  = _Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self) -> None:
        try:
            from backend.api.merge import MergeAPI
            title, dur = MergeAPI().fetch_splitter_info(self._url)
            self.resolved.emit(title, dur)
        except Exception as exc:
            self.errored.emit(str(exc))
