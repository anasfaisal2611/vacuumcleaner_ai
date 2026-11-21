"""CSP scheduling — same logic as notebook Part B (CS-24058.ipynb).

Exposed for the web GUI via ``api.adapter``:

* ``load_schedule(schedule_text, variables=...)`` → problem dict
* ``backtracking_search(variables, domains, constraints)`` → assignment
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

Task = str
Slot = int


class ScheduleFormatError(Exception):
    """Raised when a schedule file / text is malformed."""

    def __init__(self, message: str, line_number: Optional[int] = None) -> None:
        self.line_number = line_number
        full = f"Line {line_number}: {message}" if line_number is not None else message
        super().__init__(full)


def _parse_schedule_text(text: str) -> Tuple[int, List[Tuple[str, str]], Dict[str, int]]:
    """Parse count-based schedule text → (n_slots, precedences, latest)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        raise ScheduleFormatError("File too short")

    try:
        n = int(lines[0])
        precedence_count = int(lines[1])
    except ValueError as exc:
        raise ScheduleFormatError(
            "Slot and precedence counts must be integers"
        ) from exc
    if n < 1 or precedence_count < 0:
        raise ScheduleFormatError(
            "Slot count must be positive and constraint counts non-negative"
        )

    idx = 2
    precedences: List[Tuple[str, str]] = []
    for _ in range(precedence_count):
        if idx >= len(lines):
            raise ScheduleFormatError(
                "File ended before all precedence constraints were read"
            )
        match = re.fullmatch(r"\(\s*(D\d+)\s*,\s*(D\d+)\s*\)", lines[idx])
        if match is None:
            raise ScheduleFormatError(f"Invalid precedence constraint: {lines[idx]!r}")
        precedences.append((match.group(1), match.group(2)))
        idx += 1

    if idx >= len(lines):
        raise ScheduleFormatError("Missing latest-slot constraint count")
    try:
        latest_count = int(lines[idx])
    except ValueError as exc:
        raise ScheduleFormatError(
            "Latest-slot constraint count must be an integer"
        ) from exc
    if latest_count < 0:
        raise ScheduleFormatError("Latest-slot constraint count cannot be negative")
    idx += 1

    latest: Dict[str, int] = {}
    for _ in range(latest_count):
        if idx >= len(lines):
            raise ScheduleFormatError(
                "File ended before all latest-slot constraints were read"
            )
        match = re.fullmatch(r"\(\s*(D\d+)\s*,\s*T(\d+)\s*\)", lines[idx])
        if match is None:
            raise ScheduleFormatError(
                f"Invalid latest-slot constraint: {lines[idx]!r}"
            )
        latest[match.group(1)] = int(match.group(2))
        idx += 1
    if idx != len(lines):
        raise ScheduleFormatError(f"Unexpected extra schedule input: {lines[idx]!r}")

    return n, precedences, latest


def _infer_variables(
    n_slots: int,
    precedences: Sequence[Tuple[str, str]],
    latest: Dict[str, int],
) -> List[str]:
    """Build D1..Dk covering every label mentioned in constraints."""
    labels = set()
    for a, b in precedences:
        labels.add(a)
        labels.add(b)
    labels.update(latest.keys())
    if not labels:
        # No constraints — still need one task per slot minimum fallback of D1..Dn
        return [f"D{i}" for i in range(1, n_slots + 1)]
    max_idx = max(int(lab[1:]) for lab in labels)
    return [f"D{i}" for i in range(1, max_idx + 1)]


def apply_latest_slot(
    domains: Dict[str, List[int]], latest: Dict[str, int]
) -> Dict[str, List[int]]:
    """Remove slots after each task's deadline (deadline slot itself kept)."""
    for task in list(domains.keys()):
        if task in latest:
            domains[task] = [x for x in domains[task] if x <= latest[task]]
    return domains


def validate_schedule_inputs(
    variables: Sequence[str],
    n_slots: int,
    precedences: Sequence[Tuple[str, str]],
    latest: Dict[str, int],
) -> None:
    """Handout 6.4: slots >= tasks, constraint labels must exist."""
    if n_slots < len(variables):
        raise ScheduleFormatError(
            f"{n_slots} slots but {len(variables)} tasks: need at least one slot per task"
        )
    known = set(variables)
    for before, after in precedences:
        for t in (before, after):
            if t not in known:
                raise ScheduleFormatError(f"Precedence uses unknown task {t}")
    for t in latest:
        if t not in known:
            raise ScheduleFormatError(f"Latest-slot constraint uses unknown task {t}")


def load_schedule(
    schedule_text: Union[str, Any],
    variables: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Parse schedule text into a CSP problem dict for the GUI adapter.

    Parameters
    ----------
    schedule_text:
        Contents of ``schedule.txt`` (or a Path — Path is read as text).
    variables:
        Task labels from the environment (``D1..Dn``). If omitted, inferred
        from constraint labels.
    """
    from pathlib import Path

    if isinstance(schedule_text, Path):
        text = schedule_text.read_text(encoding="utf-8")
    else:
        text = str(schedule_text)

    n, precedences, latest = _parse_schedule_text(text)
    vars_list = list(variables) if variables is not None else _infer_variables(
        n, precedences, latest
    )
    validate_schedule_inputs(vars_list, n, precedences, latest)

    slots = list(range(1, n + 1))
    domains = {v: list(slots) for v in vars_list}
    apply_latest_slot(domains, latest)
    constraints = {"precedences": list(precedences), "latest": dict(latest)}
    return {
        "variables": vars_list,
        "domains": domains,
        "constraints": constraints,
        "n_slots": n,
    }


def is_consistent(
    variable: str,
    value: int,
    assignment: Dict[str, int],
    constraints: Dict[str, Any],
) -> bool:
    """Reject deadline miss, slot reuse, or precedence violations."""
    latest = constraints["latest"]
    precedences = constraints["precedences"]

    if variable in latest and value > latest[variable]:
        return False
    if value in assignment.values():
        return False

    for before, after in precedences:
        if variable == before and after in assignment:
            if value >= assignment[after]:
                return False
        elif variable == after and before in assignment:
            if value <= assignment[before]:
                return False
    return True


def forward_check(
    variable: str,
    value: int,
    assignment: Dict[str, int],
    domains: Dict[str, List[int]],
    constraints: Dict[str, Any],
) -> Optional[Dict[str, List[int]]]:
    """Copy domains; prune exclusivity + precedence; None if a domain empties."""
    new_domains = {v: list(d) for v, d in domains.items()}
    precedences = constraints["precedences"]

    for other in new_domains:
        if other == variable or other in assignment:
            continue
        if value in new_domains[other]:
            new_domains[other].remove(value)
        for before, after in precedences:
            if before == variable and after == other:
                new_domains[other] = [x for x in new_domains[other] if x > value]
            elif after == variable and before == other:
                new_domains[other] = [x for x in new_domains[other] if x < value]
        if not new_domains[other]:
            return None
    return new_domains


def degree(
    task: str, assignment: Dict[str, int], constraints: Dict[str, Any]
) -> int:
    """How many precedence edges still link this task to unassigned tasks."""
    count = 0
    for before, after in constraints["precedences"]:
        if before == task and after not in assignment:
            count += 1
        elif after == task and before not in assignment:
            count += 1
    return count


def select_unassigned_variable(
    assignment: Dict[str, int],
    domains: Dict[str, List[int]],
    constraints: Dict[str, Any],
) -> Optional[str]:
    """MRV, then highest degree, then smallest task index."""
    unassigned = [task for task in domains if task not in assignment]
    if not unassigned:
        return None
    smallest = min(len(domains[task]) for task in unassigned)
    tied = [task for task in unassigned if len(domains[task]) == smallest]
    return min(
        tied,
        key=lambda task: (-degree(task, assignment, constraints), int(task[1:])),
    )


def order_domain_values(
    variable: str,
    assignment: Dict[str, int],
    domains: Dict[str, List[int]],
    constraints: Dict[str, Any],
) -> List[int]:
    """Least-constraining-value ordering."""

    def cost(value: int) -> float:
        result = forward_check(variable, value, assignment, domains, constraints)
        if result is None:
            return float("inf")
        removed = sum(
            len(domains[task]) - len(result[task])
            for task in domains
            if task != variable
        )
        return float(removed)

    return sorted(domains[variable], key=lambda v: (cost(v), v))


def backtracking_search(
    variables: Sequence[str],
    domains: Dict[str, List[int]],
    constraints: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """Recursive BT + FC + MRV/degree + LCV. Returns ``{Di: 'Tk'}`` or None."""

    def backtrack(
        assignment: Dict[str, int], current_domains: Dict[str, List[int]]
    ) -> Optional[Dict[str, int]]:
        if len(assignment) == len(variables):
            return dict(assignment)
        var = select_unassigned_variable(assignment, current_domains, constraints)
        if var is None:
            return None
        for value in order_domain_values(var, assignment, current_domains, constraints):
            if is_consistent(var, value, assignment, constraints):
                assignment[var] = value
                new_domains = forward_check(
                    var, value, assignment, current_domains, constraints
                )
                if new_domains is not None:
                    result = backtrack(assignment, new_domains)
                    if result is not None:
                        return result
                del assignment[var]
        return None

    raw = backtrack({}, {v: list(domains[v]) for v in variables})
    if raw is None:
        return None
    # GUI-friendly slot labels
    return {task: f"T{slot}" for task, slot in raw.items()}


def verify_schedule(
    assignment: Dict[str, Union[str, int]], constraints: Dict[str, Any]
) -> List[Tuple[str, bool]]:
    """Return (description, ok) checks for exclusivity / precedence / latest."""

    def slot_num(v: Union[str, int]) -> int:
        if isinstance(v, int):
            return v
        digits = "".join(ch for ch in str(v) if ch.isdigit())
        return int(digits) if digits else 0

    nums = {t: slot_num(s) for t, s in assignment.items()}
    checks: List[Tuple[str, bool]] = [
        (
            "Slot exclusivity: every task has a different slot",
            len(set(nums.values())) == len(nums),
        )
    ]
    for before, after in constraints["precedences"]:
        if before in nums and after in nums:
            checks.append(
                (
                    f"{before} before {after}  (T{nums[before]} < T{nums[after]})",
                    nums[before] < nums[after],
                )
            )
    for task, deadline in constraints["latest"].items():
        if task in nums:
            checks.append(
                (
                    f"{task} by T{deadline}  (got T{nums[task]})",
                    nums[task] <= deadline,
                )
            )
    return checks
