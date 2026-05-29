import uuid
import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QSpinBox, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.theme import PRIMARY, ON_PRIMARY, PRIMARY_HOVER, FG, FG_MUTED, BG, BG_MUTED, BG_SUBTLE, BORDER
from ui.widgets import Toggle, StyledInput, icon_pixmap, field
from ui.state import AppState
from backend.models import Playlist


class AddPlaylistDialog(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setWindowTitle("Add Playlist")
        self.setFixedWidth(520)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet(
            f"background:{BG}; border-radius:10px; border:1px solid {BORDER};"
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
        title = QLabel("Add Playlist")
        title.setStyleSheet(f"font-size:14px; font-weight:600; color:{FG};")
        h_lay.addWidget(title)
        h_lay.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(QIcon(icon_pixmap("x", 14, FG_MUTED)))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; border-radius:5px; }}"
            f"QPushButton:hover {{ background:{BG_SUBTLE}; }}"
        )
        close_btn.clicked.connect(self.reject)
        h_lay.addWidget(close_btn)
        root.addWidget(header)

        # ── body ──
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(18, 16, 18, 16)
        body_lay.setSpacing(14)

        self._url_input = StyledInput("https://youtube.com/playlist?list=…", mono=True)
        self._url_input.textChanged.connect(self._update_preview)
        body_lay.addWidget(field("Playlist URL", self._url_input))

        # prefix / speed / split row
        mid_row = QWidget()
        mid_lay = QHBoxLayout(mid_row)
        mid_lay.setContentsMargins(0, 0, 0, 0)
        mid_lay.setSpacing(10)

        self._prefix_input = StyledInput(next_prefix, mono=True)
        self._prefix_input.setText(next_prefix)
        self._prefix_input.setAlignment(Qt.AlignCenter)
        self._prefix_input.textChanged.connect(self._update_preview)
        pfx_w = field("Prefix", self._prefix_input)
        pfx_w.setFixedWidth(80)
        mid_lay.addWidget(pfx_w)

        # speed
        speed_w = QWidget()
        speed_lay = QHBoxLayout(speed_w)
        speed_lay.setContentsMargins(0, 0, 0, 0)
        speed_lay.setSpacing(8)
        self._speed_toggle = Toggle(False)
        self._speed_toggle.toggled.connect(self._on_speed_toggle)
        self._speed_spin = QDoubleSpinBox()
        self._speed_spin.setRange(1.0, 3.0)
        self._speed_spin.setSingleStep(0.05)
        self._speed_spin.setValue(1.5)
        self._speed_spin.setEnabled(False)
        self._speed_spin.setFixedHeight(32)
        self._speed_spin.setStyleSheet(self._spin_style(False))
        self._speed_spin.valueChanged.connect(self._update_preview)
        speed_lay.addWidget(self._speed_toggle)
        speed_lay.addWidget(self._speed_spin, 1)
        mid_lay.addWidget(field("Speed", speed_w), 1)

        # split
        split_w = QWidget()
        split_lay = QHBoxLayout(split_w)
        split_lay.setContentsMargins(0, 0, 0, 0)
        split_lay.setSpacing(8)
        self._split_toggle = Toggle(False)
        self._split_toggle.toggled.connect(self._on_split_toggle)
        self._split_spin = QSpinBox()
        self._split_spin.setRange(5, 120)
        self._split_spin.setValue(30)
        self._split_spin.setSuffix(" min")
        self._split_spin.setEnabled(False)
        self._split_spin.setFixedHeight(32)
        self._split_spin.setStyleSheet(self._spin_style(False))
        split_lay.addWidget(self._split_toggle)
        split_lay.addWidget(self._split_spin, 1)
        mid_lay.addWidget(field("Split (min)", split_w), 1)
        body_lay.addWidget(mid_row)

        # command preview
        self._preview = QLabel()
        self._preview.setWordWrap(True)
        self._preview.setStyleSheet(
            f"background:{BG_SUBTLE}; border:1px solid {BORDER}; border-radius:6px; "
            f"padding:8px 10px; font-family:'JetBrains Mono',monospace; "
            f"font-size:10.5px; color:{FG_MUTED}; line-height:1.6;"
        )
        self._update_preview()
        body_lay.addWidget(self._preview)
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

    def _spin_style(self, enabled: bool) -> str:
        bg = BG if enabled else BG_SUBTLE
        color = FG if enabled else FG_MUTED
        return (
            f"QDoubleSpinBox, QSpinBox {{ "
            f"background:{bg}; color:{color}; border:1px solid {BORDER}; "
            f"border-radius:6px; padding:0 8px; "
            f"font-family:'JetBrains Mono',monospace; font-size:12px; }}"
        )

    def _on_speed_toggle(self, checked: bool):
        self._speed_spin.setEnabled(checked)
        self._speed_spin.setStyleSheet(self._spin_style(checked))
        self._update_preview()

    def _on_split_toggle(self, checked: bool):
        self._split_spin.setEnabled(checked)
        self._split_spin.setStyleSheet(self._spin_style(checked))

    def _update_preview(self):
        url = self._url_input.text().strip() or "<url>"
        prefix = self._prefix_input.text().strip() or "00"
        speed_on = self._speed_toggle._checked
        speed = self._speed_spin.value() if speed_on else None

        lines = [
            "# preview",
            "yt-dlp -x --audio-format mp3 \\",
            '  --postprocessor-args "-ac 1" \\',
            f'  --output "{prefix}_%(playlist_index)s_%(title)s.%(ext)s" \\',
        ]
        if speed_on and speed and speed != 1.0:
            lines.append(f"  # speed: {speed:.2f}× (atempo) \\")
        lines.append(f"  {url}")
        self._preview.setText("\n".join(lines))

    def _on_add(self):
        url = self._url_input.text().strip()
        if not url:
            return
        prefix = self._prefix_input.text().strip() or str(len(self._state.playlists)).zfill(2)
        speed = self._speed_spin.value() if self._speed_toggle._checked else 1.0
        split_enabled = self._split_toggle._checked
        split_min = self._split_spin.value()

        pl = Playlist(
            id=str(uuid.uuid4()),
            prefix=prefix,
            title=url,
            url=url,
            video_count=0,
            completed=0,
            status="queued",
            active_stage="download",
            speed=speed,
            split_enabled=split_enabled,
            split_min=split_min,
            size_mb=None,
            added_at=datetime.datetime.now().strftime("%b %d, %-H:%M"),
        )
        self._state.add_playlist(pl)
        self.accept()
