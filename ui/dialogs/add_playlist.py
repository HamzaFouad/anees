from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from datetime import datetime as _dt

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QLineEdit, QFrame, QFileDialog, QListWidget, QListWidgetItem,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QDoubleValidator, QIntValidator

from ui.theme import (
    PRIMARY, ON_PRIMARY, PRIMARY_HOVER, PRIMARY_TINT_8, PRIMARY_TINT_EEF, PRIMARY_TINT_BANNER,
    FG, FG_SUBTLE, FG_MUTED, FG_FAINT, FG_DIMMED,
    BG, BG_MUTED, BG_SUBTLE, BORDER, BORDER_DASHED_BLUE,
    ERROR, ERROR_DARK,
    SURFACE_ALT, SURFACE_ALT_HOVER,
)
from ui.widgets import Toggle, StyledInput, icon_pixmap
from ui.state import AppState
from backend.models import Playlist, Video
from backend.types import PlaylistStatus, VideoStage


_PLAYLIST_RE = re.compile(
    r"^https?://"
    r"("
    r"(www\.|m\.)?youtube\.com/playlist\?.*list=[\w-]+"
    r"|youtu\.be/[\w-]+\?.*list=[\w-]+"
    r"|(www\.|m\.)?youtube\.com/watch\?.*list=[\w-]+"
    r"|(www\.|m\.)?youtube\.com/@[\w.-]+(/[\w-]+)?"
    r"|(www\.|m\.)?youtube\.com/channel/[\w-]+"
    r"|(www\.|m\.)?youtube\.com/user/[\w-]+"
    r"|soundcloud\.com/[\w-]+/sets/[\w-]+"
    r")",
    re.IGNORECASE,
)


def _is_valid_playlist_url(url: str) -> bool:
    return bool(_PLAYLIST_RE.match(url.strip()))


def _normalize_url(url: str) -> str:
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower()
    if netloc == "m.youtube.com":
        url = url.replace("m.youtube.com", "www.youtube.com", 1)
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
    yt = netloc in ("www.youtube.com", "youtube.com")
    if yt and parsed.path == "/watch":
        params = parse_qs(parsed.query)
        if "list" in params:
            return f"https://www.youtube.com/playlist?list={params['list'][0]}"
    if netloc == "youtu.be":
        params = parse_qs(parsed.query)
        if "list" in params:
            return f"https://www.youtube.com/playlist?list={params['list'][0]}"
    return url.strip()


def _fmt_now() -> str:
    n = _dt.now()
    return f"{n.strftime('%b')} {n.day}, {n.hour}:{n.strftime('%M')}"


def _fmt_duration(secs: int) -> str:
    if secs <= 0:
        return "?"
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02}:{s:02}"
    return f"{m}:{s:02}"


def _lbl(text: str) -> QLabel:
    l = QLabel(text.upper())
    l.setStyleSheet(
        f"font-size:11px; font-weight:600; color:{FG_MUTED}; "
        "letter-spacing:0.06em; background:transparent; border:none;"
    )
    return l


class AddPlaylistDialog(QDialog):
    def __init__(self, state: AppState, playlist: Playlist | None = None, parent=None):
        super().__init__(parent)
        self._state = state
        self._edit_pl = playlist
        self._source = playlist.source if playlist else "youtube"
        self._local_files: list[Path] = []

        edit_mode = playlist is not None
        title = "Edit Source" if edit_mode else "Add Source"

        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("addCard")
        card.setStyleSheet(
            f"#addCard {{ background:{BG}; border-radius:12px; border:none; }}"
        )
        outer.addWidget(card)

        root = QVBoxLayout(card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── header ──────────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet("background:transparent;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 16, 0)
        t = QLabel(title)
        t.setStyleSheet(f"font-size:14px; font-weight:700; color:{FG};")
        h_lay.addWidget(t)
        h_lay.addStretch()
        x_btn = QPushButton()
        x_btn.setIcon(QIcon(icon_pixmap("x", 15, FG_MUTED)))
        x_btn.setFixedSize(28, 28)
        x_btn.setCursor(Qt.PointingHandCursor)
        x_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; border-radius:6px; }}"
            f"QPushButton:hover {{ background:{BG_SUBTLE}; }}"
        )
        x_btn.clicked.connect(self.reject)
        h_lay.addWidget(x_btn)
        root.addWidget(header)

        _sep(root)

        # ── body ────────────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background:transparent;")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(20, 20, 20, 20)
        b_lay.setSpacing(14)

        # SOURCE TOGGLE (hidden in edit mode)
        self._source_toggle_w = _SourceToggle(self._source)
        self._source_toggle_w.setVisible(not edit_mode)
        self._source_toggle_w.source_changed.connect(self._on_source_changed)
        b_lay.addWidget(self._source_toggle_w)

        # Source pages — shown/hidden directly; avoids QStackedWidget height reservation
        self._yt_page = self._build_youtube_page()
        self._local_page = self._build_local_page()
        self._yt_page.setVisible(self._source == "youtube")
        self._local_page.setVisible(self._source == "local")
        b_lay.addWidget(self._yt_page)
        b_lay.addWidget(self._local_page)

        # RANGE
        b_lay.addWidget(self._build_range_section())

        # SETTINGS ROW: PREFIX | SPLIT | SPEED
        from backend.api.config import get_prefix_start
        next_prefix = str(get_prefix_start() + len(state.playlists)).zfill(2)
        row = QWidget(); row.setStyleSheet("background:transparent;")
        r_lay = QHBoxLayout(row)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(12)

        pfx_w = _section()
        pfx_w.setFixedWidth(80)
        pfx_w.layout().addWidget(_lbl("Prefix"))
        self._prefix_input = StyledInput(next_prefix, mono=True)
        self._prefix_input.setText(playlist.prefix if edit_mode else next_prefix)
        self._prefix_input.setAlignment(Qt.AlignCenter)
        self._prefix_input.setReadOnly(True)
        self._prefix_input.setFocusPolicy(Qt.NoFocus)
        self._prefix_input.setCursor(Qt.ArrowCursor)
        self._prefix_input.setStyleSheet(
            self._prefix_input.styleSheet() +
            f"QLineEdit {{ height:34px; background:{BG_MUTED}; color:{FG_FAINT}; }}"
        )
        pfx_w.layout().addWidget(self._prefix_input)
        r_lay.addWidget(pfx_w)

        split_on = playlist.split_enabled if edit_mode else True
        split_val = str(playlist.split_min) if edit_mode else "30"
        spl_w = _section()
        spl_w.layout().addWidget(_lbl("Split (min)"))
        self._split_toggle = Toggle(split_on)
        self._split_toggle.toggled.connect(self._on_split_toggle)
        self._split_toggle.toggled.connect(lambda _: self._update_pipeline_text())
        self._split_input = _value_input(split_val, QIntValidator(1, 999), enabled=split_on)
        spl_ctrl = _toggle_row(self._split_toggle, self._split_input)
        spl_w.layout().addWidget(spl_ctrl)
        r_lay.addWidget(spl_w, 1)

        speed_on = playlist.speed != 1.0 if edit_mode else False
        speed_val = str(playlist.speed) if edit_mode and speed_on else "1.5"
        spd_w = _section()
        spd_w.layout().addWidget(_lbl("Speed (×)"))
        self._speed_toggle = Toggle(speed_on)
        self._speed_toggle.toggled.connect(self._on_speed_toggle)
        self._speed_toggle.toggled.connect(lambda _: self._update_pipeline_text())
        self._speed_input = _value_input(speed_val, QDoubleValidator(1.0, 3.0, 2), enabled=speed_on)
        spd_ctrl = _toggle_row(self._speed_toggle, self._speed_input)
        spd_w.layout().addWidget(spd_ctrl)
        r_lay.addWidget(spd_w, 1)

        b_lay.addWidget(row)

        # DEST HINT
        self._dest_hint = QLabel()
        self._dest_hint.setStyleSheet(
            f"font-family:'JetBrains Mono','Consolas','Courier New',monospace; "
            f"font-size:12px; color:{FG_MUTED}; background:transparent; border:none;"
        )
        self._update_dest_hint()
        self._prefix_input.textChanged.connect(lambda _: self._update_dest_hint())
        b_lay.addWidget(self._dest_hint)

        root.addWidget(body)

        _sep(root)

        # ── footer ──────────────────────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(60)
        footer.setStyleSheet("background:transparent;")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(20, 0, 20, 0)
        f_lay.setSpacing(10)
        f_lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE_ALT}; color:{FG_SUBTLE}; border:none;
                border-radius:6px; padding:0 14px; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{SURFACE_ALT_HOVER}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        f_lay.addWidget(cancel_btn)

        confirm_label = "Save changes" if edit_mode else (
            "+ Add folder" if self._source == "local" else "+ Add to Queue"
        )
        self._confirm_btn = QPushButton(f"  {confirm_label}")
        self._confirm_btn.setFixedHeight(32)
        self._confirm_btn.setCursor(Qt.PointingHandCursor)
        self._confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:{ON_PRIMARY}; border:none;
                border-radius:6px; padding:0 16px; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
        """)
        self._confirm_btn.clicked.connect(self._on_confirm)
        f_lay.addWidget(self._confirm_btn)
        root.addWidget(footer)

        # Pre-fill edit mode
        if edit_mode and playlist.source == "local":
            self._folder_input.setText(playlist.url)
        if edit_mode:
            rs = playlist.range_start   # 1-based, None = no start
            re_ = playlist.range_end    # 1-based, None = no end
            from_val = max(0, (rs or 1) - 1)
            if from_val > 0:
                self._range_from_input.setText(str(from_val))
            if re_ is not None:
                self._range_to_input.setText(str(max(0, re_ - 1)))

        # Toggles now exist — refresh pipeline text with correct initial state
        self._update_pipeline_text()

    # ── page builders ────────────────────────────────────────────────────────

    def _build_youtube_page(self) -> QWidget:
        page = QWidget(); page.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lay.addWidget(_lbl("Playlist URL"))
        locked = self._edit_pl is not None and self._edit_pl.source == "youtube"
        self._url_input = StyledInput("https://youtube.com/playlist?list=…", mono=True)
        self._url_input.setStyleSheet(
            self._url_input.styleSheet() + "QLineEdit { height:36px; font-size:12px; }"
        )
        if locked:
            self._url_input.setText(self._edit_pl.url)
            self._url_input.setReadOnly(True)
            self._url_input.setStyleSheet(
                self._url_input.styleSheet() +
                f"QLineEdit {{ background:{BG_MUTED}; color:{FG_FAINT}; }}"
            )
        self._url_input.textChanged.connect(self._clear_url_error)
        lay.addWidget(self._url_input)

        self._url_error = QLabel("")
        self._url_error.setStyleSheet(
            f"font-size:11px; color:{ERROR_DARK}; background:transparent; border:none;"
        )
        self._url_error.setVisible(False)
        lay.addWidget(self._url_error)
        return page

    def _build_local_page(self) -> QWidget:
        page = QWidget(); page.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        lay.addWidget(_lbl("Folder path"))

        folder_row = QWidget(); folder_row.setStyleSheet("background:transparent;")
        fr_lay = QHBoxLayout(folder_row)
        fr_lay.setContentsMargins(0, 0, 0, 0)
        fr_lay.setSpacing(8)

        self._folder_input = StyledInput("", mono=True)
        self._folder_input.setReadOnly(True)
        self._folder_input.setPlaceholderText("No folder selected…")
        self._folder_input.setStyleSheet(
            self._folder_input.styleSheet() + "QLineEdit { height:36px; font-size:12px; }"
        )
        fr_lay.addWidget(self._folder_input, 1)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedHeight(36)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG_SUBTLE}; border:1px solid {BORDER};
                border-radius:6px; padding:0 14px; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{BG_SUBTLE}; }}
        """)
        browse_btn.clicked.connect(self._on_browse)
        fr_lay.addWidget(browse_btn)
        lay.addWidget(folder_row)

        self._local_error = QLabel("")
        self._local_error.setStyleSheet(
            f"font-size:11px; color:{ERROR_DARK}; background:transparent; border:none;"
        )
        self._local_error.setVisible(False)
        lay.addWidget(self._local_error)

        self._file_list = QListWidget()
        self._file_list.setFixedHeight(120)
        self._file_list.setStyleSheet(f"""
            QListWidget {{
                background:{BG_MUTED}; border:1px solid {BORDER};
                border-radius:8px; padding:4px;
                font-size:12px; color:{FG};
            }}
            QListWidget::item {{ padding:5px 12px; border:none; }}
            QListWidget::item:selected {{ background:{PRIMARY}20; color:{FG}; }}
        """)
        self._file_list.setVisible(False)
        lay.addWidget(self._file_list)

        self._file_footer = QLabel("")
        self._file_footer.setTextFormat(Qt.RichText)
        self._file_footer.setStyleSheet("background:transparent; border:none;")
        self._file_footer.setVisible(False)
        lay.addWidget(self._file_footer)

        self._pipeline_banner = self._build_pipeline_banner()
        lay.addWidget(self._pipeline_banner)

        return page

    def _build_pipeline_banner(self) -> QWidget:
        from ui.components.utils import icon_pixmap

        banner = QWidget()
        banner.setObjectName("pipelineBanner")
        # rgba alpha is 0-255 in Qt QSS — 0.08×255 ≈ 20
        banner.setStyleSheet(
            f"#pipelineBanner {{ background:{PRIMARY_TINT_BANNER}; border-radius:7px; border:none; }}"
        )

        lay = QHBoxLayout(banner)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(8)

        icon_lbl = QLabel()
        px = icon_pixmap("info", 28, PRIMARY)
        px.setDevicePixelRatio(2.0)
        icon_lbl.setPixmap(px)
        icon_lbl.setFixedSize(14, 14)
        icon_lbl.setStyleSheet("background:transparent; border:none;")
        lay.addWidget(icon_lbl)

        self._pipeline_lbl = QLabel()
        self._pipeline_lbl.setTextFormat(Qt.RichText)
        self._pipeline_lbl.setStyleSheet(
            f"font-size:12px; color:{FG_SUBTLE}; background:transparent; border:none;"
        )
        lay.addWidget(self._pipeline_lbl)
        lay.addStretch()

        self._update_pipeline_text()
        return banner

    def _update_pipeline_text(self) -> None:
        if not hasattr(self, "_pipeline_lbl"):
            return
        steps = []
        if hasattr(self, "_speed_toggle") and self._speed_toggle._checked:
            steps.append("Speed")
        if hasattr(self, "_split_toggle") and self._split_toggle._checked:
            steps.append("Split")
        active = ("  →  " + "  →  ".join(steps)) if steps else ""
        self._pipeline_lbl.setText(
            f'Pipeline:  '
            f'<span style="color:{FG_DIMMED}; text-decoration:line-through;">'
            f'Download  Convert</span>'
            f'{active}'
        )

    # ── range section ────────────────────────────────────────────────────────

    def _build_range_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lay.addWidget(_lbl("Range"))

        row = QWidget()
        row.setStyleSheet("background:transparent;")
        r_lay = QHBoxLayout(row)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(8)

        self._range_from_input, from_box = self._make_range_box(
            "From", "rangeBoxFrom", "rangeLblFrom", "0", FG
        )
        r_lay.addWidget(from_box, 1)

        arrow = QLabel("→")
        arrow.setAlignment(Qt.AlignCenter)
        arrow.setFixedWidth(20)
        arrow.setStyleSheet("font-size:13px; color:#CBD5E1; background:transparent; border:none;")
        r_lay.addWidget(arrow)

        self._range_to_input, to_box = self._make_range_box(
            "To", "rangeBoxTo", "rangeLblTo", "end", FG_FAINT
        )
        r_lay.addWidget(to_box, 1)

        lay.addWidget(row)

        self._range_helper = QLabel(
            "Default processes all videos. Use numbers to select a slice (e.g. 0 → 49)."
        )
        self._range_helper.setWordWrap(True)
        self._range_helper.setStyleSheet(
            f"font-size:11px; color:{FG_FAINT}; background:transparent; border:none;"
        )
        lay.addWidget(self._range_helper)

        self._range_from_input.textChanged.connect(lambda _: self._update_dest_hint())
        self._range_to_input.textChanged.connect(self._on_range_to_changed)

        return w

    def _make_range_box(
        self, label: str, box_name: str, lbl_name: str, default: str, text_color: str
    ) -> tuple[QLineEdit, QWidget]:
        box = QWidget()
        box.setObjectName(box_name)
        box.setFixedHeight(34)
        box.setStyleSheet(
            f"#{box_name} {{ border:1px solid {BORDER}; border-radius:6px; background:{BG}; }}"
        )

        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lbl = QLabel(label)
        lbl.setObjectName(lbl_name)
        lbl.setStyleSheet(
            f"#{lbl_name} {{ font-size:11px; font-weight:600; color:#8B97A9; "
            f"background:#F8FAFC; padding:0 10px; border:none; "
            f"border-right:1px solid {BORDER}; "
            f"border-top-left-radius:5px; border-bottom-left-radius:5px; }}"
        )
        lay.addWidget(lbl)

        inp = QLineEdit(default)
        inp.setFrame(False)
        inp.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; padding:0 10px; "
            f"font-family:'JetBrains Mono','Consolas','Courier New',monospace; "
            f"font-size:13px; color:{text_color}; }}"
        )
        lay.addWidget(inp, 1)

        return inp, box

    def _on_range_to_changed(self, text: str) -> None:
        is_end = not text.strip() or text.strip().lower() == "end"
        color = FG_FAINT if is_end else FG
        self._range_to_input.setStyleSheet(
            f"QLineEdit {{ border:none; background:transparent; padding:0 10px; "
            f"font-family:'JetBrains Mono','Consolas','Courier New',monospace; "
            f"font-size:13px; color:{color}; }}"
        )
        self._update_dest_hint()

    def _read_range(self) -> tuple[int | None, int | None]:
        from_str = self._range_from_input.text().strip()
        to_str = self._range_to_input.text().strip()
        try:
            from_val = max(0, int(from_str))
        except (ValueError, TypeError):
            from_val = 0
        is_end = not to_str or to_str.lower() == "end"
        try:
            to_val: int | None = max(0, int(to_str)) if not is_end else None
        except (ValueError, TypeError):
            to_val = None
        # Convert 0-based UI to 1-based backend; from=0 means "from start" → None
        range_start = from_val + 1 if from_val > 0 else None
        range_end = to_val + 1 if to_val is not None else None
        return range_start, range_end

    # ── source toggle ────────────────────────────────────────────────────────

    def _on_source_changed(self, source: str) -> None:
        self._source = source
        self._yt_page.setVisible(source == "youtube")
        self._local_page.setVisible(source == "local")
        if source == "youtube":
            self._range_helper.setText(
                "Default processes all videos. Use numbers to select a slice (e.g. 0 → 49)."
            )
        else:
            self._range_helper.setText(
                "Default processes all files. Use numbers to select a subset."
            )
        label = "+ Add folder" if source == "local" else "+ Add to Queue"
        self._confirm_btn.setText(f"  {label}")
        self.setFocus()  # prevent focus jumping to a text input on page switch
        QTimer.singleShot(0, self.adjustSize)

    # ── local folder ─────────────────────────────────────────────────────────

    def _on_browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder with MP3 files")
        if not folder:
            return
        self._folder_input.setText(folder)
        self._scan_folder(folder)

    def _scan_folder(self, folder: str) -> None:
        from backend.api.info import probe_file_duration

        files = sorted(Path(folder).glob("*.mp3"))
        self._local_files = list(files)

        self._file_list.clear()
        self._local_error.setVisible(False)

        if not files:
            self._local_error.setText("No MP3 files found in this folder.")
            self._local_error.setVisible(True)
            self._file_list.setVisible(False)
            self._file_footer.setVisible(False)
            return

        total_bytes = 0
        for f in files:
            dur = probe_file_duration(str(f))
            size = f.stat().st_size
            total_bytes += size
            item = QListWidgetItem(f"{f.stem}  ·  {_fmt_duration(dur)}")
            self._file_list.addItem(item)

        total_mb = total_bytes / 1_048_576
        n = len(files)
        self._file_footer.setText(
            f'<span style="font-size:12px;font-weight:600;color:{FG};">{n} files</span>'
            f'<span style="font-size:11px;font-family:monospace;color:{FG_FAINT};">  ·  {total_mb:.1f} MB</span>'
        )
        self._file_list.setVisible(True)
        self._file_footer.setVisible(True)

    # ── toggle handlers ──────────────────────────────────────────────────────

    def _update_dest_hint(self) -> None:
        from backend.api.config import get_output_root
        prefix = self._prefix_input.text().strip() or "??"
        root = get_output_root().rstrip("/\\")
        from_str = self._range_from_input.text().strip() or "0"
        to_str = self._range_to_input.text().strip() or "end"
        self._dest_hint.setText(f"→  {root}/{prefix}_…/  [{from_str} → {to_str}]")

    def _clear_url_error(self) -> None:
        self._url_error.setVisible(False)

    def _show_url_error(self, msg: str) -> None:
        self._url_error.setText(msg)
        self._url_error.setVisible(True)

    def _on_speed_toggle(self, checked: bool) -> None:
        self._speed_input.setEnabled(checked)
        self._speed_input.setStyleSheet(_input_style(checked))

    def _on_split_toggle(self, checked: bool) -> None:
        self._split_input.setEnabled(checked)
        self._split_input.setStyleSheet(_input_style(checked))

    # ── submit ───────────────────────────────────────────────────────────────

    def _on_confirm(self) -> None:
        if self._edit_pl is not None:
            # Edit mode: prototype — just close
            self.accept()
            return

        if self._source == "youtube":
            self._submit_youtube()
        else:
            self._submit_local()

    def _submit_youtube(self) -> None:
        url = self._url_input.text().strip()
        if not url:
            self._show_url_error("Please enter a playlist URL.")
            return
        if not _is_valid_playlist_url(url):
            self._show_url_error(
                "Must be a YouTube playlist or SoundCloud set URL.\n"
                "e.g. youtube.com/playlist?list=… or soundcloud.com/user/sets/…"
            )
            return
        url = _normalize_url(url)

        if any(p.url == url for p in self._state.playlists):
            self._show_url_error("This playlist is already in the queue.")
            return

        from backend.api.config import get_prefix_start
        prefix = self._prefix_input.text().strip() or str(get_prefix_start() + len(self._state.playlists)).zfill(2)
        speed_on = self._speed_toggle._checked
        split_on = self._split_toggle._checked

        try:
            speed = max(1.0, min(3.0, float(self._speed_input.text()))) if speed_on else 1.0
        except ValueError:
            speed = 1.5

        try:
            split_min = max(1, int(self._split_input.text())) if split_on else 30
        except ValueError:
            split_min = 30

        range_start, range_end = self._read_range()

        pl = Playlist(
            id           = str(uuid.uuid4()),
            prefix       = prefix,
            title        = url,
            url          = url,
            video_count  = 0,
            completed    = 0,
            status       = PlaylistStatus.QUEUED,
            active_stage = VideoStage.DOWNLOAD,
            speed        = speed,
            split_enabled= split_on,
            split_min    = split_min,
            size_mb      = None,
            added_at     = _fmt_now(),
            range_start  = range_start,
            range_end    = range_end,
            source       = "youtube",
        )
        from ui.api import QueueAPI
        QueueAPI(self._state).add(pl)
        self.accept()

    def _submit_local(self) -> None:
        folder = self._folder_input.text().strip()
        if not folder:
            self._local_error.setText("Please select a folder.")
            self._local_error.setVisible(True)
            return
        if not self._local_files:
            self._local_error.setText("No MP3 files found in this folder.")
            self._local_error.setVisible(True)
            return

        from backend.api.config import get_prefix_start
        from backend.api.info import probe_file_duration

        prefix = self._prefix_input.text().strip() or str(get_prefix_start() + len(self._state.playlists)).zfill(2)
        speed_on = self._speed_toggle._checked
        split_on = self._split_toggle._checked

        try:
            speed = max(1.0, min(3.0, float(self._speed_input.text()))) if speed_on else 1.0
        except ValueError:
            speed = 1.5

        try:
            split_min = max(1, int(self._split_input.text())) if split_on else 30
        except ValueError:
            split_min = 30

        range_start, range_end = self._read_range()

        videos = [
            Video(
                title=f.stem,
                duration_sec=probe_file_duration(str(f)),
                stage=VideoStage.QUEUED,
            )
            for f in self._local_files
        ]

        total_bytes = sum(f.stat().st_size for f in self._local_files)

        pl = Playlist(
            id           = str(uuid.uuid4()),
            prefix       = prefix,
            title        = Path(folder).name,
            url          = folder,
            video_count  = len(videos),
            completed    = 0,
            status       = PlaylistStatus.QUEUED,
            active_stage = VideoStage.DOWNLOAD,
            speed        = speed,
            split_enabled= split_on,
            split_min    = split_min,
            size_mb      = round(total_bytes / 1_048_576, 1),
            added_at     = _fmt_now(),
            videos       = videos,
            range_start  = range_start,
            range_end    = range_end,
            source       = "local",
        )
        from ui.api import QueueAPI
        QueueAPI(self._state).add(pl)
        self.accept()


# ── source toggle widget ──────────────────────────────────────────────────────

from PySide6.QtCore import Signal


class _SourceToggle(QWidget):
    source_changed = Signal(str)

    def __init__(self, initial: str = "youtube", parent=None):
        super().__init__(parent)
        self._source = initial
        self.setStyleSheet("background:transparent;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(7)

        lay.addWidget(_lbl("Source"))

        container = QWidget()
        container.setObjectName("segContainer")
        container.setFixedHeight(40)
        container.setStyleSheet(
            f"#segContainer {{ background:{BG}; border:1px solid {BORDER}; border-radius:7px; }}"
        )
        c_lay = QHBoxLayout(container)
        c_lay.setContentsMargins(3, 3, 3, 3)
        c_lay.setSpacing(0)

        self._yt_btn = self._make_seg("YouTube", "youtube", "play")
        self._local_btn = self._make_seg("Local folder", "local", "folder")
        c_lay.addWidget(self._yt_btn, 1)
        c_lay.addWidget(self._local_btn, 1)
        lay.addWidget(container)

        self._refresh_styles()

    def _make_seg(self, label: str, key: str, icon_key: str) -> QPushButton:
        btn = QPushButton(f"  {label}")
        btn.setFixedHeight(34)
        btn.setIconSize(QSize(14, 14))
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self._select(key))
        btn._icon_key = icon_key
        return btn

    def _select(self, key: str) -> None:
        if key == self._source:
            return
        self._source = key
        self._refresh_styles()
        self.source_changed.emit(key)

    def _refresh_styles(self) -> None:
        from ui.components.utils import icon_pixmap
        ICON_PX = 16   # logical size shown in button
        RENDER  = 32   # render at 2× for crisp Retina output
        pairs = [
            (self._yt_btn,    "youtube", "play"),
            (self._local_btn, "local",   "folder"),
        ]
        for btn, key, icon_key in pairs:
            active = self._source == key
            color = PRIMARY if active else FG_MUTED
            px = icon_pixmap(icon_key, RENDER, color)
            px.setDevicePixelRatio(2.0)
            btn.setIcon(QIcon(px))
            btn.setIconSize(QSize(ICON_PX, ICON_PX))
            if active:
                btn.setStyleSheet(
                    f"QPushButton {{ background:{PRIMARY_TINT_EEF}; color:{PRIMARY}; border:none; "
                    f"border-radius:6px; font-size:13px; font-weight:600; text-align:center; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background:transparent; color:{FG_MUTED}; border:none; "
                    f"border-radius:6px; font-size:13px; font-weight:600; text-align:center; }}"
                    f"QPushButton:hover {{ color:{FG}; }}"
                )


# ── helpers ───────────────────────────────────────────────────────────────────

def _sep(layout) -> None:
    f = QFrame(); f.setFixedHeight(1)
    f.setStyleSheet(f"background:{BORDER}; border:none;")
    layout.addWidget(f)


def _section() -> QWidget:
    w = QWidget(); w.setStyleSheet("background:transparent;")
    lay = QVBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
    return w


def _input_style(enabled: bool) -> str:
    bg    = BG       if enabled else BG_MUTED
    color = FG       if enabled else FG_DIMMED
    return (
        f"QLineEdit {{ background:{bg}; color:{color}; border:1px solid {BORDER}; "
        f"border-radius:6px; padding:0 10px; font-size:13px; }}"
    )


def _value_input(default: str, validator, enabled: bool = True) -> QLineEdit:
    e = QLineEdit(default)
    e.setFixedHeight(34)
    e.setEnabled(enabled)
    e.setValidator(validator)
    e.setAlignment(Qt.AlignCenter)
    e.setStyleSheet(_input_style(enabled))
    return e


def _toggle_row(toggle: Toggle, inp: QLineEdit) -> QWidget:
    w = QWidget(); w.setStyleSheet("background:transparent;")
    lay = QHBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(8)
    lay.addWidget(toggle)
    lay.addWidget(inp, 1)
    return w
