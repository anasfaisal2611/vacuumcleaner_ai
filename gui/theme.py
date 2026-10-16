"""Central colours and Qt Style Sheet for SafayeWala."""

from __future__ import annotations

# Colour palette (deep navy / charcoal + teal accent + amber dirt)
BG_DARK = "#0b1220"
BG_PANEL = "#121a2b"
BG_CARD = "#182235"
BG_ELEVATED = "#1e2a40"
BORDER = "#2a3a55"
TEXT = "#e8eef8"
TEXT_MUTED = "#9aa8c0"
ACCENT = "#2dd4bf"  # teal / cyan
ACCENT_DIM = "#14b8a6"
ACCENT_GLOW = "#5eead4"
AMBER = "#f59e0b"
AMBER_SOFT = "#fbbf24"
BFS_BLUE = "#38bdf8"
ASTAR_MAGENTA = "#e879f9"
SUCCESS = "#34d399"
ERROR = "#f87171"
WARNING = "#fbbf24"
ROBOT = "#5eead4"
OBSTACLE = "#334155"
FREE_CELL = "#1a2438"
STATION_GLOW = "#2dd4bf"

QSS = f"""
QWidget {{
    background-color: {BG_DARK};
    color: {TEXT};
    font-family: "Segoe UI", "SF Pro Text", Inter, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background-color: {BG_DARK};
}}
QToolTip {{
    background-color: {BG_ELEVATED};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 6px 8px;
    border-radius: 6px;
}}
QPushButton {{
    background-color: {BG_ELEVATED};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: #243352;
    border-color: {ACCENT_DIM};
}}
QPushButton:pressed {{
    background-color: #1a2740;
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    background-color: {BG_PANEL};
}}
QPushButton#primaryButton {{
    background-color: {ACCENT_DIM};
    color: #042f2e;
    border: none;
}}
QPushButton#primaryButton:hover {{
    background-color: {ACCENT};
}}
QPushButton#navButton {{
    text-align: left;
    padding: 12px 16px;
    border: none;
    border-radius: 10px;
    background-color: transparent;
    font-size: 14px;
}}
QPushButton#navButton:hover {{
    background-color: {BG_ELEVATED};
}}
QPushButton#navButton[active="true"] {{
    background-color: {BG_CARD};
    color: {ACCENT};
    border: 1px solid {BORDER};
}}
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {ACCENT_DIM};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: {BG_ELEVATED};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    margin: -6px 0;
    background: {ACCENT};
    border-radius: 8px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: {BG_PANEL};
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QTableWidget {{
    background-color: {BG_PANEL};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QHeaderView::section {{
    background-color: {BG_CARD};
    color: {TEXT_MUTED};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {BORDER};
    font-weight: 600;
}}
QLabel#titleLabel {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT};
}}
QLabel#subtitleLabel {{
    font-size: 13px;
    color: {TEXT_MUTED};
}}
QLabel#statValue {{
    font-size: 28px;
    font-weight: 700;
    color: {ACCENT};
}}
QLabel#statCaption {{
    font-size: 11px;
    color: {TEXT_MUTED};
    letter-spacing: 0.5px;
}}
QFrame#card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#sidebar {{
    background-color: {BG_PANEL};
    border-right: 1px solid {BORDER};
}}
QStatusBar {{
    background-color: {BG_PANEL};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
}}
QProgressBar {{
    background-color: {BG_ELEVATED};
    border: none;
    border-radius: 6px;
    text-align: center;
    color: {TEXT};
    height: 14px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 6px;
}}
QTextEdit, QPlainTextEdit {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px;
}}
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {BORDER};
    background: {BG_PANEL};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT_DIM};
    border-color: {ACCENT};
}}
"""
