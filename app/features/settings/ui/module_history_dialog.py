"""Диалоги истории модулей (плеер / сортировщик) — стиль как у настроек."""
import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.database import db


def _fmt_dt(iso: str) -> str:
    """Форматировать ISO-дату для отображения в списке (ДД.ММ.ГГГГ ЧЧ:ММ)."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", ""))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso[:16] if iso else ""


class _BaseHistoryDialog(QDialog):
    """Базовая оболочка диалога истории в стиле настроек (карточка, перетаскивание)."""

    _STYLE_CARD = (
        "QFrame#card { background:#141414; border-radius:18px; border:1px solid #2a2a2a; }"
    )
    _STYLE_LIST = """
        QListWidget {
            background: rgba(255,255,255,6); color: #eee;
            border: 1px solid #2a2a2a; border-radius: 12px;
            padding: 4px; outline: none;
        }
        QListWidget::item { padding: 10px 12px; border-bottom: 1px solid #222; }
        QListWidget::item:selected { background: #0078d7; color: white; }
        QListWidget::item:hover:!selected { background: rgba(255,255,255,8); }
    """
    _STYLE_BTN = """
        QPushButton { background:#2a2a2a; color:#ccc; border:none;
                      border-radius:10px; padding:0 16px; font-size:12px; }
        QPushButton:hover { background:#333; color:white; }
    """
    _STYLE_BTN_DANGER = """
        QPushButton { background:rgba(192,57,43,0.25); color:#e88; border:none;
                      border-radius:10px; padding:0 16px; font-size:12px; }
        QPushButton:hover { background:#c0392b; color:white; }
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title_text = title
        self._drag_pos = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(440)
        self.setMinimumHeight(460)
        self._build_shell()
        self._apply_shadow()

    def _build_shell(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        self._card = QFrame()
        self._card.setObjectName("card")
        self._card.setStyleSheet(self._STYLE_CARD)
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(0, 0, 0, 20)
        card_lay.setSpacing(0)

        card_lay.addWidget(self._make_header())
        card_lay.addWidget(self._make_separator())

        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(20, 14, 20, 0)
        body_lay.setSpacing(12)
        self._build_body(body_lay)
        card_lay.addWidget(body)

        footer = QWidget()
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(20, 12, 20, 0)
        self._build_footer(foot_lay)
        card_lay.addWidget(footer)

        root.addWidget(self._card)

    def _make_header(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background:#0f0f0f; border-radius:18px 18px 0 0;")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(20, 16, 16, 12)
        title = QLabel(self._title_text)
        title.setFont(QFont("Segoe UI Semibold", 14))
        title.setStyleSheet("color:#f0f0f0; border:none; background:transparent;")
        lay.addWidget(title)
        lay.addStretch()
        btn = QPushButton("✕")
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#888; border:none;
                          border-radius:8px; font-size:13px; }
            QPushButton:hover { background:#c0392b; color:white; }
        """)
        btn.clicked.connect(self.reject)
        lay.addWidget(btn)
        return frame

    def _make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#222;")
        return sep

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color:#555; letter-spacing:1.5px; border:none; background:transparent;")
        return lbl

    def _subtitle(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setStyleSheet("color:#666; border:none; background:transparent;")
        return lbl

    def _make_list(self) -> QListWidget:
        w = QListWidget()
        w.setStyleSheet(self._STYLE_LIST)
        w.setFont(QFont("Segoe UI", 10))
        w.setSpacing(2)
        return w

    def _make_tab_btn(self, text: str, key: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 10))
        btn.setFixedHeight(32)
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:#666; border:none;
                          border-radius:8px; padding:0 14px; }
            QPushButton:hover { color:#aaa; background:rgba(255,255,255,5); }
            QPushButton:checked { background:#0078d7; color:white; }
        """)
        btn.clicked.connect(lambda: self._switch_tab(key))
        return btn

    def _apply_shadow(self):
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(40)
        sh.setOffset(0, 8)
        sh.setColor(QColor(0, 0, 0, 180))
        self._card.setGraphicsEffect(sh)

    def smart_position(self, parent_geo):
        """Разместить диалог рядом с родителем, не выходя за границы экрана."""
        from PySide6.QtWidgets import QApplication

        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        w, h = self.width(), self.height()
        cy = parent_geo.top() + (parent_geo.height() - h) // 2
        cx = parent_geo.left() + (parent_geo.width() - w) // 2
        candidates = [
            (parent_geo.left() - w - 12, cy),
            (parent_geo.right() + 12, cy),
            (cx, parent_geo.top() - h - 12),
            (cx, parent_geo.bottom() + 12),
        ]
        for x, y in candidates:
            if (
                x >= screen.left()
                and x + w <= screen.right()
                and y >= screen.top()
                and y + h <= screen.bottom()
            ):
                self.move(x, y)
                return
        self.move(screen.center().x() - w // 2, screen.center().y() - h // 2)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _build_body(self, lay: QVBoxLayout):
        raise NotImplementedError

    def _build_footer(self, lay: QHBoxLayout):
        raise NotImplementedError

    def _switch_tab(self, key: str):
        pass


class PlayerHistoryDialog(_BaseHistoryDialog):
    """История просмотров плеера: вкладки «Браузер» и «Плеер»."""

    def __init__(self, parent=None):
        super().__init__("История плеера", parent)
        self._list_web.itemDoubleClicked.connect(self._on_open)
        self._list_mpv.itemDoubleClicked.connect(self._on_open)
        self._switch_tab("web")
        self._reload()

    def _build_body(self, lay: QVBoxLayout):
        days = db.get_setting("player_history_days", "player", 7)
        lay.addWidget(self._section("ХРАНЕНИЕ"))
        lay.addWidget(self._subtitle(f"Записи старше {days} дн. удаляются автоматически"))

        tab_row = QHBoxLayout()
        tab_row.setSpacing(6)
        self._tab_btns = {
            "web": self._make_tab_btn("Браузер", "web"),
            "mpv": self._make_tab_btn("Плеер", "mpv"),
        }
        for btn in self._tab_btns.values():
            tab_row.addWidget(btn)
        tab_row.addStretch()
        lay.addLayout(tab_row)

        self._stack = QStackedWidget()
        self._list_web = self._make_list()
        self._list_mpv = self._make_list()
        self._stack.addWidget(self._list_web)
        self._stack.addWidget(self._list_mpv)
        self._stack.setMinimumHeight(280)
        lay.addWidget(self._stack)

    def _build_footer(self, lay: QHBoxLayout):
        btn_web = QPushButton("Очистить браузер")
        btn_mpv = QPushButton("Очистить плеер")
        for btn in (btn_web, btn_mpv):
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._STYLE_BTN_DANGER)
        btn_web.clicked.connect(lambda: self._clear("web"))
        btn_mpv.clicked.connect(lambda: self._clear("mpv"))
        lay.addWidget(btn_web)
        lay.addWidget(btn_mpv)
        lay.addStretch()

    def _switch_tab(self, key: str):
        keys = ("web", "mpv")
        if key not in keys:
            key = "web"
        self._stack.setCurrentIndex(keys.index(key))
        for k, btn in self._tab_btns.items():
            btn.setChecked(k == key)

    def _reload(self):
        self._fill(self._list_web, db.get_player_history("web"))
        self._fill(self._list_mpv, db.get_player_history("mpv"), show_thumb=True)

    def _fill(self, widget: QListWidget, rows: list, show_thumb: bool = False):
        widget.clear()
        for r in rows:
            title = (r.get("title") or r.get("url") or "")[:120]
            when = _fmt_dt(r.get("played_at", ""))
            text = f"{title}\n{when}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, r.get("url"))
            if show_thumb and r.get("thumbnail_url"):
                item.setToolTip(r["thumbnail_url"])
            widget.addItem(item)
        if widget.count() == 0:
            empty = QListWidgetItem("Пусто")
            empty.setFlags(Qt.NoItemFlags)
            widget.addItem(empty)

    def _on_open(self, item: QListWidgetItem):
        url = item.data(Qt.UserRole)
        if not url:
            return
        QApplication.clipboard().setText(url)
        QMessageBox.information(
            self, "Ссылка",
            "URL скопирован в буфер обмена.\nВставь в плеер или браузер.",
        )

    def _clear(self, source: str):
        db.clear_player_history(source)
        self._reload()


class SorterHistoryDialog(_BaseHistoryDialog):
    """История перемещений файлов сортировщиком с поиском по пути и правилу."""

    def __init__(self, parent=None):
        super().__init__("История сортировки", parent)
        self.setFixedWidth(480)
        self._list.itemDoubleClicked.connect(self._on_copy_path)
        self._reload()

    def _build_body(self, lay: QVBoxLayout):
        days = db.get_setting("sorter_history_days", "sorter", 7)
        lay.addWidget(self._section("ХРАНЕНИЕ"))
        lay.addWidget(self._subtitle(f"Записи старше {days} дн. удаляются автоматически"))

        lay.addWidget(self._section("ПОИСК"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Расширение, имя файла, папка или часть пути…")
        self._search.setClearButtonEnabled(True)
        self._search.setStyleSheet("""
            QLineEdit {
                background:#1a1a1a; color:#eee; border:1px solid #333;
                border-radius:10px; padding:10px 12px; font-size:12px;
            }
            QLineEdit:focus { border-color:#0078d7; }
        """)
        self._search.textChanged.connect(self._reload)
        lay.addWidget(self._search)

        self._search_hint = QLabel("")
        self._search_hint.setFont(QFont("Segoe UI", 9))
        self._search_hint.setStyleSheet("color:#555; border:none; background:transparent;")
        lay.addWidget(self._search_hint)

        self._list = self._make_list()
        self._list.setMinimumHeight(280)
        lay.addWidget(self._list)

    def _build_footer(self, lay: QHBoxLayout):
        btn_clear = QPushButton("Очистить")
        btn_clear.setFixedHeight(36)
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setStyleSheet(self._STYLE_BTN_DANGER)
        btn_clear.clicked.connect(self._clear)
        lay.addWidget(btn_clear)
        lay.addStretch()
        lay.addWidget(self._hint_label())

    def _hint_label(self) -> QLabel:
        lbl = QLabel("Двойной клик — копировать путь")
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color:#555; border:none; background:transparent;")
        return lbl

    def _reload(self):
        q = self._search.text().strip() if hasattr(self, "_search") else ""
        rows = db.get_sorter_history(search=q or None)
        self._list.clear()

        if q:
            self._search_hint.setText(
                f"Найдено: {len(rows)}" if rows else "Ничего не найдено"
            )
        else:
            self._search_hint.setText("")

        for r in rows:
            src = os.path.basename(r.get("source_path", ""))
            dst = r.get("destination_path", "")
            when = _fmt_dt(r.get("moved_at", ""))
            rule = r.get("rule_name") or ""
            mode = r.get("trigger") or "manual"
            mode_lbl = "авто" if mode == "auto" else "ручной"
            dest_dir = os.path.basename(os.path.dirname(dst)) or os.path.basename(dst)
            text = f"[{mode_lbl}] {src} → {dest_dir}\n{when}"
            if rule:
                text += f" · {rule}"
            text += f"\n{dst}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, r.get("destination_path"))
            item.setToolTip(r.get("source_path", ""))
            self._list.addItem(item)
        if self._list.count() == 0:
            empty = QListWidgetItem("Пусто" if not q else "Нет совпадений")
            empty.setFlags(Qt.NoItemFlags)
            self._list.addItem(empty)

    def _on_copy_path(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            QApplication.clipboard().setText(path)

    def _clear(self):
        db.clear_sorter_history()
        self._reload()
