"""
Сохранение результата Image Enhancer с учётом настроек приложения.

Читает ``enhancer_autosave``, ``enhancer_save_path``, формат и качество JPEG
из глобального config; используется UI при «Сохранить» / автосохранении.
"""
from __future__ import annotations

import os
from datetime import datetime

from PIL import Image

from app.core import config
from app.core.paths import normalize_path

_FMT_EXT = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}


def default_save_folder() -> str:
    """Папка по умолчанию: ~/Pictures/EdgeTools."""
    return normalize_path(os.path.join(os.path.expanduser("~"), "Pictures", "EdgeTools"))


def get_save_settings() -> dict:
    """Словарь настроек сохранения из config (autosave, folder, format, jpeg_quality)."""
    cfg = config.load()
    folder = normalize_path(cfg.get("enhancer_save_path", "")) or default_save_folder()
    return {
        "autosave": bool(cfg.get("enhancer_autosave", True)),
        "folder": folder,
        "format": str(cfg.get("enhancer_format", "JPEG")).upper(),
        "jpeg_quality": int(cfg.get("enhancer_jpeg_quality", 95)),
    }


def _unique_path(folder: str, stem: str, ext: str) -> str:
    """Путь без коллизии: при существующем файле добавляет timestamp."""
    os.makedirs(folder, exist_ok=True)
    candidate = os.path.join(folder, stem + ext)
    if not os.path.exists(candidate):
        return candidate
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(folder, f"{stem}_{stamp}{ext}")


def build_output_path(source_path: str | None, settings: dict | None = None) -> str:
    """Сформировать путь ``{stem}_enhanced.{ext}`` в папке из настроек."""
    s = settings or get_save_settings()
    ext = _FMT_EXT.get(s["format"], ".jpg")
    if source_path:
        stem = os.path.splitext(os.path.basename(source_path))[0] + "_enhanced"
    else:
        stem = "enhanced"
    return _unique_path(s["folder"], stem, ext)


def save_image(img: Image.Image, path: str, settings: dict | None = None) -> str:
    """Сохранить PIL-изображение; при ошибке формата — fallback в PNG."""
    s = settings or get_save_settings()
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".jpg", ".jpeg"):
            img.convert("RGB").save(path, "JPEG", quality=s["jpeg_quality"])
        elif ext == ".webp":
            img.save(path, "WEBP", quality=s["jpeg_quality"])
        elif ext == ".bmp":
            img.save(path, "BMP")
        else:
            img.save(path, "PNG")
        return path
    except Exception:
        fallback = os.path.splitext(path)[0] + ".png"
        img.save(fallback, "PNG")
        return fallback
