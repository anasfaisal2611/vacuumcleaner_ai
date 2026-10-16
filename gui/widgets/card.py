"""Rounded card frame used across pages."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from gui import theme


class Card(QFrame):
    """A styled card with optional title."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        """Create a card; ``title`` is shown above the content area."""
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(10)
        self._title_label: QLabel | None = None
        if title:
            self._title_label = QLabel(title)
            self._title_label.setObjectName("titleLabel")
            self._title_label.setStyleSheet(
                f"font-size: 15px; font-weight: 700; color: {theme.TEXT};"
            )
            self._layout.addWidget(self._title_label)
        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        self._layout.addLayout(self.body)

    def add_widget(self, widget: QWidget) -> None:
        """Add a widget to the card body."""
        self.body.addWidget(widget)
