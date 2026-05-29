from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from ui.theme import FG_MUTED, BG_MUTED, SUCCESS, FONT_MONO, TEXT_SM
from ui.widgets import status_dot
from backend.mock_data import MOCK_HISTORY


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

        for text in ["yt-dlp 2025.04.30", " · ", "ffmpeg 7.1", " · ", "2 parallel"]:
            lay.addWidget(item(text))

        lay.addStretch()

        for text in [f"history: {len(MOCK_HISTORY)} runs", " · ", "D:\\ 18.4 GB free"]:
            lay.addWidget(item(text))
