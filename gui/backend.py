"""Adapter between the GUI and core / teammate modules.

This is the ONLY GUI file that imports teammate code (csp / integration).
If those modules are missing, methods degrade gracefully with clear messages.
Never fakes or claims a CSP result.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.environment import (
    EnvironmentFormatError,
    Grid,
    load_environment,
    unreachable_dirty_locations,
    validate_environment,
)
from core.graph_search import (
    SearchResult,
    compare_algorithms,
    format_comparison_table,
    search_with_trace,
)

logger = logging.getLogger("safayewala.backend")

Position = Tuple[int, int]

# Expected teammate APIs (document in README):
#   csp.backtracking_search(variables, domains, constraints) -> assignment | None
#   csp.load_schedule(filepath_or_text) -> schedule problem dict  (optional helper)
#   integration.execute_schedule(grid, charging_station, schedule, algorithm)
#       -> (complete_path, total_cost, success)  or a richer object


@dataclass
class MissionLeg:
    """One navigation leg of a mission."""

    from_pos: Position
    to_pos: Position
    from_label: str
    to_label: str
    path: Optional[List[Position]]
    cost: Optional[int]
    nodes_expanded: int
    expanded_order: List[Position] = field(default_factory=list)


@dataclass
class MissionResult:
    """Result of executing a cleaning schedule."""

    complete_path: List[Position]
    total_cost: int
    success: bool
    legs: List[MissionLeg]
    message: str
    schedule_source: str = "manual"  # "csp" | "manual"
    total_movements: int = 0


@dataclass
class BackendStatus:
    """Availability of teammate modules."""

    csp: bool
    integration: bool
    missing: List[str]


class Backend:
    """Facade used by all GUI pages."""

    def __init__(self) -> None:
        """Create a backend and probe for teammate modules once."""
        self._csp_module: Any = None
        self._integration_module: Any = None
        self._probe_modules()

    def _probe_modules(self) -> None:
        """Try importing csp and integration; log failures."""
        try:
            import csp as csp_mod  # type: ignore

            self._csp_module = csp_mod
            logger.info("CSP module loaded")
        except ImportError:
            self._csp_module = None
            logger.info("CSP module not found (waiting for Member 2)")

        try:
            import integration as integration_mod  # type: ignore

            self._integration_module = integration_mod
            logger.info("Integration module loaded")
        except ImportError:
            self._integration_module = None
            logger.info("Integration module not found (waiting for Member 3)")

    def status(self) -> BackendStatus:
        """Return which teammate modules are currently importable."""
        missing: List[str] = []
        if self._csp_module is None:
            missing.append("csp")
        if self._integration_module is None:
            missing.append("integration")
        return BackendStatus(
            csp=self._csp_module is not None,
            integration=self._integration_module is not None,
            missing=missing,
        )

    def load_environment(self, path: str | Path) -> Grid:
        """Load an environment file; re-raises EnvironmentFormatError."""
        return load_environment(path)

    def validate(self, grid: Grid, strict: bool = True) -> List[str]:
        """Return validation problems (empty = OK)."""
        return validate_environment(grid, strict=strict)

    def unreachable(self, grid: Grid) -> List[str]:
        """Return labels of unreachable dirty cells."""
        return unreachable_dirty_locations(grid)

    def run_search(
        self,
        grid: Grid,
        start: Position,
        goal: Position,
        algorithm: str,
    ) -> SearchResult:
        """Run a single search with full animation trace."""
        return search_with_trace(grid, start, goal, algorithm)

    def compare(
        self,
        grid: Grid,
        start: Position,
        goal: Position,
        algorithms: Sequence[str] = ("bfs", "astar"),
    ) -> List[SearchResult]:
        """Compare algorithms on one start/goal pair."""
        return compare_algorithms(grid, start, goal, algorithms)

    def compare_pairs(
        self,
        grid: Grid,
        pairs: Optional[Sequence[Tuple[Position, Position]]] = None,
        algorithms: Sequence[str] = ("bfs", "astar"),
    ) -> List[Dict[str, Any]]:
        """Compare algorithms across several pairs.

        If ``pairs`` is omitted, uses Station→each Dn and consecutive Dn pairs
        ending with Dn→Station.
        """
        if pairs is None:
            pairs = self.default_compare_pairs(grid)
        rows: List[Dict[str, Any]] = []
        for start, goal in pairs:
            for algo in algorithms:
                result = search_with_trace(grid, start, goal, algo)
                rows.append(
                    {
                        "pair": f"{self._label(grid, start)} → {self._label(grid, goal)}",
                        "start": start,
                        "goal": goal,
                        "algorithm": result.algorithm,
                        "found": result.found,
                        "cost": result.cost,
                        "nodes_expanded": result.nodes_expanded,
                        "frontier_max_size": result.frontier_max_size,
                        "runtime_ms": result.runtime_seconds * 1000.0,
                        "result": result,
                    }
                )
        return rows

    def default_compare_pairs(self, grid: Grid) -> List[Tuple[Position, Position]]:
        """Station→each Dn, consecutive dirty pairs, and last Dn→Station."""
        pairs: List[Tuple[Position, Position]] = []
        station = grid.charging_station
        dirty = grid.dirty_locations
        for d in dirty:
            pairs.append((station, d))
        for a, b in zip(dirty, dirty[1:]):
            pairs.append((a, b))
        if dirty:
            pairs.append((dirty[-1], station))
        return pairs

    @staticmethod
    def _label(grid: Grid, pos: Position) -> str:
        label = grid.position_to_label(pos)
        return label if label else f"{pos}"

    def insight_from_rows(self, rows: List[Dict[str, Any]]) -> str:
        """Auto-generate a short insight from comparison rows (not hardcoded)."""
        bfs_rows = [r for r in rows if r["algorithm"] == "bfs" and r["found"]]
        astar_rows = [r for r in rows if r["algorithm"] == "astar" and r["found"]]
        if not bfs_rows or not astar_rows:
            failed = sum(1 for r in rows if not r["found"])
            return (
                f"Some searches failed ({failed} row(s) with no path). "
                "Compare only completed pairs."
            )

        # Match by pair label
        by_pair: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for r in rows:
            by_pair.setdefault(r["pair"], {})[r["algorithm"]] = r

        equal_cost = 0
        fewer_astar = 0
        tie_expand = 0
        total = 0
        bfs_nodes = 0
        astar_nodes = 0
        for pair, algos in by_pair.items():
            if "bfs" not in algos or "astar" not in algos:
                continue
            b, a = algos["bfs"], algos["astar"]
            if not (b["found"] and a["found"]):
                continue
            total += 1
            bfs_nodes += b["nodes_expanded"]
            astar_nodes += a["nodes_expanded"]
            if b["cost"] == a["cost"]:
                equal_cost += 1
            if a["nodes_expanded"] < b["nodes_expanded"]:
                fewer_astar += 1
            elif a["nodes_expanded"] == b["nodes_expanded"]:
                tie_expand += 1

        if total == 0:
            return "No comparable successful pairs."

        if bfs_nodes == 0:
            pct = 0.0
        else:
            pct = 100.0 * (bfs_nodes - astar_nodes) / bfs_nodes

        parts = [
            f"Across {total} successful pair(s), BFS and A* agreed on cost "
            f"in {equal_cost}/{total} case(s)."
        ]
        if pct > 0.5:
            parts.append(
                f"A* expanded {pct:.0f}% fewer nodes overall "
                f"({astar_nodes} vs {bfs_nodes})."
            )
        elif pct < -0.5:
            parts.append(
                f"BFS expanded fewer nodes overall in this set "
                f"({bfs_nodes} vs {astar_nodes})."
            )
        else:
            parts.append(
                f"Node expansions were essentially tied "
                f"({astar_nodes} vs {bfs_nodes}; {tie_expand} per-pair ties)."
            )
        parts.append(f"A* expanded fewer nodes on {fewer_astar}/{total} pair(s).")
        return " ".join(parts)

    def rows_to_csv(self, rows: List[Dict[str, Any]]) -> str:
        """Serialize comparison rows to CSV text."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["Pair", "Algorithm", "Found", "Cost", "Nodes expanded", "Max frontier", "Time (ms)"]
        )
        for r in rows:
            writer.writerow(
                [
                    r["pair"],
                    r["algorithm"],
                    r["found"],
                    r["cost"],
                    r["nodes_expanded"],
                    r["frontier_max_size"],
                    f"{r['runtime_ms']:.2f}",
                ]
            )
        return buf.getvalue()

    def rows_to_text(self, rows: List[Dict[str, Any]]) -> str:
        """Plain-text table for clipboard copy."""
        # Reuse format_comparison_table for per-pair groups
        lines = ["Pair | Algorithm | Cost | Nodes | Frontier | Time (ms)"]
        lines.append("-" * 60)
        for r in rows:
            cost = "-" if r["cost"] is None else str(r["cost"])
            lines.append(
                f"{r['pair']} | {r['algorithm']} | {cost} | "
                f"{r['nodes_expanded']} | {r['frontier_max_size']} | "
                f"{r['runtime_ms']:.2f}"
            )
        return "\n".join(lines)

    def generate_schedule(
        self,
        grid: Grid,
        schedule_path: str | Path,
    ) -> Tuple[Optional[List[str]], Optional[Dict[str, str]], str]:
        """Generate a cleaning schedule via Member 2's CSP module.

        Returns:
            (ordered_labels, assignment_dict, message).
            ordered_labels is None when CSP is unavailable or fails.
        """
        if self._csp_module is None:
            return None, None, "CSP_NOT_AVAILABLE: CSP module not found yet (waiting for Member 2)"

        try:
            # Preferred helper if Member 2 provides it.
            if hasattr(self._csp_module, "load_schedule"):
                problem = self._csp_module.load_schedule(str(schedule_path))
                variables = problem.get("variables")
                domains = problem.get("domains")
                constraints = problem.get("constraints")
            else:
                return (
                    None,
                    None,
                    "CSP module found but load_schedule() is missing. "
                    "Expected load_schedule(filepath) plus "
                    "backtracking_search(variables, domains, constraints).",
                )

            assignment = self._csp_module.backtracking_search(
                variables, domains, constraints
            )
            if not assignment:
                return None, None, "CSP found no feasible schedule"

            # assignment: { "D1": "T2", ... } → order by time slot
            def slot_key(item: Tuple[str, str]) -> int:
                slot = item[1]
                digits = "".join(ch for ch in slot if ch.isdigit())
                return int(digits) if digits else 0

            ordered = [var for var, _slot in sorted(assignment.items(), key=slot_key)]
            return ordered, dict(assignment), "CSP schedule generated"
        except Exception as exc:  # noqa: BLE001 — surface to GUI
            logger.exception("CSP schedule generation failed")
            return None, None, f"CSP error: {exc}"

    def execute_mission(
        self,
        grid: Grid,
        schedule: Sequence[str],
        algorithm: str,
        schedule_source: str = "manual",
    ) -> MissionResult:
        """Execute a cleaning schedule.

        If schedule_source is \"csp\" and integration is missing, returns a
        failure MissionResult with INTEGRATION_NOT_AVAILABLE.
        If schedule_source is \"manual\", runs legs via core.graph_search.search
        so the animation can be demoed without Member 3.
        """
        if schedule_source == "csp" and self._integration_module is None:
            return MissionResult(
                complete_path=[],
                total_cost=0,
                success=False,
                legs=[],
                message="INTEGRATION_NOT_AVAILABLE: Integration module not found yet (waiting for Member 3)",
                schedule_source="csp",
            )

        if schedule_source == "csp" and self._integration_module is not None:
            try:
                result = self._integration_module.execute_schedule(
                    grid,
                    grid.charging_station,
                    list(schedule),
                    algorithm,
                )
                return self._normalize_integration_result(grid, result, schedule)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Integration execute_schedule failed")
                return MissionResult(
                    complete_path=[],
                    total_cost=0,
                    success=False,
                    legs=[],
                    message=f"Integration error: {exc}",
                    schedule_source="csp",
                )

        # Manual demo path — clearly tagged, never claimed as CSP.
        return self._execute_manual(grid, list(schedule), algorithm)

    def _normalize_integration_result(
        self,
        grid: Grid,
        result: Any,
        schedule: Sequence[str],
    ) -> MissionResult:
        """Accept either a tuple or an object from execute_schedule."""
        if isinstance(result, MissionResult):
            result.schedule_source = "csp"
            return result
        if isinstance(result, (tuple, list)) and len(result) >= 3:
            complete_path, total_cost, success = result[0], result[1], result[2]
            path = list(complete_path or [])
            return MissionResult(
                complete_path=path,
                total_cost=int(total_cost or 0),
                success=bool(success),
                legs=[],
                message="Mission complete" if success else "Mission failed",
                schedule_source="csp",
                total_movements=max(0, len(path) - 1) if path else 0,
            )
        return MissionResult(
            complete_path=[],
            total_cost=0,
            success=False,
            legs=[],
            message="Unexpected return type from execute_schedule",
            schedule_source="csp",
        )

    def _execute_manual(
        self,
        grid: Grid,
        schedule: List[str],
        algorithm: str,
    ) -> MissionResult:
        """Run Station → each label → Station using core search only."""
        legs: List[MissionLeg] = []
        complete: List[Position] = []
        current = grid.charging_station
        total_cost = 0

        waypoints: List[Tuple[str, Position]] = []
        for label in schedule:
            try:
                waypoints.append((label, grid.label_to_position(label)))
            except KeyError:
                return MissionResult(
                    complete_path=[],
                    total_cost=0,
                    success=False,
                    legs=[],
                    message=f"Unknown label in schedule: {label}",
                    schedule_source="manual",
                )
        waypoints.append(("C", grid.charging_station))

        from_label = "C"
        for to_label, goal in waypoints:
            result = search_with_trace(grid, current, goal, algorithm)
            leg = MissionLeg(
                from_pos=current,
                to_pos=goal,
                from_label=from_label,
                to_label=to_label,
                path=result.path,
                cost=result.cost,
                nodes_expanded=result.nodes_expanded,
                expanded_order=result.expanded_order,
            )
            legs.append(leg)
            if not result.found or result.path is None:
                return MissionResult(
                    complete_path=complete,
                    total_cost=total_cost,
                    success=False,
                    legs=legs,
                    message=(
                        f"MANUAL DEMO — no path for leg {from_label} → {to_label}: "
                        f"{result.message}"
                    ),
                    schedule_source="manual",
                    total_movements=max(0, len(complete) - 1) if complete else 0,
                )
            # Append path, avoiding duplicated shared endpoint.
            if not complete:
                complete.extend(result.path)
            else:
                complete.extend(result.path[1:])
            total_cost += result.cost or 0
            current = goal
            from_label = to_label

        return MissionResult(
            complete_path=complete,
            total_cost=total_cost,
            success=True,
            legs=legs,
            message="MANUAL DEMO — mission complete (not a CSP result)",
            schedule_source="manual",
            total_movements=max(0, len(complete) - 1),
        )

    def save_environment(self, grid: Grid, path: str | Path) -> None:
        """Write a Grid back out in the exact required file format."""
        obstacles = sorted(grid.obstacles)
        dirty = list(grid.dirty_locations)
        obs_str = ", ".join(f"({r},{c})" for r, c in obstacles)
        dirty_str = ", ".join(f"({r},{c})" for r, c in dirty)
        sr, sc = grid.charging_station
        text = (
            f"{grid.rows},{grid.cols}\n"
            f"{len(obstacles)}\n"
            f"{obs_str}\n"
            f"{len(dirty)}\n"
            f"{dirty_str}\n"
            f"({sr},{sc})\n"
        )
        Path(path).write_text(text, encoding="utf-8")


# Re-export for convenience
__all__ = [
    "Backend",
    "BackendStatus",
    "EnvironmentFormatError",
    "MissionLeg",
    "MissionResult",
    "format_comparison_table",
]
