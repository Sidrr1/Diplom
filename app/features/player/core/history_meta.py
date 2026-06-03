"""Метаданные для истории плеера (без тяжёлого yt-dlp)."""
from urllib.parse import parse_qs, urlparse


def youtube_video_id(url: str) -> str | None:
    if not url:
        return None
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        part = parsed.path.strip("/").split("/")[0]
        return part or None
    q = parse_qs(parsed.query)
    return (q.get("v") or [None])[0]


def thumbnail_for_url(url: str) -> str:
    vid = youtube_video_id(url)
    if vid:
        return f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"
    return ""


def display_title(url: str, title: str = "") -> str:
    if title and title.strip():
        return title.strip()[:200]
    if not url:
        return "Без названия"
    parsed = urlparse(url)
    if youtube_video_id(url):
        return f"YouTube — {youtube_video_id(url)}"
    return parsed.netloc or url[:80]
