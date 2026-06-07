"""Миксины вкладок диалога настроек EdgeTools."""
from app.features.settings.ui.pages.widgets_mixin import WidgetsMixin
from app.features.settings.ui.pages.position_mixin import PositionMixin
from app.features.settings.ui.pages.sorter_logic_mixin import SorterLogicMixin
from app.features.settings.ui.pages.ocr_mixin import OcrMixin
from app.features.settings.ui.pages.notes_mixin import NotesMixin
from app.features.settings.ui.pages.player_logic_mixin import PlayerLogicMixin
from app.features.settings.ui.pages.enhancer_mixin import EnhancerMixin

__all__ = [
    "WidgetsMixin",
    "PositionMixin",
    "SorterLogicMixin",
    "PlayerLogicMixin",
    "OcrMixin",
    "NotesMixin",
    "EnhancerMixin",
]
