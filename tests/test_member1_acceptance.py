"""End-to-end acceptance checks for Member 1 part using sample data files."""

from __future__ import annotations

from pathlib import Path

from core.environment import (
    load_environment,
    unreachable_dirty_locations,
    validate_environment,
)
from core.graph_search import search, search_with_trace, validate_path

DATA = Path(__file__).resolve().parent.parent / "data"


def test_all_three_env_files_load() -> None:
    sample = load_environment(DATA / "Environment_Sample.txt")
    ours = load_environment(DATA / "Environment.txt")
    error = load_environment(DATA / "Environment_Error.txt")

    assert sample.rows == 8 and sample.cols == 8
    assert sample.dirty_locations == [(0, 7), (3, 7), (7, 7), (7, 0)]
    assert sample.charging_station == (0, 0)
    assert validate_environment(sample, strict=True) == []
    assert unreachable_dirty_locations(sample) == []

    assert ours.rows == 10 and ours.cols == 10
    assert validate_environment(ours, strict=True) == []
    assert unreachable_dirty_locations(ours) == []

    assert validate_environment(error) == []
    assert "D4" in unreachable_dirty_locations(error)


def test_sample_bfs_astar_optimal_and_astar_fewer() -> None:
    grid = load_environment(DATA / "Environment_Sample.txt")
    pairs = [
        ((0, 0), (7, 0)),  # Station → D4
        ((0, 0), (0, 7)),  # Station → D1
        ((0, 0), (7, 7)),  # Station → D3
    ]
    for start, goal in pairs:
        bfs = search_with_trace(grid, start, goal, "bfs")
        astar = search_with_trace(grid, start, goal, "astar")
        assert bfs.found and astar.found
        assert bfs.cost == astar.cost
        assert validate_path(grid, bfs.path)
        assert validate_path(grid, astar.path)
        assert astar.nodes_expanded <= bfs.nodes_expanded

    path, cost, _ = search(grid, (0, 0), (7, 0), "bfs")
    assert cost == 7
    assert path is not None and path[0] == (0, 0) and path[-1] == (7, 0)


def test_ours_env_all_dirty_reachable_via_search() -> None:
    grid = load_environment(DATA / "Environment.txt")
    station = grid.charging_station
    for dirty in grid.dirty_locations:
        result = search_with_trace(grid, station, dirty, "astar")
        assert result.found, f"unreachable {dirty}"
        assert validate_path(grid, result.path)


def test_error_env_enclosed_dirty_has_no_path() -> None:
    grid = load_environment(DATA / "Environment_Error.txt")
    enclosed = grid.dirty_locations[3]  # D4 = (2,2)
    path, cost, expanded = search(grid, (0, 0), enclosed, "bfs")
    assert path is None and cost is None
    assert isinstance(expanded, int)
