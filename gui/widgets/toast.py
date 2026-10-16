"""Slide-in toast notifications."""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
    Qt,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from gui import theme


class _Toast(QFrame):
    """Single toast bubble."""

    def __init__(self, message: str, kind: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        colors = {
            "info": theme.ACCENT,
            "success": theme.SUCCESS,
            "error": theme.ERROR,
            "warning": theme.WARNING,
        }
        accent = colors.get(kind, theme.ACCENT)
        self.setStyleSheet(
            f"""
            QFrame#toast {{
                background-color: {theme.BG_ELEVATED};
                border: 1px solid {accent};
                border-left: 4px solid {accent};
                border-radius: 10px;
            }}
            QLabel {{ color: {theme.TEXT}; padding: 4px; }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.adjustSize()
        self.setFixedWidth(min(360, parent.width() - 40))
        self._opacity = 1.0

    def get_opacity(self) -> float:
        return self._opacity

    def set_opacity(self, value: float) -> None:
        self._opacity = value
        self.setWindowOpacity(value) if self.isWindow() else None
        # Soft fade via stylesheet alpha is awkward; hide at end instead.
        if value <= 0.05:
            self.hide()

    opacity = Property(float, get_opacity, set_opacity)


class ToastHost(QWidget):
    """Overlay host that stacks toasts in the bottom-right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")
        self._toasts: list[_Toast] = []

    def show_toast(self, message: str, kind: str = "info", ms: int = 3500) -> None:
        """Show a toast of the given kind (info/success/error/warning)."""
        toast = _Toast(message, kind, self if self.parent() is None else self.parent())
        parent = self.parentWidget() or self
        toast.setParent(parent)
        toast.show()
        self._toasts.append(toast)
        self._relayout()

        # Slide in from the right
        start = toast.pos()
        toast.move(start.x() + 40, start.y())
        anim = QPropertyAnimation(toast, b"pos", toast)
        anim.setDuration(280)
        anim.setStartValue(toast.pos())
        anim.setEndValue(start)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        toast._slide = anim  # keep ref

        QTimer.singleShot(ms, lambda t=toast: self._dismiss(t))

    def _dismiss(self, toast: _Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        toast.hide()
        toast.deleteLater()
        self._relayout()

    def _relayout(self) -> None:
        parent = self.parentWidget() or self
        margin = 16
        y = parent.height() - margin
        for toast in reversed(self._toasts):
            toast.adjustSize()
            y -= toast.height() + 8
            toast.move(parent.width() - toast.width() - margin, y)
            toast.raise_()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()
