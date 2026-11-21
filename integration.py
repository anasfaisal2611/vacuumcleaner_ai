"""Mission integration — same idea as notebook ``execute_schedule``.

Runs a CSP (or manual) task order with graph search: Station → each Di → Station.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from notebook_cells.part_a import path_cost, search

Position = Tuple[int, int]


def execute_schedule(
    grid: Any,
    charging_station: Position,
    schedule: Sequence[str],
    algorithm: str,
    legs: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Position], int, bool]:
    """Follow ``schedule`` task labels with BFS/A*, then return to station.

    Returns
    -------
    (complete_path, total_cost, success)
    """
    current = charging_station
    complete_path: List[Position] = [charging_station]
    total_cost = 0
    cleaned = set()

    targets = [(task, grid.label_to_position(task)) for task in schedule]
    targets.append(("C", charging_station))

    for name, goal in targets:
        path, cost, expanded = search(grid, current, goal, algorithm)
        if legs is not None:
            legs.append(
                {
                    "from": current,
                    "to": goal,
                    "name": name,
                    "path": path,
                    "cost": cost,
                    "expanded": expanded,
                }
            )
        if path is None:
            return complete_path, total_cost, False
        complete_path.extend(path[1:])
        total_cost += int(cost or 0)
        current = goal
        if name != "C":
            cleaned.add(goal)

    success = cleaned == set(grid.dirty_locations) and current == charging_station
    if complete_path:
        assert total_cost == path_cost(complete_path)
    return complete_path, total_cost, success
