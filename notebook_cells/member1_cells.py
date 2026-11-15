"""Member 1 demo script — thin wrapper around the notebook Part A source.

Canonical code lives in ``CS-24058.ipynb`` (Part A) and is loaded by
``notebook_cells.part_a``.  Run this file to print a BFS vs A* comparison
without opening Jupyter:

    python -m notebook_cells.member1_cells
"""

from __future__ import annotations

from pathlib import Path

from notebook_cells.part_a import (
    compare_algorithms,
    format_comparison_table,
    load_environment,
)

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = [
    ROOT / "data" / "Environment_Sample.txt",
    ROOT / "notebook_cells" / "Environment.txt",
    ROOT / "data" / "Environment.txt",
]


def main() -> None:
    env_path = next((p for p in CANDIDATES if p.exists()), None)
    if env_path is None:
        raise SystemExit("No Environment*.txt found under data/ or notebook_cells/")

    grid = load_environment(env_path)
    print(f"Loaded {env_path} — {grid.rows}x{grid.cols}")
    print(grid.render_text())
    start = grid.charging_station
    # Prefer D4 if present (sample Station→D4 cost 7), else first dirty cell.
    goal = (
        grid.label_to_position("D4")
        if len(grid.dirty_locations) >= 4
        else grid.dirty_locations[0]
    )
    results = compare_algorithms(grid, start, goal)
    print(format_comparison_table(results))
    print(grid.render_text(path=results[0].path))


if __name__ == "__main__":
    main()
