"""
Контекстное меню стикера (ПКМ): переключение режима и настройки.
"""
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction


class StickyNoteMenu(QMenu):
    """Контекстное меню для стикера."""

    def __init__(self, note, parent=None):
        """
        Args:
            note: словарь заметки (mode и прочие поля)
            parent: родительский виджет
        """
        super().__init__(parent)
        self.note = note

        self._build_menu()

    def _build_menu(self):
        """
        Собрать пункты меню.

        Returns:
            кортеж (mode_action, settings_action) для подключения сигналов снаружи
        """
        # Переключение режима
        mode_action = QAction("🔄 Переключить режим", self)
        current_mode = self.note.get('mode', 'normal')
        if current_mode == 'normal':
            mode_action.setText("🔄 Переключить в рабочий режим")
        else:
            mode_action.setText("🔄 Переключить в обычный режим")
        self.addAction(mode_action)

        self.addSeparator()

        # Настройки (глобальные)
        settings_action = QAction("⚙ Настройки", self)
        self.addAction(settings_action)

        return mode_action, settings_action
