"""Tests for core.environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.environment import (
    EnvironmentFormatError,
    load_environment,
    unreachable_dirty_locations,
    validate_environment,
)

DATA = Path(__file__).resolve().parent.parent / "data"


def test_load_sample_environment() -> None:
    """Sample file matches the course handout values."""
    grid = load_environment(DATA / "Environment_Sample.txt")
    assert grid.rows == 8 and grid.cols == 8
    assert len(grid.obstacles) == 6
    assert grid.dirty_locations == [(0, 7), (3, 7), (7, 7), (7, 0)]
    assert grid.charging_station == (0, 0)
    assert grid.task_label(0) == "D1"
    assert grid.label_to_position("D4") == (7, 0)
    assert grid.cell_type((1, 3)) == "X"
    assert grid.cell_type((0, 0)) == "C"
    assert validate_environment(grid) == []
    assert validate_environment(grid, strict=True) == []
    assert unreachable_dirty_locations(grid) == []


def test_our_environment_passes_strict() -> None:
    """Custom Environment.txt meets project minimums and is fully reachable."""
    grid = load_environment(DATA / "Environment.txt")
    assert grid.rows == 10 and grid.cols == 10
    assert len(grid.obstacles) >= 6
    assert len(grid.dirty_locations) >= 4
    assert validate_environment(grid, strict=True) == []
    assert unreachable_dirty_locations(grid) == []


def test_error_environment_unreachable() -> None:
    """Error case loads cleanly but reports an unreachable dirty label."""
    grid = load_environment(DATA / "Environment_Error.txt")
    assert validate_environment(grid) == []
    unreachable = unreachable_dirty_locations(grid)
    assert len(unreachable) >= 1
    # Enclosed cell is the last dirty location (2,2) -> D4
    assert "D4" in unreachable


def test_malformed_dimensions(tmp_path: Path) -> None:
    """Bad dimensions raise EnvironmentFormatError with a line number."""
    path = tmp_path / "bad.txt"
    # Enough non-blank lines so the dimension parser runs (not the short-file check).
    path.write_text(
        "nope\n6\n(1,1), (2,2), (3,3), (4,4), (5,5), (6,6)\n"
        "4\n(0,7), (3,7), (7,7), (7,0)\n(0,0)\n",
        encoding="utf-8",
    )
    with pytest.raises(EnvironmentFormatError) as exc:
        load_environment(path)
    assert exc.value.line_number == 1
    assert "rows,cols" in str(exc.value)


def test_malformed_coord_count(tmp_path: Path) -> None:
    """Wrong number of obstacle coordinates raises a clear error."""
    path = tmp_path / "bad_count.txt"
    path.write_text(
        "8,8\n2\n(1,1)\n4\n(0,7), (3,7), (7,7), (7,0)\n(0,0)\n",
        encoding="utf-8",
    )
    with pytest.raises(EnvironmentFormatError) as exc:
        load_environment(path)
    assert "Expected 2" in str(exc.value)


def test_overlap_detected(tmp_path: Path) -> None:
    """Validator reports charging-station / obstacle overlap."""
    path = tmp_path / "overlap.txt"
    path.write_text(
        "8,8\n1\n(0,0)\n4\n(0,7), (3,7), (7,7), (7,0)\n(0,0)\n",
        encoding="utf-8",
    )
    grid = load_environment(path)
    problems = validate_environment(grid)
    assert any("overlap" in p.lower() for p in problems)


def test_duplicate_dirty_detected(tmp_path: Path) -> None:
    """Duplicate dirty coordinates are reported by the validator."""
    path = tmp_path / "dup.txt"
    path.write_text(
        "8,8\n0\n\n4\n(0,7), (0,7), (7,7), (7,0)\n(0,0)\n",
        encoding="utf-8",
    )
    grid = load_environment(path)
    problems = validate_environment(grid)
    assert any("duplicate" in p.lower() for p in problems)


def test_render_and_matrix() -> None:
    """to_matrix / render_text produce consistent characters."""
    grid = load_environment(DATA / "Environment_Sample.txt")
    matrix = grid.to_matrix()
    assert matrix[0][0] == "C"
    assert matrix[1][3] == "X"
    assert matrix[0][7] == "D"
    text = grid.render_text(path=[(0, 0), (0, 1), (0, 2)])
    assert "C" in text
