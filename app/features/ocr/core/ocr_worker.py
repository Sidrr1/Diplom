# app/features/ocr/ocr_worker.py
import platform
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap


class OcrWorker(QThread):
    result   = Signal(str)
    error    = Signal(str)
    progress = Signal(str)

    # Tesseract не требует предзагрузки — оставляем для совместимости
    _reader = True

    def __init__(self, pixmap: QPixmap, langs: list = None):
        super().__init__()
        self._pixmap = pixmap
        self._langs  = langs or ["rus", "eng"]

    def run(self):
        try:
            import pytesseract
            import numpy as np
            from PIL import Image, ImageEnhance, ImageOps
            from PySide6.QtCore import QBuffer, QIODevice
            import io

            # Путь к tesseract на Windows
            if platform.system() == "Windows":
                pytesseract.pytesseract.tesseract_cmd = (
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                )

            self.progress.emit("Распознавание текста...")

            # QPixmap → PIL Image
            buf = QBuffer()
            buf.open(QIODevice.WriteOnly)
            self._pixmap.save(buf, "PNG")
            buf.close()
            pil_img = Image.open(io.BytesIO(buf.data().data())).convert("RGB")

            # Предобработка
            pil_img = self._preprocess(pil_img)

            # Распознавание
            lang_str = "+".join(self._langs)
            text = pytesseract.image_to_string(
                pil_img,
                lang=lang_str,
                config="--psm 6 --oem 3",
            )

            text = text.strip()
            self.result.emit(text if text else "Текст не найден")

        except ImportError:
            self.error.emit(
                "pytesseract не установлен.\n"
                "Выполни: pip install pytesseract"
            )
        except pytesseract.TesseractNotFoundError:
            self.error.emit(
                "Tesseract не найден.\n"
                "Скачай: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "и установи с поддержкой русского языка."
            )
        except Exception as e:
            self.error.emit(str(e))

    def _preprocess(self, pil_img):
        from PIL import Image, ImageEnhance, ImageOps
        import numpy as np

        # Увеличиваем — мелкий текст распознаётся лучше
        w, h = pil_img.size
        pil_img = pil_img.resize((w * 2, h * 2), Image.LANCZOS)

        # Повышаем контраст и резкость
        pil_img = ImageEnhance.Contrast(pil_img).enhance(2.0)
        pil_img = ImageEnhance.Sharpness(pil_img).enhance(2.0)

        # Инвертируем если тёмный фон
        arr = np.array(pil_img.convert("L"))
        if arr.mean() < 128:
            pil_img = ImageOps.invert(pil_img.convert("RGB"))

        return pil_img