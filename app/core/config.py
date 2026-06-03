"""Настройки приложения — таблица settings в edgetools.db."""
from app.core.settings_defaults import (
    DEFAULTS,
    KEY_MODULES,
    NOTES_DB_TO_CFG,
    BOOL_KEYS,
    INT_KEYS,
)


def _coerce(key: str, value):
    if value is None:
        return None
    if key in BOOL_KEYS:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")
    if key in INT_KEYS:
        try:
            return int(value)
        except (TypeError, ValueError):
            return DEFAULTS.get(key, 0)
    return value


def load() -> dict:
    from app.core.database import db

    cfg = dict(DEFAULTS)

    for key, module in KEY_MODULES.items():
        raw = db.get_setting(key, module)
        if raw is not None:
            cfg[key] = _coerce(key, raw)

    for db_key, cfg_key in NOTES_DB_TO_CFG.items():
        raw = db.get_setting(db_key, "notes")
        if raw is not None:
            cfg[cfg_key] = _coerce(cfg_key, raw)

    return cfg


def save(cfg: dict):
    from app.core.database import db

    for key, module in KEY_MODULES.items():
        if key in cfg:
            db.set_setting(key, cfg[key], module)

    notes_reverse = {v: k for k, v in NOTES_DB_TO_CFG.items()}
    for cfg_key, db_key in notes_reverse.items():
        if cfg_key in cfg:
            db.set_setting(db_key, cfg[cfg_key], "notes")
