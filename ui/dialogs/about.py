from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from ui.statusbar import _ffmpeg_version, _yt_dlp_version
from ui.theme import (
    BG, BG_MUTED, BG_SUBTLE, BORDER,
    FG, FG_MUTED, FG_SUBTLE,
    PRIMARY,
)
from ui.widgets import icon_pixmap

# ── Content ───────────────────────────────────────────────────────────────────
APP_NAME_AR   = "أنيس"
APP_VERSION   = "1.0.0"
APP_DESC      = "تطبيق لتسهيل تحميل وتجهيز السمعيّات من يوتيوب\nعلى بطاقات الذاكرة."
HADITH_TEXT   = "«احرِصْ على ما يَنفَعُكَ واستَعِنْ بالله ولا تَعجِزْ»"
HADITH_SOURCE = "رواه مسلم"
AYAH_TEXT     = "﴿وَاصْبِرْ وَمَا صَبْرُكَ إِلَّا بِاللَّهِ﴾"
AYAH_SOURCE   = "سورة النحل ١٢٧"
DUA_TEXT      = "نسأل اللهَ أن يجعلَه بابَ نفعٍ وسكينةٍ وثبات."

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


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About أنيس")
        self.setFixedWidth(480)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # ── outer card ────────────────────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("aboutCard")
        card.setStyleSheet(
            f"#aboutCard {{ background:{BG}; border-radius:12px; "
            f"border:1px solid {BORDER}; }}"
        )
        outer.addWidget(card)

        root = QVBoxLayout(card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── close button ──────────────────────────────────────────────────────
        hdr = QWidget(); hdr.setFixedHeight(44)
        hdr.setStyleSheet("background:transparent;")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(8, 8, 8, 0)
        h_lay.addStretch()
        x_btn = QPushButton()
        x_btn.setIcon(QIcon(icon_pixmap("x", 14, FG_MUTED)))
        x_btn.setFixedSize(28, 28)
        x_btn.setCursor(Qt.PointingHandCursor)
        x_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; border-radius:6px; }}"
            f"QPushButton:hover {{ background:{BG_SUBTLE}; }}"
        )
        x_btn.clicked.connect(self.reject)
        h_lay.addWidget(x_btn)
        root.addWidget(hdr)

        # ── scrollable body ───────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background:{BG}; border:none; }}")
        scroll.viewport().setStyleSheet(f"background:{BG};")

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(32, 4, 32, 28)
        b_lay.setSpacing(0)
        b_lay.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # logo
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(72, 72)
        px = QIcon(str(_app_icon_path())).pixmap(128, 128)
        if not px.isNull():
            icon_lbl.setPixmap(px.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_lbl.setAlignment(Qt.AlignCenter)
        b_lay.addWidget(icon_lbl, 0, Qt.AlignHCenter)
        b_lay.addSpacing(14)

        # app name
        name_lbl = QLabel(APP_NAME_AR)
        name_lbl.setStyleSheet(
            f"font-family:{ARABIC_SANS}; font-size:36px; font-weight:700; color:{FG};"
        )
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setLayoutDirection(Qt.RightToLeft)
        b_lay.addWidget(name_lbl)
        b_lay.addSpacing(6)

        # version
        ver_lbl = QLabel(f"ANEES · VERSION {APP_VERSION}")
        ver_lbl.setStyleSheet(
            f"font-size:11px; font-weight:500; color:{FG_SUBTLE}; letter-spacing:0.08em;"
        )
        ver_lbl.setAlignment(Qt.AlignCenter)
        b_lay.addWidget(ver_lbl)
        b_lay.addSpacing(16)

        # description
        desc_lbl = QLabel(APP_DESC)
        desc_lbl.setStyleSheet(
            f"font-family:{ARABIC_SANS}; font-size:14px; color:{FG_MUTED};"
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setLayoutDirection(Qt.RightToLeft)
        b_lay.addWidget(desc_lbl)
        b_lay.addSpacing(24)

        # ── hadith box ────────────────────────────────────────────────────────
        hadith_box = QFrame()
        hadith_box.setObjectName("hadithBox")
        hadith_box.setStyleSheet(
            "#hadithBox { background:rgba(0,68,255,0.04); "
            "border:1px solid rgba(0,68,255,0.12); border-radius:10px; }"
        )
        hb_lay = QVBoxLayout(hadith_box)
        hb_lay.setContentsMargins(22, 20, 22, 18)
        hb_lay.setSpacing(10)

        h_text = QLabel(HADITH_TEXT)
        h_text.setStyleSheet(
            f"font-family:{ARABIC_SERIF}; font-size:20px; font-weight:700; "
            f"color:{FG}; background:transparent; border:none;"
        )
        h_text.setWordWrap(True)
        h_text.setAlignment(Qt.AlignCenter)
        h_text.setLayoutDirection(Qt.RightToLeft)
        hb_lay.addWidget(h_text)

        h_src = QLabel(HADITH_SOURCE)
        h_src.setStyleSheet(
            f"font-family:{ARABIC_SANS}; font-size:11.5px; color:{FG_SUBTLE}; "
            "background:transparent; border:none; letter-spacing:0.02em;"
        )
        h_src.setAlignment(Qt.AlignCenter)
        h_src.setLayoutDirection(Qt.RightToLeft)
        hb_lay.addWidget(h_src)
        b_lay.addWidget(hadith_box)
        b_lay.addSpacing(20)

        # ── ayah ──────────────────────────────────────────────────────────────
        ayah_lbl = QLabel(AYAH_TEXT)
        ayah_lbl.setStyleSheet(
            f"font-family:{ARABIC_SERIF}; font-size:24px; font-weight:400; color:{PRIMARY};"
        )
        ayah_lbl.setWordWrap(True)
        ayah_lbl.setAlignment(Qt.AlignCenter)
        ayah_lbl.setLayoutDirection(Qt.RightToLeft)
        b_lay.addWidget(ayah_lbl)
        b_lay.addSpacing(8)

        ayah_src = QLabel(AYAH_SOURCE)
        ayah_src.setStyleSheet(
            f"font-family:{ARABIC_SANS}; font-size:11.5px; color:{FG_SUBTLE}; "
            "letter-spacing:0.02em;"
        )
        ayah_src.setAlignment(Qt.AlignCenter)
        ayah_src.setLayoutDirection(Qt.RightToLeft)
        b_lay.addWidget(ayah_src)
        b_lay.addSpacing(22)

        # ── dua ───────────────────────────────────────────────────────────────
        dua_lbl = QLabel(DUA_TEXT)
        dua_lbl.setStyleSheet(
            f"font-family:{ARABIC_SERIF}; font-size:15px; font-style:italic; color:{FG_MUTED};"
        )
        dua_lbl.setWordWrap(True)
        dua_lbl.setAlignment(Qt.AlignCenter)
        dua_lbl.setLayoutDirection(Qt.RightToLeft)
        b_lay.addWidget(dua_lbl)

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # ── footer ────────────────────────────────────────────────────────────
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER}; border:none;")
        root.addWidget(sep)

        footer = QWidget()
        footer.setFixedHeight(38)
        footer.setStyleSheet(f"background:{BG_MUTED};")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(16, 0, 16, 0)

        left = QLabel(f"yt-dlp {_yt_dlp_version()} · ffmpeg {_ffmpeg_version()}")
        left.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace; font-size:11px; color:{FG_SUBTLE};"
        )
        f_lay.addWidget(left)
        f_lay.addStretch()

        right = QLabel(f"{_platform_label()} · MIT")
        right.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace; font-size:11px; color:{FG_SUBTLE};"
        )
        f_lay.addWidget(right)
        root.addWidget(footer)
