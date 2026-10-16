"""Animated grid canvas for SafayeWala (QPainter, ~60 FPS)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from PySide6.QtCore import (
    QPointF,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QToolTip, QWidget

from core.environment import Grid
from core.graph_search import SearchResult
from gui import theme

Position = Tuple[int, int]


def _ease_out_cubic(t: float) -> float:
    """Cubic ease-out in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out in [0, 1]."""
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


@dataclass
class _Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    colour: QColor


@dataclass
class PlaybackState:
    """Timeline state for search / mission animation."""

    playing: bool = False
    speed: float = 1.0
    # Exploration phase
    explore_index: int = 0
    # Path draw phase (after explore)
    path_index: int = 0
    phase: str = "idle"  # idle | explore | path | robot | done
    robot_seg: float = 0.0  # progress along current path segment
    robot_path_i: int = 0
    cleaned: Set[Position] = field(default_factory=set)


class GridWidget(QWidget):
    """Custom-painted interactive grid with search / mission animations."""

    cell_clicked = Signal(int, int, object)  # row, col, mouse_button
    toast_requested = Signal(str, str)  # message, kind
    playback_changed = Signal()
    stats_tick = Signal(int, int, object)  # expanded_shown, frontier_hint, g_cost

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._grid: Optional[Grid] = None
        self._cell = 32.0
        self._origin = QPointF(0, 0)
        self._hover: Optional[Position] = None

        self._mode = "view"  # view | search | edit | mission
        self._start: Optional[Position] = None
        self._goal: Optional[Position] = None
        self._edit_painting: Optional[bool] = None  # True=add obstacle

        # Animation / visuals
        self._obstacle_pop: Dict[Position, float] = {}  # 0..1
        self._station_phase = 0.0
        self._particles: List[_Particle] = []
        self._trail: List[Tuple[float, float, float]] = []  # x,y,alpha

        self._result: Optional[SearchResult] = None
        self._path: List[Position] = []
        self._explore_colour = QColor(theme.BFS_BLUE)
        self._explored_alpha: Dict[Position, float] = {}
        self._playback = PlaybackState()
        self._robot_pos = QPointF(0, 0)
        self._robot_angle = 0.0
        self._brush_angle = 0.0
        self._cleaning_pos: Optional[Position] = None
        self._cleaning_t = 0.0
        self._leg_colours: List[QColor] = []
        self._mission_legs_paths: List[List[Position]] = []
        self._manual_badge = False

        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 FPS
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    # ------------------------------------------------------------------ API
    def set_grid(self, grid: Optional[Grid]) -> None:
        """Load a new environment and play obstacle pop-in."""
        self._grid = grid
        self.reset_playback()
        self._obstacle_pop = {}
        if grid:
            for i, obs in enumerate(sorted(grid.obstacles)):
                # Stagger stored as negative delay offset in pop progress.
                self._obstacle_pop[obs] = -0.04 * i
            self._start = grid.charging_station
            self._goal = None
            self._robot_pos = self._cell_center(grid.charging_station)
        self._recompute_layout()
        self.update()

    def grid(self) -> Optional[Grid]:
        """Return the current grid, if any."""
        return self._grid

    def set_mode(self, mode: str) -> None:
        """Set interaction mode: view, search, edit, mission."""
        self._mode = mode
        self.update()

    def set_start_goal(self, start: Optional[Position], goal: Optional[Position]) -> None:
        """Set start/goal markers for Search Lab."""
        self._start = start
        self._goal = goal
        self.update()

    def start_goal(self) -> Tuple[Optional[Position], Optional[Position]]:
        """Return current start and goal."""
        return self._start, self._goal

    def load_search_result(self, result: SearchResult, explore_colour: Optional[QColor] = None) -> None:
        """Load a search trace and prepare exploration animation."""
        self._result = result
        self._path = list(result.path or [])
        self._explore_colour = explore_colour or (
            QColor(theme.ASTAR_MAGENTA)
            if result.algorithm == "astar"
            else QColor(theme.BFS_BLUE)
        )
        self._explored_alpha.clear()
        self._playback = PlaybackState(phase="explore", playing=True)
        self._manual_badge = False
        if self._start:
            self._robot_pos = self._cell_center(self._start)
        self.playback_changed.emit()
        self.update()

    def load_mission(
        self,
        path: Sequence[Position],
        leg_paths: Optional[Sequence[Sequence[Position]]] = None,
        cleaned_targets: Optional[Sequence[Position]] = None,
        manual: bool = False,
    ) -> None:
        """Load a mission path for robot playback."""
        self._path = list(path)
        self._mission_legs_paths = [list(p) for p in (leg_paths or [])]
        palette = [
            QColor(theme.BFS_BLUE),
            QColor(theme.ASTAR_MAGENTA),
            QColor(theme.AMBER),
            QColor(theme.ACCENT),
            QColor("#a78bfa"),
            QColor("#fb7185"),
        ]
        self._leg_colours = [palette[i % len(palette)] for i in range(len(self._mission_legs_paths))]
        self._playback = PlaybackState(phase="robot", playing=True, cleaned=set())
        self._manual_badge = manual
        if self._path:
            self._robot_pos = self._cell_center(self._path[0])
        self.playback_changed.emit()
        self.update()

    def mark_cleaned(self, pos: Position) -> None:
        """Trigger cleaning effect at ``pos``."""
        self._playback.cleaned.add(pos)
        self._cleaning_pos = pos
        self._cleaning_t = 0.0
        cx, cy = self._cell_center(pos).x(), self._cell_center(pos).y()
        for _ in range(14):
            ang = random.random() * math.tau
            speed = 40 + random.random() * 60
            self._particles.append(
                _Particle(
                    cx,
                    cy,
                    math.cos(ang) * speed,
                    math.sin(ang) * speed,
                    1.0,
                    QColor(theme.AMBER_SOFT),
                )
            )
        self.update()

    # Playback controls
    def play(self) -> None:
        if self._playback.phase in {"idle", "done"}:
            return
        self._playback.playing = True
        self.playback_changed.emit()

    def pause(self) -> None:
        self._playback.playing = False
        self.playback_changed.emit()

    def toggle_play(self) -> None:
        if self._playback.playing:
            self.pause()
        else:
            self.play()

    def step(self) -> None:
        self._playback.playing = False
        self._advance(1.0)
        self.playback_changed.emit()
        self.update()

    def reset_playback(self) -> None:
        self._playback = PlaybackState()
        self._explored_alpha.clear()
        self._trail.clear()
        self._particles.clear()
        self._result = None
        self._path = []
        self._mission_legs_paths = []
        if self._grid and self._start:
            self._robot_pos = self._cell_center(self._start)
        self.playback_changed.emit()
        self.update()

    def skip_to_end(self) -> None:
        if self._result and self._result.expanded_order:
            for pos in self._result.expanded_order:
                self._explored_alpha[pos] = 0.55
            self._playback.explore_index = len(self._result.expanded_order)
        if self._path:
            self._playback.path_index = len(self._path)
            self._playback.robot_path_i = max(0, len(self._path) - 1)
            self._robot_pos = self._cell_center(self._path[-1])
            self._playback.phase = "done"
        self._playback.playing = False
        self.playback_changed.emit()
        self.update()

    def set_speed(self, speed: float) -> None:
        self._playback.speed = max(0.25, min(8.0, speed))
        self.playback_changed.emit()

    def is_playing(self) -> bool:
        return self._playback.playing

    def speed(self) -> float:
        return self._playback.speed

    # ---------------------------------------------------------------- layout
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._recompute_layout()

    def _recompute_layout(self) -> None:
        if not self._grid:
            return
        pad = 16
        w = max(1, self.width() - 2 * pad)
        h = max(1, self.height() - 2 * pad)
        self._cell = min(w / self._grid.cols, h / self._grid.rows)
        grid_w = self._cell * self._grid.cols
        grid_h = self._cell * self._grid.rows
        self._origin = QPointF((self.width() - grid_w) / 2, (self.height() - grid_h) / 2)

    def _cell_rect(self, pos: Position) -> QRectF:
        r, c = pos
        return QRectF(
            self._origin.x() + c * self._cell,
            self._origin.y() + r * self._cell,
            self._cell,
            self._cell,
        )

    def _cell_center(self, pos: Position) -> QPointF:
        rect = self._cell_rect(pos)
        return rect.center()

    def _pos_at(self, x: float, y: float) -> Optional[Position]:
        if not self._grid:
            return None
        c = int((x - self._origin.x()) // self._cell)
        r = int((y - self._origin.y()) // self._cell)
        pos = (r, c)
        return pos if self._grid.is_in_bounds(pos) else None

    # ---------------------------------------------------------------- tick
    def _on_tick(self) -> None:
        dt = 0.016 * self._playback.speed
        self._station_phase = (self._station_phase + dt * 1.8) % math.tau
        self._brush_angle = (self._brush_angle + dt * 10) % math.tau

        # Obstacle pop-in
        for pos in list(self._obstacle_pop):
            self._obstacle_pop[pos] = min(1.0, self._obstacle_pop[pos] + dt * 2.5)

        # Fade explored cells
        for pos in list(self._explored_alpha):
            self._explored_alpha[pos] = max(0.18, self._explored_alpha[pos] - dt * 0.15)

        # Particles
        alive: List[_Particle] = []
        for p in self._particles:
            p.life -= dt * 1.2
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= 0.96
            p.vy *= 0.96
            if p.life > 0:
                alive.append(p)
        self._particles = alive

        if self._cleaning_pos is not None:
            self._cleaning_t += dt * 1.5
            if self._cleaning_t >= 1.0:
                self._cleaning_pos = None

        # Trail fade
        self._trail = [(x, y, a - dt * 1.5) for x, y, a in self._trail if a - dt * 1.5 > 0]

        if self._playback.playing:
            self._advance(dt * 8)  # scale so 1x feels snappy

        self.update()

    def _advance(self, steps: float) -> None:
        pb = self._playback
        if pb.phase == "explore" and self._result:
            order = self._result.expanded_order
            pb.explore_index += steps
            while int(pb.explore_index) > len(self._explored_alpha) and len(self._explored_alpha) < len(order):
                idx = len(self._explored_alpha)
                pos = order[idx]
                self._explored_alpha[pos] = 0.85
                # Ripple particles
                center = self._cell_center(pos)
                self._particles.append(
                    _Particle(center.x(), center.y(), 0, 0, 0.6, QColor(self._explore_colour))
                )
            shown = len(self._explored_alpha)
            self.stats_tick.emit(shown, self._result.frontier_max_size, None)
            if shown >= len(order):
                pb.phase = "path" if self._path else "done"
                pb.path_index = 0
        elif pb.phase == "path":
            pb.path_index += steps * 0.8
            if pb.path_index >= len(self._path):
                pb.phase = "robot" if self._path else "done"
                pb.robot_path_i = 0
                pb.robot_seg = 0.0
                if self._path:
                    self._robot_pos = self._cell_center(self._path[0])
        elif pb.phase == "robot" and self._path:
            if pb.robot_path_i >= len(self._path) - 1:
                pb.phase = "done"
                pb.playing = False
                self.playback_changed.emit()
                return
            pb.robot_seg += steps * 0.15
            t = _ease_in_out_cubic(min(1.0, pb.robot_seg))
            a = self._path[pb.robot_path_i]
            b = self._path[pb.robot_path_i + 1]
            ca, cb = self._cell_center(a), self._cell_center(b)
            self._robot_pos = QPointF(
                ca.x() + (cb.x() - ca.x()) * t,
                ca.y() + (cb.y() - ca.y()) * t,
            )
            self._robot_angle = math.atan2(cb.y() - ca.y(), cb.x() - ca.x())
            self._trail.append((self._robot_pos.x(), self._robot_pos.y(), 0.7))
            if self._grid:
                g_cost = pb.robot_path_i
                self.stats_tick.emit(
                    len(self._explored_alpha),
                    self._result.frontier_max_size if self._result else 0,
                    g_cost,
                )
            if pb.robot_seg >= 1.0:
                pb.robot_path_i += 1
                pb.robot_seg = 0.0
                arrived = self._path[pb.robot_path_i]
                if self._grid and arrived in self._grid.dirty_locations:
                    if arrived not in pb.cleaned:
                        self.mark_cleaned(arrived)
        elif pb.phase == "done":
            pb.playing = False

    # ---------------------------------------------------------- interaction
    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = self._pos_at(event.position().x(), event.position().y())
        self._hover = pos
        if pos and self._grid:
            ctype = self._grid.cell_type(pos)
            label = self._grid.position_to_label(pos)
            tip = f"({pos[0]}, {pos[1]}) — {ctype}"
            if label:
                tip += f" [{label}]"
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        if self._mode == "edit" and self._edit_painting is not None and pos and self._grid:
            self._apply_edit(pos, self._edit_painting)
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        pos = self._pos_at(event.position().x(), event.position().y())
        if not pos or not self._grid:
            return
        button = event.button()
        if self._mode == "edit":
            if self._grid.charging_station == pos or pos in self._grid.dirty_locations:
                self.toast_requested.emit("Cannot edit station or dirty cells", "warning")
                return
            adding = pos not in self._grid.obstacles
            if button == Qt.MouseButton.RightButton:
                adding = False
            self._edit_painting = adding
            self._apply_edit(pos, adding)
            return

        if self._mode == "search":
            shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            if button == Qt.MouseButton.RightButton or shift:
                if self._grid.is_obstacle(pos):
                    self.toast_requested.emit("Goal cannot be an obstacle", "error")
                    return
                self._goal = pos
            elif button == Qt.MouseButton.LeftButton:
                if self._grid.is_obstacle(pos):
                    self.toast_requested.emit("Start cannot be an obstacle", "error")
                    return
                self._start = pos
            self.cell_clicked.emit(pos[0], pos[1], button)
            self.update()
            return

        self.cell_clicked.emit(pos[0], pos[1], button)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._edit_painting = None

    def _apply_edit(self, pos: Position, add_obstacle: bool) -> None:
        if not self._grid:
            return
        if add_obstacle:
            self._grid.obstacles.add(pos)
            self._obstacle_pop[pos] = 0.0
        else:
            self._grid.obstacles.discard(pos)
            self._obstacle_pop.pop(pos, None)
        self.update()

    # --------------------------------------------------------------- paint
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.BG_DARK))

        if not self._grid:
            painter.setPen(QColor(theme.TEXT_MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Load an environment to begin")
            return

        # Soft vignette / panel behind grid
        grid_rect = QRectF(
            self._origin.x() - 8,
            self._origin.y() - 8,
            self._cell * self._grid.cols + 16,
            self._cell * self._grid.rows + 16,
        )
        painter.setBrush(QColor(theme.BG_PANEL))
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawRoundedRect(grid_rect, 12, 12)

        for r in range(self._grid.rows):
            for c in range(self._grid.cols):
                self._paint_cell(painter, (r, c))

        # Explored overlays
        for pos, alpha in self._explored_alpha.items():
            rect = self._cell_rect(pos).adjusted(3, 3, -3, -3)
            colour = QColor(self._explore_colour)
            colour.setAlphaF(min(0.7, alpha))
            painter.setBrush(colour)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 6, 6)

        # Path glow
        self._paint_path(painter)

        # Start / goal markers
        if self._start:
            self._paint_marker(painter, self._start, QColor(theme.SUCCESS), "S")
        if self._goal:
            self._paint_marker(painter, self._goal, QColor(theme.ERROR), "G")

        # Particles
        for p in self._particles:
            col = QColor(p.colour)
            col.setAlphaF(max(0.0, p.life))
            painter.setBrush(col)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(p.x, p.y), 2.5, 2.5)

        # Robot trail
        for x, y, a in self._trail:
            col = QColor(theme.ROBOT)
            col.setAlphaF(a * 0.4)
            painter.setBrush(col)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), 4, 4)

        # Robot
        if self._playback.phase in {"robot", "path", "done", "explore"} or self._start:
            self._paint_robot(painter)

        if self._manual_badge:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(60, 40, 10, 200))
            badge = QRectF(self.width() - 210, 12, 198, 28)
            painter.drawRoundedRect(badge, 8, 8)
            painter.setPen(QColor(theme.AMBER))
            font = QFont(painter.font())
            font.setBold(True)
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "MANUAL DEMO — not CSP")

    def _paint_cell(self, painter: QPainter, pos: Position) -> None:
        grid = self._grid
        assert grid is not None
        rect = self._cell_rect(pos).adjusted(2, 2, -2, -2)
        ctype = grid.cell_type(pos)

        if ctype == "X":
            pop = _ease_out_cubic(max(0.0, self._obstacle_pop.get(pos, 1.0)))
            h = rect.height() * pop
            drawn = QRectF(rect.x(), rect.bottom() - h, rect.width(), h)
            # Raised block look
            painter.setBrush(QColor(theme.OBSTACLE))
            painter.setPen(QPen(QColor("#475569"), 1))
            painter.drawRoundedRect(drawn, 5, 5)
            # Top highlight
            hi = QColor("#64748b")
            hi.setAlphaF(0.35 * pop)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(hi)
            painter.drawRoundedRect(drawn.adjusted(2, 2, -2, -drawn.height() * 0.55), 4, 4)
            return

        # Free / dirty / station base tile
        base = QColor(theme.FREE_CELL)
        if pos in self._playback.cleaned:
            base = QColor("#12352f")
        if self._hover == pos:
            base = base.lighter(120)
        painter.setBrush(base)
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawRoundedRect(rect, 6, 6)

        if ctype == "C" or pos == grid.charging_station:
            self._paint_station(painter, rect)
        elif ctype == "D" and pos not in self._playback.cleaned:
            self._paint_dirty(painter, rect, grid.position_to_label(pos) or "D")
        elif pos in self._playback.cleaned:
            # Shine + check
            painter.setPen(QPen(QColor(theme.SUCCESS), 2))
            cx, cy = rect.center().x(), rect.center().y()
            painter.drawLine(QPointF(cx - 6, cy), QPointF(cx - 1, cy + 5))
            painter.drawLine(QPointF(cx - 1, cy + 5), QPointF(cx + 7, cy - 5))

        if self._cleaning_pos == pos:
            # Ripple
            t = self._cleaning_t
            rad = rect.width() * 0.2 + t * rect.width() * 0.5
            col = QColor(theme.ACCENT)
            col.setAlphaF(max(0.0, 1.0 - t))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(col, 2))
            painter.drawEllipse(rect.center(), rad, rad)

    def _paint_station(self, painter: QPainter, rect: QRectF) -> None:
        pulse = 0.5 + 0.5 * math.sin(self._station_phase)
        grad = QRadialGradient(rect.center(), rect.width() * 0.55)
        glow = QColor(theme.STATION_GLOW)
        glow.setAlphaF(0.15 + 0.25 * pulse)
        grad.setColorAt(0.0, glow)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(rect.center(), rect.width() * 0.48, rect.height() * 0.48)
        ring = QColor(theme.ACCENT)
        ring.setAlphaF(0.5 + 0.4 * pulse)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(ring, 2))
        painter.drawEllipse(rect.adjusted(6, 6, -6, -6))
        # Lightning bolt
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.ACCENT_GLOW))
        cx, cy = rect.center().x(), rect.center().y()
        bolt = QPainterPath()
        bolt.moveTo(cx + 2, cy - 8)
        bolt.lineTo(cx - 3, cy + 1)
        bolt.lineTo(cx + 1, cy + 1)
        bolt.lineTo(cx - 2, cy + 8)
        bolt.lineTo(cx + 4, cy - 1)
        bolt.lineTo(cx - 1, cy - 1)
        bolt.closeSubpath()
        painter.drawPath(bolt)

    def _paint_dirty(self, painter: QPainter, rect: QRectF, label: str) -> None:
        # Amber dust cluster
        painter.setPen(Qt.PenStyle.NoPen)
        random.seed(hash(label) & 0xFFFF)
        for _ in range(7):
            ox = (random.random() - 0.5) * rect.width() * 0.5
            oy = (random.random() - 0.5) * rect.height() * 0.5
            rad = 2 + random.random() * 3
            col = QColor(theme.AMBER if random.random() > 0.4 else theme.AMBER_SOFT)
            col.setAlphaF(0.55 + random.random() * 0.4)
            painter.setBrush(col)
            painter.drawEllipse(rect.center() + QPointF(ox, oy), rad, rad)
        # Floating sparkle (time-based)
        sparkle_y = math.sin(self._station_phase * 2 + hash(label) % 7) * 3
        painter.setBrush(QColor(255, 255, 220, 180))
        painter.drawEllipse(rect.center() + QPointF(6, -6 + sparkle_y), 1.8, 1.8)
        # Label chip
        painter.setPen(QColor(theme.BG_DARK))
        font = QFont(painter.font())
        font.setBold(True)
        font.setPointSize(max(8, int(self._cell * 0.22)))
        painter.setFont(font)
        painter.setBrush(QColor(theme.AMBER))
        chip = QRectF(rect.right() - self._cell * 0.42, rect.top() + 2, self._cell * 0.38, self._cell * 0.28)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(chip, 4, 4)
        painter.setPen(QColor(theme.BG_DARK))
        painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, label)

    def _paint_marker(self, painter: QPainter, pos: Position, colour: QColor, text: str) -> None:
        rect = self._cell_rect(pos).adjusted(4, 4, -4, -4)
        pulse = 0.6 + 0.4 * math.sin(self._station_phase * 2)
        c = QColor(colour)
        c.setAlphaF(0.25 * pulse)
        painter.setBrush(c)
        painter.setPen(QPen(colour, 2))
        painter.drawEllipse(rect)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_path(self, painter: QPainter) -> None:
        if not self._path:
            return
        # Mission legs in distinct colours if available
        if self._mission_legs_paths:
            for i, leg in enumerate(self._mission_legs_paths):
                self._stroke_path(painter, leg, self._leg_colours[i], full=True)
            return

        n = int(min(len(self._path), max(1, self._playback.path_index + 1)))
        if self._playback.phase in {"robot", "done"}:
            n = len(self._path)
        if self._playback.phase == "explore":
            return
        colour = QColor(theme.ACCENT_GLOW)
        self._stroke_path(painter, self._path[:n], colour, full=False)

    def _stroke_path(
        self,
        painter: QPainter,
        path: Sequence[Position],
        colour: QColor,
        full: bool,
    ) -> None:
        if len(path) < 2:
            return
        pen = QPen(colour, max(2.0, self._cell * 0.12))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        pts = [self._cell_center(p) for p in path]
        for a, b in zip(pts, pts[1:]):
            painter.drawLine(a, b)
        # Direction chevrons
        painter.setBrush(colour)
        for a, b in list(zip(pts, pts[1:]))[:: max(1, len(pts) // 8)]:
            ang = math.atan2(b.y() - a.y(), b.x() - a.x())
            mid = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
            size = self._cell * 0.12
            p1 = mid + QPointF(math.cos(ang) * size, math.sin(ang) * size)
            p2 = mid + QPointF(math.cos(ang + 2.4) * size, math.sin(ang + 2.4) * size)
            p3 = mid + QPointF(math.cos(ang - 2.4) * size, math.sin(ang - 2.4) * size)
            chev = QPainterPath()
            chev.moveTo(p1)
            chev.lineTo(p2)
            chev.lineTo(p3)
            chev.closeSubpath()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(chev)

    def _paint_robot(self, painter: QPainter) -> None:
        pos = self._robot_pos
        r = max(6.0, self._cell * 0.28)
        # Glow
        grad = QRadialGradient(pos, r * 1.8)
        g = QColor(theme.ROBOT)
        g.setAlphaF(0.35)
        grad.setColorAt(0, g)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(pos, r * 1.6, r * 1.6)
        # Body
        body = QLinearGradient(pos.x() - r, pos.y() - r, pos.x() + r, pos.y() + r)
        body.setColorAt(0, QColor("#99f6e4"))
        body.setColorAt(1, QColor("#0d9488"))
        painter.setBrush(body)
        painter.setPen(QPen(QColor("#042f2e"), 1.5))
        painter.drawEllipse(pos, r, r * 0.85)
        # Sensor eye (faces travel direction)
        eye = pos + QPointF(math.cos(self._robot_angle) * r * 0.35, math.sin(self._robot_angle) * r * 0.35)
        painter.setBrush(QColor("#ecfeff"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(eye, r * 0.22, r * 0.22)
        painter.setBrush(QColor("#0f172a"))
        painter.drawEllipse(eye, r * 0.1, r * 0.1)
        # Spinning brush under body
        painter.setPen(QPen(QColor(theme.AMBER), 2))
        for i in range(3):
            ang = self._brush_angle + i * (math.tau / 3)
            painter.drawLine(
                pos,
                pos + QPointF(math.cos(ang) * r * 0.7, math.sin(ang) * r * 0.55),
            )
