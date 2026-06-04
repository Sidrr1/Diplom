# app/features/ocr/ocr_worker.py
import io

from PySide6.QtCore import QBuffer, QIODevice, QThread, Signal
from PySide6.QtGui import QPixmap

from app.features.ocr.core.ocr_engine import recognize
from app.features.ocr.core.ocr_settings import langs_tesseract_str


class OcrWorker(QThread):
    result = Signal(str)
    error = Signal(str)
    progress = Signal(str)

    _reader = True

    def __init__(self, pixmap: QPixmap, langs: list | None = None):
        super().__init__()
        self._pixmap = pixmap
        self._langs = langs

    def run(self):
        try:
            from PIL import Image, ImageEnhance, ImageOps
            import numpy as np

            self.progress.emit("Подготовка изображения...")

            buf = QBuffer()
            buf.open(QIODevice.WriteOnly)
            self._pixmap.save(buf, "PNG")
            buf.close()
            pil_img = Image.open(io.BytesIO(buf.data().data())).convert("RGB")
            pil_img = self._preprocess(pil_img)

            lang_str = "+".join(self._langs) if self._langs else langs_tesseract_str()
            self.progress.emit("Распознавание (подбор режима)...")

            text, conf, psm = recognize(pil_img, lang_str)
            if conf > 0:
                self.progress.emit(f"Готово · PSM {psm} · ~{conf}%")
            else:
                self.progress.emit("Готово")

            text = text.strip()
            self.result.emit(text if text else "Текст не найден")

        except ImportError:
            self.error.emit(
                "pytesseract не установлен.\n"
                "Выполни: pip install pytesseract"
            )
        except Exception as e:
            import pytesseract

            err = str(e)
            if isinstance(e, pytesseract.TesseractNotFoundError) or "tesseract" in err.lower():
                self.error.emit(
                    "Tesseract не найден.\n"
                    "Скачай: https://github.com/UB-Mannheim/tesseract/wiki\n"
                    "и установи нужные языки (rus, eng)."
                )
            else:
                self.error.emit(err)

    def _preprocess(self, pil_img):
        from PIL import Image, ImageEnhance, ImageOps
        import numpy as np

        w, h = pil_img.size
        scale = 2 if max(w, h) < 1200 else 1
        if scale > 1:
            pil_img = pil_img.resize((w * scale, h * scale), Image.LANCZOS)

        pil_img = ImageEnhance.Contrast(pil_img).enhance(1.8)
        pil_img = ImageEnhance.Sharpness(pil_img).enhance(1.6)

        arr = np.array(pil_img.convert("L"))
        if arr.mean() < 128:
            pil_img = ImageOps.invert(pil_img.convert("RGB"))

        return pil_img
