"""Animated bar chart drawn with QPainter (no external chart libs)."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QObject, Property, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gui import theme


class _ProgressBridge(QObject):
    def __init__(self, on_change) -> None:
        super().__init__()
        self._t = 0.0
        self._on_change = on_change

    def get_t(self) -> float:
        return self._t

    def set_t(self, v: float) -> None:
        self._t = v
        self._on_change()

    t = Property(float, get_t, set_t)


class BarChartWidget(QWidget):
    """Grouped bar chart with eased grow-in animation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self._labels: List[str] = []
        self._series: List[Tuple[str, List[float], str]] = []  # name, values, colour
        self._bridge = _ProgressBridge(self.update)
        self._anim = QPropertyAnimation(self._bridge, b"t", self)
        self._anim.setDuration(800)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._title = ""

    def set_chart(
        self,
        labels: Sequence[str],
        series: Sequence[Tuple[str, Sequence[float], str]],
        title: str = "",
    ) -> None:
        """Set chart data and replay the grow animation.

        Args:
            labels: Category labels along X.
            series: List of (name, values, colour_hex).
            title: Optional chart title.
        """
        self._labels = list(labels)
        self._series = [(n, list(vals), colour) for n, vals, colour in series]
        self._title = title
        self._anim.stop()
        self._bridge.set_t(0.0)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -12)

        painter.fillRect(self.rect(), QColor(theme.BG_CARD))
        painter.setPen(QColor(theme.TEXT))
        font = QFont(painter.font())
        font.setBold(True)
        painter.setFont(font)
        if self._title:
            painter.drawText(rect.adjusted(0, 0, 0, -rect.height() + 18), Qt.AlignmentFlag.AlignLeft, self._title)

        if not self._labels or not self._series:
            painter.setPen(QColor(theme.TEXT_MUTED))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No data yet")
            return

        chart = rect.adjusted(36, 28, -8, -36)
        max_val = max((max(vals) if vals else 0) for _, vals, _ in self._series) or 1.0
        n_groups = len(self._labels)
        n_series = len(self._series)
        group_w = chart.width() / max(n_groups, 1)
        bar_w = max(6.0, (group_w * 0.7) / max(n_series, 1))
        t = self._bridge.t

        # Axes
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawLine(chart.bottomLeft(), chart.bottomRight())
        painter.drawLine(chart.bottomLeft(), chart.topLeft())

        for gi, label in enumerate(self._labels):
            gx = chart.left() + gi * group_w + group_w * 0.15
            for si, (_name, values, colour) in enumerate(self._series):
                val = values[gi] if gi < len(values) else 0.0
                h = (val / max_val) * chart.height() * t
                x = gx + si * (bar_w + 4)
                bar = QRectF(x, chart.bottom() - h, bar_w, h)
                painter.setBrush(QColor(colour))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bar, 4, 4)
            painter.setPen(QColor(theme.TEXT_MUTED))
            small = QFont(painter.font())
            small.setPointSize(8)
            small.setBold(False)
            painter.setFont(small)
            painter.drawText(
                QRectF(chart.left() + gi * group_w, chart.bottom() + 4, group_w, 24),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label if len(label) <= 14 else label[:12] + "…",
            )

        # Legend
        lx = chart.left()
        ly = rect.top()
        for name, _vals, colour in self._series:
            painter.setBrush(QColor(colour))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(lx, ly, 10, 10), 2, 2)
            painter.setPen(QColor(theme.TEXT_MUTED))
            painter.drawText(int(lx + 14), int(ly + 10), name)
            lx += 80
