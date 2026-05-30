import uuid
from datetime import datetime as _dt


def _fmt_now() -> str:
    n = _dt.now()
    return f"{n.strftime('%b')} {n.day}, {n.hour}:{n.strftime('%M')}"


from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, ON_PRIMARY, PRIMARY_HOVER,
    FG, FG_MUTED, BG, BG_MUTED, BG_SUBTLE, BORDER,
)
from ui.widgets import StyledInput, icon_pixmap, field
from ui.state import AppState
from backend.models import Playlist


class AddPlaylistDialog(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setWindowTitle("Add Playlist")
        self.setFixedWidth(480)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("addPlaylistDialog")
        self.setStyleSheet(
            f"#addPlaylistDialog {{ background:{BG}; border-radius:10px; border:1px solid {BORDER}; }}"
        )

        next_prefix = str(len(state.playlists)).zfill(2)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── header ──
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(f"border-bottom:1px solid {BORDER};")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(18, 0, 18, 0)
        t = QLabel("Add Playlist")
        t.setStyleSheet(f"font-size:14px; font-weight:600; color:{FG};")
        h_lay.addWidget(t)
        h_lay.addStretch()
        x_btn = QPushButton()
        x_btn.setIcon(QIcon(icon_pixmap("x", 14, FG_MUTED)))
        x_btn.setFixedSize(28, 28)
        x_btn.setCursor(Qt.PointingHandCursor)
        x_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; border-radius:5px; }}"
            f"QPushButton:hover {{ background:{BG_SUBTLE}; }}"
        )
        x_btn.clicked.connect(self.reject)
        h_lay.addWidget(x_btn)
        root.addWidget(header)

        # ── body ──
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(18, 16, 18, 16)
        body_lay.setSpacing(14)

        self._url_input = StyledInput("https://youtube.com/playlist?list=…", mono=True)
        body_lay.addWidget(field("Playlist URL", self._url_input))

        self._prefix_input = StyledInput(next_prefix, mono=True)
        self._prefix_input.setText(next_prefix)
        self._prefix_input.setAlignment(Qt.AlignCenter)
        pfx_w = field("Prefix", self._prefix_input)
        pfx_w.setFixedWidth(80)
        body_lay.addWidget(pfx_w)
        root.addWidget(body)

        # ── footer ──
        footer = QWidget()
        footer.setFixedHeight(52)
        footer.setStyleSheet(f"background:{BG_MUTED}; border-top:1px solid {BORDER};")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(18, 0, 18, 0)
        f_lay.setSpacing(8)
        f_lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG}; border:1px solid {BORDER};
                border-radius:6px; padding:0 16px; font-size:13px;
            }}
            QPushButton:hover {{ background:{BG_SUBTLE}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        f_lay.addWidget(cancel_btn)

        add_btn = QPushButton("  Add to Queue")
        add_btn.setIcon(QIcon(icon_pixmap("plus", 13, ON_PRIMARY)))
        add_btn.setFixedHeight(32)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:{ON_PRIMARY}; border:none;
                border-radius:6px; padding:0 16px; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
        """)
        add_btn.clicked.connect(self._on_add)
        f_lay.addWidget(add_btn)
        root.addWidget(footer)

    def _on_add(self) -> None:
        url = self._url_input.text().strip()
        if not url:
            return
        prefix = self._prefix_input.text().strip() or str(len(self._state.playlists)).zfill(2)

        pl = Playlist(
            id           = str(uuid.uuid4()),
            prefix       = prefix,
            title        = url,
            url          = url,
            video_count  = 0,
            completed    = 0,
            status       = "queued",
            active_stage = "download",
            speed        = 1.0,
            split_enabled= False,
            split_min    = 30,
            size_mb      = None,
            added_at     = _fmt_now(),
        )
        from ui.api import QueueAPI
        QueueAPI(self._state).add(pl)
        self.accept()
