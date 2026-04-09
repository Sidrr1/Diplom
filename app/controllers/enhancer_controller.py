from PySide6.QtCore import QObject
from PIL import Image


class EnhancerController(QObject):
    def __init__(self, view):
        super().__init__()
        self._view       = view
        self._worker     = None
        self._use_esrgan = True
        view.enhance_requested.connect(self._on_enhance)
        view.colorize_requested.connect(self._on_colorize)

    def _on_enhance(self, img: Image.Image):
        self._run("enhance", img, None)

    def _on_colorize(self, img: Image.Image, skin_bgr):
        self._run("colorize", img, skin_bgr)

    def _run(self, task: str, img: Image.Image, skin_bgr):
        if self._worker and self._worker.isRunning():
            return
        from app.features.image_enhancer.core.enhance_worker import EnhanceWorker
        self._worker = EnhanceWorker(task, img, skin_bgr, self._use_esrgan)
        self._worker.progress.connect(self._view.set_progress)
        self._worker.finished.connect(
            lambda res, info: self._view.show_result(res, info))
        self._worker.error.connect(self._view.show_error)
        self._worker.start()