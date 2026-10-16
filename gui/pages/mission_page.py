"""Full Mission page: CSP schedule + navigation (with manual demo fallback)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from core.environment import Grid
from gui import theme
from gui.backend import Backend
from gui.grid_widget import GridWidget
from gui.widgets.card import Card
from gui.widgets.playback_bar import PlaybackBar


class MissionPage(QWidget):
    """Integrated cleaning mission (CSP or manual demo)."""

    toast = Signal(str, str)

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.backend = backend
        self._grid: Grid | None = None
        self._schedule: list[str] = []
        self._schedule_source = "manual"
        self._assignment: dict | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        left = QVBoxLayout()
        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet(
            f"background:{theme.BG_ELEVATED}; border:1px solid {theme.WARNING}; "
            f"border-radius:10px; padding:10px; color:{theme.WARNING};"
        )
        left.addWidget(self.banner)

        self.canvas = GridWidget()
        self.canvas.set_mode("mission")
        self.canvas.toast_requested.connect(self.toast.emit)
        left.addWidget(self.canvas, stretch=1)
        left.addWidget(PlaybackBar(self.canvas))
        self.progress = QProgressBar()
        left.addWidget(self.progress)
        self.leg_label = QLabel("Current leg: —")
        left.addWidget(self.leg_label)
        root.addLayout(left, stretch=3)

        side = QVBoxLayout()
        status = self.backend.status()
        self._refresh_banner(status)

        sched_card = Card("Schedule")
        load_btn = QPushButton("Load Schedule…")
        load_btn.clicked.connect(self.load_schedule)
        sched_card.add_widget(load_btn)
        self.csp_btn = QPushButton("Generate via CSP")
        self.csp_btn.clicked.connect(self.generate_csp)
        sched_card.add_widget(self.csp_btn)

        sched_card.add_widget(QLabel("Order (drag to reorder — manual demo)"))
        self.order_list = QListWidget()
        self.order_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.order_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        sched_card.add_widget(self.order_list)

        manual_btn = QPushButton("Use manual demo order")
        manual_btn.clicked.connect(self.use_manual)
        sched_card.add_widget(manual_btn)
        side.addWidget(sched_card)

        run_card = Card("Execute")
        self.algo = QComboBox()
        self.algo.addItems(["bfs", "astar"])
        run_card.add_widget(QLabel("Algorithm"))
        run_card.add_widget(self.algo)
        go = QPushButton("Start mission")
        go.setObjectName("primaryButton")
        go.clicked.connect(self.start_mission)
        run_card.add_widget(go)
        self.summary = QLabel("No mission run yet.")
        self.summary.setWordWrap(True)
        run_card.add_widget(self.summary)
        side.addWidget(run_card)
        side.addStretch(1)
        root.addLayout(side, stretch=1)

        self._schedule_path: Path | None = None

    def _refresh_banner(self, status) -> None:
        if status.csp and status.integration:
            self.banner.hide()
            return
        missing = ", ".join(status.missing) or "csp, integration"
        self.banner.setText(
            f"CSP/Integration not found yet (waiting for Member 2/3). "
            f"Missing: {missing}. You can still run a clearly labeled "
            f"manual demo order below — it is NOT a CSP result."
        )
        self.banner.show()

    def set_grid(self, grid: Grid) -> None:
        self._grid = grid
        self.canvas.set_grid(grid)
        self._fill_default_order()
        self._refresh_banner(self.backend.status())

    def _fill_default_order(self) -> None:
        self.order_list.clear()
        if not self._grid:
            return
        for i in range(len(self._grid.dirty_locations)):
            label = self._grid.task_label(i)
            item = QListWidgetItem(label)
            self.order_list.addItem(item)
        self._schedule = [self.order_list.item(i).text() for i in range(self.order_list.count())]
        self._schedule_source = "manual"

    def load_schedule(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Schedule", str(Path("data")), "Text (*.txt);;All (*)"
        )
        if path:
            self._schedule_path = Path(path)
            self.toast.emit(f"Schedule file set: {Path(path).name}", "info")

    def generate_csp(self) -> None:
        if not self._grid:
            self.toast.emit("Load an environment first", "warning")
            return
        if not self._schedule_path:
            self.toast.emit("Load a Schedule.txt first", "warning")
            return
        ordered, assignment, message = self.backend.generate_schedule(
            self._grid, self._schedule_path
        )
        if ordered is None:
            self.toast.emit(message, "error")
            self._schedule_source = "manual"
            return
        self.order_list.clear()
        for label in ordered:
            chip = label
            if assignment and label in assignment:
                chip = f"{assignment[label]} → {label}"
            self.order_list.addItem(QListWidgetItem(chip))
        self._schedule = ordered
        self._assignment = assignment
        self._schedule_source = "csp"
        self.toast.emit(message, "success")

    def use_manual(self) -> None:
        self._schedule = []
        for i in range(self.order_list.count()):
            text = self.order_list.item(i).text()
            # Strip "T1 → D2" chips down to D2 if needed
            if "→" in text:
                text = text.split("→")[-1].strip()
            self._schedule.append(text)
        self._schedule_source = "manual"
        self.toast.emit("Using MANUAL DEMO order (not a CSP result)", "warning")

    def start_mission(self) -> None:
        if not self._grid:
            self.toast.emit("Load an environment first", "warning")
            return
        self.use_manual() if self._schedule_source != "csp" else None
        # Refresh order from list for manual
        if self._schedule_source == "manual":
            self._schedule = []
            for i in range(self.order_list.count()):
                text = self.order_list.item(i).text()
                if "→" in text:
                    text = text.split("→")[-1].strip()
                self._schedule.append(text)

        if not self._schedule:
            self.toast.emit("Schedule is empty", "warning")
            return

        result = self.backend.execute_mission(
            self._grid,
            self._schedule,
            self.algo.currentText(),
            schedule_source=self._schedule_source,
        )
        if not result.success and not result.legs and not result.complete_path:
            self.toast.emit(result.message, "error")
            self.summary.setText(result.message)
            return

        leg_paths = [leg.path or [] for leg in result.legs if leg.path]
        self.canvas.load_mission(
            result.complete_path,
            leg_paths=leg_paths,
            manual=(result.schedule_source == "manual"),
        )
        self.progress.setValue(100 if result.success else 50)
        if result.legs:
            last = result.legs[-1] if result.success else next(
                (L for L in result.legs if not L.path), result.legs[-1]
            )
            self.leg_label.setText(
                f"Legs: {len(result.legs)} | Last: {last.from_label} → {last.to_label}"
            )
        status = "Mission complete" if result.success else "Mission failed"
        colour = theme.SUCCESS if result.success else theme.ERROR
        self.summary.setText(
            f"<b style='color:{colour}'>{status}</b><br>"
            f"{result.message}<br>"
            f"Total movements: {result.total_movements}<br>"
            f"Total cost: {result.total_cost}<br>"
            f"Source: {result.schedule_source.upper()}"
        )
        kind = "success" if result.success else "error"
        self.toast.emit(result.message, kind)
