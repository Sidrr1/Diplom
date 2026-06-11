"""
Фоновый поток Qt для тяжёлой обработки изображений.

Не блокирует UI: вызывает ``enhance()`` или ``colorize()`` и шлёт
сигналы progress / finished / error обратно во view.
"""
from PySide6.QtCore import QThread, Signal
from PIL import Image
import gc


class EnhanceWorker(QThread):
    """QThread: улучшение качества или раскраска в фоне."""

    progress = Signal(int)
    finished = Signal(Image.Image, str)
    error    = Signal(str)

    def __init__(self, task: str, img: Image.Image,
                 fidelity: float = 0.7,
                 intensity: float = 1.0):
        """
        Args:
            task: ``"enhance"`` или ``"colorize"``
            img: исходное PIL-изображение
            fidelity: похожесть на оригинал (0–1), только для enhance
            intensity: сила эффекта (0–1), только для enhance
        """
        super().__init__()
        self._task      = task
        self._img       = img
        self._fidelity  = fidelity
        self._intensity = intensity

    def run(self):
        """Точка входа потока: патч basicsr, затем enhance или colorize."""
        try:
            # Патч basicsr при первом запуске (в фоновом потоке)
            self._patch_basicsr()

            if self._task == "enhance":
                from app.features.image_enhancer.core.enhancer import enhance
                result, info = enhance(
                    self._img,
                    fidelity=self._fidelity,
                    intensity=self._intensity,
                    progress_cb=self.progress.emit
                )
                self.finished.emit(result, info)

            elif self._task == "colorize":
                from app.features.image_enhancer.core.colorizer import colorize
                result = colorize(self._img, progress_cb=self.progress.emit)
                self.finished.emit(result, "Раскраска завершена (siggraph17)")

            # Garbage collection после обработки
            gc.collect()

        except Exception as e:
            self.error.emit(str(e))

    def _patch_basicsr(self):
        """Патч совместимости basicsr + torchvision."""
        import sys
        if "torchvision.transforms.functional_tensor" not in sys.modules:
            import types
            import torchvision.transforms.functional as _F
            _mod = types.ModuleType("torchvision.transforms.functional_tensor")
            _mod.rgb_to_grayscale = _F.rgb_to_grayscale
            sys.modules["torchvision.transforms.functional_tensor"] = _mod