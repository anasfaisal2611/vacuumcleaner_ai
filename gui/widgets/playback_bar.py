"""Shared Play / Pause / Step / Reset / Speed controls."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

from gui.grid_widget import GridWidget


class PlaybackBar(QWidget):
    """Wire standard playback buttons to a GridWidget."""

    def __init__(self, grid: GridWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._grid = grid
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.btn_play = QPushButton("Play")
        self.btn_play.setObjectName("primaryButton")
        self.btn_step = QPushButton("Step")
        self.btn_reset = QPushButton("Reset")
        self.btn_skip = QPushButton("Skip")
        for b in (self.btn_play, self.btn_step, self.btn_reset, self.btn_skip):
            layout.addWidget(b)

        layout.addWidget(QLabel("Speed"))
        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setMinimum(25)   # 0.25x
        self.speed.setMaximum(800)  # 8x
        self.speed.setValue(100)
        self.speed.setFixedWidth(140)
        layout.addWidget(self.speed)
        self.speed_label = QLabel("1.00x")
        layout.addWidget(self.speed_label)
        layout.addStretch(1)

        self.btn_play.clicked.connect(self._toggle)
        self.btn_step.clicked.connect(grid.step)
        self.btn_reset.clicked.connect(grid.reset_playback)
        self.btn_skip.clicked.connect(grid.skip_to_end)
        self.speed.valueChanged.connect(self._on_speed)
        grid.playback_changed.connect(self._sync)

    def _toggle(self) -> None:
        self._grid.toggle_play()
        self._sync()

    def _on_speed(self, value: int) -> None:
        speed = value / 100.0
        self._grid.set_speed(speed)
        self.speed_label.setText(f"{speed:.2f}x")

    def _sync(self) -> None:
        self.btn_play.setText("Pause" if self._grid.is_playing() else "Play")
