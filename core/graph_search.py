"""Graph-based search for SafayeWala robot navigation.

Required functions (exact names/signatures for the course handout):
  get_successors, goal_test, path_cost, heuristic, search

Also provides search_with_trace (for GUI animation), compare helpers,
and optional UCS / Greedy algorithms.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Dict, List, Optional, Sequence, Set, Tuple

from core.environment import Grid, Position

# Deterministic action expansion order.
_ACTIONS: Tuple[Tuple[str, int, int], ...] = (
    ("UP", -1, 0),
    ("DOWN", 1, 0),
    ("LEFT", 0, -1),
    ("RIGHT", 0, 1),
)

SUPPORTED_ALGORITHMS = ("bfs", "astar", "ucs", "greedy")


@dataclass
class SearchResult:
    """Full trace of a single search run (used by tests and the GUI)."""

    path: Optional[List[Position]]
    cost: Optional[int]
    nodes_expanded: int
    expanded_order: List[Position] = field(default_factory=list)
    frontier_max_size: int = 0
    runtime_seconds: float = 0.0
    algorithm: str = ""
    found: bool = False
    message: str = ""


def get_successors(
    state: Position,
    grid: Grid,
) -> List[Tuple[Position, str, int]]:
    """Return valid successor states in order UP, DOWN, LEFT, RIGHT.

    Args:
        state: Current robot position (row, col).
        grid: Environment representation.

    Returns:
        List of (next_state, action, step_cost) triples. step_cost is always 1.
        Cells outside the grid and obstacle cells are excluded.
    """
    successors: List[Tuple[Position, str, int]] = []
    r, c = state
    for action, dr, dc in _ACTIONS:
        nxt = (r + dr, c + dc)
        if grid.is_free(nxt):
            successors.append((nxt, action, 1))
    return successors


def goal_test(state: Position, goal_state: Position) -> bool:
    """Return True if ``state`` equals ``goal_state``."""
    return state == goal_state


def path_cost(path: Optional[Sequence[Position]]) -> int:
    """Return the total cost of a path.

    Each move costs 1, so the cost is ``len(path) - 1``.
    Empty path, None, or a single-state path all return 0.
    """
    if not path:
        return 0
    return max(0, len(path) - 1)


def heuristic(state: Position, goal_state: Position) -> int:
    """Manhattan distance estimate from ``state`` to ``goal_state``.

    Why this heuristic is appropriate
    ---------------------------------
    Movement is four-directional with unit step cost, so the Manhattan
    distance |dr| + |dc| is the length of the shortest path on an empty grid.
    Obstacles can only lengthen real paths, never shorten them, so h never
    overestimates the true cost (admissible). It is also consistent:
    h(n) <= c(n, n') + h(n') for every successor n', which means A* with a
    closed set (graph-search) remains optimal.
    """
    return abs(state[0] - goal_state[0]) + abs(state[1] - goal_state[1])


def reconstruct_path(
    parent: Dict[Position, Optional[Position]],
    goal: Position,
) -> List[Position]:
    """Rebuild the start→goal path by following the parent map backwards."""
    path: List[Position] = [goal]
    current: Optional[Position] = goal
    while current is not None:
        prev = parent.get(current)
        if prev is None:
            break
        path.append(prev)
        current = prev
    path.reverse()
    return path


def validate_path(grid: Grid, path: Optional[Sequence[Position]]) -> bool:
    """Return True if ``path`` is a valid walk on ``grid``.

    Checks: every cell in bounds, not an obstacle, and consecutive cells
    are adjacent (Manhattan distance exactly 1). An empty/None path is
    considered invalid. A single-cell path is valid if that cell is free.
    """
    if not path:
        return False
    for pos in path:
        if not grid.is_free(pos):
            return False
    for a, b in zip(path, path[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            return False
    return True


def _normalize_algorithm(algorithm: str) -> str:
    """Map user-facing names to an internal key; raise ValueError if unknown."""
    key = algorithm.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    aliases = {
        "bfs": "bfs",
        "astar": "astar",
        "a*": "astar",
        "ucs": "ucs",
        "uniformcost": "ucs",
        "uniformcostsearch": "ucs",
        "greedy": "greedy",
        "greedybestfirst": "greedy",
    }
    if key not in aliases:
        raise ValueError(
            f"Unknown algorithm {algorithm!r}. "
            f"Supported: {', '.join(SUPPORTED_ALGORITHMS)} "
            f"(also accept 'A*')."
        )
    return aliases[key]


def _invalid_endpoint_message(grid: Grid, start: Position, goal: Position) -> Optional[str]:
    """Return a failure reason if start/goal cannot be used, else None."""
    if not grid.is_in_bounds(start):
        return f"Start {start} is out of bounds"
    if not grid.is_in_bounds(goal):
        return f"Goal {goal} is out of bounds"
    if grid.is_obstacle(start):
        return f"Start {start} is an obstacle"
    if grid.is_obstacle(goal):
        return f"Goal {goal} is an obstacle"
    return None


def _bfs(grid: Grid, start: Position, goal: Position) -> SearchResult:
    """Breadth-first search (uninformed, optimal for unit costs).

    FIFO queue, explored set, parent dict. A node is counted as expanded
    when it is popped from the frontier and its successors are generated.
    Goal test is performed on pop (same convention as A*).
    """
    frontier: deque[Position] = deque([start])
    frontier_set: Set[Position] = {start}
    parent: Dict[Position, Optional[Position]] = {start: None}
    expanded_order: List[Position] = []
    frontier_max = 1
    nodes_expanded = 0

    while frontier:
        frontier_max = max(frontier_max, len(frontier))
        current = frontier.popleft()
        frontier_set.discard(current)
        nodes_expanded += 1
        expanded_order.append(current)

        if goal_test(current, goal):
            path = reconstruct_path(parent, goal)
            return SearchResult(
                path=path,
                cost=path_cost(path),
                nodes_expanded=nodes_expanded,
                expanded_order=expanded_order,
                frontier_max_size=frontier_max,
                algorithm="bfs",
                found=True,
                message="Path found",
            )

        for nxt, _action, _cost in get_successors(current, grid):
            if nxt not in parent:
                parent[nxt] = current
                frontier.append(nxt)
                frontier_set.add(nxt)

    return SearchResult(
        path=None,
        cost=None,
        nodes_expanded=nodes_expanded,
        expanded_order=expanded_order,
        frontier_max_size=frontier_max,
        algorithm="bfs",
        found=False,
        message="No path found",
    )


def _best_first(
    grid: Grid,
    start: Position,
    goal: Position,
    algorithm: str,
) -> SearchResult:
    """Shared priority-queue search for A*, UCS, and Greedy.

    Optional extras
    ---------------
    * ``ucs`` — uniform-cost search, ordered by g (path cost so far).
    * ``greedy`` — greedy best-first, ordered by h only (not optimal).

    Priority key is (primary, secondary, insertion_counter) for deterministic
    tie-breaking. Stale heap entries are skipped via a best_g / closed set.
    Expansion is counted when a node is popped and not already closed.
    Goal test is performed on pop.
    """
    counter = 0
    # (priority_tuple, insertion_counter, state, g)
    heap: List[Tuple[Tuple[int, int, int], int, Position, int]] = []

    def priority(g: int, state: Position) -> Tuple[int, int, int]:
        h = heuristic(state, goal)
        if algorithm == "astar":
            return (g + h, h, counter)
        if algorithm == "ucs":
            return (g, h, counter)
        # greedy
        return (h, g, counter)

    heappush(heap, (priority(0, start), counter, start, 0))
    counter += 1

    parent: Dict[Position, Optional[Position]] = {start: None}
    best_g: Dict[Position, int] = {start: 0}
    closed: Set[Position] = set()
    expanded_order: List[Position] = []
    frontier_max = 1
    nodes_expanded = 0
    # Approximate frontier size: entries not yet closed.
    in_frontier: Set[Position] = {start}

    while heap:
        frontier_max = max(frontier_max, len(in_frontier))
        _prio, _cnt, current, g = heappop(heap)
        in_frontier.discard(current)

        if current in closed:
            continue
        # Skip stale entries with a worse g than the best known.
        if g > best_g.get(current, g):
            continue

        nodes_expanded += 1
        expanded_order.append(current)
        closed.add(current)

        if goal_test(current, goal):
            path = reconstruct_path(parent, goal)
            return SearchResult(
                path=path,
                cost=path_cost(path),
                nodes_expanded=nodes_expanded,
                expanded_order=expanded_order,
                frontier_max_size=frontier_max,
                algorithm=algorithm,
                found=True,
                message="Path found",
            )

        for nxt, _action, step in get_successors(current, grid):
            new_g = g + step
            if nxt in closed:
                continue
            if new_g < best_g.get(nxt, float("inf")):
                best_g[nxt] = new_g
                parent[nxt] = current
                heappush(heap, (priority(new_g, nxt), counter, nxt, new_g))
                counter += 1
                in_frontier.add(nxt)

    return SearchResult(
        path=None,
        cost=None,
        nodes_expanded=nodes_expanded,
        expanded_order=expanded_order,
        frontier_max_size=frontier_max,
        algorithm=algorithm,
        found=False,
        message="No path found",
    )


def search_with_trace(
    grid: Grid,
    start: Position,
    goal: Position,
    algorithm: str,
) -> SearchResult:
    """Run a search algorithm and return a full :class:`SearchResult` trace.

    Args:
        grid: Environment.
        start: Starting position.
        goal: Target position.
        algorithm: One of bfs, astar (A*), ucs, greedy.

    Returns:
        SearchResult with path/cost/trace fields. On failure ``found`` is False
        and ``path`` / ``cost`` are None (nodes_expanded still reported).

    Raises:
        ValueError: If ``algorithm`` is not supported.
    """
    algo = _normalize_algorithm(algorithm)
    t0 = time.perf_counter()

    reason = _invalid_endpoint_message(grid, start, goal)
    if reason is not None:
        return SearchResult(
            path=None,
            cost=None,
            nodes_expanded=0,
            expanded_order=[],
            frontier_max_size=0,
            runtime_seconds=time.perf_counter() - t0,
            algorithm=algo,
            found=False,
            message=reason,
        )

    # Start == goal: already there — zero expansions.
    if start == goal:
        return SearchResult(
            path=[start],
            cost=0,
            nodes_expanded=0,
            expanded_order=[],
            frontier_max_size=0,
            runtime_seconds=time.perf_counter() - t0,
            algorithm=algo,
            found=True,
            message="Start equals goal (zero expansions)",
        )

    if algo == "bfs":
        result = _bfs(grid, start, goal)
    else:
        result = _best_first(grid, start, goal, algo)

    result.runtime_seconds = time.perf_counter() - t0
    result.algorithm = algo
    return result


def search(
    grid: Grid,
    start: Position,
    goal: Position,
    algorithm: str,
) -> Tuple[Optional[List[Position]], Optional[int], int]:
    """Find a path from ``start`` to ``goal`` using ``algorithm``.

    Args:
        grid: Environment representation.
        start: Starting position.
        goal: Target position.
        algorithm: \"bfs\", \"astar\" (also \"A*\"), optional \"ucs\" / \"greedy\".

    Returns:
        (path, cost, nodes_expanded).
        path is a list of (row, col) from start to goal inclusive, or None.
        If start == goal: ([start], 0, 0).
        If no path / invalid endpoints: (None, None, nodes_expanded).

    Raises:
        ValueError: Unknown algorithm name.
    """
    result = search_with_trace(grid, start, goal, algorithm)
    return result.path, result.cost, result.nodes_expanded


def compare_algorithms(
    grid: Grid,
    start: Position,
    goal: Position,
    algorithms: Sequence[str] = ("bfs", "astar"),
) -> List[SearchResult]:
    """Run several algorithms on the same start/goal and return their traces."""
    return [search_with_trace(grid, start, goal, algo) for algo in algorithms]


def format_comparison_table(results: Sequence[SearchResult]) -> str:
    """Format search results as a plain-text comparison table."""
    headers = (
        "Algorithm",
        "Path found",
        "Cost",
        "Nodes expanded",
        "Max frontier",
        "Time (ms)",
    )
    rows: List[Tuple[str, ...]] = [headers]
    for r in results:
        rows.append(
            (
                r.algorithm,
                "yes" if r.found else "no",
                "-" if r.cost is None else str(r.cost),
                str(r.nodes_expanded),
                str(r.frontier_max_size),
                f"{r.runtime_seconds * 1000:.2f}",
            )
        )

    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    lines: List[str] = []
    for i, row in enumerate(rows):
        line = " | ".join(cell.ljust(widths[j]) for j, cell in enumerate(row))
        lines.append(line)
        if i == 0:
            lines.append("-+-".join("-" * w for w in widths))
    return "\n".join(lines)
