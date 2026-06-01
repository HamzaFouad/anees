from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from ui.statusbar import _ffmpeg_version, _yt_dlp_version
from ui.theme import BG, BG_MUTED, BORDER, FG, FG_MUTED, FG_SUBTLE, PRIMARY
from ui.widgets import RoundedDialog, icon_pixmap

# ── Content ───────────────────────────────────────────────────────────────────
APP_NAME_AR   = "أنيس"
APP_VERSION   = "1.0.0"
APP_DESC      = "تطبيق لتسهيل تحميل وتجهيز السمعيّات من يوتيوب\nعلى بطاقات الذاكرة."
HADITH_TEXT   = "«احرِصْ على ما يَنفَعُكَ واستَعِنْ بالله ولا تَعجِزْ»"
HADITH_SOURCE = "رواه مسلم"
AYAH_TEXT     = "﴿وَاصْبِرْ وَمَا صَبْرُكَ إِلَّا بِاللَّهِ﴾"
AYAH_SOURCE   = "سورة النحل ١٢٧"
DUA_TEXT      = "أسأل اللهَ أن يجعلَه بابَ نفعٍ وسكينةٍ وثبات."

ARABIC_SERIF = "'Amiri','Apple Arabic','Arabic Typesetting','Traditional Arabic',serif"
ARABIC_SANS  = "'IBM Plex Sans Arabic','.AppleSystemUIFont','Segoe UI',sans-serif"


def _app_icon_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "images"  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parent.parent / "images"
    if sys.platform == "darwin":
        icns = base / "anees.icns"
        if icns.exists():
            return icns
    return base / "anees.ico"


def _platform_label() -> str:
    if sys.platform == "win32":   return "Windows"
    if sys.platform == "darwin":  return "macOS"
    return "Linux"


class AboutDialog(RoundedDialog):
    def __init__(self, parent=None):
        # Empty title — about page has no header text, just the close button
        super().__init__(title="", width=480, body_margins=(0, 0, 0, 0),
                         header_separator=False, header_height=36, parent=parent)
        self.setWindowTitle("About أنيس")
        self.setFixedHeight(560)

        # ── content ───────────────────────────────────────────────────────────
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        b = QVBoxLayout(inner)
        b.setContentsMargins(32, 0, 32, 24)
        b.setSpacing(0)
        b.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # logo
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(100, 100)
        px = QIcon(str(_app_icon_path())).pixmap(256, 256)
        if not px.isNull():
            icon_lbl.setPixmap(px.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_lbl.setAlignment(Qt.AlignCenter)
        b.addWidget(icon_lbl, 0, Qt.AlignHCenter)
        b.addSpacing(4)

        # name
        name_lbl = QLabel(APP_NAME_AR)
        name_lbl.setStyleSheet(
            f"font-family:{ARABIC_SANS}; font-size:36px; font-weight:700; color:{FG};"
        )
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setLayoutDirection(Qt.RightToLeft)
        b.addWidget(name_lbl)
        b.addSpacing(6)

        # version
        ver_lbl = QLabel(f"ANEES · VERSION {APP_VERSION}")
        ver_lbl.setStyleSheet(
            f"font-size:11px; font-weight:500; color:{FG_SUBTLE}; letter-spacing:0.08em;"
        )
        ver_lbl.setAlignment(Qt.AlignCenter)
        b.addWidget(ver_lbl)
        b.addSpacing(16)

        # description
        desc_lbl = QLabel(APP_DESC)
        desc_lbl.setStyleSheet(
            f"font-family:{ARABIC_SANS}; font-size:14px; color:{FG_MUTED};"
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setLayoutDirection(Qt.RightToLeft)
        b.addWidget(desc_lbl)
        b.addSpacing(24)

        # hadith box
        hadith_box = QFrame()
        hadith_box.setObjectName("hadithBox")
        hadith_box.setFixedWidth(400)
        hadith_box.setStyleSheet(
            "#hadithBox { background:rgba(0,68,255,0.04); "
            "border:1px solid rgba(0,68,255,0.12); border-radius:10px; }"
        )
        hb = QVBoxLayout(hadith_box)
        hb.setContentsMargins(22, 20, 22, 18)
        hb.setSpacing(10)

        h_text = QLabel(HADITH_TEXT)
        h_text.setStyleSheet(
            f"font-family:{ARABIC_SERIF}; font-size:20px; font-weight:700; "
            f"color:{FG}; background:transparent; border:none;"
        )
        h_text.setWordWrap(True)
        h_text.setAlignment(Qt.AlignCenter)
        h_text.setLayoutDirection(Qt.RightToLeft)
        h_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        hb.addWidget(h_text)

        h_src = QLabel(HADITH_SOURCE)
        h_src.setStyleSheet(
            f"font-family:{ARABIC_SANS}; font-size:11.5px; color:{FG_SUBTLE}; "
            "background:transparent; border:none; letter-spacing:0.02em;"
        )
        h_src.setAlignment(Qt.AlignCenter)
        h_src.setLayoutDirection(Qt.RightToLeft)
        hb.addWidget(h_src)
        b.addWidget(hadith_box)
        b.addSpacing(20)

        # ayah
        ayah_lbl = QLabel(AYAH_TEXT)
        ayah_lbl.setStyleSheet(
            f"font-family:{ARABIC_SERIF}; font-size:24px; font-weight:400; color:{PRIMARY};"
        )
        ayah_lbl.setWordWrap(True)
        ayah_lbl.setAlignment(Qt.AlignCenter)
        ayah_lbl.setLayoutDirection(Qt.RightToLeft)
        b.addWidget(ayah_lbl)
        b.addSpacing(8)

        ayah_src = QLabel(AYAH_SOURCE)
        ayah_src.setStyleSheet(
            f"font-family:{ARABIC_SANS}; font-size:11.5px; color:{FG_SUBTLE}; "
            "letter-spacing:0.02em;"
        )
        ayah_src.setAlignment(Qt.AlignCenter)
        ayah_src.setLayoutDirection(Qt.RightToLeft)
        b.addWidget(ayah_src)
        b.addSpacing(22)

        # dua
        dua_lbl = QLabel(DUA_TEXT)
        dua_lbl.setStyleSheet(
            f"font-family:{ARABIC_SERIF}; font-size:15px; font-style:italic; color:{FG_MUTED};"
        )
        dua_lbl.setWordWrap(True)
        dua_lbl.setAlignment(Qt.AlignCenter)
        dua_lbl.setLayoutDirection(Qt.RightToLeft)
        b.addWidget(dua_lbl)

        self.body_layout.addWidget(inner)

        # footer
        f_lay = self.add_footer(height=34)
        left = QLabel(f"yt-dlp {_yt_dlp_version()} · ffmpeg {_ffmpeg_version()}")
        left.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace; font-size:11px; color:{FG_SUBTLE};"
        )
        f_lay.addWidget(left)
        f_lay.addStretch()
        right = QLabel(_platform_label())
        right.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace; font-size:11px; color:{FG_SUBTLE};"
        )
        f_lay.addWidget(right)
