"""Перенос config.json и rules.json в edgetools.db (один раз)."""
import json
import os
import shutil
from datetime import datetime

from app.core.settings_defaults import KEY_MODULES

_LEGACY_CONFIG = os.path.join(
    os.path.expanduser("~"), "AppData", "Roaming", "EdgeTools", "config.json"
)
_LEGACY_RULES = os.path.join(
    os.path.expanduser("~"), "AppData", "Roaming", "EdgeTools", "rules.json"
)


def migrate_legacy_json(db) -> None:
    """Импорт старых JSON в SQLite, затем переименование в .bak."""
    _migrate_config(db)
    _migrate_rules(db)


def _migrate_config(db) -> None:
    if not os.path.isfile(_LEGACY_CONFIG):
        return
    try:
        with open(_LEGACY_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[migrate] config.json read error: {e}")
        return

    for key, module in KEY_MODULES.items():
        if key in data:
            db.set_setting(key, data[key], module)

    notes_map = {
        "notes_edge_position": "edge_position",
        "notes_width": "note_width",
        "notes_height": "note_height",
        "notes_opacity": "notes_opacity",
        "notes_mode": "notes_mode",
    }
    for cfg_key, db_key in notes_map.items():
        if cfg_key in data:
            db.set_setting(db_key, data[cfg_key], "notes")

    _backup(_LEGACY_CONFIG)
    print("[migrate] config.json -> settings table")


def _migrate_rules(db) -> None:
    if not os.path.isfile(_LEGACY_RULES):
        return
    if db.count_sorter_rules() > 0:
        _backup(_LEGACY_RULES)
        print("[migrate] rules.json skipped (DB already has rules)")
        return
    try:
        with open(_LEGACY_RULES, "r", encoding="utf-8") as f:
            rules = json.load(f)
    except Exception as e:
        print(f"[migrate] rules.json read error: {e}")
        return

    if not isinstance(rules, list):
        return

    for r in rules:
        if not isinstance(r, dict):
            continue
        folder = r.get("folder", "")
        rule_type = r.get("type", "extension")
        patterns = r.get("patterns", [])
        if folder and patterns:
            db.add_sorter_rule(folder, rule_type, patterns)

    _backup(_LEGACY_RULES)
    print(f"[migrate] rules.json -> sorter_rules ({len(rules)} rules)")


def _backup(path: str) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = f"{path}.bak.{ts}"
    try:
        shutil.move(path, dest)
        print(f"[migrate] backed up to {dest}")
    except Exception as e:
        print(f"[migrate] backup failed for {path}: {e}")
