from __future__ import annotations
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.theme import (
    BG, BG_SUBTLE, BORDER, ERROR, ERROR_BG, ERROR_BORDER,
    FG, FG_MUTED, PRIMARY, FONT_MONO, TEXT_SM,
)
from ui.widgets import RoundedDialog, icon_label


class FfmpegMissingDialog(RoundedDialog):
    """Shown at startup when ffmpeg cannot be found.

    On macOS the bundled app should always ship ffmpeg, so this only appears
    when running from source without a local ffmpeg install.
    """

    def __init__(self, parent=None):
        super().__init__(title="ffmpeg not found", width=480, parent=parent)
        self.setWindowTitle("ffmpeg not found")

        b = self.body_layout
        b.setSpacing(16)

        # error banner
        banner = QWidget()
        banner.setStyleSheet(
            f"background:{ERROR_BG}; border:1px solid {ERROR_BORDER}; border-radius:8px;"
        )
        ban_lay = QHBoxLayout(banner)
        ban_lay.setContentsMargins(12, 10, 12, 10)
        ban_lay.setSpacing(10)
        ban_lay.addWidget(icon_label("alert", 16, ERROR))
        msg = QLabel(
            "ffmpeg is required to convert downloads to MP3.\n"
            "It could not be found on this system."
        )
        msg.setStyleSheet(f"font-size:12px; color:{FG};")
        msg.setWordWrap(True)
        ban_lay.addWidget(msg, 1)
        b.addWidget(banner)

        # platform-specific fix instructions
        if sys.platform == "darwin":
            b.addWidget(_section(
                "Install via Homebrew",
                "brew install ffmpeg",
                "Open Terminal and run:",
            ))
        elif sys.platform == "win32":
            b.addWidget(_section(
                "Install ffmpeg",
                "winget install ffmpeg",
                "Open PowerShell and run:",
            ))
        else:
            b.addWidget(_section(
                "Install ffmpeg",
                "sudo apt install ffmpeg",
                "Open a terminal and run:",
            ))

        note = QLabel(
            "After installing ffmpeg, relaunch Anees."
        )
        note.setStyleSheet(f"font-size:{TEXT_SM}px; color:{FG_MUTED};")
        b.addWidget(note)

        # close button
        row = QWidget(); row.setStyleSheet("background:transparent;")
        r_lay = QHBoxLayout(row)
        r_lay.setContentsMargins(0, 4, 0, 0)
        r_lay.addStretch()
        quit_btn = QPushButton("Quit")
        quit_btn.setFixedSize(80, 32)
        quit_btn.setStyleSheet(
            f"QPushButton {{ background:{BG_SUBTLE}; border:1px solid {BORDER};"
            f" border-radius:6px; font-size:13px; color:{FG}; }}"
            f"QPushButton:hover {{ background:{BORDER}; }}"
        )
        quit_btn.clicked.connect(self.reject)
        r_lay.addWidget(quit_btn)
        b.addWidget(row)


def _section(heading: str, command: str, label: str) -> QWidget:
    w = QWidget(); w.setStyleSheet("background:transparent;")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)

    lbl = QLabel(label)
    lbl.setStyleSheet(f"font-size:12px; color:{FG_MUTED}; background:transparent;")
    lay.addWidget(lbl)

    code_row = QWidget()
    code_row.setStyleSheet(
        f"background:{BG_SUBTLE}; border:1px solid {BORDER}; border-radius:6px;"
    )
    cr_lay = QHBoxLayout(code_row)
    cr_lay.setContentsMargins(12, 8, 12, 8)

    code_lbl = QLabel(command)
    code_lbl.setStyleSheet(
        f"font-family:{FONT_MONO}; font-size:12px; color:{FG};"
    )
    code_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    cr_lay.addWidget(code_lbl)
    cr_lay.addStretch()

    copy_btn = QPushButton("Copy")
    copy_btn.setFixedSize(52, 24)
    copy_btn.setStyleSheet(
        f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
        f" border-radius:4px; font-size:11px; }}"
        f"QPushButton:hover {{ background:#0039D9; }}"
    )
    from PySide6.QtWidgets import QApplication
    copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(command))
    cr_lay.addWidget(copy_btn)

    lay.addWidget(code_row)
    return w
