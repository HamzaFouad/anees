from __future__ import annotations
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QFrame
from PySide6.QtCore import Qt

from ui.theme import PRIMARY, PRIMARY_TINT_8, BORDER, PIPELINE_STAGES
from ui.components.chip import Chip


class PipelineStrip(QWidget):
    def __init__(self, active_stage: str = "download",
                 split_enabled: bool = True, compact: bool = False,
                 running: bool = False,
                 stage_counts: dict | None = None,
                 speed_enabled: bool = True,
                 parent=None):
        super().__init__(parent)
        self._active       = active_stage
        self._split        = split_enabled
        self._speed        = speed_enabled
        self._compact      = compact
        self._running      = running
        self._counts       = stage_counts or {}
        self._count_labels: dict[str, QLabel] = {}
        self._build()

    def _stage_index(self, key: str) -> int:
        for i, (k, *_) in enumerate(PIPELINE_STAGES):
            if k == key:
                return i
        return -1

    def _build(self):
        for child in self.findChildren(QWidget):
            child.deleteLater()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4 if self._compact else 6)

        stages = [(k, lbl, short, ico) for k, lbl, short, ico in PIPELINE_STAGES
                  if (self._split or k != "split")
                  and (self._speed or k != "speed")]

        for i, (key, label, short, _) in enumerate(stages):
            bg, fg, dot_color = PRIMARY_TINT_8, PRIMARY, PRIMARY

            if key in self._counts and not self._compact:
                done, total = self._counts[key]
                display = f"{label}  {done}/{total}"
            else:
                display = short if self._compact else label

            chip = Chip(display, bg, fg, dot=dot_color,
                        compact=self._compact, tooltip=label)
            self._count_labels[key] = chip.label
            lay.addWidget(chip)

            if i < len(stages) - 1:
                sep = QFrame()
                sep.setFixedSize(6 if self._compact else 10, 1)
                sep.setStyleSheet(f"background:{BORDER};")
                lay.addWidget(sep)

        lay.addStretch()

    def update_stage(self, active_stage: str, split_enabled: bool,
                     running: bool | None = None,
                     stage_counts: dict | None = None,
                     speed_enabled: bool | None = None):
        self._active = active_stage
        self._split  = split_enabled
        if running is not None:
            self._running = running
        if stage_counts is not None:
            self._counts = stage_counts
        if speed_enabled is not None:
            self._speed = speed_enabled
        self._build()

    def update_counts_only(self, stage_counts: dict) -> None:
        """Update count text in-place — no layout rebuild, safe to call every tick."""
        self._counts = stage_counts
        for key, lbl in self._count_labels.items():
            if key in stage_counts and not self._compact:
                done, total = stage_counts[key]
                stage_label = next((l for k, l, *_ in PIPELINE_STAGES if k == key), key)
                lbl.setText(f"{stage_label}  {done}/{total}")
