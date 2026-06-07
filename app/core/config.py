"""
Загрузка и сохранение настроек EdgeTools.

Читает и записывает ключи из таблицы settings в edgetools.db,
приводя типы к bool/int/str согласно settings_defaults.
"""
from app.core.settings_defaults import (
    DEFAULTS,
    KEY_MODULES,
    NOTES_DB_TO_CFG,
    BOOL_KEYS,
    INT_KEYS,
)


def _coerce(key: str, value):
    """
    Привести значение из БД к типу, ожидаемому конфигурацией.

    Args:
        key: имя ключа настройки.
        value: сырое строковое значение из SQLite.

    Returns:
        bool, int или str в зависимости от типа ключа.
    """
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
    """
    Загрузить полный словарь настроек приложения.

    Returns:
        Словарь cfg с DEFAULTS и значениями из БД; пути нормализуются.
    """
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

    from app.core.paths import normalize_path

    if cfg.get("sorter_source"):
        cfg["sorter_source"] = normalize_path(cfg["sorter_source"])
    if cfg.get("enhancer_save_path"):
        cfg["enhancer_save_path"] = normalize_path(cfg["enhancer_save_path"])
    if cfg.get("player_cookies_path"):
        cfg["player_cookies_path"] = normalize_path(cfg["player_cookies_path"])

    return cfg


def _persist_key(db, key: str, val) -> None:
    """
    Записать один ключ настройки в БД с нормализацией путей.

    Args:
        db: экземпляр Database.
        key: ключ настройки.
        val: значение для сохранения.
    """
    module = KEY_MODULES[key]
    from app.core.paths import normalize_path
    if key in ("sorter_source", "enhancer_save_path", "player_cookies_path") and val:
        val = normalize_path(val)
    db.set_setting(key, val, module)


def save(cfg: dict):
    """
    Сохранить все известные ключи конфигурации в БД.

    Args:
        cfg: полный или частичный словарь настроек.
    """
    from app.core.database import db

    for key in KEY_MODULES:
        if key in cfg:
            _persist_key(db, key, cfg[key])

    notes_reverse = {v: k for k, v in NOTES_DB_TO_CFG.items()}
    for cfg_key, db_key in notes_reverse.items():
        if cfg_key in cfg:
            db.set_setting(db_key, cfg[cfg_key], "notes")


def save_keys(cfg: dict, keys: set[str]) -> None:
    """
    Сохранить только указанные ключи конфигурации.

    Args:
        cfg: словарь настроек.
        keys: множество имён ключей для записи.
    """
    from app.core.database import db

    notes_reverse = {v: k for k, v in NOTES_DB_TO_CFG.items()}
    for key in keys:
        if key in KEY_MODULES and key in cfg:
            _persist_key(db, key, cfg[key])
        elif key in notes_reverse and key in cfg:
            db.set_setting(notes_reverse[key], cfg[key], "notes")
