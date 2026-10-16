"""Environment load / validate page."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.environment import Grid
from gui.backend import Backend, EnvironmentFormatError
from gui.grid_widget import GridWidget
from gui.widgets.card import Card
from gui.widgets.playback_bar import PlaybackBar

DATA = Path(__file__).resolve().parents[2] / "data"


class EnvironmentPage(QWidget):
    """Load environments, show validation checklist and grid."""

    environment_loaded = Signal(object)  # Grid
    toast = Signal(str, str)

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.backend = backend
        self.grid_widget = GridWidget()
        self.grid_widget.set_mode("view")
        self.grid_widget.toast_requested.connect(self.toast.emit)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Center canvas
        center = QVBoxLayout()
        center.addWidget(self.grid_widget, stretch=1)
        center.addWidget(PlaybackBar(self.grid_widget))
        root.addLayout(center, stretch=3)

        # Right panel
        side = QVBoxLayout()
        side.setSpacing(10)
        controls = Card("Load Environment")
        for text, slot in (
            ("Load Sample", self.load_sample),
            ("Load Ours", self.load_ours),
            ("Load Error Case", self.load_error),
            ("Load Environment…", self.load_dialog),
        ):
            btn = QPushButton(text)
            if text.startswith("Load Sample"):
                btn.setObjectName("primaryButton")
            btn.clicked.connect(slot)
            controls.add_widget(btn)
        side.addWidget(controls)

        self.summary = Card("Summary")
        self.summary_label = QLabel("No environment loaded.")
        self.summary_label.setWordWrap(True)
        self.summary.add_widget(self.summary_label)
        side.addWidget(self.summary)

        self.checklist = Card("Validation")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.check_host = QWidget()
        self.check_layout = QVBoxLayout(self.check_host)
        self.check_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.check_host)
        self.checklist.add_widget(scroll)
        side.addWidget(self.checklist, stretch=1)

        self.warn = QLabel("")
        self.warn.setWordWrap(True)
        self.warn.setStyleSheet("color: #fbbf24; font-weight: 600;")
        side.addWidget(self.warn)

        root.addLayout(side, stretch=1)
        self._grid: Grid | None = None

    def load_sample(self) -> None:
        self._load_path(DATA / "Environment_Sample.txt")

    def load_ours(self) -> None:
        self._load_path(DATA / "Environment.txt")

    def load_error(self) -> None:
        self._load_path(DATA / "Environment_Error.txt")

    def load_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Environment",
            str(DATA),
            "Text files (*.txt);;All files (*)",
        )
        if path:
            self._load_path(Path(path))

    def _load_path(self, path: Path) -> None:
        try:
            grid = self.backend.load_environment(path)
        except EnvironmentFormatError as exc:
            self.toast.emit(str(exc), "error")
            self._show_checklist([f"Format error: {exc}"], ok=False)
            return
        except OSError as exc:
            self.toast.emit(f"Cannot read file: {exc}", "error")
            return
        self.apply_grid(grid, source=path.name)

    def apply_grid(self, grid: Grid, source: str = "") -> None:
        """Apply a loaded grid to the canvas and checklist."""
        self._grid = grid
        self.grid_widget.set_grid(grid)
        problems = self.backend.validate(grid, strict=True)
        unreachable = self.backend.unreachable(grid)
        self.summary_label.setText(
            f"<b>{source or 'Environment'}</b><br>"
            f"Size: {grid.rows} × {grid.cols}<br>"
            f"Obstacles: {len(grid.obstacles)}<br>"
            f"Dirty: {len(grid.dirty_locations)}<br>"
            f"Station: {grid.charging_station}"
        )
        rules = [
            ("Coordinates in bounds / no overlaps", not problems or all("Strict" in p for p in problems)),
            ("No validation problems", len([p for p in problems if not p.startswith("Strict")]) == 0),
            ("Strict project minimums", not any(p.startswith("Strict") for p in problems)),
            ("All dirty reachable", len(unreachable) == 0),
        ]
        # Rebuild detailed list
        details = []
        for p in problems:
            details.append(f"✗ {p}")
        if not problems:
            details.append("✓ Logical validation passed")
        if unreachable:
            details.append(f"✗ Unreachable: {', '.join(unreachable)}")
        else:
            details.append("✓ All dirty locations reachable from station")
        self._show_checklist(details, ok=not problems and not unreachable)
        if unreachable:
            self.warn.setText(
                f"Warning: unreachable dirty location(s): {', '.join(unreachable)}"
            )
        else:
            self.warn.setText("")
        self.toast.emit(f"Loaded {source or 'environment'}", "success")
        self.environment_loaded.emit(grid)

    def _show_checklist(self, lines: list[str], ok: bool) -> None:
        while self.check_layout.count():
            item = self.check_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for line in lines:
            lab = QLabel(line)
            lab.setWordWrap(True)
            if line.startswith("✓"):
                lab.setStyleSheet("color: #34d399;")
            elif line.startswith("✗"):
                lab.setStyleSheet("color: #f87171;")
            self.check_layout.addWidget(lab)
        self.check_layout.addStretch(1)

    def current_grid(self) -> Grid | None:
        return self._grid
