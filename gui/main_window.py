"""Main application window for SafayeWala."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QSettings, Qt, QPoint
from PySide6.QtGui import QAction, QKeySequence, QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from gui import theme
from gui.backend import Backend
from gui.pages.about_page import AboutPage
from gui.pages.compare_page import ComparePage
from gui.pages.environment_page import EnvironmentPage
from gui.pages.mission_page import MissionPage
from gui.pages.search_lab_page import SearchLabPage
from gui.team import APP_NAME, TAGLINE
from gui.widgets.toast import ToastHost


class _LogoBadge(QWidget):
    """Tiny drawn vacuum logo + wordmark for the sidebar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(64)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(theme.ACCENT))
        p.setPen(QPen(QColor("#042f2e"), 1.5))
        p.drawEllipse(10, 16, 32, 28)
        p.setBrush(QColor("#ecfeff"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(28, 24, 7, 7)
        p.setPen(QColor(theme.TEXT))
        font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(50, 38, APP_NAME)


class MainWindow(QMainWindow):
    """Sidebar + stacked pages + toast host."""

    def __init__(self, backend: Backend | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — {TAGLINE}")
        self.setMinimumSize(1100, 700)
        self.backend = backend or Backend()
        self.settings = QSettings("SafayeWala", "SafayeWala")

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        side_l = QVBoxLayout(self.sidebar)
        side_l.setContentsMargins(12, 12, 12, 12)
        side_l.setSpacing(6)
        side_l.addWidget(_LogoBadge())
        self._nav_btns: list[QPushButton] = []
        self._pages_meta = [
            ("Environment", "environment"),
            ("Search Lab", "search"),
            ("Full Mission", "mission"),
            ("Compare", "compare"),
            ("About", "about"),
        ]
        for i, (label, _key) in enumerate(self._pages_meta):
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda checked=False, idx=i: self._go(idx))
            side_l.addWidget(btn)
            self._nav_btns.append(btn)
        side_l.addStretch(1)
        self.collapse_btn = QPushButton("« Collapse")
        self.collapse_btn.clicked.connect(self._toggle_sidebar)
        side_l.addWidget(self.collapse_btn)
        root.addWidget(self.sidebar)

        # Pages
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.env_page = EnvironmentPage(self.backend)
        self.search_page = SearchLabPage(self.backend)
        self.mission_page = MissionPage(self.backend)
        self.compare_page = ComparePage(self.backend)
        self.about_page = AboutPage()
        for page in (
            self.env_page,
            self.search_page,
            self.mission_page,
            self.compare_page,
            self.about_page,
        ):
            self.stack.addWidget(page)
        right.addWidget(self.stack)
        root.addLayout(right, stretch=1)

        # Status + toasts
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")
        self.toasts = ToastHost(self)

        # Wire signals
        self.env_page.environment_loaded.connect(self._on_env_loaded)
        self.env_page.toast.connect(self._toast)
        self.search_page.toast.connect(self._toast)
        self.mission_page.toast.connect(self._toast)
        self.compare_page.toast.connect(self._toast)

        self._collapsed = False
        self._go(0)
        self._setup_shortcuts()

        # Restore geometry
        geo = self.settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)

    def _setup_shortcuts(self) -> None:
        open_act = QAction("Open", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self.env_page.load_dialog)
        self.addAction(open_act)

        space = QAction("PlayPause", self)
        space.setShortcut(Qt.Key.Key_Space)
        space.triggered.connect(self._play_pause_current)
        self.addAction(space)

        step = QAction("Step", self)
        step.setShortcut(Qt.Key.Key_Right)
        step.triggered.connect(self._step_current)
        self.addAction(step)

        reset = QAction("Reset", self)
        reset.setShortcut(Qt.Key.Key_R)
        reset.triggered.connect(self._reset_current)
        self.addAction(reset)

    def _current_grid_widget(self):
        page = self.stack.currentWidget()
        if hasattr(page, "grid_widget"):
            return page.grid_widget
        if hasattr(page, "canvas"):
            return page.canvas
        if hasattr(page, "canvas_a"):
            return page.canvas_a
        return None

    def _play_pause_current(self) -> None:
        gw = self._current_grid_widget()
        if gw:
            gw.toggle_play()

    def _step_current(self) -> None:
        gw = self._current_grid_widget()
        if gw:
            gw.step()

    def _reset_current(self) -> None:
        gw = self._current_grid_widget()
        if gw:
            gw.reset_playback()

    def _go(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        # Subtle slide via moving the stack (lightweight)
        self.stack.setGraphicsEffect(None)

    def _toggle_sidebar(self) -> None:
        self._collapsed = not self._collapsed
        self.sidebar.setFixedWidth(64 if self._collapsed else 220)
        self.collapse_btn.setText("»" if self._collapsed else "« Collapse")

    def _on_env_loaded(self, grid) -> None:
        self.search_page.set_grid(grid)
        self.mission_page.set_grid(grid)
        self.compare_page.set_grid(grid)
        self.statusBar().showMessage(
            f"Environment {grid.rows}x{grid.cols} | "
            f"{len(grid.obstacles)} obstacles | {len(grid.dirty_locations)} dirty"
        )

    def _toast(self, message: str, kind: str = "info") -> None:
        self.toasts.show_toast(message, kind)
        self.statusBar().showMessage(message, 4000)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.settings.setValue("geometry", self.saveGeometry())
        folder = self.settings.value("last_folder")
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.toasts.setGeometry(0, 0, self.width(), self.height())
        self.toasts.raise_()
