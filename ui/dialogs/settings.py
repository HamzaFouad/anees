from __future__ import annotations
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.theme import PRIMARY, ON_PRIMARY, PRIMARY_HOVER, FG, FG_MUTED, BG, BG_SUBTLE, BORDER
from ui.widgets import RoundedDialog, StyledInput, icon_pixmap
from ui.state import AppState


class SettingsDialog(RoundedDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(title="Settings", width=520, body_margins=(18, 20, 18, 20), parent=parent)
        self._state = state

        # ── body content ──────────────────────────────────────────────────────
        self.body_layout.setSpacing(6)

        self.body_layout.addWidget(self._make_label("Download folder"))

        row = QWidget(); row.setStyleSheet("background:transparent;")
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
        self.body_layout.addWidget(row)

        hint = QLabel("Each playlist is saved to a subfolder: prefix_playlist-name/")
        hint.setStyleSheet(f"font-size:11px; color:{FG_MUTED};")
        self.body_layout.addWidget(hint)

        # ── footer ────────────────────────────────────────────────────────────
        f_lay = self.add_footer()
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
