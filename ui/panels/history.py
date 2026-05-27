from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, FG, FG_MUTED, FG_SUBTLE, BG, BG_MUTED, BG_SUBTLE, BORDER,
    SUCCESS, SUCCESS_BG, SUCCESS_DARK, ERROR_BG, ERROR_DARK,
)
from ui.widgets import Badge, icon_pixmap, icon_label
from backend.mock_data import MOCK_HISTORY
from backend.models import HistoryRun


class HistoryPanel(QWidget):
    rerun_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded: set[str] = {"run-047"}
        self._query = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_summary())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(18, 14, 18, 14)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_widget)
        root.addWidget(scroll)

        self._rebuild()

    def _build_summary(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(62)
        w.setStyleSheet(f"background:{BG}; border-bottom:1px solid {BORDER};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(24)

        totals = {
            "runs": len(MOCK_HISTORY),
            "videos": sum(r.video_count for r in MOCK_HISTORY),
            "size_gb": sum(r.size_mb for r in MOCK_HISTORY) / 1024,
        }
        for label, value in [
            ("Total runs", str(totals["runs"])),
            ("Videos processed", str(totals["videos"])),
            ("Total size", f"{totals['size_gb']:.1f} GB"),
        ]:
            col = QWidget()
            col_lay = QVBoxLayout(col)
            col_lay.setContentsMargins(0, 0, 0, 0)
            col_lay.setSpacing(2)
            lbl = QLabel(label.upper())
            lbl.setStyleSheet(
                f"font-size:10px; color:{FG_MUTED}; letter-spacing:.04em; font-weight:500;"
            )
            val = QLabel(value)
            val.setStyleSheet(f"font-size:18px; font-weight:600; color:{FG};")
            col_lay.addWidget(lbl)
            col_lay.addWidget(val)
            lay.addWidget(col)

        lay.addStretch()

        # CSV badge
        csv_w = QWidget()
        csv_w.setStyleSheet(
            f"background:{BG_SUBTLE}; border-radius:6px; padding:4px 0px;"
        )
        csv_lay = QHBoxLayout(csv_w)
        csv_lay.setContentsMargins(10, 6, 10, 6)
        csv_lay.setSpacing(8)
        csv_lbl = QLabel("~/.anees/history.csv")
        csv_lbl.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; font-family:'JetBrains Mono',monospace;"
        )
        csv_lay.addWidget(csv_lbl)

        sep = QWidget()
        sep.setFixedSize(1, 14)
        sep.setStyleSheet(f"background:{BORDER};")
        csv_lay.addWidget(sep)

        open_btn = QPushButton("Open CSV")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; color:{PRIMARY}; font-size:11px; }}"
        )
        csv_lay.addWidget(open_btn)

        sep2 = QWidget()
        sep2.setFixedSize(1, 14)
        sep2.setStyleSheet(f"background:{BORDER};")
        csv_lay.addWidget(sep2)

        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; color:{FG_MUTED}; font-size:11px; }}"
        )
        csv_lay.addWidget(clear_btn)
        lay.addWidget(csv_w)
        return w

    def set_query(self, q: str):
        self._query = q.lower()
        self._rebuild()

    def _rebuild(self):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        q = self._query
        runs = [
            r for r in MOCK_HISTORY
            if not q or q in r.started_at.lower()
            or any(q in p.title.lower() for p in r.playlists)
        ]

        for i, run in enumerate(runs):
            row = _HistoryRow(run, run.id in self._expanded)
            row.toggle_requested.connect(lambda _, rid=run.id: self._toggle(rid))
            row.rerun_requested.connect(self.rerun_requested)
            self._list_layout.insertWidget(i, row)

        if not runs:
            empty = QLabel("No matching history entries.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"font-size:13px; color:{FG_MUTED}; padding:40px;")
            self._list_layout.insertWidget(0, empty)

    def _toggle(self, run_id: str):
        if run_id in self._expanded:
            self._expanded.discard(run_id)
        else:
            self._expanded.add(run_id)
        self._rebuild()


class _HistoryRow(QWidget):
    toggle_requested = Signal()
    rerun_requested = Signal()

    def __init__(self, run: HistoryRun, expanded: bool, parent=None):
        super().__init__(parent)
        self._run = run
        self._expanded = expanded
        self.setStyleSheet(
            f"background:{BG}; border:1px solid {BORDER}; border-radius:8px;"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        if expanded:
            root.addWidget(self._build_detail())

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(14)

        # run number badge
        num_lbl = QLabel(f"#{str(self._run.num).zfill(3)}")
        num_lbl.setFixedWidth(64)
        num_lbl.setAlignment(Qt.AlignCenter)
        num_lbl.setStyleSheet(
            f"background:{BG_SUBTLE}; border-radius:4px; padding:4px 10px; "
            f"font-family:'JetBrains Mono',monospace; font-size:12px; "
            f"font-weight:700; color:{FG_SUBTLE};"
        )
        lay.addWidget(num_lbl)

        # date + badges
        mid = QWidget()
        mid_lay = QVBoxLayout(mid)
        mid_lay.setContentsMargins(0, 0, 0, 0)
        mid_lay.setSpacing(4)

        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(8)
        date_lbl = QLabel(self._run.started_at)
        date_lbl.setStyleSheet(f"font-size:13px; font-weight:500; color:{FG};")
        top_lay.addWidget(date_lbl)

        if self._run.status == "success":
            badge = Badge("Complete", "success")
            top_lay.addWidget(badge)
        elif self._run.status == "partial":
            badge = Badge("Partial", "queued")
            top_lay.addWidget(badge)

        if self._run.merged:
            mbadge = Badge("Merged", "primary")
            top_lay.addWidget(mbadge)

        top_lay.addStretch()
        mid_lay.addWidget(top)

        path_lbl = QLabel(self._run.output_path)
        path_lbl.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; font-family:'JetBrains Mono',monospace;"
        )
        path_lbl.setMaximumWidth(400)
        mid_lay.addWidget(path_lbl)
        lay.addWidget(mid, 1)

        # stats
        for label, value in [
            (str(self._run.playlist_count), "playlists"),
            (str(self._run.video_count), "videos"),
            (f"{self._run.size_mb/1024:.2f} GB", "size"),
            (f"{self._run.duration_min}m", "duration"),
        ]:
            col = QWidget()
            col_lay = QVBoxLayout(col)
            col_lay.setContentsMargins(0, 0, 0, 0)
            col_lay.setSpacing(1)
            val = QLabel(value)
            val.setAlignment(Qt.AlignRight)
            val.setStyleSheet(f"font-size:13px; font-weight:600; color:{FG};")
            lbl = QLabel(label.upper())
            lbl.setAlignment(Qt.AlignRight)
            lbl.setStyleSheet(
                f"font-size:10px; color:{FG_MUTED}; letter-spacing:.04em;"
            )
            col_lay.addWidget(val)
            col_lay.addWidget(lbl)
            lay.addWidget(col)

        # action buttons
        btns = QWidget()
        btns_lay = QHBoxLayout(btns)
        btns_lay.setContentsMargins(0, 0, 0, 0)
        btns_lay.setSpacing(4)

        folder_btn = self._icon_btn("folder", "Open output folder")
        btns_lay.addWidget(folder_btn)

        rerun_btn = self._icon_btn("refresh", "Re-run with same playlists")
        rerun_btn.clicked.connect(self.rerun_requested)
        btns_lay.addWidget(rerun_btn)

        expand_icon = "chev_down" if self._expanded else "chev_right"
        toggle_btn = self._icon_btn(expand_icon, "Toggle details", border=False)
        toggle_btn.clicked.connect(self.toggle_requested)
        btns_lay.addWidget(toggle_btn)
        lay.addWidget(btns)

        w.mousePressEvent = lambda e: self.toggle_requested.emit()
        return w

    def _icon_btn(self, icon: str, tooltip: str, border: bool = True) -> QPushButton:
        btn = QPushButton()
        btn.setIcon(QIcon(icon_pixmap(icon, 13, FG_MUTED)))
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(tooltip)
        border_style = f"border:1px solid {BORDER};" if border else "border:none;"
        btn.setStyleSheet(
            f"QPushButton {{ background:{BG}; {border_style} border-radius:6px; }}"
            f"QPushButton:hover {{ background:{BG_SUBTLE}; }}"
        )
        return btn

    def _build_detail(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background:{BG_SUBTLE}; border-top:1px solid {BORDER};"
        )
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # column header
        hdr = QWidget()
        hdr.setStyleSheet(f"border-bottom:1px solid {BORDER};")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(14, 8, 14, 8)
        hdr_lay.setSpacing(10)
        for text, stretch, align in [
            ("#", 0, Qt.AlignLeft),
            ("Playlist", 1, Qt.AlignLeft),
            ("Videos", 0, Qt.AlignRight),
            ("Size", 0, Qt.AlignRight),
            ("Speed", 0, Qt.AlignRight),
        ]:
            lbl = QLabel(text.upper())
            lbl.setStyleSheet(
                f"font-size:10px; color:{FG_MUTED}; font-weight:500; letter-spacing:.04em;"
            )
            lbl.setAlignment(align)
            if not stretch:
                lbl.setFixedWidth(60)
            hdr_lay.addWidget(lbl, stretch)
        lay.addWidget(hdr)

        for i, p in enumerate(self._run.playlists):
            row = QWidget()
            border_bottom = (
                f"border-bottom:1px solid #EAECF0;"
                if i < len(self._run.playlists) - 1
                else ""
            )
            row.setStyleSheet(f"background:{BG}; {border_bottom}")
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(14, 8, 14, 8)
            row_lay.setSpacing(10)

            pfx = QLabel(p.prefix)
            pfx.setFixedWidth(60)
            pfx.setStyleSheet(
                f"font-family:'JetBrains Mono',monospace; font-size:11px; "
                f"font-weight:600; color:{FG_MUTED};"
            )
            row_lay.addWidget(pfx)

            title = QLabel(p.title)
            title.setStyleSheet(f"font-size:12px; color:{FG};")
            title.setMaximumWidth(400)
            row_lay.addWidget(title, 1)

            for value in [str(p.videos), f"{p.size_mb:.1f} MB", f"{p.speed}×"]:
                lbl = QLabel(value)
                lbl.setFixedWidth(60)
                lbl.setAlignment(Qt.AlignRight)
                lbl.setStyleSheet(f"font-size:12px; color:{FG_MUTED};")
                row_lay.addWidget(lbl)

            lay.addWidget(row)

        return w
