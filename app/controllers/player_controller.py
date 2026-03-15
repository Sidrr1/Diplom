import os
import threading
from app.features.player.stream_worker import StreamWorker

class PlayerController:
    def __init__(self, view):
        self.view    = view
        self._worker = None
        view.play_requested.connect(self._on_play)

    def _on_play(self, url: str):
        if not url.startswith("http") and not os.path.isfile(url):
            return
        print(f"[controller] play requested: {url}")

        direct_exts = (".mp4", ".m3u8", ".mkv", ".avi", ".webm", ".ts", ".flv", ".mp3")
        is_direct = os.path.isfile(url) or any(ext in url.split("?")[0] for ext in direct_exts)
        if is_direct:
            self.view.switch_to_mpv()
            self.view.set_loading(False)
            self.view.play(url, "")
            return

        self.view.set_loading(True)
        self._run_worker(url)

    def _run_worker(self, url: str):
        quality = self.view.current_quality()
        self._worker = StreamWorker(url, quality)
        self._worker.ready.connect(self._on_ready)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_ready(self, video_url: str, audio_url: str, qualities: list):
        print(f"[controller] ready: {video_url[:60]}...")
        self.view.switch_to_mpv()
        self.view.set_loading(False)
        self.view.update_qualities(qualities)
        self.view.play(video_url, audio_url)

    def _on_error(self, msg: str):
        print(f"[controller] error: {msg}")
        self.view.set_loading(False)
        self.view.show_error(msg)

