"""Папка-входящие сортировщика — одна настройка для UI, автосорта и «Сортировать всё»."""
from __future__ import annotations

import os

from app.core.database import db
from app.core.paths import normalize_path

_KEY = "sorter_source"
_MODULE = "sorter"


def get_source_folder() -> str:
    """Текущая папка из БД (нормализованный путь)."""
    raw = db.get_setting(_KEY, _MODULE, "") or ""
    if not str(raw).strip():
        return ""
    return normalize_path(raw)


def set_source_folder(path: str) -> str:
    """Сохранить папку-входящие; возвращает нормализованный путь."""
    norm = normalize_path(path)
    db.set_setting(_KEY, norm, _MODULE)
    return norm


def is_source_valid() -> bool:
    src = get_source_folder()
    return bool(src and os.path.isdir(src))
