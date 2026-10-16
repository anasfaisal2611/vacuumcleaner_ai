"""FastAPI server for SafayeWala — JSON REST + optional static web/dist."""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.adapter import EnvironmentFormatError, adapter
from api.schemas import (
    BackendStatusResponse,
    CompareRequest,
    EnvironmentInfo,
    HealthResponse,
    LoadEnvironmentRequest,
    LoadEnvironmentResponse,
    MissionExecuteRequest,
    MissionExecuteResponse,
    MissionLegResponse,
    SaveEnvironmentRequest,
    SaveEnvironmentResponse,
    ScheduleGenerateRequest,
    ScheduleGenerateResponse,
    SearchRequest,
    SearchResultResponse,
)
from core.environment import unreachable_dirty_locations

logger = logging.getLogger("safayewala.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "web" / "dist"

app = FastAPI(title="SafayeWala API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def error_json(
    status: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    """Return a structured error payload (never a raw stack trace)."""
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details}},
    )


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s: %s\n%s", request.url.path, exc, traceback.format_exc())
    return error_json(500, "INTERNAL_ERROR", "An unexpected server error occurred")


@app.exception_handler(RequestValidationError)
async def validation_exception(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return error_json(422, "VALIDATION_ERROR", "Invalid request", exc.errors())


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/api/backend-status", response_model=BackendStatusResponse)
def backend_status() -> BackendStatusResponse:
    status = adapter.status()
    return BackendStatusResponse(
        csp=status.csp, integration=status.integration, missing=status.missing
    )


@app.get("/api/environments", response_model=list[EnvironmentInfo])
def list_environments() -> list[EnvironmentInfo]:
    return [EnvironmentInfo(**item) for item in adapter.list_environments()]


@app.post("/api/environment/load")
def load_environment(body: LoadEnvironmentRequest) -> Any:
    try:
        if body.name:
            grid, text = adapter.load_from_name(body.name)
        elif body.text is not None:
            grid, text = adapter.load_from_text(body.text)
        else:
            return error_json(
                400, "MISSING_INPUT", "Provide either 'name' or 'text'"
            )
    except FileNotFoundError as exc:
        return error_json(404, "NOT_FOUND", str(exc))
    except EnvironmentFormatError as exc:
        return error_json(
            400,
            "ENV_FORMAT_ERROR",
            str(exc),
            {"lineNumber": exc.line_number},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("load_environment failed")
        return error_json(400, "ENV_LOAD_ERROR", str(exc))

    unreachable = unreachable_dirty_locations(grid)
    return {
        "grid": adapter.grid_payload(grid),
        "validation": adapter.validation_checklist(grid),
        "unreachable": unreachable,
        "rawText": text,
    }


@app.post("/api/environment/save", response_model=SaveEnvironmentResponse)
def save_environment(body: SaveEnvironmentRequest) -> SaveEnvironmentResponse:
    grid = adapter.grid_from_payload(body.grid.model_dump())
    return SaveEnvironmentResponse(text=adapter.save_text(grid))


@app.post("/api/search")
def search(body: SearchRequest) -> Any:
    try:
        grid, _ = adapter.load_from_text(body.env_text)
    except EnvironmentFormatError as exc:
        return error_json(400, "ENV_FORMAT_ERROR", str(exc), {"lineNumber": exc.line_number})
    try:
        result = adapter.run_search(grid, tuple(body.start), tuple(body.goal), body.algorithm)
    except ValueError as exc:
        return error_json(400, "BAD_ALGORITHM", str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("search failed")
        return error_json(400, "SEARCH_ERROR", str(exc))
    return adapter.search_result_dict(result)


@app.post("/api/compare")
def compare(body: CompareRequest) -> Any:
    try:
        grid, _ = adapter.load_from_text(body.env_text)
    except EnvironmentFormatError as exc:
        return error_json(400, "ENV_FORMAT_ERROR", str(exc), {"lineNumber": exc.line_number})

    pairs = None
    if body.pairs:
        pairs = [(tuple(p[0]), tuple(p[1])) for p in body.pairs]  # type: ignore[misc]
    try:
        return adapter.compare(grid, pairs=pairs, algorithms=body.algorithms)
    except Exception as exc:  # noqa: BLE001
        logger.exception("compare failed")
        return error_json(400, "COMPARE_ERROR", str(exc))


@app.post("/api/schedule/generate")
def schedule_generate(body: ScheduleGenerateRequest) -> Any:
    try:
        grid, _ = adapter.load_from_text(body.env_text)
    except EnvironmentFormatError as exc:
        return error_json(400, "ENV_FORMAT_ERROR", str(exc), {"lineNumber": exc.line_number})

    result = adapter.generate_schedule(grid, body.schedule_text)
    if result.get("error_code") == "CSP_NOT_AVAILABLE":
        return error_json(503, "CSP_NOT_AVAILABLE", result["message"])
    return {
        "schedule": result["schedule"],
        "assignment": result["assignment"],
        "message": result["message"],
        "constraintsChecked": result["constraintsChecked"],
    }


@app.post("/api/mission/execute")
def mission_execute(body: MissionExecuteRequest) -> Any:
    try:
        grid, _ = adapter.load_from_text(body.env_text)
    except EnvironmentFormatError as exc:
        return error_json(400, "ENV_FORMAT_ERROR", str(exc), {"lineNumber": exc.line_number})

    result = adapter.execute_mission(
        grid,
        body.schedule,
        body.algorithm,
        schedule_source=body.schedule_source,
    )
    if "INTEGRATION_NOT_AVAILABLE" in result.message:
        return error_json(503, "INTEGRATION_NOT_AVAILABLE", result.message)

    legs = [
        {
            "from": list(leg.from_pos),
            "to": list(leg.to_pos),
            "fromLabel": leg.from_label,
            "toLabel": leg.to_label,
            "path": leg.path,
            "cost": leg.cost,
            "nodesExpanded": leg.nodes_expanded,
            "expandedOrder": leg.expanded_order,
        }
        for leg in result.legs
    ]
    return {
        "completePath": result.complete_path,
        "totalCost": result.total_cost,
        "totalMovements": result.total_movements,
        "success": result.success,
        "legs": legs,
        "message": result.message,
        "scheduleSource": result.schedule_source,
    }


# Serve built frontend in production when web/dist exists.
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="frontend")
