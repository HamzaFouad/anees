from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, PRIMARY_HOVER, ON_PRIMARY,
    FG, FG_MUTED, FG_SUBTLE, BG, BG_MUTED, BG_SUBTLE, BORDER,
    SUCCESS_BG, SUCCESS_DARK, ERROR_BG, ERROR_DARK, ERROR_TINT_4,
)
from ui.widgets import icon_pixmap, icon_label, Checkbox
from backend.mock_data import MOCK_LOGS
from backend.models import LogEntry


class DiagnosticsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sent = False
        self._bundle = {
            "logs": True,
            "system": True,
            "versions": True,
            "config": True,
            "queue_state": True,
        }
        self._message = ""

        logs = MOCK_LOGS
        self._err_count = sum(1 for l in logs if l.lvl == "error")
        self._warn_count = sum(1 for l in logs if l.lvl == "warn")

        self.setWindowTitle("Send diagnostics")
        self.setFixedWidth(580)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("diagnosticsDialog")
        self.setStyleSheet(
            f"#diagnosticsDialog {{ background:{BG}; border-radius:10px; border:1px solid {BORDER}; }}"
        )

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)
        self._root.addWidget(self._build_header())
        self._root.addWidget(self._build_body())
        self._root.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"border-bottom:1px solid {BORDER};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        text = QWidget()
        text_lay = QVBoxLayout(text)
        text_lay.setContentsMargins(0, 0, 0, 0)
        text_lay.setSpacing(6)

        title_row = QWidget()
        title_lay = QHBoxLayout(title_row)
        title_lay.setContentsMargins(0, 0, 0, 0)
        title_lay.setSpacing(8)
        title_lay.addWidget(icon_label("shield", 15, FG))
        title_lbl = QLabel("Send diagnostics to developer")
        title_lbl.setStyleSheet(f"font-size:15px; font-weight:600; color:{FG};")
        title_lay.addWidget(title_lbl)
        text_lay.addWidget(title_row)

        desc = QLabel(
            "Helps the developer reproduce and fix issues. Personally identifying details "
            "(your username, video URLs, output file paths) are stripped before sending."
        )
        desc.setStyleSheet(f"font-size:12px; color:{FG_MUTED}; line-height:1.5;")
        desc.setWordWrap(True)
        text_lay.addWidget(desc)
        lay.addWidget(text, 1)

        close_btn = QPushButton()
        close_btn.setIcon(QIcon(icon_pixmap("x", 14, FG_MUTED)))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; border-radius:5px; }}"
            f"QPushButton:hover {{ background:{BG_SUBTLE}; }}"
        )
        close_btn.clicked.connect(self.reject)
        lay.addWidget(close_btn)
        return w

    def _build_body(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(14)

        # error summary banner
        if self._err_count > 0:
            banner = QWidget()
            banner.setStyleSheet(
                f"background:{ERROR_TINT_4}; border:1px solid {ERROR_BG}; border-radius:6px;"
            )
            b_lay = QHBoxLayout(banner)
            b_lay.setContentsMargins(12, 10, 12, 10)
            b_lay.setSpacing(10)
            b_lay.addWidget(icon_label("alert", 15, ERROR_DARK))
            errs = f"<b>{self._err_count} error{'s' if self._err_count != 1 else ''}</b>"
            warns = f"<b>{self._warn_count} warning{'s' if self._warn_count != 1 else ''}</b>"
            msg = QLabel(
                f"Detected {errs} and {warns} in the most recent run. These will be included."
            )
            msg.setStyleSheet(f"font-size:12px; color:#7F1D1D; line-height:1.5;")
            msg.setWordWrap(True)
            msg.setTextFormat(Qt.RichText)
            b_lay.addWidget(msg, 1)
            lay.addWidget(banner)

        # optional message
        msg_lbl = QLabel("What were you doing? (optional)")
        msg_lbl.setStyleSheet(
            f"font-size:11px; font-weight:500; color:{FG_MUTED}; "
            f"letter-spacing:.04em; text-transform:uppercase;"
        )
        lay.addWidget(msg_lbl)

        self._msg_edit = QTextEdit()
        self._msg_edit.setPlaceholderText(
            "e.g. Adding a 24-video Lex Fridman playlist, ffmpeg crashed on video 06…"
        )
        self._msg_edit.setFixedHeight(80)
        self._msg_edit.setStyleSheet(f"""
            QTextEdit {{
                background:{BG}; border:1px solid {BORDER}; border-radius:6px;
                padding:8px 10px; font-size:13px; color:{FG}; font-family:inherit;
                line-height:1.5;
            }}
            QTextEdit:focus {{ border-color:{PRIMARY}; }}
        """)
        lay.addWidget(self._msg_edit)

        # included items
        included_lbl = QLabel("Included in this report")
        included_lbl.setStyleSheet(
            f"font-size:11px; font-weight:500; color:{FG_MUTED}; "
            f"letter-spacing:.04em; text-transform:uppercase;"
        )
        lay.addWidget(included_lbl)

        items_container = QWidget()
        items_container.setStyleSheet(
            f"border:1px solid {BORDER}; border-radius:8px; background:{BG};"
        )
        items_lay = QVBoxLayout(items_container)
        items_lay.setContentsMargins(0, 0, 0, 0)
        items_lay.setSpacing(0)

        items = [
            ("logs",        "Recent logs",          f"{len(MOCK_LOGS)} entries · last 24h · {self._err_count} errors, {self._warn_count} warnings"),
            ("system",      "System info",          "Windows 11 23H2 · 16 GB RAM · x64 · 1920×1080"),
            ("versions",    "Tool versions",        "Anees 0.1.0 · yt-dlp 2025.04.30 · ffmpeg 7.1"),
            ("config",      "Config (anonymized)",  "Paths replaced with <user>, playlist IDs truncated"),
            ("queue_state", "Current queue state",  "4 playlists · runState=running · 11/24 videos done"),
        ]
        self._check_rows: list[_BundleRow] = []
        for i, (key, label, sub) in enumerate(items):
            border = f"border-bottom:1px solid #EAECF0;" if i < len(items) - 1 else ""
            row = _BundleRow(key, label, sub, self._bundle[key], border)
            row.toggled.connect(lambda checked, k=key: self._on_bundle_toggle(k, checked))
            items_lay.addWidget(row)
            self._check_rows.append(row)
        lay.addWidget(items_container)

        # not included
        shield_row = QWidget()
        shield_row.setStyleSheet(
            f"background:{BG_SUBTLE}; border:1px solid {BORDER}; border-radius:6px;"
        )
        s_lay = QHBoxLayout(shield_row)
        s_lay.setContentsMargins(12, 10, 12, 10)
        s_lay.setSpacing(10)
        s_lay.addWidget(icon_label("shield", 14, SUCCESS_DARK))

        shield_text = QWidget()
        st_lay = QVBoxLayout(shield_text)
        st_lay.setContentsMargins(0, 0, 0, 0)
        st_lay.setSpacing(4)
        not_lbl = QLabel("Not included")
        not_lbl.setStyleSheet(f"font-size:11.5px; font-weight:600; color:{FG};")
        st_lay.addWidget(not_lbl)
        not_desc = QLabel(
            "YouTube URLs · video titles · output mp3 files · your Windows username · network IPs"
        )
        not_desc.setStyleSheet(f"font-size:11px; color:{FG_MUTED}; line-height:1.6;")
        not_desc.setWordWrap(True)
        st_lay.addWidget(not_desc)
        s_lay.addWidget(shield_text, 1)
        lay.addWidget(shield_row)
        return w

    def _on_bundle_toggle(self, key: str, checked: bool):
        self._bundle[key] = checked

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(52)
        w.setStyleSheet(f"background:{BG_MUTED}; border-top:1px solid {BORDER};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(8)

        copy_btn = QPushButton("  Copy bundle")
        copy_btn.setIcon(QIcon(icon_pixmap("copy", 13, FG_MUTED)))
        copy_btn.setFixedHeight(28)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{FG_MUTED}; border:none;
                font-size:12px; padding:0 10px;
            }}
            QPushButton:hover {{ color:{FG}; }}
        """)
        lay.addWidget(copy_btn)
        lay.addStretch()

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
        lay.addWidget(cancel_btn)

        send_btn = QPushButton("  Send report")
        send_btn.setIcon(QIcon(icon_pixmap("send", 13, ON_PRIMARY)))
        send_btn.setFixedHeight(32)
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:{ON_PRIMARY}; border:none;
                border-radius:6px; padding:0 16px; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
        """)
        send_btn.clicked.connect(self._on_send)
        lay.addWidget(send_btn)
        return w

    def _on_send(self):
        self._show_success()

    def _show_success(self):
        # clear layout
        while self._root.count():
            item = self._root.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        success = QWidget()
        success.setStyleSheet(f"background:{BG};")
        s_lay = QVBoxLayout(success)
        s_lay.setContentsMargins(24, 24, 24, 20)
        s_lay.setSpacing(0)
        s_lay.setAlignment(Qt.AlignHCenter)

        icon_container = QWidget()
        icon_container.setFixedSize(48, 48)
        icon_container.setStyleSheet(
            f"background:{SUCCESS_BG}; border-radius:99px;"
        )
        ic_lay = QHBoxLayout(icon_container)
        ic_lay.setContentsMargins(0, 0, 0, 0)
        ic_lay.addWidget(icon_label("check", 24, SUCCESS_DARK), alignment=Qt.AlignCenter)
        s_lay.addWidget(icon_container, alignment=Qt.AlignHCenter)
        s_lay.addSpacing(14)

        title = QLabel("Diagnostics sent")
        title.setAlignment(Qt.AlignHCenter)
        title.setStyleSheet(f"font-size:16px; font-weight:600; color:{FG};")
        s_lay.addWidget(title)
        s_lay.addSpacing(8)

        ref_code = "ANS-2026-05-27-#7Q4B"
        desc = QLabel(
            f'Reference <code style="font-family:monospace; background:{BG_SUBTLE}; '
            f'padding:1px 6px; border-radius:3px;">{ref_code}</code> — saved to your clipboard. '
            f'Quote it if you reach out about this issue.'
        )
        desc.setAlignment(Qt.AlignHCenter)
        desc.setTextFormat(Qt.RichText)
        desc.setStyleSheet(f"font-size:12px; color:{FG_MUTED}; line-height:1.5;")
        desc.setWordWrap(True)
        s_lay.addWidget(desc)
        s_lay.addSpacing(18)

        done_btn = QPushButton("Done")
        done_btn.setFixedHeight(34)
        done_btn.setFixedWidth(100)
        done_btn.setCursor(Qt.PointingHandCursor)
        done_btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:#fff; border:none;
                border-radius:6px; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:#0039D9; }}
        """)
        done_btn.clicked.connect(self.accept)
        s_lay.addWidget(done_btn, alignment=Qt.AlignHCenter)

        self._root.addWidget(success)


from PySide6.QtCore import Signal as _Signal


class _BundleRow(QWidget):
    toggled = _Signal(bool)

    def __init__(self, key: str, label: str, sub: str, checked: bool, border_style: str, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"background:{'#fff' if checked else BG_SUBTLE}; {border_style}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        self._box = Checkbox(checked)
        lay.addWidget(self._box)

        text = QWidget()
        text_lay = QVBoxLayout(text)
        text_lay.setContentsMargins(0, 0, 0, 0)
        text_lay.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"font-size:12.5px; font-weight:500; "
            f"color:{FG if checked else FG_MUTED};"
        )
        text_lay.addWidget(lbl)
        sub_lbl = QLabel(sub)
        sub_lbl.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; font-family:'JetBrains Mono',monospace;"
        )
        text_lay.addWidget(sub_lbl)
        lay.addWidget(text, 1)

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self._box.checked = self._checked
        self.toggled.emit(self._checked)
        super().mousePressEvent(event)
            p.drawRoundedRect(0, 0, 16, 16, 4, 4)
