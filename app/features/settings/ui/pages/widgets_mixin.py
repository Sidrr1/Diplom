"""Страницы настроек и общие виджеты."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QSlider, QComboBox, QLineEdit, QSpinBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.core.autostart import is_enabled
from app.features.settings.ui import settings_styles as ss


class WidgetsMixin:
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
        lay.addWidget(self._section("YOUTUBE"))
        lay.addWidget(self._make_player_cookies_card())
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

    def _make_player_cookies_card(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(ss.STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.addWidget(self._row_title("Cookies YouTube"))
        hdr.addStretch()
        btn_help = QPushButton("Как получить?")
        btn_help.setCursor(Qt.PointingHandCursor)
        btn_help.setFlat(True)
        btn_help.setFont(QFont("Segoe UI", 9))
        btn_help.setStyleSheet("""
            QPushButton { color:#9ecbff; border:none; padding:0 4px; }
            QPushButton:hover { color:#0078d7; text-decoration:underline; }
        """)
        btn_help.clicked.connect(self._show_player_cookies_help)
        hdr.addWidget(btn_help)
        lay.addLayout(hdr)

        row = QHBoxLayout()
        row.setSpacing(8)

        self._player_cookies_box = QFrame()
        self._player_cookies_box.setObjectName("cookiesPath")
        self._player_cookies_box.setStyleSheet("""
            QFrame#cookiesPath {
                background:#141414; border-radius:8px;
                border:1px solid #2e2e2e;
            }
        """)
        path_lay = QHBoxLayout(self._player_cookies_box)
        path_lay.setContentsMargins(10, 8, 10, 8)
        self._player_cookies_stored = self.cfg.get("player_cookies_path", "")
        self._player_cookies_edit = QLineEdit()
        self._player_cookies_edit.setPlaceholderText("Не обязательно")
        self._player_cookies_edit.setReadOnly(True)
        self._player_cookies_edit.setFont(QFont("Segoe UI", 10))
        self._player_cookies_edit.setMinimumHeight(22)
        self._player_cookies_edit.setStyleSheet("""
            QLineEdit {
                background:transparent; color:#888; border:none;
                selection-background-color:#0078d7;
            }
        """)
        path_lay.addWidget(self._player_cookies_edit, 1)
        row.addWidget(self._player_cookies_box, 1)

        btn_pick = self._sorter_btn_secondary("Файл…")
        btn_pick.setFixedWidth(72)
        btn_pick.clicked.connect(self._choose_player_cookies)
        row.addWidget(btn_pick)

        self._btn_cookies_clear = self._sorter_btn_secondary("✕")
        self._btn_cookies_clear.setFixedSize(34, 34)
        self._btn_cookies_clear.setToolTip("Сбросить")
        self._btn_cookies_clear.clicked.connect(self._clear_player_cookies)
        row.addWidget(self._btn_cookies_clear)

        lay.addLayout(row)
        self._update_player_cookies_status()
        return frame

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
        frame.setStyleSheet(ss.STYLE_ROW_FRAME)
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
        frame = QFrame(); frame.setStyleSheet(ss.STYLE_ROW_FRAME)
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
        self._sorter_inbox_card.setStyleSheet(ss.STYLE_ROW_FRAME)
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
        self._sorter_auto_card.setStyleSheet(ss.STYLE_ROW_FRAME)
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
        frame = QFrame(); frame.setStyleSheet(ss.STYLE_ROW_FRAME)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(6)
        val = self.cfg.get(cfg_key, 100)
        hdr = QHBoxLayout()
        hdr.addWidget(self._row_title("Прозрачность окна"))
        hdr.addStretch()
        lbl = QLabel(f"{val}%"); lbl.setFont(QFont("Segoe UI", 11))
        lbl.setStyleSheet(ss.STYLE_LABEL_BLUE)
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
        lbl.setStyleSheet(ss.STYLE_LABEL_TITLE)
        return lbl

    def _row_subtitle(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(ss.STYLE_LABEL_SUB)
        return lbl

    def _toggle_row(self, title: str, subtitle: str, checked: bool):
        frame = QFrame(); frame.setStyleSheet(ss.STYLE_ROW_FRAME)
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

    