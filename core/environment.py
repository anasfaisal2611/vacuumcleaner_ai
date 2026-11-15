"""Environment loading and validation for SafayeWala.

Member 1's ``Grid`` / ``load_environment`` live in the Jupyter notebook
``notebook_cells/CS-24058.ipynb`` (Part A).  This module re-exports those
symbols and keeps GUI/API helpers that are *not* part of the course notebook
API: ``validate_environment`` and ``unreachable_dirty_locations``.
"""

from __future__ import annotations

from collections import deque
from typing import List, Set

# Source of truth: notebook Part A (CS-24058.ipynb).
from notebook_cells.part_a import (  # noqa: F401
    EnvironmentFormatError,
    Grid,
    Position,
    load_environment,
)

__all__ = [
    "EnvironmentFormatError",
    "Grid",
    "Position",
    "load_environment",
    "unreachable_dirty_locations",
    "validate_environment",
]


def validate_environment(grid: Grid, strict: bool = False) -> List[str]:
    """Validate logical consistency of a loaded grid.

    Args:
        grid: Environment to check.
        strict: If True, also enforce project minimums
            (grid >= 8x8, >= 6 obstacles, >= 4 dirty locations).

    Returns:
        List of problem descriptions. Empty list means the grid is valid.
    """
    problems: List[str] = []

    if grid.charging_station is None:
        problems.append("Charging station is missing")
    else:
        if not grid.is_in_bounds(grid.charging_station):
            problems.append(
                f"Charging station {grid.charging_station} is outside the grid"
            )

    for pos in grid.obstacles:
        if not grid.is_in_bounds(pos):
            problems.append(f"Obstacle {pos} is outside the grid")

    for i, pos in enumerate(grid.dirty_locations):
        label = f"D{i + 1}"
        if not grid.is_in_bounds(pos):
            problems.append(f"Dirty location {label} {pos} is outside the grid")

    if len(grid.obstacles) != len(set(grid.obstacles)):
        problems.append("Duplicate obstacle coordinates")

    seen_dirty: Set[Position] = set()
    for i, pos in enumerate(grid.dirty_locations):
        if pos in seen_dirty:
            problems.append(f"Duplicate dirty location at {pos}")
        seen_dirty.add(pos)

    station = grid.charging_station
    for pos in grid.obstacles:
        if pos == station:
            problems.append(f"Charging station overlaps obstacle at {pos}")
        if pos in seen_dirty:
            problems.append(f"Obstacle overlaps dirty location at {pos}")

    for pos in grid.dirty_locations:
        if pos == station:
            problems.append(f"Charging station overlaps dirty location at {pos}")

    if strict:
        if grid.rows < 8 or grid.cols < 8:
            problems.append(
                f"Strict: grid must be at least 8x8 (got {grid.rows}x{grid.cols})"
            )
        if len(grid.obstacles) < 6:
            problems.append(
                f"Strict: need at least 6 obstacles (got {len(grid.obstacles)})"
            )
        if len(grid.dirty_locations) < 4:
            problems.append(
                f"Strict: need at least 4 dirty locations "
                f"(got {len(grid.dirty_locations)})"
            )

    return problems


def unreachable_dirty_locations(grid: Grid) -> List[str]:
    """Return labels of dirty cells unreachable from the charging station.

    Uses a BFS flood-fill from the charging station over free cells.
    This is a reachability helper for validation / GUI warnings — not part of
    the BFS vs A* algorithm comparison.
    """
    if not grid.is_free(grid.charging_station):
        return [grid.task_label(i) for i in range(len(grid.dirty_locations))]

    visited: Set[Position] = set()
    queue: deque[Position] = deque([grid.charging_station])
    visited.add(grid.charging_station)

    deltas = ((-1, 0), (1, 0), (0, -1), (0, 1))
    while queue:
        r, c = queue.popleft()
        for dr, dc in deltas:
            nxt = (r + dr, c + dc)
            if nxt not in visited and grid.is_free(nxt):
                visited.add(nxt)
                queue.append(nxt)

    unreachable: List[str] = []
    for i, pos in enumerate(grid.dirty_locations):
        if pos not in visited:
            unreachable.append(grid.task_label(i))
    return unreachable
