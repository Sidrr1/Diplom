"""Ключи настроек EdgeTools и значения по умолчанию."""

DEFAULTS = {
    "autostart": False,
    "player_quality": "Авто",
    "player_opacity": 100,
    "player_volume": 70,
    "player_history_days": 7,
    "sorter_source": "",
    "sorter_auto_enabled": False,
    "sorter_opacity": 100,
    "sorter_history_days": 7,
    "enhancer_autosave": True,
    "enhancer_format": "JPEG",
    "enhancer_jpeg_quality": 95,
    "notes_edge_position": "right",
    "notes_width": 250,
    "notes_height": 200,
    "notes_opacity": 100,
    "notes_mode": "normal",
}

# key -> module в таблице settings
KEY_MODULES = {
    "autostart": "global",
    "player_quality": "player",
    "player_opacity": "player",
    "player_volume": "player",
    "player_history_days": "player",
    "sorter_source": "sorter",
    "sorter_auto_enabled": "sorter",
    "sorter_opacity": "sorter",
    "sorter_history_days": "sorter",
    "enhancer_autosave": "enhancer",
    "enhancer_format": "enhancer",
    "enhancer_jpeg_quality": "enhancer",
}

# ключи в БД (module notes) -> ключ в cfg
NOTES_DB_TO_CFG = {
    "edge_position": "notes_edge_position",
    "note_width": "notes_width",
    "note_height": "notes_height",
    "notes_opacity": "notes_opacity",
    "notes_mode": "notes_mode",
}

BOOL_KEYS = frozenset({"autostart", "enhancer_autosave", "sorter_auto_enabled"})
INT_KEYS = frozenset({
    "player_opacity", "player_volume", "player_history_days",
    "sorter_opacity", "sorter_history_days",
    "enhancer_jpeg_quality", "notes_width", "notes_height", "notes_opacity",
})
