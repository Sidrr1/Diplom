# app/controllers/ocr_controller.py
import platform
from PySide6.QtCore import QObject, QTimer, Signal, QThread


class TesseractChecker(QThread):
    """Проверяет наличие Tesseract в системе."""
    ready = Signal()
    error = Signal(str)

    def run(self):
        try:
            import pytesseract
            if platform.system() == "Windows":
                pytesseract.pytesseract.tesseract_cmd = (
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                )
            # Проверяем что tesseract доступен
            pytesseract.get_tesseract_version()
            self.ready.emit()
        except Exception as e:
            self.error.emit(str(e))


class OcrController(QObject):
    model_loading = Signal()
    model_ready   = Signal()
    model_error   = Signal(str)

    def __init__(self):
        super().__init__()
        self._checker    = None
        self._anim_step  = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(600)
        self._check()

    def _check(self):
        try:
            import pytesseract
            print("[ocr] проверка Tesseract...")
            self._checker = TesseractChecker()
            self._checker.ready.connect(self._on_ready)
            self._checker.error.connect(self._on_error)
            self._anim_timer.timeout.connect(self._anim_tick)
            self._anim_timer.start()
            self.model_loading.emit()
            self._checker.start()
        except ImportError:
            print("[ocr] pytesseract не установлен")
            self.model_error.emit("pytesseract не установлен.\npip install pytesseract")

    def _on_ready(self):
        self._anim_timer.stop()
        print("[ocr] Tesseract готов ✓")
        self.model_ready.emit()

    def _on_error(self, msg: str):
        self._anim_timer.stop()
        print(f"[ocr] ошибка: {msg}")
        self.model_error.emit(
            "Tesseract не найден.\n"
            "Скачай: https://github.com/UB-Mannheim/tesseract/wiki"
        )

    def _anim_tick(self):
        self._anim_step += 1

    @property
    def anim_step(self) -> int:
        return self._anim_step

    def launch(self):
        from app.features.ocr.ui.ocr_overlay import OcrOverlay
        from app.features.ocr.ui.ocr_result_view import _launch_ocr

        self._overlay = OcrOverlay()
        self._overlay.area_selected.connect(_launch_ocr)
        self._overlay.cancelled.connect(self._overlay.deleteLater)