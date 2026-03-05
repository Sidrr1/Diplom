from app.features.player.stream_worker import StreamWorker


class PlayerController:
    def __init__(self, view):
        self.view    = view
        self._worker = None
        view.play_requested.connect(self._on_play)

    def _on_play(self, url: str):
        print(f"[controller] play requested: {url}")
        self.view.set_loading(True)
        quality = self.view.current_quality()
        self._worker = StreamWorker(url, quality)
        self._worker.ready.connect(self._on_ready)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_ready(self, video_url: str, audio_url: str, qualities: list):
        print(f"[controller] ready: video={video_url[:60]}... audio={bool(audio_url)}")
        self.view.set_loading(False)
        self.view.update_qualities(qualities)
        self.view.play(video_url, audio_url)

    def _on_error(self, msg: str):
        print(f"[controller] error: {msg}")
        self.view.set_loading(False)
        self.view.show_error(msg)