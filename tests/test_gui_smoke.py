"""Offscreen smoke test for the SafayeWala GUI."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Must be set before QApplication is created.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from gui.backend import Backend
from gui.main_window import MainWindow

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    """Shared QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_loads_sample_and_runs_search(qapp: QApplication) -> None:
    """Create the main window, load sample, run BFS and A*, close cleanly."""
    backend = Backend()
    window = MainWindow(backend)
    window.show()

    grid = backend.load_environment(DATA / "Environment_Sample.txt")
    window.env_page.apply_grid(grid, source="Environment_Sample.txt")
    assert window.env_page.current_grid() is not None

    bfs = backend.run_search(grid, (0, 0), (7, 0), "bfs")
    astar = backend.run_search(grid, (0, 0), (7, 0), "astar")
    assert bfs.found and astar.found
    assert bfs.cost == astar.cost
    assert astar.nodes_expanded <= bfs.nodes_expanded

    window.search_page.set_grid(grid)
    window.search_page.canvas_a.load_search_result(bfs)
    window.mission_page.set_grid(grid)
    # Manual mission should succeed on the sample.
    result = backend.execute_mission(
        grid, ["D1", "D2", "D3", "D4"], "bfs", schedule_source="manual"
    )
    assert result.success
    assert result.schedule_source == "manual"

    # CSP path should report missing module while Member 2/3 absent.
    csp_result = backend.execute_mission(
        grid, ["D1"], "bfs", schedule_source="csp"
    )
    assert not csp_result.success
    assert "INTEGRATION_NOT_AVAILABLE" in csp_result.message or "not found" in csp_result.message.lower()

    window.close()
