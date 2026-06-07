"""Логика вкладки сортировщика (без немедленного сохранения в БД)."""
import os

from PySide6.QtWidgets import QFileDialog, QMessageBox

from app.core.paths import normalize_path
from app.features.file_sorter.core.source_folder import set_source_folder


class SorterLogicMixin:
    """Обработчики вкладки сортировщика: выбор папки и валидация автосорта."""

    def _choose_sorter_src(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Папка-входящие", self._sorter_src_edit.text().strip()
        )
        if folder:
            self._sorter_src_edit.setText(normalize_path(folder))

    def _set_sorter_downloads(self):
        downloads = normalize_path(os.path.join(os.path.expanduser("~"), "Downloads"))
        if os.path.isdir(downloads):
            self._sorter_src_edit.setText(downloads)
        else:
            QMessageBox.warning(
                self,
                "Загрузки",
                "Папка «Загрузки» не найдена. Укажите путь вручную через «Обзор…».",
            )

    def _persist_sorter_source(self):
        norm = set_source_folder(self._sorter_src_edit.text())
        self.cfg["sorter_source"] = norm
        if norm != self._sorter_src_edit.text().strip():
            self._sorter_src_edit.blockSignals(True)
            self._sorter_src_edit.setText(norm)
            self._sorter_src_edit.blockSignals(False)

    def _update_sorter_watch_ui(self):
        if not hasattr(self, "_lbl_sorter_watch"):
            return
        src = self._sorter_src_edit.text().strip()
        valid = bool(src and os.path.isdir(src))
        auto = self._cb_sorter_auto.isChecked()

        self._cb_sorter_auto.setEnabled(valid)

        _status_base = (
            "color:{fg}; background:rgba(255,255,255,4); border-radius:8px;"
            "padding:10px 12px; border-left:3px solid {accent};"
        )
        if auto and valid:
            self._lbl_sorter_watch.setText(
                f"● Активно — только «{os.path.basename(src)}»\n{src}"
            )
            self._lbl_sorter_watch.setStyleSheet(
                _status_base.format(fg="#5a9fd4", accent="#0078d7")
            )
        elif auto and not valid:
            self._lbl_sorter_watch.setText(
                "● Укажите существующую папку-входящие (кнопка «Загрузки» или «Обзор…»)"
            )
            self._lbl_sorter_watch.setStyleSheet(
                _status_base.format(fg="#e88", accent="#c0392b")
            )
        elif valid:
            self._lbl_sorter_watch.setText(
                f"○ Готово: «{os.path.basename(src)}». Включите переключатель выше."
            )
            self._lbl_sorter_watch.setStyleSheet(
                _status_base.format(fg="#888", accent="#444")
            )
        else:
            self._lbl_sorter_watch.setText(
                "○ Выберите папку-входящие. Остальные диски и папки не отслеживаются."
            )
            self._lbl_sorter_watch.setStyleSheet(
                _status_base.format(fg="#666", accent="#333")
            )

    def _on_sorter_source_changed(self):
        src = self._sorter_src_edit.text().strip()
        if self._cb_sorter_auto.isChecked() and not (src and os.path.isdir(src)):
            self._cb_sorter_auto.blockSignals(True)
            self._cb_sorter_auto.setChecked(False)
            self._cb_sorter_auto.blockSignals(False)
        self._update_sorter_watch_ui()
        self._mark_tab_dirty("sorter")

    def _on_sorter_auto_toggled(self, checked: bool):
        src = self._sorter_src_edit.text().strip()
        if checked and (not src or not os.path.isdir(src)):
            self._cb_sorter_auto.blockSignals(True)
            self._cb_sorter_auto.setChecked(False)
            self._cb_sorter_auto.blockSignals(False)
            QMessageBox.warning(
                self,
                "Автосортировка",
                "Сначала укажите папку (например «Загрузки»).\n"
                "Сортируются только файлы из этой папки, не весь компьютер.",
            )
            self._update_sorter_watch_ui()
            return
        self._update_sorter_watch_ui()
        self._mark_tab_dirty("sorter")
