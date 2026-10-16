"""About / credits page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from gui import theme
from gui.team import APP_NAME, COURSE, INSTITUTION, TAGLINE, TEAM
from gui.widgets.card import Card


class AboutPage(QWidget):
    """Project info and team list."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel(APP_NAME)
        title.setObjectName("titleLabel")
        title.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {theme.ACCENT};")
        layout.addWidget(title)

        tag = QLabel(TAGLINE)
        tag.setObjectName("subtitleLabel")
        layout.addWidget(tag)

        course = Card("Course")
        course.add_widget(QLabel(f"<b>{COURSE}</b><br>{INSTITUTION}"))
        layout.addWidget(course)

        flow = Card("How it works")
        flow.add_widget(
            QLabel(
                "<b>Schedule.txt</b> → CSP solver (Member 2) → cleaning order<br>"
                "→ <b>Graph Search</b> (Member 1: BFS / A*) between waypoints<br>"
                "→ <b>Integration</b> (Member 3) runs the full mission back to station<br>"
                "→ <b>SafayeWala GUI</b> visualises every step."
            )
        )
        layout.addWidget(flow)

        team = Card("Team")
        for name, roll, role in TEAM:
            lab = QLabel(f"<b>{name}</b> — {roll}<br><span style='color:{theme.TEXT_MUTED}'>{role}</span>")
            team.add_widget(lab)
        layout.addWidget(team)

        note = QLabel(
            "Edit names in <code>gui/team.py</code>. "
            "CSP and Integration modules are provided by other members — "
            "this GUI never fakes their results."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(note)
        layout.addStretch(1)
