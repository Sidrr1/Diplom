"""Вкладка OCR."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QScrollArea, QMessageBox, QProgressDialog,
)
from PySide6.QtCore import Qt, QEventLoop
from PySide6.QtGui import QFont

from app.features.settings.ui import settings_styles as ss


class OcrMixin:
    def _page_ocr(self) -> QWidget:
        from app.features.ocr.core.ocr_settings import (
            get_ocr_langs,
            is_postprocess_enabled,
        )

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(self._section("ТОЧНОСТЬ"))
        card_pp = QFrame()
        card_pp.setStyleSheet(ss.STYLE_ROW_FRAME)
        pp_lay = QHBoxLayout(card_pp)
        pp_lay.setContentsMargins(14, 10, 14, 10)
        pp_lay.addWidget(self._row_title("Постобработка текста"))
        pp_lay.addStretch()
        self._cb_ocr_postprocess = QCheckBox()
        self._cb_ocr_postprocess.setChecked(is_postprocess_enabled())
        self._cb_ocr_postprocess.setStyleSheet("""
            QCheckBox::indicator { width:44px; height:24px; border-radius:12px;
                                   background:#333; border:none; }
            QCheckBox::indicator:checked { background:#0078d7; }
        """)
        pp_lay.addWidget(self._cb_ocr_postprocess)
        lay.addWidget(card_pp)

        lay.addWidget(self._section("ЯЗЫКИ РАСПОЗНАВАНИЯ"))

        card_lang = QFrame()
        card_lang.setStyleSheet(ss.STYLE_ROW_FRAME)
        lang_lay = QVBoxLayout(card_lang)
        lang_lay.setContentsMargins(14, 12, 14, 12)
        lang_lay.setSpacing(10)

        hdr = QHBoxLayout()
        icon = QLabel("🌐")
        icon.setFixedSize(28, 28)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            "background:rgba(0,120,215,0.12);border-radius:8px;font-size:14px;"
        )
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(self._row_title("Языки распознавания"))
        hdr.addWidget(icon)
        hdr.addLayout(col, 1)
        lang_lay.addLayout(hdr)

        quick = QHBoxLayout()
        quick.setSpacing(6)
        for label, slot in (
            ("Rus+Eng", self._ocr_pick_rus_eng),
            ("Все", self._ocr_pick_all),
            ("Сброс", self._ocr_pick_none),
        ):
            b = QPushButton(label)
            b.setFixedHeight(28)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton{background:#2a2a2a;color:#aaa;border:none;
                              border-radius:6px;font-size:10px;padding:0 10px;}
                QPushButton:hover{background:#0078d7;color:white;}
            """)
            b.clicked.connect(slot)
            quick.addWidget(b)
        quick.addStretch()
        lang_lay.addLayout(quick)

        carousel = QHBoxLayout()
        carousel.setSpacing(0)

        self._btn_ocr_prev = QPushButton("‹")
        self._btn_ocr_prev.setFixedSize(28, 80)
        self._btn_ocr_prev.setCursor(Qt.PointingHandCursor)
        self._btn_ocr_prev.setStyleSheet(ss.OCR_ARROW)
        self._btn_ocr_prev.clicked.connect(self._ocr_carousel_prev)
        carousel.addWidget(self._btn_ocr_prev)

        self._ocr_card = QPushButton()
        self._ocr_card.setObjectName("ocrCarousel")
        self._ocr_card.setMinimumHeight(80)
        self._ocr_card.setCursor(Qt.PointingHandCursor)
        self._ocr_card.setStyleSheet(ss.OCR_CARD_BASE)
        self._ocr_card.clicked.connect(self._ocr_toggle_current)
        card_lay = QVBoxLayout(self._ocr_card)
        card_lay.setContentsMargins(16, 12, 16, 12)
        card_lay.setSpacing(4)

        self._lbl_ocr_name = QLabel("—")
        self._lbl_ocr_name.setAlignment(Qt.AlignCenter)
        self._lbl_ocr_name.setStyleSheet(
            "color:#f0f0f0;font-size:18px;font-weight:600;border:none;background:transparent;"
        )
        self._lbl_ocr_name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        card_lay.addWidget(self._lbl_ocr_name)

        self._lbl_ocr_code = QLabel("")
        self._lbl_ocr_code.setAlignment(Qt.AlignCenter)
        self._lbl_ocr_code.setStyleSheet(
            "color:#0078d7;font-size:11px;font-weight:600;border:none;background:transparent;"
        )
        self._lbl_ocr_code.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        card_lay.addWidget(self._lbl_ocr_code)

        carousel.addWidget(self._ocr_card, 1)

        self._btn_ocr_next = QPushButton("›")
        self._btn_ocr_next.setFixedSize(28, 80)
        self._btn_ocr_next.setCursor(Qt.PointingHandCursor)
        self._btn_ocr_next.setStyleSheet(ss.OCR_ARROW)
        self._btn_ocr_next.clicked.connect(self._ocr_carousel_next)
        carousel.addWidget(self._btn_ocr_next)

        lang_lay.addLayout(carousel)

        tags_row = QHBoxLayout()
        tags_row.setSpacing(6)
        tags_lbl = self._row_subtitle("Выбрано")
        tags_lbl.setFixedWidth(52)
        tags_row.addWidget(tags_lbl)
        strip_scroll = QScrollArea()
        strip_scroll.setWidgetResizable(True)
        strip_scroll.setFrameShape(QFrame.NoFrame)
        strip_scroll.setFixedHeight(30)
        strip_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        strip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        strip_scroll.setStyleSheet(
            "QScrollArea{background:#141414;border-radius:8px;border:1px solid #2a2a2a;}"
        )
        self._ocr_selected_inner = QWidget()
        self._ocr_selected_inner.setStyleSheet("background:transparent;")
        self._ocr_selected_strip = QHBoxLayout(self._ocr_selected_inner)
        self._ocr_selected_strip.setContentsMargins(4, 2, 4, 2)
        self._ocr_selected_strip.setSpacing(4)
        self._ocr_selected_strip.addStretch()
        strip_scroll.setWidget(self._ocr_selected_inner)
        tags_row.addWidget(strip_scroll, 1)
        lang_lay.addLayout(tags_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_refresh = QPushButton("↻")
        btn_refresh.setFixedSize(32, 32)
        btn_refresh.setToolTip("Обновить список")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet("""
            QPushButton{background:#252525;color:#ccc;border:1px solid #333;border-radius:8px;}
            QPushButton:hover{background:#333;color:white;border-color:#0078d7;}
        """)
        btn_refresh.clicked.connect(self._reload_ocr_lang_list)
        btn_row.addWidget(btn_refresh)

        btn_dl = QPushButton("⬇  Скачать выбранные")
        btn_dl.setFixedHeight(32)
        btn_dl.setCursor(Qt.PointingHandCursor)
        btn_dl.setStyleSheet("""
            QPushButton{background:rgba(0,120,215,0.2);color:#9ecbff;border:1px solid #0078d7;
                          border-radius:8px;font-size:11px;}
            QPushButton:hover{background:#0078d7;color:white;}
            QPushButton:disabled{background:#252525;color:#555;border-color:#333;}
        """)
        btn_dl.clicked.connect(self._ocr_download_selected)
        btn_row.addWidget(btn_dl, 1)
        self._btn_ocr_download = btn_dl
        lang_lay.addLayout(btn_row)

        from app.features.ocr.core.tesseract_env import tessdata_dir

        path_hint = self._row_subtitle(
            f"Пакеты скачиваются при сохранении · {tessdata_dir()}"
        )
        path_hint.setWordWrap(True)
        lang_lay.addWidget(path_hint)

        lay.addWidget(card_lang)

        self._ocr_catalog: list[str] = []
        self._ocr_selected: set[str] = set()
        self._ocr_carousel_idx = 0
        self._ocr_lang_installed: set[str] = set()
        self._ocr_download_worker = None
        self._fill_ocr_lang_list(set(get_ocr_langs()))

        lay.addStretch()
        self._ocr_page = page
        return page

    def _fill_ocr_lang_list(self, selected: set[str] | None = None):
        from app.features.ocr.core.tesseract_env import (
            list_catalog_langs,
            list_installed_langs,
        )

        if selected is None:
            selected = set(self._ocr_selected)

        self._ocr_catalog = list_catalog_langs()
        self._ocr_selected = set(selected)
        self._ocr_lang_installed = set(list_installed_langs())

        if self._ocr_carousel_idx >= len(self._ocr_catalog):
            self._ocr_carousel_idx = max(0, len(self._ocr_catalog) - 1)

        self._ocr_update_lang_count_label()
        self._ocr_refresh_carousel()
        self._ocr_rebuild_selected_strip()

    def _ocr_update_lang_count_label(self):
        pass

    def _ocr_current_code(self) -> str | None:
        if not self._ocr_catalog:
            return None
        idx = max(0, min(self._ocr_carousel_idx, len(self._ocr_catalog) - 1))
        return self._ocr_catalog[idx]

    def _ocr_carousel_prev(self):
        if not self._ocr_catalog:
            return
        self._ocr_carousel_idx = (self._ocr_carousel_idx - 1) % len(self._ocr_catalog)
        self._ocr_refresh_carousel()

    def _ocr_carousel_next(self):
        if not self._ocr_catalog:
            return
        self._ocr_carousel_idx = (self._ocr_carousel_idx + 1) % len(self._ocr_catalog)
        self._ocr_refresh_carousel()

    def _ocr_go_to_lang(self, code: str):
        if code in self._ocr_catalog:
            self._ocr_carousel_idx = self._ocr_catalog.index(code)
            self._ocr_refresh_carousel()

    def _ocr_refresh_carousel(self):
        from app.features.ocr.core.tesseract_env import lang_display, lang_tag

        code = self._ocr_current_code()
        if not code:
            self._lbl_ocr_name.setText("Нет языков")
            self._lbl_ocr_code.setText("")
            self._btn_ocr_prev.setEnabled(False)
            self._btn_ocr_next.setEnabled(False)
            return

        installed = code in self._ocr_lang_installed
        selected = code in self._ocr_selected
        tag = lang_tag(code)

        self._lbl_ocr_name.setText(lang_display(code))
        if installed:
            self._lbl_ocr_code.setText(tag)
            self._lbl_ocr_code.setStyleSheet(
                "color:#9ecbff;font-size:11px;font-weight:600;border:none;background:transparent;"
            )
        else:
            self._lbl_ocr_code.setText(tag)
            self._lbl_ocr_code.setStyleSheet(
                "color:#555;font-size:11px;font-weight:600;border:none;background:transparent;"
            )

        if selected:
            self._ocr_card.setStyleSheet(ss.OCR_CARD_ON)
        elif installed:
            self._ocr_card.setStyleSheet(ss.OCR_CARD_INSTALLED)
        else:
            self._ocr_card.setStyleSheet(ss.OCR_CARD_BASE)

        self._btn_ocr_prev.setEnabled(len(self._ocr_catalog) > 1)
        self._btn_ocr_next.setEnabled(len(self._ocr_catalog) > 1)

    def _ocr_toggle_current(self):
        code = self._ocr_current_code()
        if not code:
            return
        if code in self._ocr_selected:
            self._ocr_selected.discard(code)
        else:
            self._ocr_selected.add(code)
        self._ocr_update_lang_count_label()
        self._ocr_refresh_carousel()
        self._ocr_rebuild_selected_strip()
        self._mark_tab_dirty("ocr")

    def _ocr_rebuild_selected_strip(self):
        from app.features.ocr.core.tesseract_env import lang_tag

        while self._ocr_selected_strip.count():
            item = self._ocr_selected_strip.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self._ocr_selected:
            lbl = QLabel("—")
            lbl.setStyleSheet("color:#444;font-size:10px;border:none;background:transparent;")
            self._ocr_selected_strip.addWidget(lbl)
        else:
            for code in sorted(self._ocr_selected, key=lang_tag):
                pill = QPushButton(lang_tag(code))
                pill.setFixedHeight(22)
                pill.setCursor(Qt.PointingHandCursor)
                pill.setStyleSheet(ss.OCR_TAG)
                pill.clicked.connect(lambda _=False, c=code: self._ocr_go_to_lang(c))
                self._ocr_selected_strip.addWidget(pill)

        self._ocr_selected_strip.addStretch()

    def _ocr_download_selected(self) -> bool:
        from app.features.ocr.core.tesseract_env import (
            lang_display,
            missing_lang_packs,
        )

        selected = self._collect_ocr_langs()
        if not selected:
            QMessageBox.warning(self, "OCR", "Сначала отметьте языки в списке.")
            return False
        missing = missing_lang_packs(selected)
        if not missing:
            QMessageBox.information(
                self,
                "OCR",
                "Все выбранные языки уже установлены.",
            )
            return True
        return self._run_ocr_lang_download(missing)

    def _run_ocr_lang_download(self, codes: list[str]) -> bool:
        from app.features.ocr.core.lang_download_worker import LangDownloadWorker
        from app.features.ocr.core.tesseract_env import lang_display

        if not codes:
            return True
        if self._ocr_download_worker and self._ocr_download_worker.isRunning():
            return False

        names = ", ".join(lang_display(c) for c in codes)
        dlg = QProgressDialog(f"Скачивание: {names}", "Отмена", 0, 100, self)
        dlg.setWindowTitle("Языки OCR")
        dlg.setMinimumWidth(360)
        dlg.setAutoClose(False)
        dlg.setAutoReset(False)
        dlg.setValue(0)

        worker = LangDownloadWorker(codes, self)
        self._ocr_download_worker = worker
        ok = {"value": False}

        def on_progress(code: str, done: int, total: int) -> None:
            if total > 0:
                dlg.setValue(min(99, int(100 * done / total)))
            dlg.setLabelText(f"Скачивание {lang_display(code)} ({code})…")

        def on_ok(_done: list) -> None:
            ok["value"] = True
            dlg.setValue(100)
            loop.quit()

        def on_fail(code: str, msg: str) -> None:
            QMessageBox.warning(
                self,
                "OCR",
                f"Не удалось скачать «{lang_display(code)}» ({code}):\n{msg}",
            )
            loop.quit()

        def on_cancel() -> None:
            if worker.isRunning():
                worker.requestInterruption()
                worker.terminate()
            loop.quit()

        loop = QEventLoop(self)
        dlg.canceled.connect(on_cancel)
        worker.progress.connect(on_progress)
        worker.lang_started.connect(
            lambda c: dlg.setLabelText(f"Скачивание {lang_display(c)} ({c})…")
        )
        worker.finished_ok.connect(on_ok)
        worker.failed.connect(on_fail)
        worker.finished.connect(dlg.close)

        if getattr(self, "_btn_ocr_download", None):
            self._btn_ocr_download.setEnabled(False)
        worker.start()
        dlg.show()
        loop.exec()
        worker.wait(500)
        if getattr(self, "_btn_ocr_download", None):
            self._btn_ocr_download.setEnabled(True)
        self._ocr_download_worker = None

        if ok["value"]:
            self._reload_ocr_lang_list()
        return ok["value"]

    def _ocr_pick_rus_eng(self):
        self._ocr_selected = {c for c in ("rus", "eng") if c in self._ocr_catalog}
        self._ocr_update_lang_count_label()
        self._ocr_refresh_carousel()
        self._ocr_rebuild_selected_strip()
        self._mark_tab_dirty("ocr")

    def _ocr_pick_all(self):
        self._ocr_selected = set(self._ocr_catalog)
        self._ocr_update_lang_count_label()
        self._ocr_refresh_carousel()
        self._ocr_rebuild_selected_strip()
        self._mark_tab_dirty("ocr")

    def _ocr_pick_none(self):
        self._ocr_selected.clear()
        self._ocr_update_lang_count_label()
        self._ocr_refresh_carousel()
        self._ocr_rebuild_selected_strip()
        self._mark_tab_dirty("ocr")

    def _reload_ocr_lang_list(self):
        """Обновить список без пересоздания вкладки (фикс сдвига QStackedWidget)."""
        self._fill_ocr_lang_list(set(self._ocr_selected))

    def _collect_ocr_langs(self) -> list[str]:
        selected = getattr(self, "_ocr_selected", None)
        if isinstance(selected, set):
            return sorted(selected)
        from app.features.ocr.core.ocr_settings import get_ocr_langs
        return get_ocr_langs()

    
