"""Настройки OCR в SQLite (модуль ocr)."""
from __future__ import annotations

import json

from app.core.database import db

_MODULE = "ocr"
_KEY_LANGS = "ocr_langs"
_KEY_POSTPROCESS = "ocr_postprocess"
_DEFAULT_LANGS = ["rus", "eng"]


def get_ocr_langs() -> list[str]:
    raw = db.get_setting(_KEY_LANGS, _MODULE, "")
    if not raw:
        return list(_DEFAULT_LANGS)
    try:
        data = json.loads(raw)
        if isinstance(data, list) and data:
            return [str(x).strip() for x in data if str(x).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    # legacy: "rus+eng"
    if "+" in str(raw):
        return [p.strip() for p in str(raw).split("+") if p.strip()]
    return list(_DEFAULT_LANGS)


def set_ocr_langs(codes: list[str]) -> None:
    clean = []
    for c in codes:
        c = str(c).strip()
        if c and c not in clean:
            clean.append(c)
    if not clean:
        clean = list(_DEFAULT_LANGS)
    db.set_setting(_KEY_LANGS, json.dumps(clean, ensure_ascii=False), _MODULE)


def langs_tesseract_str() -> str:
    from app.features.ocr.core.tesseract_env import list_installed_langs

    installed = set(list_installed_langs())
    langs = [c for c in get_ocr_langs() if c in installed]
    if not langs:
        langs = [c for c in ("rus", "eng") if c in installed] or ["eng"]
    return "+".join(langs)


def is_postprocess_enabled() -> bool:
    raw = db.get_setting(_KEY_POSTPROCESS, _MODULE, "1")
    return str(raw).lower() in ("1", "true", "yes", "on")


def set_postprocess_enabled(enabled: bool) -> None:
    db.set_setting(_KEY_POSTPROCESS, "1" if enabled else "0", _MODULE)
