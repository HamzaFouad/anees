from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import QMimeData
from PySide6.QtGui import QIcon, QDrag, QPainter, QColor, QPen

from ui.theme import (
    PRIMARY, PRIMARY_TINT_8, FG, FG_MUTED, BG, BG_MUTED, BG_SUBTLE, BORDER,
    DISABLED_BG, DISABLED_FG, INACTIVE,
    SUCCESS, ERROR, ERROR_DARK, TEXT_MD,
)
from ui.widgets import Btn, SlimProgressBar, icon_pixmap, status_dot, EmptyState
from ui.state import AppState
from backend.models import Playlist, RunState


class QueueList(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setFixedWidth(280)
        self.setStyleSheet(f"background:{BG_SUBTLE};")

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
        self._list_widget = _DroppableList()
        self._list_widget.setStyleSheet(f"background:{BG_SUBTLE};")
        self._list_widget.reorder_requested.connect(
            lambda pid, idx: self._api.reorder(pid, idx)
        )
        self._list_widget.drag_ended.connect(self._on_drag_ended)
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
            QPushButton:disabled {{ background:{DISABLED_BG}; color:{DISABLED_FG}; }}
        """)
        f_lay.addWidget(self._add_btn)
        root.addWidget(footer)

        self._rebuild_pending = False

        self._add_btn.clicked.connect(self._on_add)
        state.playlists_changed.connect(self._rebuild)
        state.selection_changed.connect(self._refresh_selection)
        state.run_state_changed.connect(self._on_run_state)
        state.query_changed.connect(self._rebuild)
        from ui.api import QueueAPI
        self._api = QueueAPI(state)
        self._rebuild()

    def _on_drag_ended(self):
        if self._rebuild_pending:
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
        # defer if any row is mid-drag; the drop/release will trigger a rebuild anyway
        if any(isinstance(self._list_layout.itemAt(i).widget(), PlaylistRow)
               and self._list_layout.itemAt(i).widget()._drag_start is not None
               for i in range(self._list_layout.count())
               if self._list_layout.itemAt(i).widget()):
            self._rebuild_pending = True
            return
        self._rebuild_pending = False

        # remove old rows (except stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        q = self._state.query.lower()
        pls = [p for p in self._state.playlists if not q or q in p.title.lower()]
        self._count_lbl.setText(f"Playlists ({len(pls)})")

        if not pls:
            empty = EmptyState("list", "Queue is empty", "Add a YouTube playlist to begin.")
            self._list_layout.insertWidget(0, empty)
        else:
            for i, pl in enumerate(pls):
                row = PlaylistRow(pl, pl.id == self._state.selected_id, self._state.locked)
                row.selected.connect(lambda _, pid=pl.id: self._api.select(pid))
                row.remove_clicked.connect(lambda _, pid=pl.id: self._api.remove(pid))
                self._list_layout.insertWidget(i, row)

        # update add button style
        has_items = bool(self._state.playlists)
        from ui.theme import PRIMARY_HOVER, ON_PRIMARY
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY if not has_items else BG};
                color:{ON_PRIMARY if not has_items else FG};
                border:{'none' if not has_items else f'1px solid {BORDER}'};
                border-radius:6px; font-size:{TEXT_MD}px; font-weight:500;
            }}
            QPushButton:hover {{ background:{PRIMARY_HOVER if not has_items else BG_MUTED}; }}
            QPushButton:disabled {{ background:{DISABLED_BG}; color:{DISABLED_FG}; }}
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
        self._drag_start = None   # QPoint | None; cleared after every drag
        self.setCursor(Qt.PointingHandCursor)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # main clickable area
        self._main = QWidget()
        self._main.setCursor(Qt.PointingHandCursor)

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

        failed_count = sum(1 for v in pl.videos if v.stage == "failed")
        has_failures = failed_count > 0 and pl.status == "done"
        dot_color = ERROR if has_failures else (SUCCESS if pl.status == "done" else (PRIMARY if pl.status == "active" else INACTIVE))
        top_lay.addWidget(status_dot(dot_color))

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
            color=ERROR if has_failures else (SUCCESS if pl.status == "done" else PRIMARY),
            bar_height=3,
        )
        bar.set_value(pl.completed, pl.video_count)
        bot_lay.addWidget(bar, 1)
        cnt_text = f"{pl.completed}/{pl.video_count}" + (f" · {failed_count} failed" if has_failures else "")
        cnt = QLabel(cnt_text)
        cnt.setStyleSheet(
            f"font-size:10px; color:{ERROR_DARK if has_failures else FG_MUTED}; "
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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
            self.selected.emit(True)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self._locked:
            return
        if self._drag_start is None:
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 12:
            return
        start = self._drag_start
        self._drag_start = None   # clear before exec so stale point never lingers

        # Parent the QDrag on the window, not on self. If _rebuild() fires during
        # drag.exec() (e.g. a video completes) it calls deleteLater() on this row,
        # which would also destroy a self-parented QDrag mid-flight and crash.
        drag = QDrag(self.window())
        mime = QMimeData()
        mime.setText(self._pl.id)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(start)
        drag.exec(Qt.MoveAction)

    def set_selected(self, sel: bool):
        self._selected = sel
        self._apply_style()

    def _apply_style(self):
        if self._selected:
            self.setStyleSheet(
                f"background:{PRIMARY_TINT_8}; border:none; border-left:2px solid {PRIMARY};"
            )
        else:
            self.setStyleSheet(f"background:{BG_SUBTLE}; border:none;")
        self._main.setStyleSheet("background:transparent; border:none;")

    def enterEvent(self, event):
        if not self._selected:
            self.setStyleSheet(f"background:{BG_MUTED}; border:none;")
        if not self._locked and hasattr(self, "_rm_btn"):
            self._rm_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style()
        if not self._locked and hasattr(self, "_rm_btn"):
            self._rm_btn.setVisible(False)
        super().leaveEvent(event)


class _DroppableList(QWidget):
    """Inner list widget that accepts playlist drag-drops and shows a drop indicator."""
    reorder_requested = Signal(str, int)   # playlist_id, target_index
    drag_ended = Signal()                  # emitted when drag leaves or drops

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._drop_idx = -1

    # ── drag/drop events ──────────────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            self._drop_idx = self._index_at(int(event.position().y()))
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._drop_idx = -1
        self.update()
        self.drag_ended.emit()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            pid = event.mimeData().text()
            idx = self._index_at(int(event.position().y()))
            self._drop_idx = -1
            self.update()
            self.reorder_requested.emit(pid, idx)
            self.drag_ended.emit()
            event.acceptProposedAction()

    # ── drop indicator ────────────────────────────────────────────────────────
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_idx < 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(PRIMARY), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        y = self._indicator_y(self._drop_idx)
        p.drawLine(4, y, self.width() - 4, y)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _row_widgets(self) -> list[QWidget]:
        lay = self.layout()
        rows = []
        for i in range(lay.count()):
            item = lay.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), PlaylistRow):
                rows.append(item.widget())
        return rows

    def _index_at(self, y: int) -> int:
        for i, w in enumerate(self._row_widgets()):
            if y < w.y() + w.height() // 2:
                return i
        return len(self._row_widgets())

    def _indicator_y(self, idx: int) -> int:
        rows = self._row_widgets()
        if not rows:
            return 0
        if idx >= len(rows):
            w = rows[-1]
            return w.y() + w.height()
        return rows[idx].y()
