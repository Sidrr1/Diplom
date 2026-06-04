import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QGraphicsDropShadowEffect, QSlider,
    QComboBox, QStackedWidget, QWidget, QLineEdit, QFileDialog, QGridLayout,
    QRadioButton, QScrollArea, QMessageBox, QProgressDialog,
)
from PySide6.QtCore import Qt, Signal, QTimer, QEventLoop
from PySide6.QtGui import QColor, QFont
from app.core import config
from app.core.autostart import set_autostart, is_enabled


class SettingsDialog(QDialog):
    settings_changed = Signal(dict)
    open_auth_browser = Signal(str)

    _player_view_ref = None
    _edge_panel_ref = None
    _visible_instances: list = []

    @classmethod
    def set_player_view(cls, view):
        cls._player_view_ref = view

    @classmethod
    def set_edge_panel(cls, panel):
        cls._edge_panel_ref = panel

    @classmethod
    def is_any_visible(cls) -> bool:
        return any(d.isVisible() for d in cls._visible_instances if d is not None)

    TABS = [
        ("⚙", "general"),
        ("▶", "player"),
        ("📁", "sorter"),
        ("🔍", "ocr"),
        ("📝", "notes"),
        ("🖼", "enhancer"),
    ]

    _STYLE_CARD        = "QFrame#card{background:#141414;border-radius:18px;border:1px solid #2a2a2a;}"
    _STYLE_ROW_FRAME   = "QFrame{background:#1e1e1e;border-radius:12px;border:1px solid #2a2a2a;}"
    _STYLE_LABEL_TITLE = "color:#e0e0e0; border:none; background:transparent;"
    _STYLE_LABEL_SUB   = "color:#555; border:none; background:transparent;"
    _STYLE_LABEL_BLUE  = "color:#0078d7; border:none; background:transparent;"

    def __init__(self, parent=None, initial_tab: str = "general"):
        super().__init__(parent)
        if initial_tab == "accounts":
            initial_tab = "general"
            self._open_accounts_on_show = True
        else:
            self._open_accounts_on_show = False
        self.cfg = config.load()
        # Без WindowStaysOnTopHint — не блокирует взаимодействие с другими окнами
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self._drag_pos = None
        self._build_ui(initial_tab)
        self._apply_shadow()
        SettingsDialog._visible_instances.append(self)

    def showEvent(self, event):
        super().showEvent(event)
        panel = SettingsDialog._edge_panel_ref
        if panel:
            panel.collapse_for_overlay()

    def closeEvent(self, event):
        try:
            SettingsDialog._visible_instances.remove(self)
        except ValueError:
            pass
        super().closeEvent(event)

    # ── Построение UI ─────────────────────────────────────────────────────

    def _build_ui(self, initial_tab: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        self._card = self._make_card(initial_tab)
        root.addWidget(self._card)

    def _make_card(self, initial_tab: str) -> QFrame:
        card = QFrame(); card.setObjectName("card")
        card.setStyleSheet(self._STYLE_CARD)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 20); lay.setSpacing(0)
        lay.addWidget(self._make_header())
        lay.addLayout(self._make_tabs_row())
        lay.addWidget(self._make_separator())
        lay.addLayout(self._make_stack_layout())
        lay.addSpacing(16)
        lay.addWidget(self._make_save_btn())
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
        lay.addWidget(title); lay.addStretch()
        lay.addWidget(self._make_close_btn())
        return frame

    def _make_close_btn(self) -> QPushButton:
        btn = QPushButton("✕"); btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#888; border:none;
                          border-radius:8px; font-size:13px; }
            QPushButton:hover { background:#c0392b; color:white; }
        """)
        btn.clicked.connect(self.reject)
        return btn

    def _make_tabs_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(16, 12, 16, 0); row.setSpacing(6)
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
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background:#222; margin:8px 0 0 0;")
        return sep

    def _make_stack_layout(self) -> QVBoxLayout:
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_general())
        self._stack.addWidget(self._page_player())
        self._stack.addWidget(self._page_sorter())
        self._stack.addWidget(self._page_ocr())
        self._stack.addWidget(self._page_notes())
        self._stack.addWidget(self._page_enhancer())
        lay = QVBoxLayout()
        lay.setContentsMargins(16, 12, 16, 0)
        lay.addWidget(self._stack)
        return lay

    def _make_save_btn(self) -> QPushButton:
        btn = QPushButton("Сохранить")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(42)
        btn.setStyleSheet("""
            QPushButton { background:#0078d7; color:white; border:none;
                          border-radius:10px; font-size:13px; font-weight:600;
                          margin:0 16px; }
            QPushButton:hover   { background:#1a8fe3; }
            QPushButton:pressed { background:#006cbf; }
        """)
        btn.clicked.connect(self._save)
        return btn

    def _apply_shadow(self):
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(40); sh.setOffset(0, 8)
        sh.setColor(QColor(0, 0, 0, 180))
        self._card.setGraphicsEffect(sh)

    # ── Страницы ──────────────────────────────────────────────────────────

    def _page_general(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)
        lay.addWidget(self._section("СИСТЕМА"))
        row, self._cb_autostart = self._toggle_row(
            "Запуск вместе с Windows",
            "Приложение стартует при входе в систему",
            is_enabled(),
        )
        lay.addWidget(row)
        lay.addStretch()
        return page

    def _accounts_open_btn(self) -> QPushButton:
        btn = QPushButton("Привязка аккаунтов")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(40)
        btn.setStyleSheet("""
            QPushButton { background:#1e3a5f; color:#9ecbff; border:1px solid #0078d7;
                          border-radius:10px; font-size:12px; font-weight:600; }
            QPushButton:hover { background:#0078d7; color:white; }
        """)
        btn.clicked.connect(self._open_accounts_binding)
        return btn

    def _open_accounts_binding(self):
        from app.features.settings.ui.accounts_binding_dialog import (
            AccountsBindingDialog,
        )

        dlg = AccountsBindingDialog(self, parent=self)
        dlg.smart_position(self.geometry())
        dlg.exec()

    def _page_player(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)
        lay.addWidget(self._section("ВОСПРОИЗВЕДЕНИЕ"))
        lay.addWidget(self._make_quality_row())
        lay.addWidget(self._section("ВНЕШНИЙ ВИД"))
        lay.addWidget(self._opacity_row("player_opacity", "_lbl_player_opacity", "_slider_player_opacity"))
        lay.addWidget(self._section("АККАУНТЫ"))
        lay.addWidget(self._accounts_open_btn())
        lay.addWidget(self._section("ИСТОРИЯ"))
        lay.addWidget(self._history_days_row("player_history_days", "_spin_player_hist_days"))
        lay.addWidget(self._history_open_btn("player"))
        lay.addStretch()
        return page

    def _resolve_player_view(self):
        if self._player_view_ref is not None:
            return self._player_view_ref
        p = self.parent()
        while p is not None:
            if hasattr(p, "pause_webview_for_auth"):
                return p
            p = p.parent() if hasattr(p, "parent") else None
        return None

    def _page_sorter(self) -> QWidget:
        from app.core.database import db
        from app.features.file_sorter.core.source_folder import is_source_valid

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        self._make_sorter_inbox_card()
        lay.addWidget(self._sorter_inbox_card)

        auto_on = str(db.get_setting("sorter_auto_enabled", "sorter", "0")).lower() in (
            "1", "true", "yes", "on"
        )
        if auto_on and not is_source_valid():
            auto_on = False
            db.set_setting("sorter_auto_enabled", False, "sorter")
        self._make_sorter_auto_card(auto_on)
        lay.addWidget(self._sorter_auto_card)

        self._sorter_src_edit.textChanged.connect(self._on_sorter_source_changed)
        self._update_sorter_watch_ui()

        lay.addWidget(self._section("ВНЕШНИЙ ВИД"))
        lay.addWidget(self._opacity_row("sorter_opacity", "_lbl_sorter_opacity", "_slider_sorter_opacity"))
        lay.addWidget(self._section("ИСТОРИЯ"))
        lay.addWidget(self._history_days_row("sorter_history_days", "_spin_sorter_hist_days"))
        lay.addWidget(self._history_open_btn("sorter"))
        lay.addStretch()
        return page

    @staticmethod
    def _days_label(n: int) -> str:
        n = int(n)
        if n % 10 == 1 and n % 100 != 11:
            word = "день"
        elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
            word = "дня"
        else:
            word = "дней"
        return f"{n} {word}"

    def _history_stepper_btn(self, text: str, handler) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(34, 34)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 14))
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:#888; border:none;
                          border-radius:8px; }
            QPushButton:hover { background:rgba(255,255,255,10); color:white; }
            QPushButton:pressed { background:#0078d7; color:white; }
        """)
        btn.clicked.connect(handler)
        return btn

    def _history_days_row(self, cfg_key: str, spin_attr: str) -> QFrame:
        from PySide6.QtWidgets import QSpinBox

        frame = QFrame()
        frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(self._row_title("Хранить историю"))
        sub = self._row_subtitle("Старые записи удаляются автоматически")
        sub.setWordWrap(True)
        col.addWidget(sub)
        lay.addLayout(col, stretch=1)

        val = int(self.cfg.get(cfg_key, 7))
        spin = QSpinBox()
        spin.setRange(1, 365)
        spin.setValue(val)
        spin.hide()
        setattr(self, spin_attr, spin)

        stepper = QFrame()
        stepper.setFixedHeight(42)
        stepper.setStyleSheet(
            "QFrame { background:#252525; border-radius:12px; border:1px solid #333; }"
        )
        s_lay = QHBoxLayout(stepper)
        s_lay.setContentsMargins(2, 2, 2, 2)
        s_lay.setSpacing(0)

        value_lbl = QLabel(self._days_label(val))
        value_lbl.setAlignment(Qt.AlignCenter)
        value_lbl.setMinimumWidth(72)
        value_lbl.setFont(QFont("Segoe UI Semibold", 11))
        value_lbl.setStyleSheet(
            "color:#0078d7; border:none; background:transparent; padding:0 6px;"
        )

        spin.valueChanged.connect(lambda v, lbl=value_lbl: lbl.setText(self._days_label(v)))

        btn_minus = self._history_stepper_btn(
            "−", lambda: spin.setValue(max(1, spin.value() - 1))
        )
        btn_plus = self._history_stepper_btn(
            "+", lambda: spin.setValue(min(365, spin.value() + 1))
        )
        s_lay.addWidget(btn_minus)
        s_lay.addWidget(value_lbl, stretch=1)
        s_lay.addWidget(btn_plus)
        lay.addWidget(stepper)
        return frame

    def _history_open_btn(self, module: str) -> QPushButton:
        btn = QPushButton("Открыть историю")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(40)
        btn.setStyleSheet("""
            QPushButton { background:#1e3a5f; color:#9ecbff; border:1px solid #0078d7;
                          border-radius:10px; font-size:12px; font-weight:600; margin:0 16px; }
            QPushButton:hover { background:#0078d7; color:white; }
        """)
        btn.clicked.connect(lambda: self._open_module_history(module))
        return btn

    def _open_module_history(self, module: str):
        from app.features.settings.ui.module_history_dialog import (
            PlayerHistoryDialog,
            SorterHistoryDialog,
        )
        if module == "player":
            dlg = PlayerHistoryDialog(self)
        elif module == "sorter":
            dlg = SorterHistoryDialog(self)
        else:
            return
        dlg.smart_position(self.geometry())
        dlg.exec()

    # ── Строки страниц ────────────────────────────────────────────────────

    def _make_quality_row(self) -> QFrame:
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QHBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 12)
        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(self._row_title("Качество по умолчанию"))
        col.addWidget(self._row_subtitle("Применяется при загрузке нового видео"))
        self._combo_quality = QComboBox()
        self._combo_quality.addItems(["Авто", "1080p", "720p", "480p", "360p"])
        idx = self._combo_quality.findText(self.cfg.get("player_quality", "Авто"))
        if idx >= 0: self._combo_quality.setCurrentIndex(idx)
        self._combo_quality.setFixedWidth(80)
        self._combo_quality.setStyleSheet("""
            QComboBox { background:#2a2a2a; color:white; border:none;
                        border-radius:8px; padding:4px 8px; font-size:11px; }
            QComboBox::drop-down { border:none; }
            QComboBox QAbstractItemView { background:#1a1a1a; color:white;
                selection-background-color:#0078d7; border:1px solid #333; }
        """)
        lay.addLayout(col, stretch=1); lay.addWidget(self._combo_quality)
        return frame

    def _sorter_btn_secondary(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(32)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background:#252525; color:#ccc; border:1px solid #333;
                border-radius:8px; font-size:11px; padding:0 14px;
            }
            QPushButton:hover { background:#333; color:white; border-color:#0078d7; }
        """)
        return btn

    def _make_sorter_inbox_card(self) -> None:
        from app.features.file_sorter.core.source_folder import get_source_folder

        self._sorter_inbox_card = QFrame()
        self._sorter_inbox_card.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QVBoxLayout(self._sorter_inbox_card)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        icon = QLabel("📥")
        icon.setFixedSize(32, 32)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            "background:rgba(0,120,215,0.12); border-radius:10px; font-size:16px;"
        )
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(self._row_title("Папка-входящие"))
        hint = self._row_subtitle(
            "Сюда попадают новые файлы (Загрузки и т.п.). Отсюда EdgeTools разносит их по правилам."
        )
        hint.setWordWrap(True)
        col.addWidget(hint)
        hdr.addWidget(icon)
        hdr.addLayout(col, 1)
        lay.addLayout(hdr)

        path_box = QFrame()
        path_box.setStyleSheet(
            "QFrame{background:#141414;border-radius:10px;border:1px solid #2e2e2e;}"
        )
        path_lay = QHBoxLayout(path_box)
        path_lay.setContentsMargins(12, 10, 12, 10)
        path_lay.setSpacing(8)

        self._sorter_src_edit = QLineEdit()
        src = get_source_folder() or self.cfg.get("sorter_source", "")
        self._sorter_src_edit.setText(src)
        self._sorter_src_edit.setPlaceholderText(r"C:\Users\…\Downloads")
        self._sorter_src_edit.setToolTip(src)
        self._sorter_src_edit.setFont(QFont("Segoe UI", 10))
        self._sorter_src_edit.setStyleSheet("""
            QLineEdit {
                background:transparent; color:#e8e8e8; border:none;
                font-size:11px; selection-background-color:#0078d7;
            }
        """)
        self._sorter_src_edit.textChanged.connect(
            lambda t: self._sorter_src_edit.setToolTip(t.strip())
        )
        path_lay.addWidget(self._sorter_src_edit, 1)
        lay.addWidget(path_box)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_browse = self._sorter_btn_secondary("Обзор…")
        btn_browse.clicked.connect(self._choose_sorter_src)
        btn_dl = self._sorter_btn_secondary("Загрузки")
        btn_dl.clicked.connect(self._set_sorter_downloads)
        btn_row.addWidget(btn_browse)
        btn_row.addWidget(btn_dl)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _make_sorter_auto_card(self, auto_on: bool) -> None:
        self._sorter_auto_card = QFrame()
        self._sorter_auto_card.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QVBoxLayout(self._sorter_auto_card)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(self._row_title("Автосортировка"))
        col.addWidget(self._row_subtitle("Пока запущен EdgeTools — без кнопки «Сортировать всё»"))
        row.addLayout(col, 1)

        self._cb_sorter_auto = QCheckBox()
        self._cb_sorter_auto.setChecked(auto_on)
        self._cb_sorter_auto.setCursor(Qt.PointingHandCursor)
        self._cb_sorter_auto.setStyleSheet("""
            QCheckBox::indicator { width:44px; height:24px; border-radius:12px;
                                   background:#333; border:none; }
            QCheckBox::indicator:checked { background:#0078d7; }
        """)
        self._cb_sorter_auto.toggled.connect(self._on_sorter_auto_toggled)
        row.addWidget(self._cb_sorter_auto, 0, Qt.AlignVCenter)
        lay.addLayout(row)

        self._lbl_sorter_watch = QLabel()
        self._lbl_sorter_watch.setWordWrap(True)
        self._lbl_sorter_watch.setFont(QFont("Segoe UI", 9))
        self._lbl_sorter_watch.setStyleSheet(
            "color:#666; background:rgba(255,255,255,4); border-radius:8px;"
            "padding:10px 12px; border-left:3px solid #333;"
        )
        lay.addWidget(self._lbl_sorter_watch)

    def _opacity_row(self, cfg_key: str, lbl_attr: str, slider_attr: str) -> QFrame:
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(6)
        val = self.cfg.get(cfg_key, 100)
        hdr = QHBoxLayout()
        hdr.addWidget(self._row_title("Прозрачность окна"))
        hdr.addStretch()
        lbl = QLabel(f"{val}%"); lbl.setFont(QFont("Segoe UI", 11))
        lbl.setStyleSheet(self._STYLE_LABEL_BLUE)
        setattr(self, lbl_attr, lbl)
        hdr.addWidget(lbl)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(20, 100); slider.setValue(val)
        slider.setStyleSheet("""
            QSlider::groove:horizontal { height:4px; background:rgba(255,255,255,20);
                                         border-radius:2px; }
            QSlider::sub-page:horizontal { background:#0078d7; border-radius:2px; }
            QSlider::handle:horizontal   { width:14px; height:14px; margin:-5px 0;
                                           background:#0078d7; border-radius:7px; }
        """)
        slider.valueChanged.connect(lambda v, l=lbl: l.setText(f"{v}%"))
        setattr(self, slider_attr, slider)
        lay.addLayout(hdr); lay.addWidget(slider)
        return frame

    # ── Вспомогательные виджеты ───────────────────────────────────────────

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color:#555; letter-spacing:1.5px;")
        return lbl

    def _row_title(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 11))
        lbl.setStyleSheet(self._STYLE_LABEL_TITLE)
        return lbl

    def _row_subtitle(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(self._STYLE_LABEL_SUB)
        return lbl

    def _toggle_row(self, title: str, subtitle: str, checked: bool):
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QHBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 12)
        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(self._row_title(title))
        col.addWidget(self._row_subtitle(subtitle))
        cb = QCheckBox(); cb.setChecked(checked)
        cb.setStyleSheet("""
            QCheckBox::indicator { width:44px; height:24px; border-radius:12px;
                                   background:#333; border:none; }
            QCheckBox::indicator:checked { background:#0078d7; }
        """)
        lay.addLayout(col, stretch=1); lay.addWidget(cb)
        return frame, cb

    # ── Позиционирование ──────────────────────────────────────────────────

    def smart_position(self, parent_geo):
        """Позиционирует диалог рядом с родительским окном в свободном месте."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        w, h = self.width(), self.height()
        cy = parent_geo.top() + (parent_geo.height() - h) // 2
        cx = parent_geo.left() + (parent_geo.width() - w) // 2

        candidates = [
            (parent_geo.left() - w - 12, cy),       # слева
            (parent_geo.right() + 12,    cy),        # справа
            (cx, parent_geo.top() - h - 12),         # сверху
            (cx, parent_geo.bottom() + 12),          # снизу
        ]
        for x, y in candidates:
            if (x >= screen.left() and x + w <= screen.right() and
                    y >= screen.top() and y + h <= screen.bottom()):
                self.move(x, y)
                return
        self.move(screen.center().x() - w // 2, screen.center().y() - h // 2)

    # ── Логика ────────────────────────────────────────────────────────────

    def _switch_tab(self, key: str):
        keys = [k for _, k in self.TABS]
        if key not in keys: key = keys[0]
        self._stack.setCurrentIndex(keys.index(key))
        for k, btn in self._tab_btns.items():
            btn.setChecked(k == key)

    def _choose_sorter_src(self):
        from app.core.paths import normalize_path

        folder = QFileDialog.getExistingDirectory(
            self, "Папка-входящие", self._sorter_src_edit.text().strip()
        )
        if folder:
            self._sorter_src_edit.setText(normalize_path(folder))

    def _set_sorter_downloads(self):
        import os
        from app.core.paths import normalize_path

        downloads = normalize_path(os.path.join(os.path.expanduser("~"), "Downloads"))
        if os.path.isdir(downloads):
            self._sorter_src_edit.setText(downloads)
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Загрузки",
                "Папка «Загрузки» не найдена. Укажите путь вручную через «Обзор…».",
            )

    def _persist_sorter_source(self):
        from app.features.file_sorter.core.source_folder import set_source_folder

        norm = set_source_folder(self._sorter_src_edit.text())
        self.cfg["sorter_source"] = norm
        if norm != self._sorter_src_edit.text().strip():
            self._sorter_src_edit.blockSignals(True)
            self._sorter_src_edit.setText(norm)
            self._sorter_src_edit.blockSignals(False)

    def _update_sorter_watch_ui(self):
        import os

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
        import os
        from app.core.database import db
        from app.features.file_sorter.core.auto_watcher import get_auto_watcher

        self._persist_sorter_source()
        src = self._sorter_src_edit.text().strip()
        if self._cb_sorter_auto.isChecked() and not (src and os.path.isdir(src)):
            self._cb_sorter_auto.blockSignals(True)
            self._cb_sorter_auto.setChecked(False)
            self._cb_sorter_auto.blockSignals(False)
            db.set_setting("sorter_auto_enabled", False, "sorter")
            self.cfg["sorter_auto_enabled"] = False

        self._update_sorter_watch_ui()
        get_auto_watcher().reload()
        self.settings_changed.emit({"sorter_source": src})

    def _on_sorter_auto_toggled(self, checked: bool):
        import os
        from PySide6.QtWidgets import QMessageBox
        from app.core.database import db
        from app.features.file_sorter.core.auto_watcher import get_auto_watcher

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

        self._persist_sorter_source()
        db.set_setting("sorter_auto_enabled", checked, "sorter")
        self.cfg["sorter_auto_enabled"] = checked
        get_auto_watcher().reload()
        self._update_sorter_watch_ui()
        self.settings_changed.emit({
            "sorter_auto_enabled": checked,
            "sorter_source": src,
        })
        print(f"[settings] Sorter auto: {checked}, folder={src or '(none)'}")

    def _save(self):
        self.cfg["autostart"]      = self._cb_autostart.isChecked()
        self.cfg["player_quality"] = self._combo_quality.currentText()
        self.cfg["player_opacity"] = self._slider_player_opacity.value()
        self.cfg["player_history_days"] = self._spin_player_hist_days.value()
        from app.features.file_sorter.core.auto_watcher import get_auto_watcher
        from app.features.file_sorter.core.source_folder import set_source_folder, is_source_valid

        self.cfg["sorter_source"] = set_source_folder(self._sorter_src_edit.text())
        auto = self._cb_sorter_auto.isChecked()
        if auto and not is_source_valid():
            auto = False
            self._cb_sorter_auto.setChecked(False)
        self.cfg["sorter_auto_enabled"] = auto
        from app.core.database import db
        db.set_setting("sorter_auto_enabled", self.cfg["sorter_auto_enabled"], "sorter")
        get_auto_watcher().reload()
        self.cfg["sorter_opacity"] = self._slider_sorter_opacity.value()
        self.cfg["sorter_history_days"] = self._spin_sorter_hist_days.value()

        from app.features.ocr.core.ocr_settings import (
            set_ocr_langs,
            set_postprocess_enabled,
            is_postprocess_enabled,
        )

        langs = self._collect_ocr_langs()
        if not langs:
            QMessageBox.warning(
                self,
                "OCR",
                "Выберите хотя бы один язык Tesseract.",
            )
            langs = ["rus", "eng"]
        from app.features.ocr.core.tesseract_env import missing_lang_packs

        to_fetch = missing_lang_packs(langs)
        if to_fetch and not self._run_ocr_lang_download(to_fetch):
            return
        set_ocr_langs(langs)
        if hasattr(self, "_cb_ocr_postprocess"):
            set_postprocess_enabled(self._cb_ocr_postprocess.isChecked())
        else:
            set_postprocess_enabled(is_postprocess_enabled())
        self.cfg["ocr_langs"] = langs

        # Enhancer settings
        self.cfg["enhancer_autosave"] = self._cb_enhancer_autosave.isChecked()
        self.cfg["enhancer_format"] = self._combo_enhancer_format.currentText()
        self.cfg["enhancer_jpeg_quality"] = self._slider_enhancer_quality.value()

        # Notes settings
        from app.core.database import db
        selected_position = None
        for pos, btn in self._notes_position_btns.items():
            if btn.isChecked():
                selected_position = pos
                break
        if selected_position:
            db.set_setting('edge_position', selected_position, 'notes')
            self.cfg['notes_edge_position'] = selected_position  # Добавляем в cfg для emit

        note_width = self._notes_width_slider.value()
        note_height = self._notes_height_slider.value()
        notes_opacity = self._slider_notes_opacity.value()

        db.set_setting('note_width', str(note_width), 'notes')
        db.set_setting('note_height', str(note_height), 'notes')
        db.set_setting('notes_opacity', str(notes_opacity), 'notes')

        notes_mode = 'work' if getattr(self, '_mode_work_radio', None) and self._mode_work_radio.isChecked() else 'normal'
        db.set_setting('notes_mode', notes_mode, 'notes')

        # Добавляем в cfg для emit
        self.cfg['notes_width'] = note_width
        self.cfg['notes_height'] = note_height
        self.cfg['notes_opacity'] = notes_opacity
        self.cfg['notes_mode'] = notes_mode

        config.save(self.cfg)
        from app.core.database import db
        db.purge_expired_histories()
        set_autostart(self.cfg["autostart"])
        self.settings_changed.emit(self.cfg)
        self.accept()

    # ── Перетаскивание ────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # ── Страница OCR ──────────────────────────────────────────────────────

    _OCR_ARROW = """
        QPushButton {
            background:transparent; color:#555; border:none;
            font-size:20px; font-weight:bold; padding:0;
        }
        QPushButton:hover { color:#0078d7; }
        QPushButton:disabled { color:#2a2a2a; }
    """
    _OCR_CARD_BASE = """
        QPushButton#ocrCarousel {
            background:#141414; border-radius:14px; border:2px solid #2a2a2a;
        }
        QPushButton#ocrCarousel:hover { border-color:#444; }
    """
    _OCR_CARD_ON = """
        QPushButton#ocrCarousel {
            background:rgba(0,120,215,0.12); border-radius:14px;
            border:2px solid #0078d7;
        }
        QPushButton#ocrCarousel:hover { border-color:#0094ff; }
    """
    _OCR_CARD_INSTALLED = """
        QPushButton#ocrCarousel {
            background:rgba(0,120,215,0.08); border-radius:14px;
            border:2px solid rgba(0,120,215,0.45);
        }
        QPushButton#ocrCarousel:hover { border-color:#0078d7; }
    """
    _OCR_TAG = """
        QPushButton {
            background:rgba(0,120,215,0.2); color:#9ecbff;
            border:1px solid #0078d7; border-radius:6px;
            font-size:10px; font-weight:600; padding:2px 8px; min-height:0;
        }
        QPushButton:hover { background:#0078d7; color:white; }
    """

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
        card_pp.setStyleSheet(self._STYLE_ROW_FRAME)
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
        card_lang.setStyleSheet(self._STYLE_ROW_FRAME)
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
        self._btn_ocr_prev.setStyleSheet(self._OCR_ARROW)
        self._btn_ocr_prev.clicked.connect(self._ocr_carousel_prev)
        carousel.addWidget(self._btn_ocr_prev)

        self._ocr_card = QPushButton()
        self._ocr_card.setObjectName("ocrCarousel")
        self._ocr_card.setMinimumHeight(80)
        self._ocr_card.setCursor(Qt.PointingHandCursor)
        self._ocr_card.setStyleSheet(self._OCR_CARD_BASE)
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
        self._btn_ocr_next.setStyleSheet(self._OCR_ARROW)
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
            self._ocr_card.setStyleSheet(self._OCR_CARD_ON)
        elif installed:
            self._ocr_card.setStyleSheet(self._OCR_CARD_INSTALLED)
        else:
            self._ocr_card.setStyleSheet(self._OCR_CARD_BASE)

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
                pill.setStyleSheet(self._OCR_TAG)
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

    def _ocr_pick_all(self):
        self._ocr_selected = set(self._ocr_catalog)
        self._ocr_update_lang_count_label()
        self._ocr_refresh_carousel()
        self._ocr_rebuild_selected_strip()

    def _ocr_pick_none(self):
        self._ocr_selected.clear()
        self._ocr_update_lang_count_label()
        self._ocr_refresh_carousel()
        self._ocr_rebuild_selected_strip()

    def _reload_ocr_lang_list(self):
        """Обновить список без пересоздания вкладки (фикс сдвига QStackedWidget)."""
        self._fill_ocr_lang_list(set(self._ocr_selected))

    def _collect_ocr_langs(self) -> list[str]:
        selected = getattr(self, "_ocr_selected", None)
        if isinstance(selected, set):
            return sorted(selected)
        from app.features.ocr.core.ocr_settings import get_ocr_langs
        return get_ocr_langs()

    # ── Страница Notes ────────────────────────────────────────────────────

    def _page_notes(self) -> QWidget:
        """Настройки Smart Notes."""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(self._section("РЕЖИМ РАБОТЫ"))
        lay.addWidget(self._make_notes_mode_row())

        lay.addWidget(self._section("ПОЛОЖЕНИЕ"))
        lay.addWidget(self._make_notes_position_row())

        lay.addWidget(self._section("РАЗМЕР СТИКЕРОВ"))
        lay.addWidget(self._make_notes_size_row())

        lay.addWidget(self._section("ВНЕШНИЙ ВИД"))
        lay.addWidget(self._opacity_row("notes_opacity", "_lbl_notes_opacity", "_slider_notes_opacity"))

        lay.addStretch()
        return page

    def _make_notes_mode_row(self) -> QFrame:
        """Переключение режима работы заметок."""
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(8)

        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(self._row_title("Режим работы"))
        col.addWidget(self._row_subtitle("Обычные заметки или список задач"))
        lay.addLayout(col)

        # Читаем текущий режим из БД (пока заглушка — будет per-sticker)
        from app.core.database import db
        current_mode = db.get_setting('notes_mode', 'notes', 'normal')

        # Два радио-баттона
        radio_layout = QHBoxLayout()
        radio_layout.setSpacing(12)

        self._mode_normal_radio = QRadioButton("📝 Обычный режим (заметки)")
        self._mode_normal_radio.setCursor(Qt.PointingHandCursor)
        self._mode_normal_radio.toggled.connect(lambda checked: self._on_mode_changed('normal') if checked else None)
        radio_layout.addWidget(self._mode_normal_radio)

        self._mode_work_radio = QRadioButton("✅ Рабочий режим (задачи)")
        self._mode_work_radio.setCursor(Qt.PointingHandCursor)
        self._mode_work_radio.toggled.connect(lambda checked: self._on_mode_changed('work') if checked else None)
        radio_layout.addWidget(self._mode_work_radio)

        self._mode_normal_radio.blockSignals(True)
        self._mode_work_radio.blockSignals(True)
        self._mode_normal_radio.setChecked(current_mode == 'normal')
        self._mode_work_radio.setChecked(current_mode == 'work')
        self._mode_normal_radio.blockSignals(False)
        self._mode_work_radio.blockSignals(False)

        radio_layout.addStretch()
        lay.addLayout(radio_layout)

        return frame

    def _make_notes_position_row(self) -> QFrame:
        """Выбор положения Edge-панели для заметок."""
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(8)

        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(self._row_title("Положение Edge-панели"))
        col.addWidget(self._row_subtitle("Где показывать кнопку заметок"))
        lay.addLayout(col)

        # Визуальный экранчик с 4 квадратиками
        from app.core.database import db
        current_pos = db.get_setting('edge_position', 'notes', 'right')

        screen_widget = QWidget()
        screen_widget.setFixedSize(120, 90)
        screen_layout = QGridLayout(screen_widget)
        screen_layout.setContentsMargins(0, 0, 0, 0)
        screen_layout.setSpacing(0)

        # Центральный экран (серый прямоугольник)
        center = QLabel()
        center.setFixedSize(60, 50)
        center.setStyleSheet("background:#2a2a2a; border-radius:4px;")
        screen_layout.addWidget(center, 1, 1, Qt.AlignCenter)

        # 4 кнопки по углам (соответствие UI ↔ позиция стикеров)
        self._notes_position_btns = {}
        positions = [
            ('left', 0, 0),    # левый верхний угол UI → стикеры СЛЕВА
            ('right', 0, 2),   # правый верхний угол UI → стикеры СПРАВА
            ('bottom', 2, 0),  # левый нижний угол UI → стикеры СНИЗУ
            ('top', 2, 2)      # правый нижний угол UI → стикеры СВЕРХУ
        ]

        for pos, row, col in positions:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setChecked(pos == current_pos)
            btn.setFixedSize(20, 20)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, p=pos: self._select_notes_position(p))
            btn.setStyleSheet("""
                QPushButton {
                    background:#444;
                    border:2px solid #555;
                    border-radius:4px;
                }
                QPushButton:hover {
                    background:#555;
                    border:2px solid #0078d7;
                }
                QPushButton:checked {
                    background:#0078d7;
                    border:2px solid #1a8fe3;
                }
            """)
            self._notes_position_btns[pos] = btn
            screen_layout.addWidget(btn, row, col, Qt.AlignCenter)

        lay.addWidget(screen_widget, 0, Qt.AlignCenter)

        return frame

    def _make_notes_size_row(self) -> QFrame:
        """Размер стикеров."""
        frame = QFrame(); frame.setStyleSheet(self._STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(8)

        from app.core.database import db
        width = int(db.get_setting('note_width', 'notes', '250'))
        height = int(db.get_setting('note_height', 'notes', '200'))

        # Ширина
        width_row = QHBoxLayout()
        width_row.addWidget(self._row_subtitle("Ширина:"))
        self._notes_width_slider = QSlider(Qt.Horizontal)
        self._notes_width_slider.setRange(200, 400)
        self._notes_width_slider.setValue(width)
        self._notes_width_lbl = QLabel(f"{width}px")
        self._notes_width_lbl.setStyleSheet(self._STYLE_LABEL_BLUE)
        self._notes_width_slider.valueChanged.connect(lambda v: self._notes_width_lbl.setText(f"{v}px"))
        width_row.addWidget(self._notes_width_slider, 1)
        width_row.addWidget(self._notes_width_lbl)
        lay.addLayout(width_row)

        # Высота
        height_row = QHBoxLayout()
        height_row.addWidget(self._row_subtitle("Высота:"))
        self._notes_height_slider = QSlider(Qt.Horizontal)
        self._notes_height_slider.setRange(150, 400)
        self._notes_height_slider.setValue(height)
        self._notes_height_lbl = QLabel(f"{height}px")
        self._notes_height_lbl.setStyleSheet(self._STYLE_LABEL_BLUE)
        self._notes_height_slider.valueChanged.connect(lambda v: self._notes_height_lbl.setText(f"{v}px"))
        height_row.addWidget(self._notes_height_slider, 1)
        height_row.addWidget(self._notes_height_lbl)
        lay.addLayout(height_row)

        return frame

    def _on_mode_changed(self, mode: str):
        """Обработчик смены режима работы заметок."""
        from app.core.database import db
        db.set_setting('notes_mode', mode, 'notes')
        self.settings_changed.emit({'notes_mode': mode})
        print(f"[settings] Notes mode changed to: {mode}")

    def _select_notes_position(self, position: str):
        """Выбрать положение Edge-панели."""
        for pos, btn in self._notes_position_btns.items():
            btn.setChecked(pos == position)

    # ── Страница Enhancer ─────────────────────────────────────────────────

    def _page_enhancer(self) -> QWidget:
        """Настройки Image Enhancer."""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(self._section("IMAGE ENHANCER"))

        # Автосохранение
        row, self._cb_enhancer_autosave = self._toggle_row(
            "Автосохранение результата",
            "Сохранять улучшенное изображение автоматически",
            self.cfg.get("enhancer_autosave", True),
        )
        lay.addWidget(row)

        # Формат сохранения
        format_frame = QFrame()
        format_frame.setStyleSheet(self._STYLE_ROW_FRAME)
        format_lay = QHBoxLayout(format_frame)
        format_lay.setContentsMargins(14, 12, 14, 12)

        format_col = QVBoxLayout()
        format_col.setSpacing(2)
        format_col.addWidget(self._row_title("Формат сохранения"))
        format_col.addWidget(self._row_subtitle("Формат выходного файла"))

        self._combo_enhancer_format = QComboBox()
        self._combo_enhancer_format.addItems(["PNG", "JPEG", "WEBP"])
        self._combo_enhancer_format.setCurrentText(self.cfg.get("enhancer_format", "PNG"))
        self._combo_enhancer_format.setFixedWidth(100)
        self._combo_enhancer_format.setStyleSheet("""
            QComboBox {
                background:#2a2a2a; color:white; border:none;
                border-radius:6px; padding:6px 10px; font-size:11px;
            }
            QComboBox::drop-down { border:none; }
            QComboBox QAbstractItemView {
                background:#1e1e1e; color:white;
                selection-background-color:#0078d7; border:1px solid #333;
            }
        """)

        format_lay.addLayout(format_col, stretch=1)
        format_lay.addWidget(self._combo_enhancer_format)
        lay.addWidget(format_frame)

        # Качество JPEG
        quality_frame = QFrame()
        quality_frame.setStyleSheet(self._STYLE_ROW_FRAME)
        quality_lay = QVBoxLayout(quality_frame)
        quality_lay.setContentsMargins(14, 12, 14, 12)
        quality_lay.setSpacing(6)

        quality_val = self.cfg.get("enhancer_jpeg_quality", 95)
        quality_hdr = QHBoxLayout()
        quality_hdr.addWidget(self._row_title("Качество JPEG"))
        quality_hdr.addStretch()

        self._lbl_enhancer_quality = QLabel(f"{quality_val}%")
        self._lbl_enhancer_quality.setFont(QFont("Segoe UI", 11))
        self._lbl_enhancer_quality.setStyleSheet(self._STYLE_LABEL_BLUE)
        quality_hdr.addWidget(self._lbl_enhancer_quality)

        self._slider_enhancer_quality = QSlider(Qt.Horizontal)
        self._slider_enhancer_quality.setRange(70, 100)
        self._slider_enhancer_quality.setValue(quality_val)
        self._slider_enhancer_quality.setStyleSheet("""
            QSlider::groove:horizontal { height:4px; background:rgba(255,255,255,20);
                                         border-radius:2px; }
            QSlider::sub-page:horizontal { background:#0078d7; border-radius:2px; }
            QSlider::handle:horizontal   { width:14px; height:14px; margin:-5px 0;
                                           background:#0078d7; border-radius:7px; }
        """)
        self._slider_enhancer_quality.valueChanged.connect(
            lambda v: self._lbl_enhancer_quality.setText(f"{v}%")
        )

        quality_lay.addLayout(quality_hdr)
        quality_lay.addWidget(self._slider_enhancer_quality)
        lay.addWidget(quality_frame)

        lay.addStretch()
        return page