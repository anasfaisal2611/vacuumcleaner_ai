"""Pydantic request/response models (camelCase aliases for the frontend)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    """Base model that serializes to camelCase JSON."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        ser_json_by_alias=True,
    )


class ErrorBody(CamelModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(CamelModel):
    error: ErrorBody


class HealthResponse(CamelModel):
    status: str = "ok"


class BackendStatusResponse(CamelModel):
    csp: bool
    integration: bool
    missing: List[str]


class EnvironmentInfo(CamelModel):
    name: str
    label: str


class DirtyCell(CamelModel):
    label: str
    pos: Tuple[int, int]


class GridPayload(CamelModel):
    rows: int
    cols: int
    obstacles: List[Tuple[int, int]]
    dirty: List[DirtyCell]
    station: Tuple[int, int]


class ValidationItem(CamelModel):
    rule: str
    ok: bool
    message: str


class LoadEnvironmentRequest(CamelModel):
    name: Optional[str] = None
    text: Optional[str] = None


class LoadEnvironmentResponse(CamelModel):
    grid: GridPayload
    validation: List[ValidationItem]
    unreachable: List[str]
    raw_text: str = Field(serialization_alias="rawText")


class SaveEnvironmentRequest(CamelModel):
    grid: GridPayload


class SaveEnvironmentResponse(CamelModel):
    text: str


class SearchRequest(CamelModel):
    env_text: str = Field(alias="envText")
    start: Tuple[int, int]
    goal: Tuple[int, int]
    algorithm: str

    model_config = ConfigDict(populate_by_name=True)


class SearchResultResponse(CamelModel):
    algorithm: str
    found: bool
    path: Optional[List[Tuple[int, int]]] = None
    cost: Optional[int] = None
    nodes_expanded: int = Field(serialization_alias="nodesExpanded")
    expanded_order: List[Tuple[int, int]] = Field(serialization_alias="expandedOrder")
    frontier_max_size: int = Field(serialization_alias="frontierMaxSize")
    runtime_ms: float = Field(serialization_alias="runtimeMs")
    message: str

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, ser_json_by_alias=True)


class CompareRequest(CamelModel):
    env_text: str = Field(alias="envText")
    pairs: Optional[List[List[Tuple[int, int]]]] = None
    algorithms: Optional[List[str]] = None

    model_config = ConfigDict(populate_by_name=True)


class CompareRow(CamelModel):
    pair: str
    algorithm: str
    found: bool
    cost: Optional[int] = None
    nodes_expanded: int = Field(serialization_alias="nodesExpanded")
    frontier_max_size: int = Field(serialization_alias="frontierMaxSize")
    runtime_ms: float = Field(serialization_alias="runtimeMs")

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, ser_json_by_alias=True)


class CompareResponse(CamelModel):
    rows: List[CompareRow]
    insight: str
    totals: Dict[str, Any]


class ScheduleGenerateRequest(CamelModel):
    env_text: str = Field(alias="envText")
    schedule_text: str = Field(alias="scheduleText")

    model_config = ConfigDict(populate_by_name=True)


class ScheduleGenerateResponse(CamelModel):
    schedule: Optional[List[str]] = None
    assignment: Optional[Dict[str, str]] = None
    message: str
    constraints_checked: List[str] = Field(
        default_factory=list, serialization_alias="constraintsChecked"
    )

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, ser_json_by_alias=True)


class MissionExecuteRequest(CamelModel):
    env_text: str = Field(alias="envText")
    schedule: List[str]
    algorithm: str
    schedule_source: str = Field(alias="scheduleSource", default="manual")

    model_config = ConfigDict(populate_by_name=True)


class MissionLegResponse(CamelModel):
    from_pos: Tuple[int, int] = Field(serialization_alias="from")
    to_pos: Tuple[int, int] = Field(serialization_alias="to")
    from_label: str = Field(serialization_alias="fromLabel")
    to_label: str = Field(serialization_alias="toLabel")
    path: Optional[List[Tuple[int, int]]] = None
    cost: Optional[int] = None
    nodes_expanded: int = Field(serialization_alias="nodesExpanded")
    expanded_order: List[Tuple[int, int]] = Field(
        default_factory=list, serialization_alias="expandedOrder"
    )

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, ser_json_by_alias=True)


class MissionExecuteResponse(CamelModel):
    complete_path: List[Tuple[int, int]] = Field(serialization_alias="completePath")
    total_cost: int = Field(serialization_alias="totalCost")
    total_movements: int = Field(serialization_alias="totalMovements")
    success: bool
    legs: List[MissionLegResponse]
    message: str
    schedule_source: str = Field(serialization_alias="scheduleSource")

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, ser_json_by_alias=True)
