"""Настройки напоминаний о задачах (модуль notes)."""
from __future__ import annotations

import json

from app.core.database import db

_MODULE = "notes"
_KEY_ENABLED = "reminder_enabled"
_KEY_MODE = "reminder_mode"
_KEY_DAILY_TIME = "reminder_daily_time"
_KEY_OFFSETS = "reminder_offsets"

MODES = ("daily", "before", "both")

OFFSET_CHOICES = (
    ("5m", 5, "5 мин"),
    ("15m", 15, "15 мин"),
    ("1h", 60, "1 час"),
    ("3h", 180, "3 часа"),
    ("1d", 1440, "1 день"),
)

_OFFSET_MINUTES = {k: m for k, m, _ in OFFSET_CHOICES}


def is_enabled() -> bool:
    return str(db.get_setting(_KEY_ENABLED, _MODULE, "0")).lower() in (
        "1", "true", "yes", "on",
    )


def set_enabled(on: bool) -> None:
    db.set_setting(_KEY_ENABLED, "1" if on else "0", _MODULE)


def get_mode() -> str:
    raw = str(db.get_setting(_KEY_MODE, _MODULE, "both")).strip()
    return raw if raw in MODES else "both"


def set_mode(mode: str) -> None:
    db.set_setting(_KEY_MODE, mode if mode in MODES else "both", _MODULE)


def get_daily_time() -> tuple[int, int]:
    raw = str(db.get_setting(_KEY_DAILY_TIME, _MODULE, "12:00"))
    try:
        h, m = raw.split(":")
        return int(h) % 24, int(m) % 60
    except (ValueError, TypeError):
        return 12, 0


def set_daily_time(hour: int, minute: int) -> None:
    db.set_setting(
        _KEY_DAILY_TIME,
        f"{int(hour) % 24:02d}:{int(minute) % 60:02d}",
        _MODULE,
    )


def get_offsets() -> list[str]:
    raw = db.get_setting(_KEY_OFFSETS, _MODULE, "")
    if not raw:
        return ["1h", "1d"]
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data if str(x) in _OFFSET_MINUTES]
    except (json.JSONDecodeError, TypeError):
        pass
    return ["1h", "1d"]


def set_offsets(keys: list[str]) -> None:
    clean = [k for k in keys if k in _OFFSET_MINUTES]
    if not clean:
        clean = ["1h"]
    db.set_setting(_KEY_OFFSETS, json.dumps(clean, ensure_ascii=False), _MODULE)


def offset_minutes(key: str) -> int:
    return _OFFSET_MINUTES.get(key, 60)
