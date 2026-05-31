import os
import sys
import shutil
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from ui.theme import FG_MUTED, BG_MUTED, SUCCESS, FONT_MONO, TEXT_SM
from ui.widgets import status_dot


def _yt_dlp_version() -> str:
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except Exception:
        return "?"


def _ffmpeg_version() -> str:
    exe = _ffmpeg_exe()
    try:
        r = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=3)
        line = r.stdout.split("\n")[0]
        return line.split("version ")[1].split(" ")[0] if "version" in line else "?"
    except Exception:
        return "?"


def _ffmpeg_exe() -> str:
    if getattr(sys, "frozen", False):
        name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        path = os.path.join(sys._MEIPASS, name)  # type: ignore[attr-defined]
        if os.path.exists(path):
            return path
    # macOS .app launches with a minimal PATH — check Homebrew locations explicitly
    if sys.platform == "darwin":
        for candidate in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
            if os.path.exists(candidate):
                return candidate
    return "ffmpeg"


def _disk_free() -> str:
    try:
        usage = shutil.disk_usage(str(Path.home() / "Downloads"))
        gb = usage.free / 1024 ** 3
        return f"{gb:.1f} GB free"
    except Exception:
        return ""


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
