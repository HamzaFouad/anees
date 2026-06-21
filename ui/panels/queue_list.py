from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import QMimeData
from PySide6.QtGui import QIcon, QDrag, QPainter, QColor, QPen

from ui.theme import (
    PRIMARY, PRIMARY_TINT_8, FG, FG_MUTED, BG, BG_MUTED, BG_SUBTLE, BORDER, ROW_DIVIDER,
    DISABLED_BG, DISABLED_FG, INACTIVE,
    SUCCESS, SUCCESS_BG, SUCCESS_DARK, ERROR, ERROR_DARK, TEXT_MD,
    WARN_BG, WARN_DARK,
)
from ui.widgets import Btn, Chip, SlimProgressBar, icon_pixmap, status_dot, EmptyState
from ui.state import AppState
from backend.models import Playlist, RunState


class QueueList(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setFixedWidth(280)
        self.setStyleSheet(f"background:{BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header
        self._header = QWidget()
        self._header.setFixedHeight(34)
        self._header.setStyleSheet(f"background:{BG};")
        h_lay = QHBoxLayout(self._header)
        h_lay.setContentsMargins(16, 0, 10, 0)
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(
            f"font-size:11px; font-weight:700; color:{FG_MUTED}; "
            f"letter-spacing:0.1em; text-transform:uppercase;"
        )
        h_lay.addWidget(self._count_lbl)
        h_lay.addStretch()
        self._hint_lbl = QLabel("drag to reorder")
        self._hint_lbl.setStyleSheet(
            f"font-size:11px; color:#A6B0BF;"
        )
        h_lay.addWidget(self._hint_lbl)
        root.addWidget(self._header)

        # scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background:{BG}; border:none; }}")
        self._list_widget = _DroppableList()
        self._list_widget.setStyleSheet(f"background:{BG};")
        self._list_widget.reorder_requested.connect(
            lambda pid, idx: self._api.reorder(pid, idx)
        )
        self._list_widget.drag_ended.connect(self._on_drag_ended)
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_widget)
        scroll.viewport().setStyleSheet(f"background:{BG};")
        root.addWidget(scroll)

        # footer add button
        footer = QWidget()
        footer.setObjectName("SidebarFooter")
        footer.setFixedHeight(52)
        footer.setStyleSheet(
            f"#SidebarFooter {{ background:{BG}; border-top:1px solid {BORDER}; }}"
        )
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(10, 7, 10, 7)
        self._add_btn = QPushButton("  Add playlist")
        self._add_btn.setIcon(QIcon(icon_pixmap("plus", 13, PRIMARY)))
        self._add_btn.setFixedHeight(38)
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{PRIMARY};
                border:1px dashed #BFD0FF; border-radius:8px;
                font-size:12px; font-weight:600;
            }}
            QPushButton:hover {{ background:{BG_SUBTLE}; }}
            QPushButton:disabled {{
                background:{DISABLED_BG}; color:{DISABLED_FG};
                border:1px dashed {BORDER};
            }}
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
        if locked:
            self._add_btn.setIcon(QIcon(icon_pixmap("plus", 13, DISABLED_FG)))
            self._add_btn.setText("  Locked while running")
        else:
            self._add_btn.setIcon(QIcon(icon_pixmap("plus", 13, PRIMARY)))
            self._add_btn.setText("  Add playlist")
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
            empty = EmptyState("list", "Queue is empty", "Add YouTube playlists to begin.")
            self._list_layout.insertWidget(0, empty)
        else:
            for i, pl in enumerate(pls):
                row = PlaylistRow(pl, pl.id == self._state.selected_id, self._state.locked)
                row.selected.connect(lambda _, pid=pl.id: self._api.select(pid))
                row.remove_clicked.connect(lambda _, pid=pl.id: self._api.remove(pid))
                self._list_layout.insertWidget(i, row)


    def _refresh_selection(self, pid: str):
        for i in range(self._list_layout.count()):
            w = self._list_layout.itemAt(i).widget()
            if isinstance(w, PlaylistRow):
                w.set_selected(w._pl.id == pid)


def _status_chip(status: str, run_state: str) -> Chip:
    if run_state == "paused":
        return Chip("Paused", WARN_BG, WARN_DARK, dot="#F59E0B")
    elif status == "active":
        return Chip("Running", PRIMARY_TINT_8, PRIMARY, dot=PRIMARY)
    elif status == "done":
        return Chip("Done", SUCCESS_BG, SUCCESS_DARK, dot=SUCCESS)
    else:
        return Chip("Queued", BG_SUBTLE, FG_MUTED, dot=INACTIVE)


class PlaylistRow(QWidget):
    selected       = Signal(bool)
    remove_clicked = Signal(bool)

    def __init__(self, pl: Playlist, is_selected: bool, locked: bool, parent=None):
        super().__init__(parent)
        self._pl         = pl
        self._selected   = is_selected
        self._locked     = locked
        self._drag_start = None
        self.setCursor(Qt.PointingHandCursor)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(2, 0, 6, 0)   # 2px left = painted accent space
        outer.setSpacing(0)

        self._main = QWidget()
        self._main.setStyleSheet("background:transparent;")
        m_lay = QVBoxLayout(self._main)
        m_lay.setContentsMargins(10, 10, 0, 11)
        m_lay.setSpacing(6)

        # ── Row A: status chip + title ──────────────────────────────────────────
        row_a = QWidget()
        row_a.setStyleSheet("background:transparent;")
        ra_lay = QHBoxLayout(row_a)
        ra_lay.setContentsMargins(0, 0, 0, 0)
        ra_lay.setSpacing(8)
        ra_lay.addWidget(_status_chip(pl.status, pl.run_state))
        title_lbl = QLabel(pl.title)
        title_lbl.setStyleSheet(
            f"font-size:12px; font-weight:600; color:{FG}; background:transparent; border:none;"
        )
        title_lbl.setMaximumWidth(155)
        ra_lay.addWidget(title_lbl, 1)
        m_lay.addWidget(row_a)

        # ── Row B: config meta  ·  [start:end]  ···  count ─────────────────────
        failed_count = sum(1 for v in pl.videos if v.stage == "failed")
        has_failures = failed_count > 0 and pl.status == "done"

        row_b = QWidget()
        row_b.setStyleSheet("background:transparent;")
        rb_lay = QHBoxLayout(row_b)
        rb_lay.setContentsMargins(0, 0, 0, 0)
        rb_lay.setSpacing(0)

        speed_str = f"×{pl.speed}" if pl.speed != 1.0 else "×1"
        split_str = f"/{pl.split_min}m" if pl.split_enabled else "no split"
        has_range = pl.range_start is not None or pl.range_end is not None
        range_str = f"[{pl.range_start or 1}:{pl.range_end}]" if has_range else ""
        meta = "  ·  ".join(filter(None, [pl.prefix, speed_str, split_str, range_str]))

        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; "
            f"font-family:'JetBrains Mono',monospace; background:transparent; border:none;"
        )
        rb_lay.addWidget(meta_lbl)
        rb_lay.addStretch()

        cnt_text = (
            f"{pl.completed}/{pl.video_count} · {failed_count}✗"
            if has_failures else f"{pl.completed}/{pl.video_count}"
        )
        cnt_lbl = QLabel(cnt_text)
        cnt_lbl.setStyleSheet(
            f"font-size:10px; color:{ERROR_DARK if has_failures else FG_MUTED}; "
            f"font-family:'JetBrains Mono',monospace; background:transparent; border:none;"
        )
        rb_lay.addWidget(cnt_lbl)
        m_lay.addWidget(row_b)

        # ── Row C: progress bar + percentage ───────────────────────────────────
        row_c = QWidget()
        row_c.setStyleSheet("background:transparent;")
        rc_lay = QHBoxLayout(row_c)
        rc_lay.setContentsMargins(0, 0, 0, 0)
        rc_lay.setSpacing(6)

        if has_failures:
            bar_color, pct_color = ERROR, ERROR_DARK
        elif pl.status == "done":
            bar_color, pct_color = SUCCESS, SUCCESS
        elif pl.run_state == "paused":
            bar_color, pct_color = "#F59E0B", "#F59E0B"
        else:
            bar_color, pct_color = PRIMARY, FG_MUTED

        bar = SlimProgressBar(color=bar_color, bar_height=3)
        bar.set_value(pl.completed, pl.video_count)
        rc_lay.addWidget(bar, 1)

        pct = int(pl.completed / pl.video_count * 100) if pl.video_count > 0 else 0
        pct_lbl = QLabel(f"{pct}%")
        pct_lbl.setFixedWidth(30)
        pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pct_lbl.setStyleSheet(
            f"font-size:10px; font-weight:700; color:{pct_color}; "
            f"background:transparent; border:none;"
        )
        rc_lay.addWidget(pct_lbl)
        m_lay.addWidget(row_c)

        outer.addWidget(self._main, 1)

        # remove button — always visible so layout width never shifts
        if not locked:
            self._rm_btn = QPushButton()
            self._rm_btn.setIcon(QIcon(icon_pixmap("x", 12, FG_MUTED)))
            self._rm_btn.setFixedSize(24, 24)
            self._rm_btn.setCursor(Qt.PointingHandCursor)
            self._rm_btn.setStyleSheet(
                "QPushButton { background:transparent; border:none; border-radius:4px; }"
                "QPushButton:hover { background:#E5E7EB; }"
            )
            self._rm_btn.clicked.connect(self.remove_clicked)
            outer.addWidget(self._rm_btn)

    # ── Paint (selected state only — no hover) ────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#F5F7FF" if self._selected else BG))
        if self._selected:
            painter.fillRect(0, 0, 2, self.height(), QColor(PRIMARY))
        painter.setPen(QPen(QColor(ROW_DIVIDER), 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

    # ── Mouse ─────────────────────────────────────────────────────────────────
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
        self._drag_start = None
        drag = QDrag(self.window())
        mime = QMimeData()
        mime.setText(self._pl.id)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(start)
        drag.exec(Qt.MoveAction)

    def set_selected(self, sel: bool):
        self._selected = sel
        self.update()


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
