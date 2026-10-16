"""Adapter — the ONLY module that imports teammate CSP / integration code.

Expected teammate signatures (see README):
  csp.backtracking_search(variables, domains, constraints)
  csp.load_schedule(filepath_or_text)
  integration.execute_schedule(grid, charging_station, schedule, algorithm)
"""

from __future__ import annotations

import logging
import tempfile
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
from core.graph_search import SearchResult, search_with_trace

logger = logging.getLogger("safayewala.adapter")

Position = Tuple[int, int]
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class MissionLeg:
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
    complete_path: List[Position]
    total_cost: int
    success: bool
    legs: List[MissionLeg]
    message: str
    schedule_source: str
    total_movements: int = 0


@dataclass
class BackendStatus:
    csp: bool
    integration: bool
    missing: List[str]


class Adapter:
    """Bridge between HTTP handlers and core / teammate modules."""

    def __init__(self) -> None:
        self._csp: Any = None
        self._integration: Any = None
        self._probe()

    def _probe(self) -> None:
        try:
            import csp as csp_mod  # type: ignore

            self._csp = csp_mod
            logger.info("CSP module loaded")
        except ImportError:
            self._csp = None
            logger.info("CSP module not found (Member 2)")

        try:
            import integration as integration_mod  # type: ignore

            self._integration = integration_mod
            logger.info("Integration module loaded")
        except ImportError:
            self._integration = None
            logger.info("Integration module not found (Member 3)")

    def status(self) -> BackendStatus:
        missing: List[str] = []
        if self._csp is None:
            missing.append("csp")
        if self._integration is None:
            missing.append("integration")
        return BackendStatus(
            csp=self._csp is not None,
            integration=self._integration is not None,
            missing=missing,
        )

    def list_environments(self) -> List[Dict[str, str]]:
        mapping = {
            "Environment_Sample.txt": "Sample",
            "Environment.txt": "Ours",
            "Environment_Error.txt": "Error case",
        }
        items: List[Dict[str, str]] = []
        for path in sorted(DATA_DIR.glob("Environment*.txt")):
            items.append(
                {
                    "name": path.name,
                    "label": mapping.get(path.name, path.stem),
                }
            )
        return items

    def load_from_name(self, name: str) -> Tuple[Grid, str]:
        safe = Path(name).name
        path = DATA_DIR / safe
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Environment file not found: {safe}")
        text = path.read_text(encoding="utf-8")
        return load_environment(path), text

    def load_from_text(self, text: str) -> Tuple[Grid, str]:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(text)
            tmp_path = Path(tmp.name)
        try:
            grid = load_environment(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
        return grid, text

    def validation_checklist(self, grid: Grid) -> List[Dict[str, Any]]:
        problems = validate_environment(grid, strict=True)
        unreachable = unreachable_dirty_locations(grid)
        logical = [p for p in problems if not p.startswith("Strict:")]
        strict = [p for p in problems if p.startswith("Strict:")]
        return [
            {
                "rule": "coordinates_and_overlaps",
                "ok": len(logical) == 0,
                "message": "OK" if not logical else "; ".join(logical),
            },
            {
                "rule": "strict_minimums",
                "ok": len(strict) == 0,
                "message": "OK" if not strict else "; ".join(strict),
            },
            {
                "rule": "all_dirty_reachable",
                "ok": len(unreachable) == 0,
                "message": (
                    "OK"
                    if not unreachable
                    else f"Unreachable: {', '.join(unreachable)}"
                ),
            },
        ]

    def grid_payload(self, grid: Grid) -> Dict[str, Any]:
        return {
            "rows": grid.rows,
            "cols": grid.cols,
            "obstacles": [list(p) for p in sorted(grid.obstacles)],
            "dirty": [
                {"label": grid.task_label(i), "pos": list(pos)}
                for i, pos in enumerate(grid.dirty_locations)
            ],
            "station": list(grid.charging_station),
        }

    def grid_from_payload(self, payload: Dict[str, Any]) -> Grid:
        dirty = [tuple(d["pos"]) for d in payload["dirty"]]
        return Grid(
            rows=int(payload["rows"]),
            cols=int(payload["cols"]),
            obstacles={tuple(o) for o in payload["obstacles"]},
            dirty_locations=[(int(r), int(c)) for r, c in dirty],
            charging_station=tuple(payload["station"]),  # type: ignore[arg-type]
        )

    def save_text(self, grid: Grid) -> str:
        obstacles = sorted(grid.obstacles)
        dirty = list(grid.dirty_locations)
        obs_str = ", ".join(f"({r},{c})" for r, c in obstacles)
        dirty_str = ", ".join(f"({r},{c})" for r, c in dirty)
        sr, sc = grid.charging_station
        return (
            f"{grid.rows},{grid.cols}\n"
            f"{len(obstacles)}\n"
            f"{obs_str}\n"
            f"{len(dirty)}\n"
            f"{dirty_str}\n"
            f"({sr},{sc})\n"
        )

    def search_result_dict(self, result: SearchResult) -> Dict[str, Any]:
        return {
            "algorithm": result.algorithm,
            "found": result.found,
            "path": result.path,
            "cost": result.cost,
            "nodesExpanded": result.nodes_expanded,
            "expandedOrder": result.expanded_order,
            "frontierMaxSize": result.frontier_max_size,
            "runtimeMs": result.runtime_seconds * 1000.0,
            "message": result.message,
        }

    def run_search(
        self,
        grid: Grid,
        start: Position,
        goal: Position,
        algorithm: str,
    ) -> SearchResult:
        return search_with_trace(grid, start, goal, algorithm)

    def default_pairs(self, grid: Grid) -> List[Tuple[Position, Position]]:
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

    def _label(self, grid: Grid, pos: Position) -> str:
        return grid.position_to_label(pos) or str(pos)

    def compare(
        self,
        grid: Grid,
        pairs: Optional[Sequence[Tuple[Position, Position]]] = None,
        algorithms: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        algos = list(algorithms or ("bfs", "astar"))
        use_pairs = list(pairs) if pairs else self.default_pairs(grid)
        rows: List[Dict[str, Any]] = []
        for start, goal in use_pairs:
            for algo in algos:
                result = search_with_trace(grid, start, goal, algo)
                rows.append(
                    {
                        "pair": f"{self._label(grid, start)} → {self._label(grid, goal)}",
                        "algorithm": result.algorithm,
                        "found": result.found,
                        "cost": result.cost,
                        "nodesExpanded": result.nodes_expanded,
                        "frontierMaxSize": result.frontier_max_size,
                        "runtimeMs": result.runtime_seconds * 1000.0,
                    }
                )
        return {
            "rows": rows,
            "insight": self.insight_from_rows(rows),
            "totals": self._totals(rows),
        }

    def _totals(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        totals: Dict[str, Any] = {}
        for r in rows:
            algo = r["algorithm"]
            bucket = totals.setdefault(
                algo, {"nodesExpanded": 0, "cost": 0, "found": 0, "failed": 0}
            )
            if r["found"]:
                bucket["found"] += 1
                bucket["nodesExpanded"] += r["nodesExpanded"]
                bucket["cost"] += r["cost"] or 0
            else:
                bucket["failed"] += 1
        return totals

    def insight_from_rows(self, rows: List[Dict[str, Any]]) -> str:
        by_pair: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for r in rows:
            by_pair.setdefault(r["pair"], {})[r["algorithm"]] = r

        equal_cost = 0
        fewer_astar = 0
        tie_expand = 0
        total = 0
        bfs_nodes = 0
        astar_nodes = 0
        failures = sum(1 for r in rows if not r["found"])

        for algos in by_pair.values():
            if "bfs" not in algos or "astar" not in algos:
                continue
            b, a = algos["bfs"], algos["astar"]
            if not (b["found"] and a["found"]):
                continue
            total += 1
            bfs_nodes += b["nodesExpanded"]
            astar_nodes += a["nodesExpanded"]
            if b["cost"] == a["cost"]:
                equal_cost += 1
            if a["nodesExpanded"] < b["nodesExpanded"]:
                fewer_astar += 1
            elif a["nodesExpanded"] == b["nodesExpanded"]:
                tie_expand += 1

        if total == 0:
            if failures:
                return (
                    f"No comparable successful pairs ({failures} failed row(s)). "
                    "Check unreachable goals or obstacles."
                )
            return "No comparable successful pairs."

        pct = 0.0 if bfs_nodes == 0 else 100.0 * (bfs_nodes - astar_nodes) / bfs_nodes
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
                f"BFS expanded fewer nodes overall ({bfs_nodes} vs {astar_nodes})."
            )
        else:
            parts.append(
                f"Node expansions were essentially tied "
                f"({astar_nodes} vs {bfs_nodes}; {tie_expand} per-pair ties)."
            )
        parts.append(f"A* expanded fewer nodes on {fewer_astar}/{total} pair(s).")
        if failures:
            parts.append(f"{failures} row(s) reported no path.")
        return " ".join(parts)

    def generate_schedule(
        self,
        grid: Grid,
        schedule_text: str,
    ) -> Dict[str, Any]:
        if self._csp is None:
            return {
                "schedule": None,
                "assignment": None,
                "message": "CSP module not found yet (waiting for Member 2)",
                "constraintsChecked": [],
                "error_code": "CSP_NOT_AVAILABLE",
            }
        try:
            if not hasattr(self._csp, "load_schedule") or not hasattr(
                self._csp, "backtracking_search"
            ):
                return {
                    "schedule": None,
                    "assignment": None,
                    "message": (
                        "CSP module found but missing load_schedule / "
                        "backtracking_search"
                    ),
                    "constraintsChecked": [],
                    "error_code": "CSP_NOT_AVAILABLE",
                }
            problem = self._csp.load_schedule(schedule_text)
            assignment = self._csp.backtracking_search(
                problem.get("variables"),
                problem.get("domains"),
                problem.get("constraints"),
            )
            if not assignment:
                return {
                    "schedule": None,
                    "assignment": None,
                    "message": "CSP found no feasible schedule",
                    "constraintsChecked": list(problem.get("constraints", [])),
                    "error_code": None,
                }

            def slot_key(item: Tuple[str, str]) -> int:
                digits = "".join(ch for ch in item[1] if ch.isdigit())
                return int(digits) if digits else 0

            ordered = [v for v, _ in sorted(assignment.items(), key=slot_key)]
            return {
                "schedule": ordered,
                "assignment": dict(assignment),
                "message": "CSP schedule generated",
                "constraintsChecked": ["precedence", "latest-slot", "exclusivity"],
                "error_code": None,
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("CSP failed")
            return {
                "schedule": None,
                "assignment": None,
                "message": f"CSP error: {exc}",
                "constraintsChecked": [],
                "error_code": "CSP_ERROR",
            }

    def execute_mission(
        self,
        grid: Grid,
        schedule: Sequence[str],
        algorithm: str,
        schedule_source: str = "manual",
    ) -> MissionResult:
        if schedule_source == "csp":
            if self._integration is None:
                return MissionResult(
                    complete_path=[],
                    total_cost=0,
                    success=False,
                    legs=[],
                    message=(
                        "INTEGRATION_NOT_AVAILABLE: Integration module not found "
                        "yet (waiting for Member 3)"
                    ),
                    schedule_source="csp",
                )
            try:
                raw = self._integration.execute_schedule(
                    grid, grid.charging_station, list(schedule), algorithm
                )
                return self._normalize_integration(raw)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Integration failed")
                return MissionResult(
                    complete_path=[],
                    total_cost=0,
                    success=False,
                    legs=[],
                    message=f"Integration error: {exc}",
                    schedule_source="csp",
                )
        return self._execute_manual(grid, list(schedule), algorithm)

    def _normalize_integration(self, result: Any) -> MissionResult:
        if isinstance(result, (tuple, list)) and len(result) >= 3:
            path, cost, success = result[0], result[1], result[2]
            path_list = list(path or [])
            return MissionResult(
                complete_path=path_list,
                total_cost=int(cost or 0),
                success=bool(success),
                legs=[],
                message="Mission complete" if success else "Mission failed",
                schedule_source="csp",
                total_movements=max(0, len(path_list) - 1) if path_list else 0,
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
            legs.append(
                MissionLeg(
                    from_pos=current,
                    to_pos=goal,
                    from_label=from_label,
                    to_label=to_label,
                    path=result.path,
                    cost=result.cost,
                    nodes_expanded=result.nodes_expanded,
                    expanded_order=result.expanded_order,
                )
            )
            if not result.found or result.path is None:
                return MissionResult(
                    complete_path=complete,
                    total_cost=total_cost,
                    success=False,
                    legs=legs,
                    message=(
                        f"MANUAL DEMO — no path for {from_label} → {to_label}: "
                        f"{result.message}"
                    ),
                    schedule_source="manual",
                    total_movements=max(0, len(complete) - 1) if complete else 0,
                )
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


# Singletons / re-exports
adapter = Adapter()
__all__ = ["Adapter", "EnvironmentFormatError", "adapter"]
