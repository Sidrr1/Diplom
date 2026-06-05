"""Масштаб UI от разрешения экрана (база 1920×1080)."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

REF_WIDTH = 1920
REF_HEIGHT = 1080
SCALE_MIN = 0.9
SCALE_MAX = 1.75


def screen_scale() -> float:
    screen = QApplication.primaryScreen()
    if screen is None:
        return 1.0
    geo = screen.availableGeometry()
    sx = geo.width() / REF_WIDTH
    sy = geo.height() / REF_HEIGHT
    return max(SCALE_MIN, min(SCALE_MAX, min(sx, sy)))


def scale_px(value: float, scale: float | None = None) -> int:
    s = screen_scale() if scale is None else scale
    return max(1, int(round(value * s)))


def scale_font(size: int, scale: float | None = None) -> int:
    return max(7, scale_px(size, scale))
