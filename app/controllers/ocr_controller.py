"""
Контроллер модуля OCR в EdgeTools.

Проверяет доступность Tesseract при старте и запускает оверлей выбора области экрана.
"""
from PySide6.QtCore import QObject, QTimer, Signal, QThread


class TesseractChecker(QThread):
    """Фоновая проверка установки Tesseract (не блокирует UI)."""

    ready = Signal()
    error = Signal(str)

    def run(self):
        """Пробует получить версию Tesseract через pytesseract."""
        try:
            import pytesseract
            from app.features.ocr.core.tesseract_env import configure_pytesseract

            configure_pytesseract()
            pytesseract.get_tesseract_version()
            self.ready.emit()
        except Exception as e:
            self.error.emit(str(e))


class OcrController(QObject):
    """
    Управление жизненным циклом OCR: проверка движка и запуск захвата экрана.

    Сигналы model_loading / model_ready / model_error — для индикации на Edge Panel.
    """

    model_loading = Signal()
    model_ready   = Signal()
    model_error   = Signal(str)

    def __init__(self):
        """Стартует проверку Tesseract и анимацию загрузки на кнопке OCR."""
        super().__init__()
        self._checker    = None
        self._anim_step  = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(600)
        self._check()

    def _check(self):
        """Запуск TesseractChecker в отдельном потоке."""
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
        """Tesseract найден — останавливаем анимацию и сообщаем UI."""
        self._anim_timer.stop()
        print("[ocr] Tesseract готов ✓")
        self.model_ready.emit()

    def _on_error(self, msg: str):
        """Tesseract недоступен — показываем подсказку по установке."""
        self._anim_timer.stop()
        print(f"[ocr] ошибка: {msg}")
        self.model_error.emit(
            "Tesseract не найден.\n"
            "Скачай: https://github.com/UB-Mannheim/tesseract/wiki"
        )

    def _anim_tick(self):
        """Шаг анимации «загрузка» на кнопке OCR (⏳ / ⌛)."""
        self._anim_step += 1

    @property
    def anim_step(self) -> int:
        """Текущий кадр анимации загрузки."""
        return self._anim_step

    def launch(self):
        """Открыть полноэкранный оверлей для выбора области распознавания."""
        from app.features.ocr.ui.ocr_overlay import OcrOverlay
        from app.features.ocr.ui.ocr_result_view import _launch_ocr

        self._overlay = OcrOverlay()
        self._overlay.area_selected.connect(_launch_ocr)
        self._overlay.cancelled.connect(self._overlay.deleteLater)