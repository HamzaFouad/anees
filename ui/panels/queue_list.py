from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, FG, FG_MUTED, BG, BG_MUTED, BG_SUBTLE, BORDER,
    SUCCESS,
)
from ui.widgets import Btn, SlimProgressBar, icon_pixmap
from ui.state import AppState
from backend.models import Playlist, RunState


class QueueList(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setFixedWidth(280)
        self.setStyleSheet(f"background:{BG_SUBTLE}; border-right:1px solid {BORDER};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header
        self._header = QWidget()
        self._header.setFixedHeight(34)
        self._header.setStyleSheet(f"background:{BG_SUBTLE};")
        h_lay = QHBoxLayout(self._header)
        h_lay.setContentsMargins(12, 0, 10, 0)
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(
            f"font-size:10px; font-weight:500; color:{FG_MUTED}; "
            f"letter-spacing:0.06em; text-transform:uppercase;"
        )
        h_lay.addWidget(self._count_lbl)
        h_lay.addStretch()
        self._hint_lbl = QLabel("drag to reorder")
        self._hint_lbl.setStyleSheet(
            f"font-size:10px; color:{FG_MUTED}; font-family:'JetBrains Mono',monospace;"
        )
        h_lay.addWidget(self._hint_lbl)
        root.addWidget(self._header)

        # scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background:{BG_SUBTLE}; border:none; }}")
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet(f"background:{BG_SUBTLE};")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_widget)
        scroll.viewport().setStyleSheet(f"background:{BG_SUBTLE};")
        root.addWidget(scroll)

        # footer add button
        footer = QWidget()
        footer.setFixedHeight(46)
        footer.setStyleSheet(f"background:{BG_SUBTLE}; border-top:1px solid {BORDER};")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(10, 7, 10, 7)
        self._add_btn = QPushButton("  Add playlist")
        self._add_btn.setIcon(QIcon(icon_pixmap("plus", 13, FG_MUTED)))
        self._add_btn.setFixedHeight(28)
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG}; border:1px solid {BORDER};
                border-radius:6px; font-size:12px; font-weight:500;
            }}
            QPushButton:hover {{ background:{BG_MUTED}; }}
            QPushButton:disabled {{ background:#F3F4F6; color:{FG_MUTED}; }}
        """)
        f_lay.addWidget(self._add_btn)
        root.addWidget(footer)

        self._add_btn.clicked.connect(self._on_add)
        state.playlists_changed.connect(self._rebuild)
        state.selection_changed.connect(self._refresh_selection)
        state.run_state_changed.connect(self._on_run_state)
        state.query_changed.connect(self._rebuild)
        self._rebuild()

    def _on_add(self):
        if not self._state.locked:
            from ui.dialogs.add_playlist import AddPlaylistDialog
            AddPlaylistDialog(self._state, self.window()).exec()

    def _on_run_state(self, rs: RunState):
        locked = rs in (RunState.RUNNING, RunState.PAUSED)
        self._add_btn.setDisabled(locked)
        self._add_btn.setText("  Locked while running" if locked else "  Add playlist")
        self._hint_lbl.setText("locked" if locked else "drag to reorder")
        self._rebuild()

    def _rebuild(self):
        # remove old rows (except stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        q = self._state.query.lower()
        pls = [p for p in self._state.playlists if not q or q in p.title.lower()]
        self._count_lbl.setText(f"Playlists ({len(pls)})")

        if not pls:
            empty = _EmptyState()
            self._list_layout.insertWidget(0, empty)
        else:
            for i, pl in enumerate(pls):
                row = PlaylistRow(pl, pl.id == self._state.selected_id, self._state.locked)
                row.selected.connect(lambda _, pid=pl.id: self._state.set_selected(pid))
                row.remove_clicked.connect(lambda _, pid=pl.id: self._state.remove_playlist(pid))
                self._list_layout.insertWidget(i, row)

        # update add button style
        has_items = bool(self._state.playlists)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background:{'#0044FF' if not has_items else BG};
                color:{'#fff' if not has_items else FG};
                border:{'none' if not has_items else f'1px solid {BORDER}'};
                border-radius:6px; font-size:12px; font-weight:500;
            }}
            QPushButton:hover {{ background:{'#0039D9' if not has_items else BG_MUTED}; }}
            QPushButton:disabled {{ background:#F3F4F6; color:{FG_MUTED}; }}
        """)

    def _refresh_selection(self, pid: str):
        for i in range(self._list_layout.count()):
            w = self._list_layout.itemAt(i).widget()
            if isinstance(w, PlaylistRow):
                w.set_selected(w._pl.id == pid)


class PlaylistRow(QWidget):
    selected      = Signal(bool)
    remove_clicked = Signal(bool)

    def __init__(self, pl: Playlist, is_selected: bool, locked: bool, parent=None):
        super().__init__(parent)
        self._pl = pl
        self._selected = is_selected
        self._locked = locked
        self.setCursor(Qt.PointingHandCursor)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # main clickable area
        self._main = QPushButton()
        self._main.setFlat(True)
        self._main.setCursor(Qt.PointingHandCursor)
        self._main.clicked.connect(self.selected)

        m_lay = QHBoxLayout(self._main)
        m_lay.setContentsMargins(12, 10, 4, 10)
        m_lay.setSpacing(10)

        # prefix
        pfx = QLabel(pl.prefix)
        pfx.setFixedWidth(22)
        pfx.setAlignment(Qt.AlignCenter)
        pfx.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace; font-size:11px; "
            f"font-weight:600; color:{FG_MUTED};"
        )
        m_lay.addWidget(pfx)

        # title + progress
        mid = QWidget()
        mid_lay = QVBoxLayout(mid)
        mid_lay.setContentsMargins(0, 0, 0, 0)
        mid_lay.setSpacing(4)

        # status dot + title
        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(6)

        dot_color = SUCCESS if pl.status == "done" else (PRIMARY if pl.status == "active" else "#D6D3D1")
        dot = QLabel()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background:{dot_color}; border-radius:3px;")
        top_lay.addWidget(dot)

        title = QLabel(pl.title)
        title.setStyleSheet(
            f"font-size:12.5px; font-weight:{'500' if is_selected else '400'}; color:{FG};"
        )
        title.setMaximumWidth(200)
        top_lay.addWidget(title, 1)
        mid_lay.addWidget(top)

        # progress bar + count
        bot = QWidget()
        bot_lay = QHBoxLayout(bot)
        bot_lay.setContentsMargins(0, 0, 0, 0)
        bot_lay.setSpacing(6)
        bar = SlimProgressBar(
            color=SUCCESS if pl.status == "done" else PRIMARY,
            bar_height=3,
        )
        bar.set_value(pl.completed, pl.video_count)
        bot_lay.addWidget(bar, 1)
        cnt = QLabel(f"{pl.completed}/{pl.video_count}")
        cnt.setStyleSheet(
            f"font-size:10px; color:{FG_MUTED}; "
            f"font-family:'JetBrains Mono',monospace; min-width:36px;"
        )
        cnt.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bot_lay.addWidget(cnt)
        mid_lay.addWidget(bot)

        m_lay.addWidget(mid, 1)
        outer.addWidget(self._main, 1)

        # remove button (hidden unless hovered, invisible when locked)
        if not locked:
            self._rm_btn = QPushButton()
            self._rm_btn.setIcon(QIcon(icon_pixmap("x", 12, FG_MUTED)))
            self._rm_btn.setFixedSize(24, 24)
            self._rm_btn.setCursor(Qt.PointingHandCursor)
            self._rm_btn.setStyleSheet(
                "QPushButton { background:transparent; border:none; border-radius:4px; }"
                "QPushButton:hover { background:#E5E7EB; }"
            )
            self._rm_btn.setVisible(False)
            self._rm_btn.clicked.connect(self.remove_clicked)
            outer.addWidget(self._rm_btn)
            outer.setContentsMargins(0, 0, 6, 0)

        self._apply_style()

    def set_selected(self, sel: bool):
        self._selected = sel
        self._apply_style()

    def _apply_style(self):
        if self._selected:
            bg = "rgba(0,68,255,0.08)"
            border_left = f"border-left:2px solid {PRIMARY};"
        else:
            bg = BG_SUBTLE
            border_left = "border-left:2px solid transparent;"
        self.setStyleSheet(f"background:{bg}; {border_left}")
        self._main.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; text-align:left; }}"
        )

    def enterEvent(self, event):
        if not self._selected:
            self.setStyleSheet(f"background:{BG_SUBTLE}; border-left:2px solid transparent;")
        if not self._locked and hasattr(self, "_rm_btn"):
            self._rm_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style()
        if not self._locked and hasattr(self, "_rm_btn"):
            self._rm_btn.setVisible(False)
        super().leaveEvent(event)


class _EmptyState(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 30, 16, 30)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        icon_w = QWidget()
        icon_w.setFixedSize(44, 44)
        icon_w.setStyleSheet(f"background:#E5E7EB; border-radius:8px;")
        i_lay = QHBoxLayout(icon_w)
        i_lay.setContentsMargins(0, 0, 0, 0)
        from ui.widgets import icon_label
        i_lay.addWidget(icon_label("list", 20, FG_MUTED), alignment=Qt.AlignCenter)
        lay.addWidget(icon_w, alignment=Qt.AlignHCenter)

        t = QLabel("Queue is empty")
        t.setStyleSheet(f"font-size:13px; font-weight:500; color:{FG};")
        t.setAlignment(Qt.AlignHCenter)
        lay.addWidget(t)

        sub = QLabel("Add a YouTube playlist to begin.")
        sub.setStyleSheet(f"font-size:11px; color:{FG_MUTED};")
        sub.setAlignment(Qt.AlignHCenter)
        sub.setWordWrap(True)
        lay.addWidget(sub)
