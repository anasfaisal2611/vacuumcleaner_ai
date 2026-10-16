# SafayeWala

**Smart cleaning, planned by AI.**

CS-323 AI term project — vacuum robot with graph search (BFS / A*) and a modern React web GUI. CSP scheduling and mission integration belong to other members; this app never fakes their results.

## Install

```bash
python -m pip install -r requirements.txt
cd web && npm install && cd ..
```

Python **3.10+**, Node **18+**.

## Run (production)

Build the frontend, then launch the API + static UI:

```bash
cd web && npm run build && cd ..
python main.py
```

Opens `http://127.0.0.1:8000`. If `web/dist` is missing, `main.py` prints build instructions and still starts the API.

## Run (development)

Terminal 1:

```bash
uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd web && npm run dev
```

Vite proxies `/api` → port 8000.

## Tests

```bash
python -m pytest -q
cd web && npm test && npx tsc -b --noEmit && npm run build
```

## Project structure

```
core/                 # Member 1 algorithms (pure Python)
  environment.py
  graph_search.py
api/                  # FastAPI — only api/adapter.py imports csp/integration
  server.py
  schemas.py
  adapter.py
web/                  # React 18 + Vite + TS + Tailwind + Framer Motion + Zustand
  src/components/     # GridCanvas, Splash, Sidebar, …
  src/pages/
data/                 # Environment_Sample / Ours / Error
notebook_cells/
main.py
tests/
```

## Environment file format

```
8,8
6
(1,3), (2,3), (3,3), (4,3), (5,3), (6,3)
4
(0,7), (3,7), (7,7), (7,0)
(0,0)
```

Zero-based `(row,col)`. Dirty order defines D1, D2, …

### Our map (`data/Environment.txt`) — 10×10 sketch

```
C . . . . . . . . D1
. . X . . . . . . .
. . X . . X . . . .
. . X . . X . . . .
. . X . . X . . . D2
. . X . . X . D5 . .
. . . . . X . . . .
. . . . . . . . . .
. . . . . . . . . .
D4. . . . . . . . D3
```

## API endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/health` | liveness |
| GET | `/api/backend-status` | `{csp, integration, missing}` |
| GET | `/api/environments` | files in `data/` |
| POST | `/api/environment/load` | `{name}` or `{text}` |
| POST | `/api/environment/save` | `{grid}` → file text |
| POST | `/api/search` | `{envText, start, goal, algorithm}` |
| POST | `/api/compare` | pairs optional; default Station↔dirty |
| POST | `/api/schedule/generate` | CSP — `503 CSP_NOT_AVAILABLE` if missing |
| POST | `/api/mission/execute` | `scheduleSource: csp\|manual` |

Errors: `{ "error": { "code", "message", "details" } }`.

## Teammate signatures (exact)

```python
# csp.py (Member 2)
def load_schedule(filepath_or_text): ...
def backtracking_search(variables, domains, constraints):
    """→ {"D1":"T1", ...} or None"""

# integration.py (Member 3)
def execute_schedule(grid, charging_station, schedule, algorithm):
    """→ (complete_path, total_cost, success)"""
```

Until those modules exist, Full Mission shows a banner and a **Manual demo order** (clearly watermarked — not a CSP result).

## Sample search note

Station → D4 `(0,0)→(7,0)` optimal cost is **7** (Manhattan). The wall at column 3 does not block column 0. Cost **14** is `(0,0)→(7,7)` (D3).

## GUI features

- Dark-first aurora glassmorphism + light theme (persisted)
- Splash intro (once per session, skippable)
- Canvas grid with obstacle pop-in, search waves (BFS blue / A* magenta), robot trail, cleaning FX
- Playback: Play/Pause/Step/Reset/Skip + speed; Space / → / R
- Pages: Environment, Search Lab, Compare, Full Mission, About
