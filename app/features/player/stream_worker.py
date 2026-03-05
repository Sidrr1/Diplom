import yt_dlp
from PySide6.QtCore import QThread, Signal


class StreamWorker(QThread):
    ready = Signal(str, str, list)  # video_url, audio_url, qualities
    error = Signal(str)

    def __init__(self, url: str, quality: str = "Авто"):
        super().__init__()
        self.url     = url
        self.quality = quality

    def run(self):
        height_map = {"1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
        height = height_map.get(self.quality)

        fmt = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]" if height \
              else "bestvideo+bestaudio/best"

        opts = {"format": fmt, "quiet": True, "noplaylist": True}

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

                formats = info.get("formats", [])

                # Собираем качества — все форматы с видео
                heights = sorted({
                    f["height"] for f in formats
                    if f.get("height") and f.get("vcodec") != "none"
                }, reverse=True)
                qualities = ["Авто"] + [
                    f"{h}p" for h in heights if h in (2160, 1440, 1080, 720, 480, 360, 240)
                ]

                # Получаем URL видео и аудио
                requested = info.get("requested_formats")
                if requested and len(requested) >= 2:
                    # Раздельные потоки — берём оба
                    video_url = next(
                        (f["url"] for f in requested if f.get("vcodec") != "none"), None
                    )
                    audio_url = next(
                        (f["url"] for f in requested if f.get("acodec") != "none"
                         and f.get("vcodec") == "none"), None
                    )
                else:
                    # Combined поток
                    video_url = info.get("url") or formats[-1]["url"]
                    audio_url = ""

                self.ready.emit(video_url or "", audio_url or "", qualities)

        except Exception as e:
            self.error.emit(str(e))