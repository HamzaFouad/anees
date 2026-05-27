from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QWidget,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, FG, FG_MUTED, FG_SUBTLE, BG, BG_MUTED, BG_SUBTLE, BORDER,
    SUCCESS, SUCCESS_BG, SUCCESS_DARK,
)
from ui.widgets import Toggle, Badge, StyledInput, icon_pixmap, icon_label
from ui.state import AppState
from backend.models import Playlist


def _field(label: str, widget: QWidget) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    lbl = QLabel(label.upper())
    lbl.setStyleSheet(
        f"font-size:11px; font-weight:500; color:{FG_MUTED}; letter-spacing:.04em;"
    )
    lay.addWidget(lbl)
    lay.addWidget(widget)
    return w


class MergeDialog(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._selected: set[str] = {
            p.id for p in state.playlists if p.completed > 0
        }
        self._splitter_on = False
        self._splitter_url = ""
        self._splitter_resolved = False
        self._resolving = False

        self.setWindowTitle("Merge to single folder")
        self.setFixedWidth(620)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet(
            f"background:{BG}; border-radius:10px; border:1px solid {BORDER};"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._build_body())
        root.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"border-bottom:1px solid {BORDER};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        text_col = QWidget()
        text_lay = QVBoxLayout(text_col)
        text_lay.setContentsMargins(0, 0, 0, 0)
        text_lay.setSpacing(6)

        title_row = QWidget()
        title_lay = QHBoxLayout(title_row)
        title_lay.setContentsMargins(0, 0, 0, 0)
        title_lay.setSpacing(8)
        title_lay.addWidget(icon_label("merge", 15, FG))
        title_lbl = QLabel("Merge to single folder")
        title_lbl.setStyleSheet(f"font-size:15px; font-weight:600; color:{FG};")
        title_lay.addWidget(title_lbl)
        text_lay.addWidget(title_row)

        desc = QLabel(
            "Copies the processed <b>.mp3</b> files from every selected playlist into one flat "
            "folder — handy for syncing to a phone, MP3 player, or car. "
            "The original per-playlist folders stay untouched."
        )
        desc.setStyleSheet(f"font-size:12px; color:{FG_MUTED}; line-height:1.5;")
        desc.setWordWrap(True)
        text_lay.addWidget(desc)
        lay.addWidget(text_col, 1)

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

        # destination path
        dest_row = QWidget()
        dest_lay = QHBoxLayout(dest_row)
        dest_lay.setContentsMargins(0, 0, 0, 0)
        dest_lay.setSpacing(6)
        self._dest_input = StyledInput("D:\\Audio\\Anees\\_merged", mono=True)
        self._dest_input.setText("D:\\Audio\\Anees\\_merged")
        dest_lay.addWidget(self._dest_input, 1)
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
        dest_lay.addWidget(browse_btn)
        lay.addWidget(_field("Destination folder", dest_row))

        # playlists checklist
        eligible = [p for p in self._state.playlists]
        n_sel = sum(1 for p in eligible if p.id in self._selected)
        self._pl_list = _PlaylistChecklist(eligible, self._selected, self)
        self._pl_list.selection_changed.connect(self._update_footer_totals)
        lay.addWidget(_field(
            f"Playlists to include ({n_sel}/{len(eligible)} selected)",
            self._pl_list,
        ))

        # splitter clip section
        self._splitter_section = _SplitterSection(self)
        self._splitter_section.toggled.connect(self._on_splitter_toggle)
        lay.addWidget(self._splitter_section)
        return w

    def _on_splitter_toggle(self, on: bool):
        self._splitter_on = on
        self._update_footer_totals()

    def _update_footer_totals(self):
        if hasattr(self, "_footer_info"):
            total_files = sum(
                p.completed for p in self._state.playlists
                if p.id in self._selected
            )
            total_mb = sum(
                (p.size_mb or 0) for p in self._state.playlists
                if p.id in self._selected
            )
            n_sel = len(self._selected)
            self._footer_info.setText(
                f"{total_files} files · {total_mb:.1f} MB · copies, doesn't move"
            )
            self._merge_btn.setText(f"  Merge {n_sel} playlists")

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(52)
        w.setStyleSheet(f"background:{BG_MUTED}; border-top:1px solid {BORDER};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(8)

        self._footer_info = QLabel("0 files · 0 MB · copies, doesn't move")
        self._footer_info.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED};"
        )
        lay.addWidget(self._footer_info)
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

        self._merge_btn = QPushButton("  Merge playlists")
        self._merge_btn.setIcon(QIcon(icon_pixmap("merge", 13, "#fff")))
        self._merge_btn.setFixedHeight(32)
        self._merge_btn.setCursor(Qt.PointingHandCursor)
        self._merge_btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:#fff; border:none;
                border-radius:6px; padding:0 16px; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:#0039D9; }}
        """)
        self._merge_btn.clicked.connect(self.accept)
        lay.addWidget(self._merge_btn)

        self._update_footer_totals()
        return w


from PySide6.QtCore import Signal as _Signal


class _PlaylistChecklist(QWidget):
    selection_changed = _Signal()

    def __init__(self, playlists: list, selected: set, parent=None):
        super().__init__(parent)
        self._selected = selected
        self.setStyleSheet(
            f"border:1px solid {BORDER}; border-radius:6px; background:{BG};"
        )
        self.setMaximumHeight(180)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        for i, p in enumerate(playlists):
            eligible = p.completed > 0
            row = _CheckRow(p, p.id in selected, eligible)
            if eligible:
                row.toggled.connect(
                    lambda checked, pid=p.id: self._on_toggle(pid, checked)
                )
            border = f"border-bottom:1px solid #EAECF0;" if i < len(playlists) - 1 else ""
            row.setStyleSheet(
                f"background:{'rgba(0,68,255,0.04)' if p.id in selected else BG}; {border}"
            )
            lay.addWidget(row)

    def _on_toggle(self, pid: str, checked: bool):
        if checked:
            self._selected.add(pid)
        else:
            self._selected.discard(pid)
        self.selection_changed.emit()


class _CheckRow(QWidget):
    toggled = _Signal(bool)

    def __init__(self, pl: Playlist, checked: bool, eligible: bool, parent=None):
        super().__init__(parent)
        self._pl = pl
        self._checked = checked
        self._eligible = eligible

        if eligible:
            self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)

        self._check = _CheckBox(checked)
        lay.addWidget(self._check)

        pfx = QLabel(pl.prefix)
        pfx.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace; font-size:11px; "
            f"font-weight:600; color:{FG_MUTED};"
        )
        lay.addWidget(pfx)

        title = QLabel(pl.title)
        title.setStyleSheet(f"font-size:12px; color:{FG};")
        lay.addWidget(title, 1)

        stats_text = f"{pl.completed}/{pl.video_count}"
        if pl.size_mb:
            stats_text += f" · {pl.size_mb:.1f} MB"
        stats = QLabel(stats_text)
        stats.setStyleSheet(f"font-size:11px; color:{FG_MUTED};")
        lay.addWidget(stats)

        if not eligible:
            self.setEnabled(False)
            self.setStyleSheet("opacity:0.5;")

    def mousePressEvent(self, event):
        if self._eligible:
            self._checked = not self._checked
            self._check.set_checked(self._checked)
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)


class _CheckBox(QWidget):
    def __init__(self, checked: bool, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._checked = checked

    def set_checked(self, val: bool):
        self._checked = val
        self.update()

    def paintEvent(self, _):
        from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._checked:
            p.setBrush(QColor(PRIMARY))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(0, 0, 14, 14, 3, 3)
            p.setPen(QPen(QColor("#fff"), 1.5))
            path = QPainterPath()
            path.moveTo(2.5, 7)
            path.lineTo(5.5, 10)
            path.lineTo(11.5, 4)
            p.drawPath(path)
        else:
            p.setBrush(QColor(BG))
            p.setPen(QPen(QColor(BORDER), 1))
            p.drawRoundedRect(0, 0, 14, 14, 3, 3)


class _SplitterSection(QWidget):
    toggled = _Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self.setStyleSheet(
            f"border:1px solid {BORDER}; border-radius:8px; background:{BG};"
        )

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        # top row
        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(12, 10, 12, 10)
        top_lay.setSpacing(12)

        text = QWidget()
        text_lay = QVBoxLayout(text)
        text_lay.setContentsMargins(0, 0, 0, 0)
        text_lay.setSpacing(3)

        title_row = QWidget()
        title_lay = QHBoxLayout(title_row)
        title_lay.setContentsMargins(0, 0, 0, 0)
        title_lay.setSpacing(6)
        title_lay.addWidget(icon_label("scissors", 13, FG))
        title_lbl = QLabel("Splitter clip between playlists")
        title_lbl.setStyleSheet(f"font-size:12.5px; font-weight:600; color:{FG};")
        title_lay.addWidget(title_lbl)
        text_lay.addWidget(title_row)

        desc = QLabel(
            "Insert one short YouTube clip in the merged folder between each playlist — "
            "a chime, jingle, or \"next up\" marker so you hear where one playlist ends."
        )
        desc.setStyleSheet(f"font-size:11px; color:{FG_MUTED}; line-height:1.5;")
        desc.setWordWrap(True)
        text_lay.addWidget(desc)
        top_lay.addWidget(text, 1)

        self._toggle = Toggle(False)
        self._toggle.toggled.connect(self._on_toggle)
        top_lay.addWidget(self._toggle)
        self._root.addWidget(top)

        # URL row (hidden initially)
        self._url_row = QWidget()
        self._url_row.setVisible(False)
        self._url_row.setStyleSheet(f"border-top:1px solid {BORDER};")
        url_lay = QVBoxLayout(self._url_row)
        url_lay.setContentsMargins(12, 10, 12, 10)
        url_lay.setSpacing(8)

        input_row = QWidget()
        input_lay = QHBoxLayout(input_row)
        input_lay.setContentsMargins(0, 0, 0, 0)
        input_lay.setSpacing(6)
        self._url_input = StyledInput("https://youtube.com/watch?v=…", mono=True)
        input_lay.addWidget(self._url_input, 1)
        self._fetch_btn = QPushButton("Fetch")
        self._fetch_btn.setFixedHeight(32)
        self._fetch_btn.setCursor(Qt.PointingHandCursor)
        self._fetch_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG}; border:1px solid {BORDER};
                border-radius:6px; padding:0 14px; font-size:12px;
            }}
            QPushButton:hover {{ background:{BG_SUBTLE}; }}
            QPushButton:disabled {{ color:{FG_MUTED}; }}
        """)
        self._fetch_btn.clicked.connect(self._on_fetch)
        input_lay.addWidget(self._fetch_btn)
        url_lay.addWidget(input_row)

        self._resolved_card = QWidget()
        self._resolved_card.setVisible(False)
        self._root.addWidget(self._url_row)

    def _on_toggle(self, on: bool):
        self._on = on
        self._url_row.setVisible(on)
        self.toggled.emit(on)

    def _on_fetch(self):
        url = self._url_input.text().strip()
        if not url:
            return
        self._fetch_btn.setText("Resolving…")
        self._fetch_btn.setEnabled(False)
        QTimer.singleShot(600, self._on_resolved)

    def _on_resolved(self):
        self._fetch_btn.setText("Re-fetch")
        self._fetch_btn.setEnabled(True)

        if self._resolved_card.isVisible():
            return

        card = QWidget()
        card.setStyleSheet(
            f"background:{BG}; border:1px solid {BORDER}; border-radius:6px;"
        )
        card_lay = QHBoxLayout(card)
        card_lay.setContentsMargins(10, 8, 10, 8)
        card_lay.setSpacing(10)

        thumb = QWidget()
        thumb.setFixedSize(42, 42)
        thumb.setStyleSheet(
            "background:qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #1a2547, stop:1 #2a3050); border-radius:4px;"
        )
        card_lay.addWidget(thumb)

        info = QWidget()
        info_lay = QVBoxLayout(info)
        info_lay.setContentsMargins(0, 0, 0, 0)
        info_lay.setSpacing(2)
        title_lbl = QLabel("Lofi Hip Hop Radio — chill beats")
        title_lbl.setStyleSheet(f"font-size:12px; font-weight:600; color:{FG};")
        info_lay.addWidget(title_lbl)
        sub_lbl = QLabel("ChilledCow · 3:24")
        sub_lbl.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; font-family:'JetBrains Mono',monospace;"
        )
        info_lay.addWidget(sub_lbl)
        card_lay.addWidget(info, 1)

        badge = Badge("Resolved", "success")
        card_lay.addWidget(badge)

        # insert card into url_row layout
        self._url_row.layout().addWidget(card)
        self._resolved_card = card
        self._resolved_card.setVisible(True)
