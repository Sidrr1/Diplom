"""
Путь к cookies.txt для yt-dlp (YouTube) в EdgeTools.

Используется StreamWorker для авторизованных запросов к YouTube.
"""
import os

from app.core.paths import normalize_path


def _project_root() -> str:
    """Корень проекта Diplom (на четыре уровня выше этого файла)."""
    return os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )


def get_youtube_cookies_path() -> str | None:
    """
    Файл cookies для yt-dlp.

    Сначала player_cookies_path из config.json, иначе legacy cookies.txt в корне.

    Returns:
        Абсолютный путь к файлу или None, если cookies не настроены.
    """
    from app.core import config

    cfg = config.load()
    custom = normalize_path(cfg.get("player_cookies_path", ""))
    if custom and os.path.isfile(custom):
        return custom

    legacy = os.path.join(_project_root(), "cookies.txt")
    if os.path.isfile(legacy):
        return legacy
    return None
