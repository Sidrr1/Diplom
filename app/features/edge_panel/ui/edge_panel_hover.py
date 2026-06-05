"""Глобальное отслеживание курсора для Edge Panel (развёрнутый режим)."""
from PySide6.QtCore import QObject, QEvent


class EdgePanelHoverFilter(QObject):
    """Следит за мышью по всему экрану, пока панель развёрнута."""

    def __init__(self, panel):
        super().__init__(panel)
        self._panel = panel

    def eventFilter(self, watched, event):
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
