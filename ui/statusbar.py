from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from ui.theme import FG_MUTED, BG_MUTED, BORDER, SUCCESS
from backend.mock_data import MOCK_HISTORY


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setStyleSheet(f"background:{BG_MUTED}; border-top:1px solid {BORDER};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(0)

        def item(text: str, mono: bool = True) -> QLabel:
            lbl = QLabel(text)
            ff = "'JetBrains Mono', monospace" if mono else "inherit"
            lbl.setStyleSheet(f"font-size:11px; color:{FG_MUTED}; font-family:{ff};")
            return lbl

        dot = QLabel()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background:{SUCCESS}; border-radius:3px; margin-right:4px;")
        lay.addWidget(dot)
        lay.addSpacing(4)

        for text in ["yt-dlp 2025.04.30", " · ", "ffmpeg 7.1", " · ", "2 parallel"]:
            lay.addWidget(item(text))

        lay.addStretch()

        for text in [f"history: {len(MOCK_HISTORY)} runs", " · ", "D:\\ 18.4 GB free"]:
            lay.addWidget(item(text))
