"""Load Member 1 Part A symbols from ``CS-24058.ipynb`` (source of truth).

The Jupyter notebook holds the graph-search implementation.  This module
executes only the *definition* code cells in Part A (imports, Grid/loader,
helpers, BFS/A*) and exposes them for ``core/``, the API, and pytest.

The demo cell and Ramina's CSP Part B are never executed here.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List

_NOTEBOOK = Path(__file__).resolve().parent / "CS-24058.ipynb"

# Code cell indices inside Part A that define reusable symbols (not the demo).
_PART_A_DEFINITION_CELLS = (2, 4, 6, 8)

_CACHE: Dict[str, Any] | None = None


def _part_a_ended(source: str) -> bool:
    """True when we hit the Part B separator / CSP section."""
    head = source.lstrip()[:80]
    return head.startswith("# Part B") or "CSP Scheduling" in source[:120]


def load_part_a_namespace() -> Dict[str, Any]:
    """Execute Part A definition cells and return their global namespace."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    nb = json.loads(_NOTEBOOK.read_text(encoding="utf-8"))
    cells = nb["cells"]
    ns: Dict[str, Any] = {"__name__": "notebook_cells.part_a"}

    # Prefer the known definition indices; fall back to "all code until Part B
    # except the last demo code cell" if the notebook is rearranged.
    indices: List[int] = []
    if all(i < len(cells) and cells[i]["cell_type"] == "code" for i in _PART_A_DEFINITION_CELLS):
        indices = list(_PART_A_DEFINITION_CELLS)
    else:
        code_indices: List[int] = []
        for i, cell in enumerate(cells):
            src = "".join(cell.get("source", []))
            if _part_a_ended(src):
                break
            if cell.get("cell_type") == "code":
                code_indices.append(i)
        # Drop trailing demo cell (side-effecting prints / search runs).
        indices = code_indices[:-1] if len(code_indices) > 1 else code_indices

    for i in indices:
        src = "".join(cells[i].get("source", []))
        exec(compile(src, f"{_NOTEBOOK.name}:cell_{i}", "exec"), ns, ns)

    required = (
        "Grid",
        "load_environment",
        "EnvironmentFormatError",
        "get_successors",
        "goal_test",
        "path_cost",
        "heuristic",
        "search",
        "search_with_trace",
        "SearchResult",
        "validate_path",
        "compare_algorithms",
        "format_comparison_table",
        "SUPPORTED_ALGORITHMS",
        "Position",
    )
    missing = [name for name in required if name not in ns]
    if missing:
        raise ImportError(
            f"Part A notebook is missing symbols: {missing}. "
            f"Check {_NOTEBOOK}."
        )

    _CACHE = ns
    return ns


def _export_into(module: ModuleType) -> None:
    """Copy Part A public names onto ``module``."""
    ns = load_part_a_namespace()
    for name, value in ns.items():
        if name.startswith("_") and name not in {"_ACTIONS", "_COORD_RE"}:
            continue
        if name in {"__name__", "__builtins__"}:
            continue
        setattr(module, name, value)


# Eagerly bind symbols at import time so ``from notebook_cells.part_a import X`` works.
_ns = load_part_a_namespace()
Grid = _ns["Grid"]
Position = _ns["Position"]
EnvironmentFormatError = _ns["EnvironmentFormatError"]
load_environment = _ns["load_environment"]
get_successors = _ns["get_successors"]
goal_test = _ns["goal_test"]
path_cost = _ns["path_cost"]
heuristic = _ns["heuristic"]
reconstruct_path = _ns["reconstruct_path"]
SearchResult = _ns["SearchResult"]
search = _ns["search"]
search_with_trace = _ns["search_with_trace"]
validate_path = _ns["validate_path"]
compare_algorithms = _ns["compare_algorithms"]
format_comparison_table = _ns["format_comparison_table"]
SUPPORTED_ALGORITHMS = _ns["SUPPORTED_ALGORITHMS"]

__all__ = [
    "EnvironmentFormatError",
    "Grid",
    "Position",
    "SUPPORTED_ALGORITHMS",
    "SearchResult",
    "compare_algorithms",
    "format_comparison_table",
    "get_successors",
    "goal_test",
    "heuristic",
    "load_environment",
    "load_part_a_namespace",
    "path_cost",
    "reconstruct_path",
    "search",
    "search_with_trace",
    "validate_path",
]
