"""Animated splash screen for SafayeWala."""

from __future__ import annotations

import math

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QObject,
    QPointF,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from gui import theme
from gui.team import APP_NAME, TAGLINE


class _FadeBridge(QObject):
    def __init__(self, cb) -> None:
        super().__init__()
        self._v = 0.0
        self._cb = cb

    def get(self) -> float:
        return self._v

    def set(self, v: float) -> None:
        self._v = v
        self._cb()

    value = Property(float, get, set)


class SplashScreen(QWidget):
    """~2s splash with drawn vacuum logo and wordmark; skippable."""

    finished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.resize(900, 560)
        self._progress = 0.0
        self._robot_x = 0.0
        self._phase = 0.0
        self._bridge = _FadeBridge(self.update)
        self._fade = QPropertyAnimation(self._bridge, b"value", self)
        self._fade.setDuration(400)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade.finished.connect(self.finished.emit)

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._elapsed = 0.0
        self._done = False

    def start(self) -> None:
        """Begin splash animation."""
        self._elapsed = 0.0
        self._done = False
        self._timer.start()
        self.show()

    def _tick(self) -> None:
        self._elapsed += 0.016
        self._phase += 0.016
        self._progress = min(1.0, self._elapsed / 2.0)
        self._robot_x = self._progress
        self.update()
        if self._progress >= 1.0 and not self._done:
            self._done = True
            self._timer.stop()
            QTimer.singleShot(200, self._fade.start)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._skip()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        self._skip()

    def _skip(self) -> None:
        if self._done:
            return
        self._done = True
        self._timer.stop()
        self._fade.start()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(theme.BG_DARK))

        for cx, cy, colour in (
            (0.2, 0.3, theme.ACCENT),
            (0.8, 0.4, theme.ASTAR_MAGENTA),
            (0.5, 0.8, theme.AMBER),
        ):
            g = QRadialGradient(self.width() * cx, self.height() * cy, self.width() * 0.35)
            c = QColor(colour)
            c.setAlpha(35)
            g.setColorAt(0, c)
            g.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), g)

        trail_w = self.width() * 0.7 * self._robot_x
        trail_rect_y = self.height() * 0.42
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(
            self.width() * 0.15,
            trail_rect_y - 28,
            max(1.0, trail_w),
            56,
            20,
            20,
        )

        font = QFont("Segoe UI", 40, QFont.Weight.Bold)
        p.setFont(font)
        alpha = int(255 * min(1.0, self._robot_x * 1.4))
        col = QColor(theme.TEXT)
        col.setAlpha(alpha)
        p.setPen(col)
        p.drawText(self.rect().adjusted(0, -40, 0, 0), Qt.AlignmentFlag.AlignCenter, APP_NAME)

        sub = QFont("Segoe UI", 12)
        p.setFont(sub)
        muted = QColor(theme.TEXT_MUTED)
        muted.setAlpha(alpha)
        p.setPen(muted)
        p.drawText(
            self.rect().adjusted(0, 50, 0, 0),
            Qt.AlignmentFlag.AlignCenter,
            TAGLINE,
        )

        rx = self.width() * 0.15 + trail_w
        ry = trail_rect_y
        self._draw_robot(p, rx, ry)

        bar_w = self.width() * 0.4
        bar_x = (self.width() - bar_w) / 2
        bar_y = self.height() * 0.78
        p.setBrush(QColor(theme.BG_ELEVATED))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(bar_x, bar_y, bar_w, 8, 4, 4)
        p.setBrush(QColor(theme.ACCENT))
        p.drawRoundedRect(bar_x, bar_y, bar_w * self._progress, 8, 4, 4)

        hint = QColor(theme.TEXT_MUTED)
        hint.setAlpha(160)
        p.setPen(hint)
        p.drawText(
            int(bar_x),
            int(bar_y + 28),
            int(bar_w),
            20,
            Qt.AlignmentFlag.AlignCenter,
            "Click or press any key to skip",
        )

        if self._bridge.value > 0:
            overlay = QColor(theme.BG_DARK)
            overlay.setAlphaF(self._bridge.value)
            p.fillRect(self.rect(), overlay)

    def _draw_robot(self, p: QPainter, x: float, y: float) -> None:
        r = 22.0
        glow = QRadialGradient(x, y, r * 2)
        c = QColor(theme.ROBOT)
        c.setAlpha(80)
        glow.setColorAt(0, c)
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(x, y), r * 1.6, r * 1.6)
        p.setBrush(QColor(theme.ACCENT))
        p.setPen(QPen(QColor("#042f2e"), 2))
        p.drawEllipse(QPointF(x, y), r, r * 0.8)
        p.setBrush(QColor("#ecfeff"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(x + 8, y - 2), 5, 5)
        for i in range(5):
            sx = x - 30 - i * 12
            sy = y + math.sin(self._phase * 4 + i) * 6
            p.setBrush(QColor(theme.ACCENT_GLOW))
            p.drawEllipse(QPointF(sx, sy), 2, 2)
