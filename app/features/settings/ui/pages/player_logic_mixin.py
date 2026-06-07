"""Логика вкладки плеера (cookies YouTube)."""
import os

from PySide6.QtWidgets import QFileDialog, QMessageBox

from app.core.paths import normalize_path

_COOKIES_HELP = (
    "<b>Зачем</b><br>"
    "Помогает открывать YouTube в плеере, если без входа ролик не грузится.<br><br>"
    "<b>Как получить</b><br>"
    "1. Войди на <b>youtube.com</b> в Chrome или Edge.<br>"
    "2. Расширение <b>Get cookies.txt LOCALLY</b> → Export.<br>"
    "3. Сохрани .txt и укажи его кнопкой «Файл…».<br><br>"
    "Не обязательно, если смотришь через встроенный браузер. "
    "Файл личный — периодически обновляй."
)


class PlayerLogicMixin:
    """Логика вкладки плеера: выбор и отображение файла cookies YouTube."""

    def _choose_player_cookies(self) -> None:
        start = getattr(self, "_player_cookies_stored", "") or self._player_cookies_edit.text().strip()
        if not start or not os.path.isfile(start):
            start = os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Файл cookies для YouTube",
            start,
            "Текстовые файлы (*.txt);;Все файлы (*.*)",
        )
        if path:
            self._player_cookies_stored = normalize_path(path)
            self._update_player_cookies_status()
            self._mark_tab_dirty("player")

    def _clear_player_cookies(self) -> None:
        self._player_cookies_stored = ""
        self._player_cookies_edit.clear()
        self._update_player_cookies_status()
        self._mark_tab_dirty("player")

    def _show_player_cookies_help(self) -> None:
        QMessageBox.information(self, "Cookies для YouTube", _COOKIES_HELP)

    def _update_player_cookies_status(self) -> None:
        if not hasattr(self, "_player_cookies_edit"):
            return

        path = getattr(self, "_player_cookies_stored", "") or self._player_cookies_edit.text().strip()
        box = getattr(self, "_player_cookies_box", None)
        clear_btn = getattr(self, "_btn_cookies_clear", None)

        if clear_btn:
            clear_btn.setVisible(bool(path))

        if not path:
            self._player_cookies_edit.clear()
            self._player_cookies_edit.setToolTip("")
            self._player_cookies_edit.setStyleSheet("""
                QLineEdit {
                    background:transparent; color:#888; border:none;
                    selection-background-color:#0078d7;
                }
            """)
            if box:
                box.setStyleSheet("""
                    QFrame#cookiesPath {
                        background:#141414; border-radius:8px;
                        border:1px solid #2e2e2e;
                    }
                """)
            return

        self._player_cookies_edit.setToolTip(path)
        self._player_cookies_edit.setText(os.path.basename(path))

        if not box:
            return

        if os.path.isfile(path):
            self._player_cookies_edit.setStyleSheet("""
                QLineEdit {
                    background:transparent; color:#9ecbff; border:none;
                    selection-background-color:#0078d7;
                }
            """)
            box.setStyleSheet("""
                QFrame#cookiesPath {
                    background:#141414; border-radius:8px;
                    border:1px solid rgba(0,120,215,0.35);
                }
            """)
        else:
            self._player_cookies_edit.setStyleSheet("""
                QLineEdit {
                    background:transparent; color:#ffb347; border:none;
                    selection-background-color:#0078d7;
                }
            """)
            box.setStyleSheet("""
                QFrame#cookiesPath {
                    background:#141414; border-radius:8px;
                    border:1px solid rgba(255,179,71,0.45);
                }
            """)
            self._player_cookies_edit.setToolTip(f"Файл не найден:\n{path}")
