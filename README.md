# SafayeWala

**Smart cleaning, planned by AI.**

Desktop application for the CS-323 Artificial Intelligence term project: an intelligent vacuum-cleaning robot that navigates a grid with BFS / A*, and (when teammates deliver their modules) follows a CSP-generated cleaning schedule.

## Install

```bash
python -m pip install -r requirements.txt
```

Requires **Python 3.10+**.

## Run the GUI

```bash
python main.py
```

You should see a short animated splash, then the main window. Use the sidebar:

| Page | Purpose |
|------|---------|
| Environment | Load Sample / Ours / Error / any `.txt` |
| Search Lab | Pick start/goal, run BFS or A*, watch the wave |
| Full Mission | CSP schedule (or manual demo) + robot run |
| Compare | Multi-pair BFS vs A* table + charts |
| About | Course info and team list (`gui/team.py`) |

Keyboard: `Space` play/pause, `→` step, `R` reset, `Ctrl+O` open environment.

## Run tests

```bash
python -m pytest -q
```

GUI smoke tests use `QT_QPA_PLATFORM=offscreen` (set automatically in `tests/test_gui_smoke.py`).

## Project structure

```
core/                 # Part A — pure Python (no Qt)
  environment.py      # Grid, load_environment, validate, reachability
  graph_search.py     # get_successors, heuristic, BFS, A*, search_with_trace
data/
  Environment_Sample.txt
  Environment.txt         # our custom 10×10 map
  Environment_Error.txt   # unreachable dirty cell
gui/                  # Part B — PySide6
  backend.py          # ONLY file that imports csp / integration
  grid_widget.py      # animated canvas
  pages/ … widgets/
notebook_cells/
  member1_cells.py    # notebook-ready copy of Member 1 code
main.py
tests/
requirements.txt
```

## Environment file format

One logical item per line (blank lines allowed):

```
8,8
6
(1,3), (2,3), (3,3), (4,3), (5,3), (6,3)
4
(0,7), (3,7), (7,7), (7,0)
(0,0)
```

1. `rows,cols`
2. Number of obstacles
3. Obstacle coordinates
4. Number of dirty locations
5. Dirty coordinates (order defines D1, D2, …)
6. Charging station

Coordinates are **zero-based**; top-left is `(0,0)`.

### Our environment (`data/Environment.txt`) ASCII

```
    0  1  2  3  4  5  6  7  8  9
 0  C  .  .  .  .  .  .  .  . D1
 1  .  .  X  .  .  .  .  .  .  .
 2  .  .  X  .  .  X  .  .  .  .
 3  .  .  X  .  .  X  .  .  .  .
 4  .  .  X  .  .  X  .  .  . D2
 5  .  .  X  .  .  X  . D5 .  .
 6  .  .  .  .  .  X  .  .  .  .
 7  .  .  .  .  .  .  .  .  .  .
 8  .  .  .  .  .  .  .  .  .  .
 9 D4  .  .  .  .  .  .  .  . D3
```

Two wall segments with gaps so BFS and A* expand differently on long routes.

## Core API (Member 1)

```python
from core import load_environment, search, search_with_trace

grid = load_environment("data/Environment_Sample.txt")
path, cost, nodes = search(grid, (0, 0), (7, 0), "bfs")
result = search_with_trace(grid, (0, 0), (7, 0), "astar")
```

Required function signatures:

- `get_successors(state, grid) -> list[tuple[next_state, action, step_cost]]`
- `goal_test(state, goal_state) -> bool`
- `path_cost(path) -> int`
- `heuristic(state, goal_state) -> int`  (Manhattan; admissible & consistent)
- `search(grid, start, goal, algorithm) -> (path, cost, nodes_expanded)`

Action expansion order is always **UP, DOWN, LEFT, RIGHT**.

### Sample note: station → D4 `(0,0) → (7,0)`

Optimal cost is **7** (Manhattan). The wall at column 3 does **not** block column 0, so the robot walks straight down the left edge. Cost 14 is the Manhattan / optimal cost for `(0,0) → (7,7)` (D3).

## What other members must provide

The GUI adapter (`gui/backend.py`) is the **only** place that imports teammate code. It never fakes CSP results.

### Member 2 — CSP (`csp.py`)

```python
def load_schedule(filepath_or_text):
    """Parse Schedule.txt → dict with keys:
    variables, domains, constraints
    """

def backtracking_search(variables, domains, constraints):
    """Return assignment dict { "D1": "T1", ... } or None / {} on failure."""
```

### Member 3 — Integration (`integration.py`)

```python
def execute_schedule(grid, charging_station, schedule, algorithm):
    """schedule: ordered list of labels e.g. ["D1","D2","D3","D4"]
    Returns (complete_path, total_cost, success)
    or a richer object the adapter can normalize.
    """
```

Until those modules exist, **Full Mission** shows a banner and offers a **manual demo order** (drag chips). That path is clearly labeled `MANUAL DEMO — not a CSP result`.

Schedule `*.txt` files belong to Member 2 — this repo only notes them here.

## Part A vs Part B

| Part | Owner | Deliverable |
|------|-------|-------------|
| A | Member 1 | `core/`, `data/`, `tests/test_*.py`, `notebook_cells/` |
| B | Member 1 (GUI) | `gui/`, `main.py` |
| CSP | Member 2 | `csp.py` + `Schedule*.txt` |
| Integration | Member 3 | `integration.py` |
