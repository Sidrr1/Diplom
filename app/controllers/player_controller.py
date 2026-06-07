"""
Контроллер медиаплеера EdgeTools.

Принимает URL/файл из PlayerView, через StreamWorker извлекает потоки (yt-dlp)
и передаёт прямые ссылки в MPV. Обрабатывает seek-reload для YouTube.
"""
import os
from app.features.player.core.stream_worker import StreamWorker

YOUTUBE_DOMAINS = ("youtube.com", "youtu.be")


class PlayerController:
    """
    Связка PlayerView ↔ StreamWorker ↔ MPV.

    Для прямых файлов (.mp4 и т.д.) сразу отдаёт URL в MPV без yt-dlp.
    """

    def __init__(self, view):
        """
        Args:
            view: PlayerView — источник сигнала play_requested.
        """
        self.view         = view
        self._worker      = None
        self._current_url = None
        # Флаги повторных попыток при HLS и split-потоках при перемотке
        self._hls_retry        = False
        self._seek_muxed_tried = False
        self._worker_gen       = 0
        view.play_requested.connect(self._on_play)

    def _on_play(self, url: str):
        """
        Обработка запроса воспроизведения или специального seek-reload.

        Формат seek: __seek__{url}__at__{seconds}
        """
        if url.startswith("__seek__"):
            parts     = url.split("__at__")
            real_url  = parts[0].replace("__seek__", "", 1)
            start_pos = float(parts[1]) if len(parts) > 1 else 0.0
            self._current_url = real_url
            self._hls_retry = False
            self._seek_muxed_tried = False
            print(f"[controller] seek-reload: {real_url[:60]} from {start_pos:.1f}s")
            self.view.set_loading(True)
            # 1080p+ split: start= на googlevideo висит — для seek берём 720p muxed
            self._run_worker(
                real_url,
                start_pos=start_pos,
                force_quality="720p",
                prefer_muxed=True,
            )
            return

        if not url.startswith("http") and not os.path.isfile(url):
            return
        if url == self._current_url:
            if self._worker and self._worker.isRunning():
                print("[controller] skip duplicate play (worker running)")
                return
            if getattr(self.view, "_loading_play", False):
                print("[controller] skip duplicate play (loading)")
                return
        print(f"[controller] play requested: {url}")
        self._current_url = url
        self._hls_retry = False

        # Локальные файлы и прямые URL — без yt-dlp
        direct_exts = (".mp4", ".m3u8", ".mkv", ".avi", ".webm", ".ts", ".flv", ".mp3")
        is_direct = os.path.isfile(url) or any(ext in url.split("?")[0] for ext in direct_exts)
        if is_direct:
            self.view.switch_to_mpv()
            self.view.set_loading(False)
            self.view.play(url, "", original_url=url, start_pos=0.0)
            return

        self.view.set_loading(True)
        self._run_worker(url)

    def _run_worker(
        self,
        url: str,
        start_pos: float = 0.0,
        force_quality: str = None,
        prefer_muxed: bool = False,
    ):
        """
        Запуск StreamWorker в фоне; прерывает предыдущий, если ещё работает.

        Args:
            url: исходная ссылка (YouTube и т.д.)
            start_pos: позиция для seek-reload
            force_quality: переопределить качество из UI ("720p", "480p")
            prefer_muxed: запросить единый поток (видео+аудио) для перемотки
        """
        prev = self._worker
        if prev and prev.isRunning():
            try:
                prev.ready.disconnect()
                prev.error.disconnect()
            except (TypeError, RuntimeError):
                pass
            prev.requestInterruption()
        self._worker_gen += 1
        if hasattr(self.view, "_play_gen"):
            self.view._play_gen += 1
        gen = self._worker_gen
        quality = force_quality or self.view.current_quality()
        if prefer_muxed:
            print(f"[controller] seek muxed extract {quality}")
        self._worker = StreamWorker(url, quality, prefer_muxed=prefer_muxed)
        self._worker.ready.connect(
            lambda v, a, q: self._on_ready(v, a, q, start_pos, gen)
        )
        self._worker.error.connect(lambda msg: self._on_error(msg, gen))
        self._worker.start()

    def _is_hls_url(self, url: str) -> bool:
        """True, если URL указывает на HLS/manifest (MPV не воспроизводит напрямую)."""
        low = (url or "").lower()
        return any(x in low for x in ("manifest", "m3u8", "hls_playlist"))

    def _on_ready(
        self,
        video_url: str,
        audio_url: str,
        qualities: list,
        start_pos: float = 0.0,
        gen: int = 0,
    ):
        """
        Потоки получены — возможны повторы (HLS → 720p, split seek → 480p muxed).

        При успехе переключает view в MPV и вызывает play().
        """
        if gen != self._worker_gen:
            return
        if self._is_hls_url(video_url) and self._current_url and not self._hls_retry:
            self._hls_retry = True
            print("[controller] HLS/manifest — повтор с 720p")
            self._run_worker(
                self._current_url,
                start_pos=start_pos,
                force_quality="720p",
                prefer_muxed=start_pos > 0,
            )
            return
        if start_pos > 0 and audio_url:
            if self._seek_muxed_tried:
                self.view.set_loading(False)
                self.view.show_error("Перемотка: нет единого потока, выбери 480p вручную")
                return
            self._seek_muxed_tried = True
            print("[controller] seek вернул split — повтор muxed 480p")
            self._run_worker(
                self._current_url,
                start_pos=start_pos,
                force_quality="480p",
                prefer_muxed=True,
            )
            return
        print(
            f"[controller] ready: {'split' if audio_url else 'merged'} "
            f"{video_url[:60]}... start={start_pos:.1f}s"
        )
        try:
            from app.core.database import db
            from app.features.player.core.history_meta import display_title
            url = self._current_url or ""
            if url.startswith("http"):
                db.add_player_history(
                    url,
                    title=display_title(url),
                    last_position=start_pos,
                )
        except Exception as e:
            print(f"[controller] player history: {e}")
        self.view.switch_to_mpv()
        self.view.set_loading(False)
        self.view.update_qualities(qualities)
        self.view.play(video_url, audio_url,
                       original_url=self._current_url,
                       start_pos=start_pos)

    def _on_error(self, msg: str, gen: int = 0):
        """Ошибка извлечения потока — сброс loading и сообщение в UI."""
        if gen != self._worker_gen:
            return
        print(f"[controller] error: {msg}")
        self.view.set_loading(False)
        self.view.show_error(msg)

    def cleanup(self):
        """Остановить воркер и MPV/WebView при выходе из модуля."""
        print("[controller] Cleanup player")
        w = self._worker
        self._worker = None
        if w and w.isRunning():
            try:
                w.ready.disconnect()
                w.error.disconnect()
            except (TypeError, RuntimeError):
                pass
            w.wait(8000)
        if hasattr(self.view, "shutdown"):
            self.view.shutdown()
