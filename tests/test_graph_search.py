"""Tests for core.graph_search."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.environment import Grid, load_environment
from core.graph_search import (
    compare_algorithms,
    format_comparison_table,
    get_successors,
    heuristic,
    path_cost,
    search,
    search_with_trace,
    validate_path,
)

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def sample() -> Grid:
    """Load the course sample environment."""
    return load_environment(DATA / "Environment_Sample.txt")


@pytest.fixture
def ours() -> Grid:
    """Load our custom environment."""
    return load_environment(DATA / "Environment.txt")


@pytest.fixture
def error_env() -> Grid:
    """Load the unreachable-dirty failure environment."""
    return load_environment(DATA / "Environment_Error.txt")


@pytest.mark.parametrize("algorithm", ["bfs", "astar", "A*"])
def test_sample_station_to_d4(sample: Grid, algorithm: str) -> None:
    """BFS and A* find a valid optimal path from station to D4 (7,0)."""
    path, cost, expanded = search(sample, (0, 0), (7, 0), algorithm)
    assert path is not None
    assert validate_path(sample, path)
    assert cost == path_cost(path)
    # Manhattan is 7; wall at col 3 does not block the left column.
    assert cost == 7
    assert expanded >= 0


def test_bfs_astar_equal_cost_astar_expands_fewer(sample: Grid, ours: Grid) -> None:
    """Both algorithms are optimal; A* expands no more nodes than BFS."""
    pairs = [
        ((0, 0), (7, 0)),
        ((0, 0), (0, 7)),
        ((0, 0), (7, 7)),
        ((0, 7), (7, 0)),
    ]
    for grid in (sample, ours):
        for start, goal in pairs:
            if not grid.is_free(start) or not grid.is_free(goal):
                continue
            bfs = search_with_trace(grid, start, goal, "bfs")
            astar = search_with_trace(grid, start, goal, "astar")
            assert bfs.found and astar.found
            assert bfs.cost == astar.cost
            assert validate_path(grid, bfs.path)
            assert validate_path(grid, astar.path)
            assert astar.nodes_expanded <= bfs.nodes_expanded


def test_start_equals_goal(sample: Grid) -> None:
    """Start == goal returns ([start], 0, 0) for both algorithms."""
    for algo in ("bfs", "astar"):
        path, cost, expanded = search(sample, (0, 0), (0, 0), algo)
        assert path == [(0, 0)]
        assert cost == 0
        assert expanded == 0


def test_no_path_enclosed(error_env: Grid) -> None:
    """Unreachable enclosed dirty cell returns (None, None, n)."""
    goal = error_env.dirty_locations[3]  # D4 enclosed at (2,2)
    for algo in ("bfs", "astar"):
        path, cost, expanded = search(error_env, (0, 0), goal, algo)
        assert path is None
        assert cost is None
        assert isinstance(expanded, int)
        assert expanded >= 0
        result = search_with_trace(error_env, (0, 0), goal, algo)
        assert result.found is False
        assert "No path" in result.message or result.message


def test_goal_on_obstacle_and_oob(sample: Grid) -> None:
    """Obstacle / out-of-bounds endpoints fail without raising."""
    for algo in ("bfs", "astar"):
        path, cost, expanded = search(sample, (0, 0), (1, 3), algo)
        assert path is None and cost is None and expanded == 0
        path, cost, expanded = search(sample, (0, 0), (99, 99), algo)
        assert path is None and cost is None and expanded == 0
        path, cost, expanded = search(sample, (-1, 0), (0, 0), algo)
        assert path is None and cost is None and expanded == 0


def test_get_successors_corner_and_obstacle(sample: Grid) -> None:
    """Successors respect bounds, obstacles, and UP/DOWN/LEFT/RIGHT order."""
    # Top-left corner: only DOWN and RIGHT.
    succ = get_successors((0, 0), sample)
    actions = [a for _, a, _ in succ]
    assert actions == ["DOWN", "RIGHT"]
    # Next to obstacle (1,3): cannot move onto it.
    succ2 = get_successors((1, 2), sample)
    next_states = {s for s, _, _ in succ2}
    assert (1, 3) not in next_states
    # Order is always UP, DOWN, LEFT, RIGHT among the valid ones.
    assert [a for _, a, _ in succ2] == sorted(
        [a for _, a, _ in succ2],
        key=lambda a: ["UP", "DOWN", "LEFT", "RIGHT"].index(a),
    )


def test_path_cost_edge_cases() -> None:
    """path_cost handles None, empty, single, and multi-cell paths."""
    assert path_cost(None) == 0
    assert path_cost([]) == 0
    assert path_cost([(0, 0)]) == 0
    assert path_cost([(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)]) == 4


def test_heuristic_values() -> None:
    """Manhattan distance examples."""
    assert heuristic((0, 0), (7, 0)) == 7
    assert heuristic((0, 0), (7, 7)) == 14
    assert heuristic((3, 4), (3, 4)) == 0


def test_unknown_algorithm_raises(sample: Grid) -> None:
    """Unknown algorithm names raise ValueError listing supported ones."""
    with pytest.raises(ValueError) as exc:
        search(sample, (0, 0), (7, 0), "dijkstra")
    assert "bfs" in str(exc.value).lower()


def test_cost_equals_manhattan_on_empty_grid() -> None:
    """On an empty open grid, optimal cost equals Manhattan distance."""
    grid = Grid(rows=5, cols=5, obstacles=set(), dirty_locations=[], charging_station=(0, 0))
    start, goal = (0, 0), (4, 4)
    for algo in ("bfs", "astar"):
        path, cost, _ = search(grid, start, goal, algo)
        assert cost == heuristic(start, goal) == 8
        assert validate_path(grid, path)


def test_compare_and_table(sample: Grid) -> None:
    """compare_algorithms + format_comparison_table produce usable output."""
    results = compare_algorithms(sample, (0, 0), (7, 0))
    assert len(results) == 2
    table = format_comparison_table(results)
    assert "bfs" in table
    assert "astar" in table


def test_optional_ucs_greedy(sample: Grid) -> None:
    """Optional UCS finds the same optimal cost; greedy finds some path."""
    ucs = search_with_trace(sample, (0, 0), (7, 0), "ucs")
    greedy = search_with_trace(sample, (0, 0), (7, 0), "greedy")
    bfs = search_with_trace(sample, (0, 0), (7, 0), "bfs")
    assert ucs.found and ucs.cost == bfs.cost
    assert greedy.found
    assert validate_path(sample, greedy.path)
