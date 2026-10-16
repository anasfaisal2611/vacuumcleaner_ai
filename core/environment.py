"""Environment loading, validation, and Grid model for SafayeWala.

The environment file format (one logical item per line, in order):
  1. rows,cols
  2. number of obstacles
  3. obstacle coordinates as (row,col) tuples
  4. number of dirty locations
  5. dirty coordinates as (row,col) tuples
  6. charging station as (row,col)

Dirty labels D1, D2, ... are assigned in the order they appear in the file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set, Tuple, Union

# Zero-based (row, col). Top-left is (0, 0).
Position = Tuple[int, int]

_COORD_RE = re.compile(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)")


class EnvironmentFormatError(Exception):
    """Raised when an environment file is malformed (syntax / structure)."""

    def __init__(self, message: str, line_number: Optional[int] = None) -> None:
        """Create an error with an optional 1-based line number.

        Args:
            message: Human-readable description of the problem.
            line_number: 1-based source line, if known.
        """
        self.line_number = line_number
        if line_number is not None:
            full = f"Line {line_number}: {message}"
        else:
            full = message
        super().__init__(full)


@dataclass
class Grid:
    """Grid-based vacuum environment.

    Attributes:
        rows: Number of rows.
        cols: Number of columns.
        obstacles: Set of obstacle cell positions.
        dirty_locations: Ordered list of dirty cells (D1 is index 0).
        charging_station: Single charging-station position.
    """

    rows: int
    cols: int
    obstacles: Set[Position] = field(default_factory=set)
    dirty_locations: List[Position] = field(default_factory=list)
    charging_station: Position = (0, 0)

    def is_in_bounds(self, pos: Position) -> bool:
        """Return True if ``pos`` lies inside the grid."""
        r, c = pos
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_obstacle(self, pos: Position) -> bool:
        """Return True if ``pos`` is an obstacle cell."""
        return pos in self.obstacles

    def is_free(self, pos: Position) -> bool:
        """Return True if ``pos`` is in bounds and not an obstacle.

        Dirty cells and the charging station are free to walk on.
        """
        return self.is_in_bounds(pos) and not self.is_obstacle(pos)

    def task_label(self, index: int) -> str:
        """Return the task label for dirty location at ``index`` (0 -> \"D1\")."""
        if index < 0 or index >= len(self.dirty_locations):
            raise IndexError(f"Dirty index out of range: {index}")
        return f"D{index + 1}"

    def label_to_position(self, label: str) -> Position:
        """Map a label like \"D1\", \"D2\", or \"C\" / \"Station\" to a position.

        Args:
            label: Dirty label (\"D1\"..) or charging-station alias.

        Returns:
            The corresponding (row, col).

        Raises:
            KeyError: If the label is unknown.
        """
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
        """Return \"C\", \"Dk\", or None if the cell has no special label."""
        if pos == self.charging_station:
            return "C"
        for i, dirty in enumerate(self.dirty_locations):
            if dirty == pos:
                return self.task_label(i)
        return None

    def cell_type(self, pos: Position) -> str:
        """Return a single-character cell type: 'C', 'D', 'X', or '.'."""
        if not self.is_in_bounds(pos):
            raise ValueError(f"Out of bounds: {pos}")
        if pos in self.obstacles:
            return "X"
        if pos == self.charging_station:
            return "C"
        if pos in self.dirty_locations:
            return "D"
        return "."

    def to_matrix(self) -> List[List[str]]:
        """Return a 2D list of characters for printing ('C','D','X','.')."""
        matrix: List[List[str]] = []
        for r in range(self.rows):
            row: List[str] = []
            for c in range(self.cols):
                row.append(self.cell_type((r, c)))
            matrix.append(row)
        return matrix

    def render_text(
        self,
        path: Optional[Sequence[Position]] = None,
        cleaned: Optional[Iterable[Position]] = None,
    ) -> str:
        """Return an ASCII rendering of the grid.

        Args:
            path: Optional path to mark with '*' (start/end keep their symbols).
            cleaned: Optional dirty cells that have already been cleaned.

        Returns:
            Multi-line ASCII string.
        """
        cleaned_set = set(cleaned or [])
        path_set = set(path or [])
        lines: List[str] = []
        header = "   " + " ".join(str(c) for c in range(self.cols))
        lines.append(header)
        for r in range(self.rows):
            cells: List[str] = []
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
    """Return (1-based line number, stripped content) for non-blank lines."""
    result: List[Tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if stripped:
            result.append((i, stripped))
    return result


def _parse_coords(text: str, line_number: int, expected: Optional[int] = None) -> List[Position]:
    """Parse all (row,col) tuples from a line.

    Args:
        text: Source line text.
        line_number: 1-based line number for error messages.
        expected: If given, require exactly this many coordinates.

    Returns:
        List of positions in the order they appear.
    """
    coords = [(int(m.group(1)), int(m.group(2))) for m in _COORD_RE.finditer(text)]
    # Reject leftover non-whitespace/comma/paren junk after stripping matches.
    residual = _COORD_RE.sub("", text)
    residual = re.sub(r"[\s,]+", "", residual)
    if residual:
        raise EnvironmentFormatError(
            f"Unexpected characters in coordinate list: {residual!r}",
            line_number,
        )
    if expected is not None and len(coords) != expected:
        raise EnvironmentFormatError(
            f"Expected {expected} coordinate(s), found {len(coords)}",
            line_number,
        )
    return coords


def load_environment(filepath: Union[str, Path]) -> Grid:
    """Load and parse an environment file into a :class:`Grid`.

    Tolerates extra spaces, blank lines, and Windows (CRLF) line endings.
    When the obstacle count is 0, an empty obstacle line is allowed (or the
    coordinate line may be omitted if the next non-blank line is the dirty count).

    Args:
        filepath: Path to the environment text file.

    Returns:
        Parsed :class:`Grid`.

    Raises:
        EnvironmentFormatError: On malformed structure or syntax.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(filepath)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise EnvironmentFormatError(f"Cannot read file: {exc}") from exc

    lines = _nonempty_lines(text)
    if len(lines) < 5:
        raise EnvironmentFormatError(
            "File too short: need dimensions, obstacle count, dirty count, "
            "dirty coordinates, and charging station (obstacle coords optional if count is 0)."
        )

    idx = 0

    # Line 1: rows,cols
    line_no, content = lines[idx]
    dim_match = re.fullmatch(r"(\d+)\s*,\s*(\d+)", content)
    if not dim_match:
        raise EnvironmentFormatError(
            f"Expected 'rows,cols', got {content!r}",
            line_no,
        )
    rows, cols = int(dim_match.group(1)), int(dim_match.group(2))
    if rows <= 0 or cols <= 0:
        raise EnvironmentFormatError("Grid dimensions must be positive", line_no)
    idx += 1

    # Line 2: obstacle count
    if idx >= len(lines):
        raise EnvironmentFormatError("Missing obstacle count")
    line_no, content = lines[idx]
    if not re.fullmatch(r"\d+", content):
        raise EnvironmentFormatError(
            f"Expected obstacle count (integer), got {content!r}",
            line_no,
        )
    n_obstacles = int(content)
    idx += 1

    # Line 3: obstacle coordinates (may be empty when count is 0)
    obstacles: List[Position] = []
    if n_obstacles == 0:
        # Optional empty / missing coordinate line.
        if idx < len(lines):
            peek_no, peek = lines[idx]
            if _COORD_RE.search(peek) or peek == "":
                obstacles = _parse_coords(peek, peek_no, expected=0)
                idx += 1
            # else: next line is dirty count — fine
    else:
        if idx >= len(lines):
            raise EnvironmentFormatError("Missing obstacle coordinates")
        line_no, content = lines[idx]
        obstacles = _parse_coords(content, line_no, expected=n_obstacles)
        idx += 1

    # Line 4: dirty count
    if idx >= len(lines):
        raise EnvironmentFormatError("Missing dirty-location count")
    line_no, content = lines[idx]
    if not re.fullmatch(r"\d+", content):
        raise EnvironmentFormatError(
            f"Expected dirty-location count (integer), got {content!r}",
            line_no,
        )
    n_dirty = int(content)
    idx += 1

    # Line 5: dirty coordinates
    if idx >= len(lines):
        raise EnvironmentFormatError("Missing dirty-location coordinates")
    line_no, content = lines[idx]
    dirty = _parse_coords(content, line_no, expected=n_dirty)
    idx += 1

    # Line 6: charging station
    if idx >= len(lines):
        raise EnvironmentFormatError("Missing charging-station coordinate")
    line_no, content = lines[idx]
    station_coords = _parse_coords(content, line_no, expected=1)
    charging_station = station_coords[0]
    idx += 1

    if idx < len(lines):
        extra_no, _ = lines[idx]
        raise EnvironmentFormatError(
            "Unexpected extra content after charging station",
            extra_no,
        )

    return Grid(
        rows=rows,
        cols=cols,
        obstacles=set(obstacles),
        dirty_locations=list(dirty),
        charging_station=charging_station,
    )


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

    # Declared counts are already checked at parse time against list lengths;
    # still verify internal consistency of the Grid object.
    if len(grid.obstacles) != len(set(grid.obstacles)):
        problems.append("Duplicate obstacle coordinates")

    seen_dirty: Set[Position] = set()
    for i, pos in enumerate(grid.dirty_locations):
        if pos in seen_dirty:
            problems.append(f"Duplicate dirty location at {pos}")
        seen_dirty.add(pos)

    # Overlaps
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

    Args:
        grid: Environment to analyse.

    Returns:
        Sorted list of labels such as [\"D2\", \"D4\"] (by numeric order).
    """
    if not grid.is_free(grid.charging_station):
        # Station itself blocked / invalid — everything dirty is unreachable.
        return [grid.task_label(i) for i in range(len(grid.dirty_locations))]

    from collections import deque

    visited: Set[Position] = set()
    queue: deque[Position] = deque([grid.charging_station])
    visited.add(grid.charging_station)

    # Local 4-neighbour expansion (UP, DOWN, LEFT, RIGHT).
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
