#stream_worker.py
import os
import yt_dlp
from PySide6.QtCore import QThread, Signal

class StreamWorker(QThread):
    ready = Signal(str, str, list)  # video_url, audio_url, qualities
    error = Signal(str)

    HEIGHT_MAP = {"1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
    KNOWN_HEIGHTS = (2160, 1440, 1080, 720, 480, 360, 240)

    def __init__(self, url: str, quality: str = "Авто"):
        super().__init__()
        self.url     = url
        self.quality = quality

    # ── Точка входа ──────────────────────────────────────────────────────

    def run(self):
        try:
            if os.path.isfile(self.url):
                self.ready.emit(self.url, "", ["Авто"])
                return
            info = self._extract_info()
            print(f"[worker] extractor: {info.get('extractor')}")
            print(f"[worker] formats type: {type(info.get('formats'))}")
            print(f"[worker] requested_formats type: {type(info.get('requested_formats'))}")
            video_url, audio_url = self._get_stream_urls(info)
            qualities = self._get_qualities(info)
            self.ready.emit(video_url, audio_url, qualities)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    # ── Приватные методы ─────────────────────────────────────────────────

    def _build_format(self) -> str:
        height = self.HEIGHT_MAP.get(self.quality)
        if not height:
            # Авто — берём merged до 720p, стабильно
            return "best[vcodec!=none][acodec!=none]/best"

        if height <= 720:
            # До 720p — merged поток, стабильная перемотка
            return (
                f"best[height<={height}][vcodec!=none][acodec!=none]"
                f"/best[height<={height}]"
            )
        else:
            # 1080p и выше — split неизбежен, принимаем риски
            return (
                f"bestvideo[height<={height}]+bestaudio"
                f"/best[height<={height}]"
            )

    def _extract_info(self) -> dict:
        opts = {
        "format": self._build_format(),
        "quiet": True,
        "noplaylist": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    }

        cookies_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
            "cookies.txt"
        )
        if os.path.isfile(cookies_path):
            print(f"[worker] используем cookies.txt")
            opts["cookiefile"] = cookies_path

        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(self.url, download=False)

    def _get_stream_urls(self, info: dict) -> tuple[str, str]:
        requested = info.get("requested_formats")
        if requested and isinstance(requested, list) and len(requested) >= 2:
            return self._split_streams(requested)
        return self._combined_stream(info)

    def _split_streams(self, requested: list) -> tuple[str, str]:
        """Раздельные потоки — видео и аудио по отдельности."""
        video_url = next(
            (f["url"] for f in requested if f.get("vcodec") != "none"), ""
        )
        audio_url = next(
            (f["url"] for f in requested
             if f.get("acodec") != "none" and f.get("vcodec") == "none"), ""
        )
        return video_url, audio_url

    def _combined_stream(self, info: dict) -> tuple[str, str]:
        formats = info.get("formats") or []
        if not isinstance(formats, list):
            formats = []
        video_url = info.get("url") or (formats[-1]["url"] if formats else "")
        return video_url, ""

    def _get_qualities(self, info: dict) -> list[str]:
        formats = info.get("formats") or []
        if not isinstance(formats, list):
            return ["Авто"]
        heights = sorted({
            f["height"] for f in formats
            if isinstance(f, dict) and f.get("height") and f.get("vcodec") != "none"
        }, reverse=True)
        return ["Авто"] + [f"{h}p" for h in heights if h in self.KNOWN_HEIGHTS]
