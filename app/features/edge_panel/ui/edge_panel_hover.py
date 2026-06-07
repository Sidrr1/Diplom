"""
Глобальное отслеживание курсора для Edge Panel EdgeTools.

Event filter на QApplication: в развёрнутом режиме сворачивает панель,
если курсор покинул рабочую зону или клик вне карточки TOOLS.
"""
from PySide6.QtCore import QObject, QEvent


class EdgePanelHoverFilter(QObject):
    """Следит за мышью по всему экрану, пока панель развёрнута."""

    def __init__(self, panel):
        """
        Args:
            panel: EdgePanelView — вызывает _sync_hover_state / _force_collapse
        """
        super().__init__(panel)
        self._panel = panel

    def eventFilter(self, watched, event):
        """
        Обработка MouseMove / HoverMove / MouseButtonPress глобально.

        Returns:
            False — событие не перехватывается, только side-effect на panel.
        """
        panel = self._panel
        if not panel._expanded or not panel.isVisible():
            return False

        etype = event.type()
        if etype in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            panel._sync_hover_state()
        elif etype == QEvent.Type.MouseButtonPress:
            if not panel._pointer_in_work_zone():
                panel._force_collapse()
        return False
