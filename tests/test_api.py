"""FastAPI TestClient tests for the SafayeWala API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.server import app

DATA = Path(__file__).resolve().parent.parent / "data"
client = TestClient(app)


def test_health() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_backend_status_missing_modules() -> None:
    r = client.get("/api/backend-status")
    assert r.status_code == 200
    body = r.json()
    assert body["csp"] is False
    assert body["integration"] is False
    assert "csp" in body["missing"]


def test_list_environments() -> None:
    r = client.get("/api/environments")
    assert r.status_code == 200
    names = {e["name"] for e in r.json()}
    assert "Environment_Sample.txt" in names
    assert "Environment.txt" in names
    assert "Environment_Error.txt" in names


def test_load_sample_ours_error() -> None:
    for name in ("Environment_Sample.txt", "Environment.txt", "Environment_Error.txt"):
        r = client.post("/api/environment/load", json={"name": name})
        assert r.status_code == 200, name
        body = r.json()
        assert "grid" in body
        assert "validation" in body
        assert "rawText" in body
    err = client.post("/api/environment/load", json={"name": "Environment_Error.txt"})
    assert "D4" in err.json()["unreachable"] or len(err.json()["unreachable"]) >= 1


def test_search_bfs_astar_sample() -> None:
    text = (DATA / "Environment_Sample.txt").read_text(encoding="utf-8")
    bfs = client.post(
        "/api/search",
        json={"envText": text, "start": [0, 0], "goal": [7, 0], "algorithm": "bfs"},
    )
    astar = client.post(
        "/api/search",
        json={"envText": text, "start": [0, 0], "goal": [7, 0], "algorithm": "astar"},
    )
    assert bfs.status_code == 200 and astar.status_code == 200
    b, a = bfs.json(), astar.json()
    assert b["found"] and a["found"]
    assert b["cost"] == a["cost"]
    assert a["nodesExpanded"] <= b["nodesExpanded"]
    assert b["cost"] == 7  # wall at col 3 does not block col 0


def test_start_equals_goal() -> None:
    text = (DATA / "Environment_Sample.txt").read_text(encoding="utf-8")
    r = client.post(
        "/api/search",
        json={"envText": text, "start": [0, 0], "goal": [0, 0], "algorithm": "bfs"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["found"]
    assert body["cost"] == 0
    assert body["nodesExpanded"] == 0


def test_unreachable_no_500() -> None:
    text = (DATA / "Environment_Error.txt").read_text(encoding="utf-8")
    # D4 is enclosed at (2,2)
    r = client.post(
        "/api/search",
        json={"envText": text, "start": [0, 0], "goal": [2, 2], "algorithm": "bfs"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is False
    assert body["path"] is None


def test_malformed_env_structured_error() -> None:
    r = client.post(
        "/api/environment/load",
        json={"text": "nope\n6\n(1,1)\n4\n(0,0), (1,0), (2,0), (3,0)\n(0,0)\n"},
    )
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "ENV_FORMAT_ERROR"
    assert "message" in err


def test_mission_manual_success() -> None:
    text = (DATA / "Environment_Sample.txt").read_text(encoding="utf-8")
    r = client.post(
        "/api/mission/execute",
        json={
            "envText": text,
            "schedule": ["D1", "D2", "D3", "D4"],
            "algorithm": "bfs",
            "scheduleSource": "manual",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["scheduleSource"] == "manual"
    assert "MANUAL" in body["message"].upper()


def test_mission_csp_not_available() -> None:
    text = (DATA / "Environment_Sample.txt").read_text(encoding="utf-8")
    r = client.post(
        "/api/mission/execute",
        json={
            "envText": text,
            "schedule": ["D1"],
            "algorithm": "bfs",
            "scheduleSource": "csp",
        },
    )
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "INTEGRATION_NOT_AVAILABLE"


def test_schedule_csp_not_available() -> None:
    text = (DATA / "Environment_Sample.txt").read_text(encoding="utf-8")
    r = client.post(
        "/api/schedule/generate",
        json={"envText": text, "scheduleText": "4\n0\n0\n"},
    )
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "CSP_NOT_AVAILABLE"
