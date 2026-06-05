"""Путь к cookies.txt для yt-dlp (YouTube)."""
import os

from app.core.paths import normalize_path


def _project_root() -> str:
    return os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )


def get_youtube_cookies_path() -> str | None:
    """Файл cookies из настроек или legacy cookies.txt в корне проекта."""
    from app.core import config

    cfg = config.load()
    custom = normalize_path(cfg.get("player_cookies_path", ""))
    if custom and os.path.isfile(custom):
        return custom

    legacy = os.path.join(_project_root(), "cookies.txt")
    if os.path.isfile(legacy):
        return legacy
    return None
