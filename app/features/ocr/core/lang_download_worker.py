"""Фоновая загрузка языковых пакетов Tesseract для UI."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.features.ocr.core.lang_downloader import download_traineddata
from app.features.ocr.core.tesseract_env import lang_display


class LangDownloadWorker(QThread):
    progress = Signal(str, int, int)  # code, bytes_done, total
    lang_started = Signal(str)
    finished_ok = Signal(list)
    failed = Signal(str, str)  # code, message

    def __init__(self, codes: list[str], parent=None):
        super().__init__(parent)
        self._codes = [c for c in codes if c]

    def run(self) -> None:
        done: list[str] = []
        for code in self._codes:
            self.lang_started.emit(code)
            try:

                def _prog(d: int, t: int) -> None:
                    self.progress.emit(code, d, t)

                download_traineddata(code, on_progress=_prog)
                done.append(code)
            except Exception as e:
                self.failed.emit(code, str(e))
                return
        self.finished_ok.emit(done)
