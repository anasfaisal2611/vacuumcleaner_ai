"""Compare BFS vs A* across multiple pairs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.environment import Grid
from gui import theme
from gui.backend import Backend
from gui.widgets.bar_chart import BarChartWidget
from gui.widgets.card import Card


class ComparePage(QWidget):
    """Tabular + chart comparison of search algorithms."""

    toast = Signal(str, str)

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.backend = backend
        self._grid: Grid | None = None
        self._rows: list = []

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        top = QHBoxLayout()
        run = QPushButton("Run Comparison")
        run.setObjectName("primaryButton")
        run.clicked.connect(self.run)
        export = QPushButton("Export CSV")
        export.clicked.connect(self.export_csv)
        copy = QPushButton("Copy as text")
        copy.clicked.connect(self.copy_text)
        top.addWidget(run)
        top.addWidget(export)
        top.addWidget(copy)
        top.addStretch(1)
        root.addLayout(top)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Pair", "Algorithm", "Cost", "Nodes expanded", "Max frontier", "Time (ms)"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        root.addWidget(self.table, stretch=2)

        charts = QHBoxLayout()
        self.chart_nodes = BarChartWidget()
        self.chart_cost = BarChartWidget()
        charts.addWidget(self.chart_nodes)
        charts.addWidget(self.chart_cost)
        root.addLayout(charts, stretch=2)

        insight_card = Card("Insight")
        self.insight = QLabel("Run a comparison to generate an insight.")
        self.insight.setWordWrap(True)
        insight_card.add_widget(self.insight)
        root.addWidget(insight_card)

    def set_grid(self, grid: Grid) -> None:
        self._grid = grid

    def run(self) -> None:
        if not self._grid:
            self.toast.emit("Load an environment first", "warning")
            return
        self._rows = self.backend.compare_pairs(self._grid)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for r in self._rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            vals = [
                r["pair"],
                r["algorithm"],
                "—" if r["cost"] is None else str(r["cost"]),
                str(r["nodes_expanded"]),
                str(r["frontier_max_size"]),
                f"{r['runtime_ms']:.2f}",
            ]
            for c, v in enumerate(vals):
                self.table.setItem(row, c, QTableWidgetItem(v))
        self.table.setSortingEnabled(True)

        # Charts: aggregate mean nodes / cost per algorithm for successful rows
        labels = ["BFS", "A*"]
        bfs_nodes = [r["nodes_expanded"] for r in self._rows if r["algorithm"] == "bfs" and r["found"]]
        astar_nodes = [r["nodes_expanded"] for r in self._rows if r["algorithm"] == "astar" and r["found"]]
        bfs_cost = [r["cost"] for r in self._rows if r["algorithm"] == "bfs" and r["found"]]
        astar_cost = [r["cost"] for r in self._rows if r["algorithm"] == "astar" and r["found"]]

        def mean(xs):
            return sum(xs) / len(xs) if xs else 0.0

        self.chart_nodes.set_chart(
            ["Avg nodes"],
            [
                ("BFS", [mean(bfs_nodes)], theme.BFS_BLUE),
                ("A*", [mean(astar_nodes)], theme.ASTAR_MAGENTA),
            ],
            title="Nodes expanded (average)",
        )
        self.chart_cost.set_chart(
            ["Avg cost"],
            [
                ("BFS", [mean(bfs_cost)], theme.BFS_BLUE),
                ("A*", [mean(astar_cost)], theme.ASTAR_MAGENTA),
            ],
            title="Path cost (average)",
        )
        self.insight.setText(self.backend.insight_from_rows(self._rows))
        self.toast.emit(f"Compared {len(self._rows)} rows", "success")

    def export_csv(self) -> None:
        if not self._rows:
            self.toast.emit("Nothing to export", "warning")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "comparison.csv", "CSV (*.csv)")
        if not path:
            return
        Path(path).write_text(self.backend.rows_to_csv(self._rows), encoding="utf-8")
        self.toast.emit(f"Saved {path}", "success")

    def copy_text(self) -> None:
        if not self._rows:
            self.toast.emit("Nothing to copy", "warning")
            return
        QGuiApplication.clipboard().setText(self.backend.rows_to_text(self._rows))
        self.toast.emit("Copied table to clipboard", "success")
