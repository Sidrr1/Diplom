"""
Логгер с UI для показа ошибок пользователю.
"""
import sys
import traceback
from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import QObject, Signal


class ErrorLogger(QObject):
    """Логгер с системным окошком для ошибок."""

    error_occurred = Signal(str, str)  # (title, message)

    def __init__(self):
        super().__init__()
        self.error_occurred.connect(self._show_error_dialog)

    def log_error(self, title: str, user_message: str, exception: Exception = None):
        """
        Логировать ошибку и показать пользователю.

        Args:
            title: Заголовок ошибки (короткий)
            user_message: Понятное сообщение для пользователя
            exception: Исключение (опционально, для детального лога)
        """
        # Печатаем в консоль для разработчика
        print(f"\n[ERROR] {title}")
        print(f"[ERROR] {user_message}")
        if exception:
            print(f"[ERROR] Exception: {exception}")
            traceback.print_exc()

        # Показываем пользователю
        self.error_occurred.emit(title, user_message)

    def _show_error_dialog(self, title: str, message: str):
        """Показать диалог с ошибкой."""
        try:
            # Проверяем есть ли QApplication
            app = QApplication.instance()
            if app is None:
                print(f"[ERROR] Cannot show dialog (no QApplication): {title} - {message}")
                return

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle(f"Ошибка: {title}")
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.Ok)

            # Тёмная тема
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


# Глобальный экземпляр логгера
_logger = None


def get_logger() -> ErrorLogger:
    """Получить глобальный экземпляр логгера."""
    global _logger
    if _logger is None:
        _logger = ErrorLogger()
    return _logger


def log_error(title: str, user_message: str, exception: Exception = None):
    """
    Удобная функция для логирования ошибок.

    Args:
        title: Заголовок ошибки
        user_message: Понятное сообщение для пользователя
        exception: Исключение (опционально)
    """
    get_logger().log_error(title, user_message, exception)


# Примеры использования:
# from app.core.logger import log_error
#
# try:
#     # код
# except Exception as e:
#     log_error(
#         "Не удалось загрузить файл",
#         "Проверьте что файл существует и не повреждён",
#         e
#     )
