from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from ui.theme import FG_MUTED, BG_MUTED, SUCCESS, FONT_MONO, TEXT_SM
from ui.widgets import status_dot
from backend.api.health import (
    get_disk_free_label,
    get_ffmpeg_version,
    get_ytdlp_version,
)


def _yt_dlp_version() -> str:
    return get_ytdlp_version()


def _ffmpeg_version() -> str:
    return get_ffmpeg_version()


def _disk_free() -> str:
    return get_disk_free_label()


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setStyleSheet(f"background:{BG_MUTED};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(0)

        def item(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"font-size:{TEXT_SM}px; color:{FG_MUTED}; font-family:{FONT_MONO};"
            )
            return lbl

        lay.addWidget(status_dot(SUCCESS))
        lay.addSpacing(6)

        yt_ver = _yt_dlp_version()
        ff_ver = _ffmpeg_version()
        for text in [f"yt-dlp {yt_ver}", " · ", f"ffmpeg {ff_ver}"]:
            lay.addWidget(item(text))

        lay.addStretch()

        disk = _disk_free()
        if disk:
            lay.addWidget(item(disk))
