from PySide6.QtCore import QThread, Signal
from PIL import Image


class EnhanceWorker(QThread):
    progress = Signal(int)
    finished = Signal(Image.Image, str)
    error    = Signal(str)

    def __init__(self, task: str, img: Image.Image,
                 skin_bgr: tuple | None = None,
                 use_esrgan: bool = True):
        super().__init__()
        self._task       = task
        self._img        = img
        self._skin_bgr   = skin_bgr
        self._use_esrgan = use_esrgan

    def run(self):
        try:
            if self._task == "enhance":
                from app.features.image_enhancer.core.enhancer import enhance
                result, info = enhance(
                    self._img,
                    use_esrgan=self._use_esrgan,
                    progress_cb=self.progress.emit
                )
                self.finished.emit(result, info)

            elif self._task == "colorize":
                from app.features.image_enhancer.core.colorizer import colorize
                result = colorize(
                    self._img,
                    skin_bgr=self._skin_bgr,
                    progress_cb=self.progress.emit
                )
                self.finished.emit(result, "Раскраска завершена (siggraph17)")

        except Exception as e:
            self.error.emit(str(e))