"""Animated count-up statistic label."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QObject, Property
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from gui import theme


class _AnimBridge(QObject):
    """QObject bridge so we can animate a float property."""

    def __init__(self, callback) -> None:
        super().__init__()
        self._value = 0.0
        self._callback = callback

    def get_value(self) -> float:
        return self._value

    def set_value(self, v: float) -> None:
        self._value = v
        self._callback(v)

    value = Property(float, get_value, set_value)


class StatCounter(QWidget):
    """Shows a caption + animated numeric value."""

    def __init__(self, caption: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        self._value_label = QLabel("0")
        self._value_label.setObjectName("statValue")
        self._caption = QLabel(caption.upper())
        self._caption.setObjectName("statCaption")
        layout.addWidget(self._value_label)
        layout.addWidget(self._caption)
        self._bridge = _AnimBridge(self._on_tick)
        self._anim = QPropertyAnimation(self._bridge, b"value", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(700)
        self._is_float = False
        self._suffix = ""

    def _on_tick(self, v: float) -> None:
        if self._is_float:
            self._value_label.setText(f"{v:.2f}{self._suffix}")
        else:
            self._value_label.setText(f"{int(round(v))}{self._suffix}")

    def set_value(
        self,
        value: float | int | None,
        *,
        animate: bool = True,
        as_float: bool = False,
        suffix: str = "",
        color: str | None = None,
    ) -> None:
        """Set the displayed value, optionally animating from the previous."""
        self._is_float = as_float
        self._suffix = suffix
        if color:
            self._value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 700;")
        else:
            self._value_label.setStyleSheet(
                f"color: {theme.ACCENT}; font-size: 28px; font-weight: 700;"
            )
        if value is None:
            self._anim.stop()
            self._value_label.setText("—")
            return
        target = float(value)
        if not animate:
            self._bridge.set_value(target)
            return
        self._anim.stop()
        self._anim.setStartValue(self._bridge.value)
        self._anim.setEndValue(target)
        self._anim.start()
