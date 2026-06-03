import os
from app.features.player.core.stream_worker import StreamWorker

YOUTUBE_DOMAINS = ("youtube.com", "youtu.be")

class PlayerController:
    def __init__(self, view):
        self.view         = view
        self._worker      = None
        self._current_url = None
        view.play_requested.connect(self._on_play)

    def _on_play(self, url: str):
        if url.startswith("__seek__"):
            parts     = url.split("__at__")
            real_url  = parts[0].replace("__seek__", "", 1)
            start_pos = float(parts[1]) if len(parts) > 1 else 0.0
            self._current_url = real_url
            print(f"[controller] seek-reload: {real_url[:60]} from {start_pos:.1f}s")
            self.view.set_loading(True)
            # 1080p+ split: start= на googlevideo висит — для seek берём 720p muxed
            self._run_worker(real_url, start_pos=start_pos, force_quality="720p")
            return

        if not url.startswith("http") and not os.path.isfile(url):
            return
        print(f"[controller] play requested: {url}")
        self._current_url = url

        direct_exts = (".mp4", ".m3u8", ".mkv", ".avi", ".webm", ".ts", ".flv", ".mp3")
        is_direct = os.path.isfile(url) or any(ext in url.split("?")[0] for ext in direct_exts)
        if is_direct:
            self.view.switch_to_mpv()
            self.view.set_loading(False)
            self.view.play(url, "", original_url=url, start_pos=0.0)
            return

        self.view.set_loading(True)
        self._run_worker(url)
        
    def _run_worker(self, url: str, start_pos: float = 0.0, force_quality: str = None):
        quality = force_quality or self.view.current_quality()
        if force_quality:
            print(f"[controller] seek extract quality={quality}")
        self._worker = StreamWorker(url, quality)
        self._worker.ready.connect(lambda v, a, q: self._on_ready(v, a, q, start_pos))
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_ready(self, video_url: str, audio_url: str, qualities: list, start_pos: float = 0.0):
        print(f"[controller] ready: {video_url[:60]}... start={start_pos:.1f}s")
        self.view.switch_to_mpv()
        self.view.set_loading(False)
        self.view.update_qualities(qualities)
        self.view.play(video_url, audio_url,
                       original_url=self._current_url,
                       start_pos=start_pos)

    def _on_error(self, msg: str):
        print(f"[controller] error: {msg}")
        self.view.set_loading(False)
        self.view.show_error(msg)