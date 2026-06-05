"""Диалог настроек EdgeTools — оболочка и вкладки."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QStackedWidget, QWidget,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont

from app.core import config
from app.features.settings.ui import settings_styles as ss
from app.features.settings.ui.settings_persistence import SettingsPersistenceMixin
from app.features.settings.ui.pages import (
    WidgetsMixin,
    PositionMixin,
    SorterLogicMixin,
    PlayerLogicMixin,
    OcrMixin,
    NotesMixin,
    EnhancerMixin,
)


class SettingsDialog(
    QDialog,
    SettingsPersistenceMixin,
    WidgetsMixin,
    SorterLogicMixin,
    PlayerLogicMixin,
    OcrMixin,
    NotesMixin,
    EnhancerMixin,
    PositionMixin,
):
    settings_changed = Signal(dict)
    open_auth_browser = Signal(str)

    _player_view_ref = None
    _edge_panel_ref = None
    _visible_instances: list = []

    TABS = [
        ("⚙", "general"),
        ("▶", "player"),
        ("📁", "sorter"),
        ("🔍", "ocr"),
        ("📝", "notes"),
        ("🖼", "enhancer"),
    ]

    _STYLE_CARD = ss.STYLE_CARD
    _STYLE_ROW_FRAME = ss.STYLE_ROW_FRAME
    _STYLE_LABEL_TITLE = ss.STYLE_LABEL_TITLE
    _STYLE_LABEL_SUB = ss.STYLE_LABEL_SUB
    _STYLE_LABEL_BLUE = ss.STYLE_LABEL_BLUE
    _STYLE_SAVE_ACTIVE = ss.SAVE_BTN_ACTIVE
    _STYLE_SAVE_IDLE = ss.SAVE_BTN_IDLE

    @classmethod
    def set_player_view(cls, view):
        cls._player_view_ref = view

    @classmethod
    def set_edge_panel(cls, panel):
        cls._edge_panel_ref = panel

    @classmethod
    def is_any_visible(cls) -> bool:
        return any(d.isVisible() for d in cls._visible_instances if d is not None)

    def __init__(self, parent=None, initial_tab: str = "general"):
        if parent is None:
            parent = SettingsDialog._edge_panel_ref
        super().__init__(parent)
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        if initial_tab == "accounts":
            initial_tab = "general"
            self._open_accounts_on_show = True
        else:
            self._open_accounts_on_show = False
        self.cfg = config.load()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self._drag_pos = None
        self._pages_loaded: set[str] = set()
        self._pages_loading: set[str] = set()
        self._current_tab: str | None = None
        self._tabs_preloaded = False
        self._init_persistence()
        self._build_ui(initial_tab)
        self._apply_shadow()
        self.adjustSize()
        SettingsDialog._visible_instances.append(self)
        self.finished.connect(self._unregister_visible)

    def _unregister_visible(self):
        try:
            SettingsDialog._visible_instances.remove(self)
        except ValueError:
            pass

    def _present(self) -> None:
        self.adjustSize()
        self.setAttribute(Qt.WA_DontShowOnScreen, False)
        self.show()
        self.raise_()
        self.activateWindow()
        if not self._tabs_preloaded:
            QTimer.singleShot(300, self._preload_all_tabs)

    def show_near(self, anchor_geo) -> None:
        self.smart_position(anchor_geo)
        self._present()

    def show_centered(self) -> None:
        from PySide6.QtWidgets import QApplication

        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        x = screen.center().x() - self.width() // 2
        y = screen.center().y() - self.height() // 2
        self.move(x, y)
        self._present()

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        panel = SettingsDialog._edge_panel_ref
        if panel:
            panel.collapse_for_overlay()
        self._update_save_button_state()

    def closeEvent(self, event):
        self._unregister_visible()
        super().closeEvent(event)

    def _build_ui(self, initial_tab: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        self._card = self._make_card(initial_tab)
        root.addWidget(self._card)

    def _make_card(self, initial_tab: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(self._STYLE_CARD)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 20)
        lay.setSpacing(0)
        lay.addWidget(self._make_header())
        lay.addLayout(self._make_tabs_row())
        lay.addWidget(self._make_separator())
        lay.addLayout(self._make_stack_layout())
        lay.addSpacing(16)
        self._save_btn = self._make_save_btn()
        lay.addWidget(self._save_btn)
        self._switch_tab(initial_tab)
        if self._open_accounts_on_show:
            QTimer.singleShot(0, self._open_accounts_binding)
        return card

    def _make_header(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background:#0f0f0f; border-radius:18px 18px 0 0;")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(20, 16, 16, 12)
        title = QLabel("Настройки")
        title.setFont(QFont("Segoe UI Semibold", 14))
        title.setStyleSheet("color:#f0f0f0;")
        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(self._make_close_btn())
        return frame

    def _make_close_btn(self) -> QPushButton:
        btn = QPushButton("✕")
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#888; border:none;
                          border-radius:8px; font-size:13px; }
            QPushButton:hover { background:#c0392b; color:white; }
        """)
        btn.clicked.connect(self.hide)
        return btn

    def _make_tabs_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(16, 12, 16, 0)
        row.setSpacing(6)
        self._tab_btns = {}
        for label, key in self.TABS:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setFixedHeight(32)
            btn.setStyleSheet("""
                QPushButton { background:transparent; color:#666; border:none;
                              border-radius:8px; padding:0 12px; }
                QPushButton:hover   { color:#aaa; background:rgba(255,255,255,5); }
                QPushButton:checked { background:#0078d7; color:white; }
            """)
            btn.clicked.connect(lambda checked, k=key: self._switch_tab(k))
            row.addWidget(btn)
            self._tab_btns[key] = btn
        row.addStretch()
        return row

    def _make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#222; margin:8px 0 0 0;")
        return sep

    def _make_stack_layout(self) -> QVBoxLayout:
        self._stack = QStackedWidget()
        for _, key in self.TABS:
            ph = QWidget()
            ph.setObjectName(f"ph_{key}")
            self._stack.addWidget(ph)
        lay = QVBoxLayout()
        lay.setContentsMargins(16, 12, 16, 0)
        lay.addWidget(self._stack)
        return lay

    def _preload_all_tabs(self) -> None:
        if self._tabs_preloaded:
            return
        for _, key in self.TABS:
            self._ensure_page(key)
        self._tabs_preloaded = True
        self.adjustSize()

    def _ensure_page(self, key: str) -> None:
        if key in self._pages_loaded or key in self._pages_loading:
            return
        builders = {
            "general": self._page_general,
            "player": self._page_player,
            "sorter": self._page_sorter,
            "ocr": self._page_ocr,
            "notes": self._page_notes,
            "enhancer": self._page_enhancer,
        }
        builder = builders.get(key)
        if not builder:
            return
        self._pages_loading.add(key)
        keys = [k for _, k in self.TABS]
        idx = keys.index(key)
        old = self._stack.widget(idx)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(idx, builder())
        self._pages_loaded.add(key)
        self._pages_loading.discard(key)
        self._wire_page_dirty(key)
        QTimer.singleShot(0, lambda k=key: self._set_tab_baseline(k))
        self.adjustSize()

    def _make_save_btn(self) -> QPushButton:
        btn = QPushButton("Сохранить")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(42)
        btn.setEnabled(False)
        btn.setStyleSheet(self._STYLE_SAVE_IDLE)
        btn.clicked.connect(self._save)
        return btn

    def _apply_shadow(self):
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(40)
        sh.setOffset(0, 8)
        sh.setColor(QColor(0, 0, 0, 180))
        self._card.setGraphicsEffect(sh)

    def _switch_tab(self, key: str):
        keys = [k for _, k in self.TABS]
        if key not in keys:
            key = keys[0]
        if self._current_tab == key and key in self._pages_loaded:
            return
        self._current_tab = key
        self._ensure_page(key)
        self._stack.setCurrentIndex(keys.index(key))
        for k, btn in self._tab_btns.items():
            btn.setChecked(k == key)
        self._refresh_tab_dirty(key)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
