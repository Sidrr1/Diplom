from PySide6.QtCore import QObject
from PIL import Image


class EnhancerController(QObject):
    def __init__(self, view):
        super().__init__()
        self._view       = view
        self._worker     = None
        view.enhance_requested.connect(self._on_enhance)
        view.colorize_requested.connect(self._on_colorize)

    def _on_enhance(self, img: Image.Image):
        # Получаем параметры из UI
        fidelity = self._view._fidelity_slider.value() / 100.0
        intensity = self._view._intensity_slider.value() / 100.0
        self._run("enhance", img, None, fidelity, intensity)

    def _on_colorize(self, img: Image.Image, skin_bgr):
        self._run("colorize", img, skin_bgr, 0.7, 1.0)

    def _run(self, task: str, img: Image.Image, skin_bgr, fidelity: float, intensity: float):
        if self._worker and self._worker.isRunning():
            return
        from app.features.image_enhancer.core.enhance_worker import EnhanceWorker
        self._worker = EnhanceWorker(task, img, skin_bgr, fidelity, intensity)
        self._worker.progress.connect(self._view.set_progress)
        self._worker.finished.connect(
            lambda res, info: self._view.show_result(res, info))
        self._worker.error.connect(self._view.show_error)
        self._worker.start()