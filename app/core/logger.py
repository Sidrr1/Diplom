"""
Централизованный логгер ошибок EdgeTools с UI-диалогом.

Печатает traceback в консоль и показывает понятное QMessageBox пользователю.
"""
import sys
import traceback
from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import QObject, Signal


class ErrorLogger(QObject):
    """Qt-логгер: сигнал error_occurred открывает диалог с тёмной темой."""

    error_occurred = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.error_occurred.connect(self._show_error_dialog)

    def log_error(self, title: str, user_message: str, exception: Exception = None):
        """
        Записать ошибку в консоль и уведомить пользователя.

        Args:
            title: короткий заголовок для диалога.
            user_message: текст без технических деталей.
            exception: исключение для traceback в консоли (опционально).
        """
        print(f"\n[ERROR] {title}")
        print(f"[ERROR] {user_message}")
        if exception:
            print(f"[ERROR] Exception: {exception}")
            traceback.print_exc()

        self.error_occurred.emit(title, user_message)

    def _show_error_dialog(self, title: str, message: str):
        """
        Показать модальный QMessageBox с ошибкой.

        Args:
            title: заголовок окна.
            message: основной текст для пользователя.
        """
        try:
            app = QApplication.instance()
            if app is None:
                print(f"[ERROR] Cannot show dialog (no QApplication): {title} - {message}")
                return

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle(f"Ошибка: {title}")
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.Ok)

            msg_box.setStyleSheet("""
                QMessageBox {
                    background: #1a1a1a;
                    color: white;
                }
                QLabel {
                    color: white;
                    font-size: 11px;
                }
                QPushButton {
                    background: #0078d7;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #1084e0;
                }
            """)

            msg_box.exec()
        except Exception as e:
            print(f"[ERROR] Failed to show error dialog: {e}")


_logger = None


def get_logger() -> ErrorLogger:
    """
    Получить глобальный экземпляр ErrorLogger (ленивая инициализация).

    Returns:
        Singleton ErrorLogger.
    """
    global _logger
    if _logger is None:
        _logger = ErrorLogger()
    return _logger


def log_error(title: str, user_message: str, exception: Exception = None):
    """
    Удобная обёртка для логирования ошибок из любого модуля EdgeTools.

    Args:
        title: заголовок ошибки.
        user_message: сообщение для пользователя.
        exception: исключение (опционально).
    """
    get_logger().log_error(title, user_message, exception)
