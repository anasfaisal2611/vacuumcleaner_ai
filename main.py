"""SafayeWala entry point — splash then main window."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure the repo root is on sys.path when launched as `python main.py`.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from gui import theme
from gui.backend import Backend
from gui.main_window import MainWindow
from gui.splash import SplashScreen


def main() -> int:
    """Launch the SafayeWala desktop application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("SafayeWala")
    app.setOrganizationName("SafayeWala")
    app.setStyleSheet(theme.QSS)

    backend = Backend()
    window = MainWindow(backend)
    splash = SplashScreen()

    def show_main() -> None:
        splash.close()
        window.show()
        window.raise_()
        window.activateWindow()

    splash.finished.connect(show_main)
    splash.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
