# stream_worker.py — извлечение потоков YouTube через yt-dlp
import os
import yt_dlp
from PySide6.QtCore import QThread, Signal


class StreamWorker(QThread):
    ready = Signal(str, str, list)  # video_url, audio_url, qualities
    error = Signal(str)

    HEIGHT_MAP = {"1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
    KNOWN_HEIGHTS = (2160, 1440, 1080, 720, 480, 360, 240)

    def __init__(self, url: str, quality: str = "Авто", prefer_muxed: bool = False):
        super().__init__()
        self.url = url
        self.quality = quality
        self.prefer_muxed = prefer_muxed

    def run(self):
        try:
            if os.path.isfile(self.url):
                self.ready.emit(self.url, "", ["Авто"])
                return
            info = self._extract_info()
            video_url, audio_url = self._get_stream_urls(info)
            if not video_url or not self._url_ok(video_url):
                raise RuntimeError("Не удалось получить прямой поток (только HLS/manifest)")
            if self.prefer_muxed and audio_url:
                raise RuntimeError(
                    "Нет единого файла для перемотки — попробуй качество 480p"
                )
            qualities = self._get_qualities(info)
            kind = "muxed" if self.prefer_muxed else ("split" if audio_url else "merged")
            print(f"[worker] stream {kind}: {video_url[:70]}...")
            self.ready.emit(video_url, audio_url, qualities)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    @staticmethod
    def _url_ok(url: str) -> bool:
        if not url:
            return False
        low = url.lower()
        bad = (
            "manifest.googlevideo",
            "/hls_playlist/",
            ".m3u8",
            "playlist_type",
            "/api/manifest/",
        )
        return not any(b in low for b in bad)

    def _build_format(self) -> str:
        height = self.HEIGHT_MAP.get(self.quality) or 720
        if self.prefer_muxed:
            return (
                f"best[height<={height}][vcodec!=none][acodec!=none]/"
                f"best[vcodec!=none][acodec!=none]/best"
            )
        height = self.HEIGHT_MAP.get(self.quality)
        if not height:
            return (
                "bestvideo[height<=720]+bestaudio/"
                "best[height<=720][vcodec!=none][acodec!=none]/best"
            )
        if height <= 720:
            return (
                f"best[height<={height}][vcodec!=none][acodec!=none]/"
                f"bestvideo[height<={height}]+bestaudio"
            )
        return (
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]"
        )

    def _extract_info(self) -> dict:
        opts = {
            "format": self._build_format(),
            "quiet": True,
            "noplaylist": True,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        }
        cookies_path = None
        try:
            from app.features.player.core.cookies_path import get_youtube_cookies_path
            cookies_path = get_youtube_cookies_path()
        except Exception:
            pass
        if cookies_path:
            print(f"[worker] cookies: {cookies_path}")
            opts["cookiefile"] = cookies_path

        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(self.url, download=False)

    def _get_stream_urls(self, info: dict) -> tuple[str, str]:
        if self.prefer_muxed:
            return self._pick_merged(info)

        requested = info.get("requested_formats")
        if requested and isinstance(requested, list) and len(requested) >= 2:
            v, a = self._split_streams(requested)
            if v and self._url_ok(v):
                return v, a

        target_h = self.HEIGHT_MAP.get(self.quality)
        v, a = self._pick_split_from_formats(info.get("formats") or [], target_h)
        if v and self._url_ok(v):
            return v, a or ""

        return self._pick_merged(info)

    def _split_streams(self, requested: list) -> tuple[str, str]:
        video_url = next(
            (f["url"] for f in requested if f.get("vcodec") not in (None, "none")), ""
        )
        audio_url = next(
            (
                f["url"] for f in requested
                if f.get("acodec") not in (None, "none")
                and f.get("vcodec") in (None, "none")
            ),
            "",
        )
        return video_url, audio_url

    def _pick_split_from_formats(self, formats: list, target_h: int | None):
        if not isinstance(formats, list):
            return "", ""
        videos = [
            f for f in formats
            if isinstance(f, dict)
            and self._url_ok(f.get("url", ""))
            and f.get("vcodec") not in (None, "none")
            and f.get("acodec") in (None, "none")
        ]
        audios = [
            f for f in formats
            if isinstance(f, dict)
            and self._url_ok(f.get("url", ""))
            and f.get("acodec") not in (None, "none")
            and f.get("vcodec") in (None, "none")
        ]
        if not videos or not audios:
            return "", ""

        if target_h:
            below = [f for f in videos if (f.get("height") or 0) <= target_h]
            if below:
                videos = below

        videos.sort(key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)
        audios.sort(key=lambda f: f.get("tbr") or 0, reverse=True)
        return videos[0]["url"], audios[0]["url"]

    def _pick_merged(self, info: dict) -> tuple[str, str]:
        formats = info.get("formats") or []
        if not isinstance(formats, list):
            formats = []

        candidates = [
            f for f in formats
            if isinstance(f, dict)
            and self._url_ok(f.get("url", ""))
            and f.get("vcodec") not in (None, "none")
            and f.get("acodec") not in (None, "none")
        ]
        target_h = self.HEIGHT_MAP.get(self.quality)
        if target_h:
            below = [f for f in candidates if (f.get("height") or 0) <= target_h]
            if below:
                candidates = below

        if candidates:
            candidates.sort(
                key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
                reverse=True,
            )
            return candidates[0]["url"], ""

        url = info.get("url") or ""
        if self._url_ok(url):
            return url, ""
        return "", ""

    def _get_qualities(self, info: dict) -> list[str]:
        formats = info.get("formats") or []
        if not isinstance(formats, list):
            return ["Авто"]
        heights = sorted({
            f["height"] for f in formats
            if isinstance(f, dict) and f.get("height") and f.get("vcodec") != "none"
        }, reverse=True)
        return ["Авто"] + [f"{h}p" for h in heights if h in self.KNOWN_HEIGHTS]
