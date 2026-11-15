"""Prove Member 1 graph code comes from the notebook, not a stale core copy."""

from __future__ import annotations

from pathlib import Path

from core.environment import Grid, load_environment
from notebook_cells.part_a import (
    Grid as NbGrid,
    load_environment as nb_load,
    search_with_trace as nb_search,
)

DATA = Path(__file__).resolve().parent.parent / "data"
NOTEBOOK = Path(__file__).resolve().parent.parent / "notebook_cells" / "CS-24058.ipynb"


def test_core_grid_is_notebook_grid() -> None:
    """core.environment.Grid must be the class defined in Part A."""
    assert Grid is NbGrid
    assert load_environment is nb_load


def test_notebook_file_exists_with_part_a() -> None:
    text = NOTEBOOK.read_text(encoding="utf-8")
    # Em dash may be stored as a literal or as a JSON \\u2014 escape.
    assert "Graph-Based Search" in text
    assert "def search_with_trace" in text
    assert "CSP Scheduling" in text


def test_sample_search_via_notebook_symbols() -> None:
    grid = nb_load(DATA / "Environment_Sample.txt")
    bfs = nb_search(grid, (0, 0), (7, 0), "bfs")
    astar = nb_search(grid, (0, 0), (7, 0), "astar")
    assert bfs.found and astar.found
    assert bfs.cost == astar.cost == 7
    assert astar.nodes_expanded <= bfs.nodes_expanded
