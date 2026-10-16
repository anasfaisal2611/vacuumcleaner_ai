# %% [markdown]
# # SafayeWala — Member 1: Environment + Graph Search
#
# **Problem formulation**
# - **State:** robot position `(row, col)` (zero-based; top-left is `(0,0)`).
# - **Initial state:** the start position passed into `search`.
# - **Actions:** UP, DOWN, LEFT, RIGHT (no diagonals). An action is valid only
#   if the resulting cell is inside the grid and is not an obstacle.
# - **Transition model:** a valid action moves the robot to the neighbouring cell.
# - **Goal state:** the goal position passed into `search`.
# - **Step cost:** every valid move costs `1`.
#
# Dirty labels `D1..Dn` follow the order of dirty coordinates in the file.
# The charging station is the usual start / end of a full mission (Member 3).

# %%
from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from heapq import heappop, heappush
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

Position = Tuple[int, int]

# %% [markdown]
# ## Grid model and environment loader
#
# File format (one item per line):
# 1. `rows,cols`
# 2. number of obstacles
# 3. obstacle coordinates
# 4. number of dirty locations
# 5. dirty coordinates
# 6. charging station

# %%
class EnvironmentFormatError(Exception):
    """Raised when an environment file is malformed."""

    def __init__(self, message: str, line_number: Optional[int] = None) -> None:
        self.line_number = line_number
        full = f"Line {line_number}: {message}" if line_number is not None else message
        super().__init__(full)


_COORD_RE = re.compile(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)")


@dataclass
class Grid:
    """Grid-based vacuum environment."""

    rows: int
    cols: int
    obstacles: Set[Position] = field(default_factory=set)
    dirty_locations: List[Position] = field(default_factory=list)
    charging_station: Position = (0, 0)

    def is_in_bounds(self, pos: Position) -> bool:
        """Return True if pos lies inside the grid."""
        r, c = pos
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_obstacle(self, pos: Position) -> bool:
        """Return True if pos is an obstacle."""
        return pos in self.obstacles

    def is_free(self, pos: Position) -> bool:
        """Return True if pos is in bounds and not an obstacle."""
        return self.is_in_bounds(pos) and not self.is_obstacle(pos)

    def task_label(self, index: int) -> str:
        """Return Dk for dirty index (0 -> D1)."""
        return f"D{index + 1}"

    def label_to_position(self, label: str) -> Position:
        """Map D1../C/Station to a position."""
        normalized = label.strip().upper()
        if normalized in {"C", "STATION", "CHARGING", "CHARGING_STATION"}:
            return self.charging_station
        match = re.fullmatch(r"D(\d+)", normalized)
        if match:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(self.dirty_locations):
                return self.dirty_locations[idx]
        raise KeyError(f"Unknown label: {label}")

    def position_to_label(self, pos: Position) -> Optional[str]:
        """Return C, Dk, or None."""
        if pos == self.charging_station:
            return "C"
        for i, dirty in enumerate(self.dirty_locations):
            if dirty == pos:
                return self.task_label(i)
        return None

    def cell_type(self, pos: Position) -> str:
        """Return 'C', 'D', 'X', or '.'."""
        if pos in self.obstacles:
            return "X"
        if pos == self.charging_station:
            return "C"
        if pos in self.dirty_locations:
            return "D"
        return "."

    def to_matrix(self) -> List[List[str]]:
        """Return a 2D character matrix."""
        return [
            [self.cell_type((r, c)) for c in range(self.cols)]
            for r in range(self.rows)
        ]

    def render_text(
        self,
        path: Optional[Sequence[Position]] = None,
        cleaned: Optional[Iterable[Position]] = None,
    ) -> str:
        """ASCII rendering; path cells marked with *."""
        cleaned_set = set(cleaned or [])
        path_set = set(path or [])
        lines = ["   " + " ".join(str(c) for c in range(self.cols))]
        for r in range(self.rows):
            cells = []
            for c in range(self.cols):
                pos = (r, c)
                ch = self.cell_type(pos)
                if pos in cleaned_set and ch == "D":
                    ch = "+"
                elif pos in path_set and ch == ".":
                    ch = "*"
                label = self.position_to_label(pos)
                if label and label.startswith("D") and pos not in cleaned_set:
                    cells.append(f"{label:>2}")
                else:
                    cells.append(f"{ch:>2}")
            lines.append(f"{r:2} " + " ".join(cells))
        return "\n".join(lines)


def _nonempty_lines(text: str) -> List[Tuple[int, str]]:
    """Return (1-based line number, content) for non-blank lines."""
    return [(i, raw.strip()) for i, raw in enumerate(text.splitlines(), 1) if raw.strip()]


def _parse_coords(text: str, line_number: int, expected: Optional[int] = None) -> List[Position]:
    """Parse (row,col) tuples from a line."""
    coords = [(int(m.group(1)), int(m.group(2))) for m in _COORD_RE.finditer(text)]
    residual = re.sub(r"[\s,]+", "", _COORD_RE.sub("", text))
    if residual:
        raise EnvironmentFormatError(f"Unexpected characters: {residual!r}", line_number)
    if expected is not None and len(coords) != expected:
        raise EnvironmentFormatError(
            f"Expected {expected} coordinate(s), found {len(coords)}", line_number
        )
    return coords


def load_environment(filepath: Union[str, Path]) -> Grid:
    """Load an environment text file into a Grid."""
    text = Path(filepath).read_text(encoding="utf-8")
    lines = _nonempty_lines(text)
    if len(lines) < 5:
        raise EnvironmentFormatError("File too short")

    idx = 0
    line_no, content = lines[idx]
    dim = re.fullmatch(r"(\d+)\s*,\s*(\d+)", content)
    if not dim:
        raise EnvironmentFormatError(f"Expected rows,cols, got {content!r}", line_no)
    rows, cols = int(dim.group(1)), int(dim.group(2))
    idx += 1

    line_no, content = lines[idx]
    n_obstacles = int(content)
    idx += 1

    obstacles: List[Position] = []
    if n_obstacles == 0:
        if idx < len(lines) and _COORD_RE.search(lines[idx][1]):
            obstacles = _parse_coords(lines[idx][1], lines[idx][0], expected=0)
            idx += 1
    else:
        obstacles = _parse_coords(lines[idx][1], lines[idx][0], expected=n_obstacles)
        idx += 1

    line_no, content = lines[idx]
    n_dirty = int(content)
    idx += 1
    dirty = _parse_coords(lines[idx][1], lines[idx][0], expected=n_dirty)
    idx += 1
    station = _parse_coords(lines[idx][1], lines[idx][0], expected=1)[0]

    return Grid(rows, cols, set(obstacles), list(dirty), station)

# %% [markdown]
# ## Required search helpers
#
# **Heuristic justification:** Manhattan distance is admissible and consistent
# for 4-directional unit-cost movement. Obstacles only make paths longer, so
# `h` never overestimates; A* with a closed set stays optimal.

# %%
_ACTIONS = (("UP", -1, 0), ("DOWN", 1, 0), ("LEFT", 0, -1), ("RIGHT", 0, 1))
SUPPORTED_ALGORITHMS = ("bfs", "astar", "ucs", "greedy")


def get_successors(state, grid):
    """Return [(next_state, action, step_cost), ...] in UP/DOWN/LEFT/RIGHT order."""
    successors = []
    r, c = state
    for action, dr, dc in _ACTIONS:
        nxt = (r + dr, c + dc)
        if grid.is_free(nxt):
            successors.append((nxt, action, 1))
    return successors


def goal_test(state, goal_state):
    """Return True if state equals goal_state."""
    return state == goal_state


def path_cost(path):
    """len(path)-1; empty/None/single-state -> 0."""
    if not path:
        return 0
    return max(0, len(path) - 1)


def heuristic(state, goal_state):
    """Manhattan distance (admissible + consistent for 4-dir unit cost)."""
    return abs(state[0] - goal_state[0]) + abs(state[1] - goal_state[1])


def reconstruct_path(parent, goal):
    """Rebuild start→goal path from the parent map."""
    path = [goal]
    current = goal
    while parent.get(current) is not None:
        current = parent[current]
        path.append(current)
    path.reverse()
    return path

# %% [markdown]
# ## BFS and A* (plus optional UCS / Greedy)

# %%
@dataclass
class SearchResult:
    """Full search trace for comparison and visualisation."""

    path: Optional[List[Position]]
    cost: Optional[int]
    nodes_expanded: int
    expanded_order: List[Position] = field(default_factory=list)
    frontier_max_size: int = 0
    runtime_seconds: float = 0.0
    algorithm: str = ""
    found: bool = False
    message: str = ""


def _normalize_algorithm(algorithm: str) -> str:
    key = algorithm.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    aliases = {
        "bfs": "bfs", "astar": "astar", "a*": "astar",
        "ucs": "ucs", "uniformcost": "ucs", "uniformcostsearch": "ucs",
        "greedy": "greedy", "greedybestfirst": "greedy",
    }
    if key not in aliases:
        raise ValueError(f"Unknown algorithm {algorithm!r}. Supported: {SUPPORTED_ALGORITHMS}")
    return aliases[key]


def _bfs(grid, start, goal):
    """BFS: FIFO queue; expand = pop + generate successors; goal test on pop."""
    frontier = deque([start])
    parent = {start: None}
    expanded_order = []
    frontier_max = 1
    nodes_expanded = 0
    while frontier:
        frontier_max = max(frontier_max, len(frontier))
        current = frontier.popleft()
        nodes_expanded += 1
        expanded_order.append(current)
        if goal_test(current, goal):
            path = reconstruct_path(parent, goal)
            return SearchResult(path, path_cost(path), nodes_expanded, expanded_order,
                                frontier_max, 0.0, "bfs", True, "Path found")
        for nxt, _, _ in get_successors(current, grid):
            if nxt not in parent:
                parent[nxt] = current
                frontier.append(nxt)
    return SearchResult(None, None, nodes_expanded, expanded_order, frontier_max,
                        0.0, "bfs", False, "No path found")


def _best_first(grid, start, goal, algorithm):
    """Shared priority-queue search for A* / UCS / Greedy."""
    counter = 0
    heap = []

    def priority(g, state):
        h = heuristic(state, goal)
        if algorithm == "astar":
            return (g + h, h, counter)
        if algorithm == "ucs":
            return (g, h, counter)
        return (h, g, counter)  # greedy (optional)

    heappush(heap, (priority(0, start), counter, start, 0))
    counter += 1
    parent = {start: None}
    best_g = {start: 0}
    closed = set()
    expanded_order = []
    frontier_max = 1
    nodes_expanded = 0
    in_frontier = {start}

    while heap:
        frontier_max = max(frontier_max, len(in_frontier))
        _, _, current, g = heappop(heap)
        in_frontier.discard(current)
        if current in closed or g > best_g.get(current, g):
            continue
        nodes_expanded += 1
        expanded_order.append(current)
        closed.add(current)
        if goal_test(current, goal):
            path = reconstruct_path(parent, goal)
            return SearchResult(path, path_cost(path), nodes_expanded, expanded_order,
                                frontier_max, 0.0, algorithm, True, "Path found")
        for nxt, _, step in get_successors(current, grid):
            if nxt in closed:
                continue
            new_g = g + step
            if new_g < best_g.get(nxt, float("inf")):
                best_g[nxt] = new_g
                parent[nxt] = current
                heappush(heap, (priority(new_g, nxt), counter, nxt, new_g))
                counter += 1
                in_frontier.add(nxt)
    return SearchResult(None, None, nodes_expanded, expanded_order, frontier_max,
                        0.0, algorithm, False, "No path found")


def search_with_trace(grid, start, goal, algorithm):
    """Run search and return a SearchResult trace."""
    algo = _normalize_algorithm(algorithm)
    t0 = time.perf_counter()
    if not grid.is_in_bounds(start) or grid.is_obstacle(start):
        return SearchResult(None, None, 0, [], 0, time.perf_counter() - t0, algo, False,
                            f"Invalid start {start}")
    if not grid.is_in_bounds(goal) or grid.is_obstacle(goal):
        return SearchResult(None, None, 0, [], 0, time.perf_counter() - t0, algo, False,
                            f"Invalid goal {goal}")
    if start == goal:
        return SearchResult([start], 0, 0, [], 0, time.perf_counter() - t0, algo, True,
                            "Start equals goal (zero expansions)")
    result = _bfs(grid, start, goal) if algo == "bfs" else _best_first(grid, start, goal, algo)
    result.runtime_seconds = time.perf_counter() - t0
    return result


def search(grid, start, goal, algorithm):
    """Return (path, cost, nodes_expanded)."""
    result = search_with_trace(grid, start, goal, algorithm)
    return result.path, result.cost, result.nodes_expanded


def format_comparison_table(results):
    """Plain-text comparison table."""
    headers = ("Algorithm", "Path found", "Cost", "Nodes expanded", "Max frontier", "Time (ms)")
    rows = [headers]
    for r in results:
        rows.append((
            r.algorithm,
            "yes" if r.found else "no",
            "-" if r.cost is None else str(r.cost),
            str(r.nodes_expanded),
            str(r.frontier_max_size),
            f"{r.runtime_seconds * 1000:.2f}",
        ))
    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    lines = []
    for i, row in enumerate(rows):
        lines.append(" | ".join(cell.ljust(widths[j]) for j, cell in enumerate(row)))
        if i == 0:
            lines.append("-+-".join("-" * w for w in widths))
    return "\n".join(lines)

# %% [markdown]
# ## Demo: sample environment, station → D4 `(7,0)`

# %%
# Adjust this path if the notebook lives elsewhere.
DATA_DIR = Path("data")
if not (DATA_DIR / "Environment_Sample.txt").exists():
    DATA_DIR = Path(__file__).resolve().parent.parent / "data"

grid = load_environment(DATA_DIR / "Environment_Sample.txt")
print(grid.render_text())
print()

start, goal = (0, 0), (7, 0)  # Station → D4
results = [search_with_trace(grid, start, goal, algo) for algo in ("bfs", "astar")]
print(format_comparison_table(results))
print()
if results[0].path:
    print("BFS path drawn on grid:")
    print(grid.render_text(path=results[0].path))
    print(f"\nOptimal cost: {results[0].cost} "
          f"(Manhattan={heuristic(start, goal)}; wall at col 3 does not block col 0)")
