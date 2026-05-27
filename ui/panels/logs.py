from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from ui.theme import (
    PRIMARY, FG, FG_MUTED, FG_SUBTLE, BG, BG_MUTED, BG_SUBTLE, BORDER,
    ERROR_BG, ERROR_DARK, WARN_BG, WARN_DARK,
)
from ui.widgets import Toggle, icon_pixmap
from backend.mock_data import MOCK_LOGS
from backend.models import LogEntry

LOG_LEVELS = ["error", "warn", "info", "debug"]

LEVEL_STYLE = {
    "error": (ERROR_BG,  ERROR_DARK),
    "warn":  (WARN_BG,   WARN_DARK),
    "info":  ("#E8ECF2", FG_SUBTLE),
    "debug": ("#F1F5F9", FG_MUTED),
}


class LogsPanel(QWidget):
    send_diagnostics_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._levels = {"error": True, "warn": True, "info": True, "debug": False}
        self._expanded: set[int] = {
            i for i, l in enumerate(MOCK_LOGS) if l.lvl == "error"
        }
        self._auto_scroll = True
        self._query = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet(f"background:#FAFBFC;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._list_widget)
        root.addWidget(self._scroll)

        root.addWidget(self._build_footer())
        self._rebuild()

    def _build_toolbar(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(44)
        w.setStyleSheet(
            f"background:{BG_SUBTLE}; border-bottom:1px solid {BORDER};"
        )
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)

        filter_lbl = QLabel("FILTER")
        filter_lbl.setStyleSheet(
            f"font-size:10px; color:{FG_MUTED}; font-weight:600; letter-spacing:.06em;"
        )
        lay.addWidget(filter_lbl)

        self._level_btns: dict[str, QPushButton] = {}
        counts = {}
        for l in MOCK_LOGS:
            counts[l.lvl] = counts.get(l.lvl, 0) + 1

        for lvl in LOG_LEVELS:
            bg, fg = LEVEL_STYLE[lvl]
            btn = QPushButton(f"{lvl.capitalize()}  {counts.get(lvl, 0)}")
            btn.setCheckable(True)
            btn.setChecked(self._levels[lvl])
            btn.setFixedHeight(24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._level_btn_style(lvl, self._levels[lvl]))
            btn.toggled.connect(lambda checked, l=lvl: self._toggle_level(l, checked))
            self._level_btns[lvl] = btn
            lay.addWidget(btn)

        lay.addStretch()

        self._auto_toggle = Toggle(self._auto_scroll)
        self._auto_toggle.toggled.connect(self._on_auto_scroll)
        auto_lbl = QLabel("Auto-scroll")
        auto_lbl.setStyleSheet(f"font-size:11px; color:{FG_MUTED};")
        lay.addWidget(auto_lbl)
        lay.addWidget(self._auto_toggle)

        sep = QWidget()
        sep.setFixedSize(1, 18)
        sep.setStyleSheet(f"background:{BORDER};")
        lay.addWidget(sep)

        diag_btn = QPushButton("  Send diagnostics")
        diag_btn.setIcon(QIcon(icon_pixmap("send", 12, "#fff")))
        diag_btn.setFixedHeight(26)
        diag_btn.setCursor(Qt.PointingHandCursor)
        diag_btn.setStyleSheet(f"""
            QPushButton {{
                background:{PRIMARY}; color:#fff; border:none;
                border-radius:5px; font-size:11px; font-weight:500; padding:0 10px;
            }}
            QPushButton:hover {{ background:#0039D9; }}
        """)
        diag_btn.clicked.connect(self.send_diagnostics_clicked)
        lay.addWidget(diag_btn)

        open_btn = QPushButton("  Open log file")
        open_btn.setIcon(QIcon(icon_pixmap("folder", 12, FG_MUTED)))
        open_btn.setFixedHeight(26)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG}; color:{FG}; border:1px solid {BORDER};
                border-radius:5px; font-size:11px; padding:0 10px;
            }}
            QPushButton:hover {{ background:{BG_SUBTLE}; }}
        """)
        lay.addWidget(open_btn)
        return w

    def _level_btn_style(self, lvl: str, on: bool) -> str:
        bg, fg = LEVEL_STYLE[lvl]
        if on:
            return (
                f"QPushButton {{ background:{bg}; color:{fg}; border:none; "
                f"border-radius:99px; font-size:11px; font-weight:500; padding:0 8px; }}"
            )
        return (
            f"QPushButton {{ background:{BG}; color:{FG_MUTED}; border:1px solid {BORDER}; "
            f"border-radius:99px; font-size:11px; padding:0 8px; opacity:0.6; }}"
        )

    def _toggle_level(self, lvl: str, checked: bool):
        self._levels[lvl] = checked
        self._level_btns[lvl].setStyleSheet(self._level_btn_style(lvl, checked))
        self._rebuild()

    def _on_auto_scroll(self, val: bool):
        self._auto_scroll = val
        if val:
            sb = self._scroll.verticalScrollBar()
            sb.setValue(sb.maximum())

    def set_query(self, q: str):
        self._query = q.lower()
        self._rebuild()

    def _rebuild(self):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        q = self._query
        filtered = [
            (i, l) for i, l in enumerate(MOCK_LOGS)
            if self._levels.get(l.lvl, True)
            and (not q or q in (l.msg + " " + l.src).lower())
        ]

        if not filtered:
            empty = QLabel("No log entries match the current filter.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"font-size:13px; color:{FG_MUTED}; padding:40px; "
                f"font-family:inherit;"
            )
            self._list_layout.insertWidget(0, empty)
        else:
            for pos, (orig_idx, entry) in enumerate(filtered):
                row = _LogRow(entry, orig_idx, orig_idx in self._expanded)
                row.toggle_requested.connect(
                    lambda _, idx=orig_idx: self._toggle_detail(idx)
                )
                self._list_layout.insertWidget(pos, row)

        if self._auto_scroll:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()
            ))

        self._update_footer(filtered)

    def _toggle_detail(self, idx: int):
        if idx in self._expanded:
            self._expanded.discard(idx)
        else:
            self._expanded.add(idx)
        self._rebuild()

    def _update_footer(self, filtered):
        if hasattr(self, "_footer_count"):
            self._footer_count.setText(
                f"{len(filtered)} of {len(MOCK_LOGS)} entries shown"
            )

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(30)
        w.setStyleSheet(
            f"background:{BG_MUTED}; border-top:1px solid {BORDER};"
        )
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(14)

        path_lbl = QLabel("~/.anees/logs/run-048.log")
        path_lbl.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; font-family:'JetBrains Mono',monospace;"
        )
        lay.addWidget(path_lbl)

        dot = QLabel("·")
        dot.setStyleSheet(f"font-size:11px; color:{FG_MUTED};")
        lay.addWidget(dot)

        self._footer_count = QLabel(f"0 of {len(MOCK_LOGS)} entries shown")
        self._footer_count.setStyleSheet(
            f"font-size:11px; color:{FG_MUTED}; font-family:'JetBrains Mono',monospace;"
        )
        lay.addWidget(self._footer_count)

        lay.addStretch()

        err_count = sum(1 for l in MOCK_LOGS if l.lvl == "error")
        warn_count = sum(1 for l in MOCK_LOGS if l.lvl == "warn")
        err_lbl = QLabel(f"{err_count} errors")
        err_lbl.setStyleSheet(
            f"font-size:11px; color:{ERROR_DARK}; font-family:'JetBrains Mono',monospace;"
        )
        lay.addWidget(err_lbl)

        dot2 = QLabel("·")
        dot2.setStyleSheet(f"font-size:11px; color:{FG_MUTED};")
        lay.addWidget(dot2)

        warn_lbl = QLabel(f"{warn_count} warnings")
        warn_lbl.setStyleSheet(
            f"font-size:11px; color:{WARN_DARK}; font-family:'JetBrains Mono',monospace;"
        )
        lay.addWidget(warn_lbl)
        return w


class _LogRow(QWidget):
    toggle_requested = Signal()

    def __init__(self, entry: LogEntry, orig_idx: int, expanded: bool, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._expanded = expanded
        self._has_detail = bool(entry.detail)

        bg, fg = LEVEL_STYLE[entry.lvl]
        is_err = entry.lvl == "error"
        is_warn = entry.lvl == "warn"

        row_bg = "rgba(239,68,68,0.04)" if is_err else (
            "rgba(245,158,11,0.04)" if is_warn else "transparent"
        )
        self.setStyleSheet(
            f"background:{row_bg}; border-bottom:1px solid #EAECF0;"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # main row
        main_row = QWidget()
        if self._has_detail:
            main_row.setCursor(Qt.PointingHandCursor)
            main_row.mousePressEvent = lambda e: self.toggle_requested.emit()
        main_lay = QHBoxLayout(main_row)
        main_lay.setContentsMargins(16, 5, 16, 5)
        main_lay.setSpacing(8)

        # expand indicator
        if self._has_detail:
            icon_key = "chev_down" if expanded else "chev_right"
            ind = QLabel()
            ind.setPixmap(icon_pixmap(icon_key, 10, FG_MUTED))
            ind.setFixedWidth(14)
        else:
            ind = QWidget()
            ind.setFixedWidth(14)
        main_lay.addWidget(ind)

        # timestamp
        ts = QLabel(entry.t)
        ts.setFixedWidth(100)
        ts.setStyleSheet(
            f"font-size:11.5px; color:{FG_MUTED}; font-family:'JetBrains Mono',monospace;"
        )
        main_lay.addWidget(ts)

        # level badge
        lvl_badge = QLabel(entry.lvl.upper())
        lvl_badge.setFixedWidth(56)
        lvl_badge.setAlignment(Qt.AlignCenter)
        lvl_badge.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:3px; "
            f"font-size:9.5px; font-weight:700; letter-spacing:.04em; "
            f"font-family:'JetBrains Mono',monospace; padding:1px 0;"
        )
        main_lay.addWidget(lvl_badge)

        # source
        src = QLabel(entry.src)
        src.setFixedWidth(80)
        src.setStyleSheet(
            f"font-size:11.5px; color:{FG_SUBTLE}; font-family:'JetBrains Mono',monospace;"
        )
        main_lay.addWidget(src)

        # message
        msg_color = ERROR_DARK if is_err else (WARN_DARK if is_warn else FG)
        msg_weight = "500" if is_err else "400"
        msg_text = entry.msg
        if entry.code:
            msg_text += f"  · {entry.code}"
        msg = QLabel(msg_text)
        msg.setStyleSheet(
            f"font-size:11.5px; color:{msg_color}; font-weight:{msg_weight}; "
            f"font-family:'JetBrains Mono',monospace;"
        )
        main_lay.addWidget(msg, 1)
        root.addWidget(main_row)

        # detail block
        if expanded and self._has_detail:
            detail = QLabel(entry.detail)
            detail.setStyleSheet(
                f"background:#0E142C; color:rgba(255,255,255,0.78); "
                f"font-size:10.5px; font-family:'JetBrains Mono',monospace; "
                f"line-height:1.7; padding:8px 16px 12px 16px; "
                f"border-left:2px solid #EF4444;"
            )
            detail.setWordWrap(True)
            detail.setContentsMargins(138, 0, 0, 0)
            root.addWidget(detail)
