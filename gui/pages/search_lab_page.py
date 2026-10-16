"""Search Lab: run BFS / A* with animated traces."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.environment import Grid
from gui import theme
from gui.backend import Backend
from gui.grid_widget import GridWidget
from gui.widgets.card import Card
from gui.widgets.playback_bar import PlaybackBar
from gui.widgets.stat_counter import StatCounter


class SearchLabPage(QWidget):
    """Interactive search playground."""

    toast = Signal(str, str)

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.backend = backend
        self._grid: Grid | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.canvas_a = GridWidget()
        self.canvas_a.set_mode("search")
        self.canvas_b = GridWidget()
        self.canvas_b.set_mode("search")
        self.canvas_b.hide()
        self.canvas_a.toast_requested.connect(self.toast.emit)
        self.canvas_b.toast_requested.connect(self.toast.emit)
        self.canvas_a.cell_clicked.connect(self._on_cell)
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.addWidget(self.canvas_a, stretch=1)
        left_l.addWidget(self.canvas_b, stretch=1)
        left_l.addWidget(PlaybackBar(self.canvas_a))
        self.splitter.addWidget(left)

        side = QWidget()
        side_l = QVBoxLayout(side)
        controls = Card("Search Lab")
        self.algo = QComboBox()
        self.algo.addItems(["bfs", "astar", "ucs", "greedy"])
        controls.add_widget(QLabel("Algorithm"))
        controls.add_widget(self.algo)

        self.start_box = QComboBox()
        self.goal_box = QComboBox()
        controls.add_widget(QLabel("Start (or left-click grid)"))
        controls.add_widget(self.start_box)
        controls.add_widget(QLabel("Goal (or right-click / Shift+click)"))
        controls.add_widget(self.goal_box)
        self.start_box.currentIndexChanged.connect(self._sync_markers)
        self.goal_box.currentIndexChanged.connect(self._sync_markers)

        self.compare_both = QCheckBox("Compare side by side (BFS | A*)")
        controls.add_widget(self.compare_both)

        run = QPushButton("Run")
        run.setObjectName("primaryButton")
        run.clicked.connect(self.run_search)
        controls.add_widget(run)
        side_l.addWidget(controls)

        stats = Card("Results")
        row = QHBoxLayout()
        self.stat_cost = StatCounter("Cost")
        self.stat_nodes = StatCounter("Expanded")
        self.stat_frontier = StatCounter("Max frontier")
        self.stat_time = StatCounter("Time")
        for s in (self.stat_cost, self.stat_nodes, self.stat_frontier, self.stat_time):
            row.addWidget(s)
        stats.body.addLayout(row)
        self.path_view = QPlainTextEdit()
        self.path_view.setReadOnly(True)
        self.path_view.setPlaceholderText("Path coordinates will appear here…")
        stats.add_widget(self.path_view)
        self.fail_label = QLabel("")
        self.fail_label.setStyleSheet(f"color: {theme.ERROR}; font-weight: 700;")
        self.fail_label.hide()
        stats.add_widget(self.fail_label)
        self.badge = QLabel("")
        self.badge.setStyleSheet(f"color: {theme.ACCENT}; font-weight: 600;")
        stats.add_widget(self.badge)
        side_l.addWidget(stats, stretch=1)

        self.splitter.addWidget(side)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        root.addWidget(self.splitter)

        self.canvas_a.stats_tick.connect(self._live_stats)

    def set_grid(self, grid: Grid) -> None:
        """Receive the active environment from the main window."""
        self._grid = grid
        self.canvas_a.set_grid(grid)
        self.canvas_b.set_grid(grid)
        self._refill_boxes()
        self.canvas_a.set_mode("search")
        self.canvas_b.set_mode("search")

    def _refill_boxes(self) -> None:
        if not self._grid:
            return
        labels = ["C (Station)"] + [
            self._grid.task_label(i) for i in range(len(self._grid.dirty_locations))
        ]
        for box in (self.start_box, self.goal_box):
            box.blockSignals(True)
            box.clear()
            box.addItems(labels)
            box.blockSignals(False)
        self.start_box.setCurrentIndex(0)
        if len(labels) > 1:
            self.goal_box.setCurrentIndex(len(labels) - 1)
        self._sync_markers()

    def _label_to_pos(self, text: str):
        assert self._grid
        if text.startswith("C"):
            return self._grid.charging_station
        return self._grid.label_to_position(text.split()[0])

    def _sync_markers(self) -> None:
        if not self._grid:
            return
        try:
            start = self._label_to_pos(self.start_box.currentText())
            goal = self._label_to_pos(self.goal_box.currentText())
        except Exception:
            return
        self.canvas_a.set_start_goal(start, goal)
        self.canvas_b.set_start_goal(start, goal)

    def _on_cell(self, r: int, c: int, button) -> None:
        if not self._grid:
            return
        pos = (r, c)
        # Update combo boxes to match clicks
        label = self._grid.position_to_label(pos)
        display = "C (Station)" if label == "C" else (label or f"{pos}")
        target = self.goal_box if button == Qt.MouseButton.RightButton else self.start_box
        idx = target.findText(display)
        if idx < 0:
            # Free cell — add temporary entry
            target.addItem(f"{pos}")
            idx = target.count() - 1
        target.setCurrentIndex(idx)

    def run_search(self) -> None:
        if not self._grid:
            self.toast.emit("Load an environment first", "warning")
            return
        start, goal = self.canvas_a.start_goal()
        if start is None or goal is None:
            self.toast.emit("Set both start and goal", "warning")
            return

        if self.compare_both.isChecked():
            self.canvas_b.show()
            bfs = self.backend.run_search(self._grid, start, goal, "bfs")
            astar = self.backend.run_search(self._grid, start, goal, "astar")
            self.canvas_a.load_search_result(bfs, QColor(theme.BFS_BLUE))
            self.canvas_b.load_search_result(astar, QColor(theme.ASTAR_MAGENTA))
            self._show_result(bfs, dual=astar)
            if bfs.found and astar.found:
                if astar.nodes_expanded < bfs.nodes_expanded:
                    self.badge.setText(
                        f"A* expanded fewer nodes ({astar.nodes_expanded} vs {bfs.nodes_expanded})"
                    )
                elif astar.nodes_expanded == bfs.nodes_expanded:
                    self.badge.setText("Tie: same node expansions")
                else:
                    self.badge.setText(
                        f"BFS expanded fewer here ({bfs.nodes_expanded} vs {astar.nodes_expanded})"
                    )
            return

        self.canvas_b.hide()
        algo = self.algo.currentText()
        result = self.backend.run_search(self._grid, start, goal, algo)
        colour = QColor(theme.ASTAR_MAGENTA if result.algorithm == "astar" else theme.BFS_BLUE)
        self.canvas_a.load_search_result(result, colour)
        self._show_result(result)
        self.badge.setText("")

    def _show_result(self, result, dual=None) -> None:
        if not result.found:
            self.fail_label.setText(f"No path found — {result.message}")
            self.fail_label.show()
            self.stat_cost.set_value(None)
            self.stat_nodes.set_value(result.nodes_expanded)
            self.stat_frontier.set_value(result.frontier_max_size)
            self.stat_time.set_value(result.runtime_seconds * 1000, as_float=True, suffix=" ms")
            self.path_view.setPlainText("")
            self.toast.emit(result.message or "No path found", "error")
            return
        self.fail_label.hide()
        self.stat_cost.set_value(result.cost)
        self.stat_nodes.set_value(result.nodes_expanded)
        self.stat_frontier.set_value(result.frontier_max_size)
        self.stat_time.set_value(result.runtime_seconds * 1000, as_float=True, suffix=" ms")
        lines = [f"{result.algorithm.upper()} path ({len(result.path or [])} cells):"]
        lines += [str(p) for p in (result.path or [])]
        if dual is not None:
            lines += ["", f"{dual.algorithm.upper()} path ({len(dual.path or [])} cells):"]
            lines += [str(p) for p in (dual.path or [])]
            lines += [
                "",
                f"Costs: {result.algorithm}={result.cost}, {dual.algorithm}={dual.cost}",
            ]
        self.path_view.setPlainText("\n".join(lines))
        self.toast.emit("Search complete", "success")

    def _live_stats(self, expanded: int, frontier: int, g_cost) -> None:
        self.stat_nodes.set_value(expanded, animate=False)
        if g_cost is not None:
            self.stat_cost.set_value(g_cost, animate=False)
