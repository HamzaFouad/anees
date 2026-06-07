import re
import uuid
from datetime import datetime as _dt

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QLineEdit, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QDoubleValidator, QIntValidator

from ui.theme import (
    PRIMARY, ON_PRIMARY, PRIMARY_HOVER,
    FG, FG_MUTED, BG, BG_SUBTLE, BORDER,
    ERROR, ERROR_DARK,
)
from ui.widgets import Toggle, StyledInput, icon_pixmap
from ui.state import AppState
from backend.models import Playlist
from backend.types import PlaylistStatus, VideoStage


_PLAYLIST_RE = re.compile(
    r"^https?://"
    r"("
    # YouTube playlist
    r"(www\.)?youtube\.com/playlist\?.*list=[\w-]+"
    r"|youtu\.be/[\w-]+\?.*list=[\w-]+"
    r"|(www\.)?youtube\.com/watch\?.*list=[\w-]+"
    r"|(www\.)?youtube\.com/@[\w.-]+(/[\w-]+)?"
    r"|(www\.)?youtube\.com/channel/[\w-]+"
    r"|(www\.)?youtube\.com/user/[\w-]+"
    # SoundCloud sets
    r"|soundcloud\.com/[\w-]+/sets/[\w-]+"
    r")",
    re.IGNORECASE,
)


def _is_valid_playlist_url(url: str) -> bool:
    return bool(_PLAYLIST_RE.match(url.strip()))


def _fmt_now() -> str:
    n = _dt.now()
    return f"{n.strftime('%b')} {n.day}, {n.hour}:{n.strftime('%M')}"


def _lbl(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        f"font-size:10px; font-weight:600; color:{FG_MUTED}; "
        "letter-spacing:0.05em; background:transparent; border:none;"
    )
    return l


class AddPlaylistDialog(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setWindowTitle("Add Playlist")
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
        t = QLabel("Add Playlist")
        t.setStyleSheet(f"font-size:15px; font-weight:700; color:{FG};")
        h_lay.addWidget(t)
        h_lay.addStretch()
        x_btn = QPushButton()
        x_btn.setIcon(QIcon(icon_pixmap("x", 14, FG_MUTED)))
        x_btn.setFixedSize(30, 30)
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
        b_lay.setSpacing(18)

        # PLAYLIST URL
        url_w = _section()
        url_w.layout().addWidget(_lbl("Playlist URL"))
        self._url_input = StyledInput("https://youtube.com/playlist?list=…", mono=True)
        self._url_input.textChanged.connect(self._clear_url_error)
        url_w.layout().addWidget(self._url_input)
        self._url_error = QLabel("")
        self._url_error.setStyleSheet(
            f"font-size:11px; color:{ERROR_DARK}; background:transparent; border:none;"
        )
        self._url_error.setVisible(False)
        url_w.layout().addWidget(self._url_error)
        b_lay.addWidget(url_w)

        # PREFIX | SPEED | SPLIT row
        from backend.api.config import get_prefix_start
        next_prefix = str(get_prefix_start() + len(state.playlists)).zfill(2)
        row = QWidget(); row.setStyleSheet("background:transparent;")
        r_lay = QHBoxLayout(row)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(12)

        # PREFIX
        pfx_w = _section()
        pfx_w.setFixedWidth(80)
        pfx_w.layout().addWidget(_lbl("Prefix"))
        self._prefix_input = StyledInput(next_prefix, mono=True)
        self._prefix_input.setText(next_prefix)
        self._prefix_input.setAlignment(Qt.AlignCenter)
        self._prefix_input.setReadOnly(True)
        self._prefix_input.setCursor(Qt.ArrowCursor)
        self._prefix_input.setStyleSheet(
            self._prefix_input.styleSheet() +
            f"QLineEdit {{ background:{BG_SUBTLE}; color:{FG_MUTED}; }}"
        )
        pfx_w.layout().addWidget(self._prefix_input)
        r_lay.addWidget(pfx_w)

        # SPLIT (MIN) — before speed, enabled by default
        spl_w = _section()
        spl_w.layout().addWidget(_lbl("Split (min)"))
        self._split_toggle = Toggle(True)
        self._split_toggle.toggled.connect(self._on_split_toggle)
        self._split_input = _value_input("30", QIntValidator(1, 999), enabled=True)
        spl_ctrl = _toggle_row(self._split_toggle, self._split_input)
        spl_w.layout().addWidget(spl_ctrl)
        r_lay.addWidget(spl_w, 1)

        # SPEED
        spd_w = _section()
        spd_w.layout().addWidget(_lbl("Speed (×)"))
        self._speed_toggle = Toggle(False)
        self._speed_toggle.toggled.connect(self._on_speed_toggle)
        self._speed_input = _value_input("1.5", QDoubleValidator(1.0, 3.0, 2), enabled=False)
        spd_ctrl = _toggle_row(self._speed_toggle, self._speed_input)
        spd_w.layout().addWidget(spd_ctrl)
        r_lay.addWidget(spd_w, 1)

        b_lay.addWidget(row)

        # destination hint
        from backend.api.config import get_output_root
        self._dest_hint = QLabel()
        self._dest_hint.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; background:transparent; border:none;"
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
        f_lay.addWidget(cancel_btn)

        add_btn = QPushButton("  + Add to Queue")
        add_btn.setFixedHeight(36)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:{ON_PRIMARY}; border:none;
                border-radius:8px; padding:0 20px; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
        """)
        add_btn.clicked.connect(self._on_add)
        f_lay.addWidget(add_btn)
        root.addWidget(footer)

    # ── toggle handlers ──────────────────────────────────────────────────────
    def _update_dest_hint(self) -> None:
        from backend.api.config import get_output_root
        prefix = self._prefix_input.text().strip() or "??"
        root = get_output_root().rstrip("/\\")
        self._dest_hint.setText(f"→  {root}/{prefix}_…/")

    def _clear_url_error(self) -> None:
        self._url_error.setVisible(False)
        self._url_input.setStyleSheet(self._url_input.styleSheet().replace(
            f"border-color:{ERROR};", ""
        ))

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
    def _on_add(self) -> None:
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

        from backend.api.config import get_prefix_start
        prefix   = self._prefix_input.text().strip() or str(get_prefix_start() + len(self._state.playlists)).zfill(2)
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
        )
        from ui.api import QueueAPI
        QueueAPI(self._state).add(pl)
        self.accept()


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
    bg    = BG       if enabled else BG_SUBTLE
    color = FG       if enabled else FG_MUTED
    return (
        f"QLineEdit {{ background:{bg}; color:{color}; border:1px solid {BORDER}; "
        f"border-radius:8px; padding:0 10px; "
        f"font-family:'JetBrains Mono',monospace; font-size:13px; }}"
    )


def _value_input(default: str, validator, enabled: bool = True) -> QLineEdit:
    e = QLineEdit(default)
    e.setFixedHeight(32)
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
