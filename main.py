"""SafayeWala production launcher.

Starts uvicorn on 127.0.0.1:8000 serving the API and (if built) web/dist,
then opens the default browser.
"""

from __future__ import annotations

import logging
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "web" / "dist"
HOST = "127.0.0.1"
PORT = 8000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("safayewala")


def main() -> None:
    """Run the API server and open the browser."""
    if not DIST.is_dir():
        print("=" * 60)
        print("web/dist not found — frontend is not built yet.")
        print("Build it with:")
        print("  cd web && npm install && npm run build")
        print()
        print("Or use development mode:")
        print("  uvicorn api.server:app --reload --host 127.0.0.1 --port 8000")
        print("  cd web && npm run dev")
        print("=" * 60)
        # Still start API-only so endpoints work during development.
        print("Starting API only on http://127.0.0.1:8000 …")

    def _open() -> None:
        time.sleep(1.2)
        url = f"http://{HOST}:{PORT}/"
        logger.info("Opening browser at %s", url)
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not open browser: %s", exc)

    threading.Thread(target=_open, daemon=True).start()
    uvicorn.run("api.server:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
