"""Unit tests for notebook-parity CSP module."""

from __future__ import annotations

from pathlib import Path

from csp import backtracking_search, load_schedule

ROOT = Path(__file__).resolve().parent.parent
NB = ROOT / "notebook_cells"


def test_ours_schedule_expected_order() -> None:
    text = (NB / "schedule.txt").read_text(encoding="utf-8")
    variables = [f"D{i}" for i in range(1, 6)]
    problem = load_schedule(text, variables=variables)
    assignment = backtracking_search(
        problem["variables"], problem["domains"], problem["constraints"]
    )
    assert assignment is not None
    ordered = [
        t
        for t, _ in sorted(
            assignment.items(),
            key=lambda kv: int("".join(c for c in kv[1] if c.isdigit()) or 0),
        )
    ]
    # Notebook expected: T1:D2, T2:D4, T3:D1, T4:D3, T5:D5
    assert ordered == ["D2", "D4", "D1", "D3", "D5"]


def test_sample_schedule_feasible() -> None:
    text = (NB / "schedule_sample.txt").read_text(encoding="utf-8")
    problem = load_schedule(text, variables=["D1", "D2", "D3", "D4"])
    assignment = backtracking_search(
        problem["variables"], problem["domains"], problem["constraints"]
    )
    assert assignment is not None
    assert len(assignment) == 4
