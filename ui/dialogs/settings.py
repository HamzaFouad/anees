from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, ON_PRIMARY, PRIMARY_HOVER,
    FG, FG_MUTED, BG, BG_MUTED, BG_SUBTLE, BORDER,
)
from ui.widgets import StyledInput, icon_pixmap
from ui.state import AppState


class SettingsDialog(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setWindowTitle("Settings")
        self.setFixedWidth(520)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QWidget()
        card.setObjectName("settingsCard")
        card.setStyleSheet(
            f"#settingsCard {{ background:{BG}; border-radius:12px; border:1px solid {BORDER}; }}"
        )
        outer.addWidget(card)
        root = QVBoxLayout(card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── header ──
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(f"border-bottom:1px solid {BORDER};")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(18, 0, 18, 0)
        t = QLabel("Settings")
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
        body_lay.setContentsMargins(18, 20, 18, 20)
        body_lay.setSpacing(6)

        body_lay.addWidget(self._make_label("Download folder"))

        row = QWidget()
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(8)

        self._path_input = StyledInput(state._output_root, mono=True)
        self._path_input.setText(state._output_root)
        row_lay.addWidget(self._path_input, 1)

        browse_btn = QPushButton("  Browse")
        browse_btn.setIcon(QIcon(icon_pixmap("folder", 13, FG_MUTED)))
        browse_btn.setFixedHeight(32)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG}; border:1px solid {BORDER};
                border-radius:6px; font-size:12px; padding:0 12px;
            }}
            QPushButton:hover {{ background:{BG_SUBTLE}; }}
        """)
        browse_btn.clicked.connect(self._browse)
        row_lay.addWidget(browse_btn)
        body_lay.addWidget(row)

        hint = QLabel("Each playlist is saved to a subfolder: prefix_playlist-name/")
        hint.setStyleSheet(f"font-size:11px; color:{FG_MUTED};")
        body_lay.addWidget(hint)
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

        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(32)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:{ON_PRIMARY}; border:none;
                border-radius:6px; padding:0 24px; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOVER}; }}
        """)
        save_btn.clicked.connect(self._save)
        f_lay.addWidget(save_btn)
        root.addWidget(footer)

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            f"font-size:10px; font-weight:500; color:{FG_MUTED}; letter-spacing:.04em;"
        )
        return lbl

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select download folder", self._path_input.text()
        )
        if path:
            self._path_input.setText(path)

    def _save(self) -> None:
        path = self._path_input.text().strip()
        if path:
            self._state.set_output_root(path)
        self.accept()
