import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QApplication, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QRect, QTimer
from PySide6.QtGui import QFont, QIcon

from app.features.file_sorter.core.rules import RulesManager


class SorterView(QWidget):
    sort_files_requested  = Signal(list)
    sort_folder_requested = Signal(str)

    _DROP_STYLE_IDLE   = "QFrame{border:2px dashed rgba(0,120,215,120);border-radius:12px;background:rgba(0,120,215,8);}"
    _DROP_STYLE_ACTIVE = "QFrame{border:2px solid #00cc66;border-radius:12px;background:rgba(0,204,102,12);}"

    def __init__(self, settings: dict = None):
        super().__init__()
        self._settings  = settings or {}
        self._drag_pos  = None
        self._resizing  = None
        self._start_geo = None
        self._border    = 8
        self.rm         = RulesManager()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(420, 420)
        self.resize(480, 560)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setWindowOpacity(self._settings.get("sorter_opacity", 100) / 100)
        self._set_window_icon()
        self._build_ui()
        self._move_to_corner()

        # Плавающая кнопка настроек — снаружи окна
        from app.features.player.ui.player_view import SettingsToggle
        self._cfg_toggle = SettingsToggle(self, tab="sorter")

    # ── Инициализация ─────────────────────────────────────────────────────

    def _set_window_icon(self):
        assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets")
        self.setWindowIcon(QIcon(os.path.join(assets, "auto_sorter.jpeg")))

    # ── Построение UI ─────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self._card = self._make_card()
        root.addWidget(self._card)
        self._refresh_table()

    def _make_card(self) -> QFrame:
        card = QFrame(); card.setObjectName("sorterCard")
        card.setStyleSheet("""
            QFrame#sorterCard { background:#111; border-radius:14px;
                                border:1px solid rgba(255,255,255,12); }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 16); lay.setSpacing(10)
        lay.addLayout(self._make_header())
        lay.addWidget(self._make_source_bar())
        lay.addWidget(self._make_drop_zone())
        lay.addWidget(self._make_log_area())
        lay.addWidget(self._section("ПРАВИЛА"))
        lay.addWidget(self._make_table())
        lay.addLayout(self._make_rule_buttons())
        return card

    def _make_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()
        title = QLabel("FILE SORTER")
        title.setFont(QFont("Segoe UI Semibold", 13))
        title.setStyleSheet("color:#0078d7;")
        # ⚙ убрана — теперь плавающая кнопка снаружи
        btn_close = self._icon_btn("✕", 28)
        btn_close.setStyleSheet(
            btn_close.styleSheet() + "QPushButton:hover{background:rgba(192,57,43,150);}"
        )
        btn_close.clicked.connect(self.close)
        hdr.addWidget(title); hdr.addStretch()
        hdr.addWidget(btn_close)
        return hdr

    def _make_source_bar(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame{background:#1a1a1a;border-radius:10px;border:1px solid #2a2a2a;}")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)
        self._lbl_source = QLabel(self._source_display())
        self._lbl_source.setFont(QFont("Segoe UI", 10))
        self._lbl_source.setStyleSheet("color:#aaa; border:none; background:transparent;")
        btn = QPushButton("▶  Сортировать всё")
        btn.setCursor(Qt.PointingHandCursor); btn.setFixedHeight(30)
        btn.setStyleSheet("""
            QPushButton { background:#0078d7; color:white; border:none;
                          border-radius:8px; padding:0 12px; font-size:11px; }
            QPushButton:hover   { background:#1a8fe3; }
            QPushButton:pressed { background:#006cbf; }
        """)
        btn.clicked.connect(self._sort_all)
        lay.addWidget(QLabel("📁")); lay.addWidget(self._lbl_source, stretch=1)
        lay.addWidget(btn)
        return frame

    def _make_drop_zone(self) -> QFrame:
        self._drop_frame = QFrame()
        self._drop_frame.setFixedHeight(100)
        self._drop_frame.setStyleSheet(self._DROP_STYLE_IDLE)
        lay = QVBoxLayout(self._drop_frame)
        lbl = QLabel("Перетащи файлы сюда")
        lbl.setAlignment(Qt.AlignCenter); lbl.setFont(QFont("Segoe UI", 11))
        lbl.setStyleSheet("color:rgba(0,120,215,180); border:none; background:transparent;")
        lay.addWidget(lbl)
        return self._drop_frame

    def _make_log_area(self) -> QScrollArea:
        self._log_area = QScrollArea()
        self._log_area.setWidgetResizable(True)
        self._log_area.setFixedHeight(120)
        self._log_area.setStyleSheet("""
            QScrollArea { background:transparent; border:none; }
            QScrollBar:vertical { background:#1a1a1a; width:6px; border-radius:3px; }
            QScrollBar::handle:vertical { background:#333; border-radius:3px; }
        """)
        self._log_widget = QWidget()
        self._log_widget.setStyleSheet("background:transparent;")
        self._log_layout = QVBoxLayout(self._log_widget)
        self._log_layout.setContentsMargins(0, 0, 0, 0); self._log_layout.setSpacing(4)
        self._log_layout.addStretch()
        self._log_area.setWidget(self._log_widget)
        return self._log_area

    def _make_table(self) -> QTableWidget:
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Тип", "Паттерн", "Папка"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setStyleSheet("""
            QTableWidget { background:#1a1a1a; color:white; border:none;
                           border-radius:10px; gridline-color:#222; }
            QTableWidget::item { padding:6px; }
            QTableWidget::item:selected { background:rgba(0,120,215,60); }
            QHeaderView::section { background:#222; color:#666; border:none;
                                   padding:6px; font-size:10px; letter-spacing:1px; }
        """)
        return self._table

    def _make_rule_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(8)
        btn_add = QPushButton("+ Добавить правило")
        btn_add.setCursor(Qt.PointingHandCursor); btn_add.setFixedHeight(36)
        btn_add.setStyleSheet("""
            QPushButton { background:#1e1e1e; color:#ccc; border:1px solid #2a2a2a;
                          border-radius:8px; font-size:12px; }
            QPushButton:hover { background:#2a2a2a; color:white; border-color:#0078d7; }
        """)
        btn_add.clicked.connect(self._add_rule)
        btn_del = QPushButton("− Удалить")
        btn_del.setCursor(Qt.PointingHandCursor); btn_del.setFixedHeight(36)
        btn_del.setStyleSheet("""
            QPushButton { background:#1e1e1e; color:#888; border:1px solid #2a2a2a;
                          border-radius:8px; font-size:12px; padding:0 14px; }
            QPushButton:hover { background:rgba(192,57,43,40); color:#ff5555;
                                border-color:#c0392b; }
        """)
        btn_del.clicked.connect(self._del_rule)
        row.addWidget(btn_add, stretch=1); row.addWidget(btn_del)
        return row

    # ── Вспомогательные виджеты ───────────────────────────────────────────

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color:#555; letter-spacing:1.5px;")
        return lbl

    def _icon_btn(self, text: str, size: int = 28, tooltip: str = "") -> QPushButton:
        btn = QPushButton(text); btn.setFixedSize(size, size)
        btn.setCursor(Qt.PointingHandCursor)
        if tooltip: btn.setToolTip(tooltip)
        btn.setStyleSheet(f"""
            QPushButton {{ background:rgba(255,255,255,8); color:#aaa; border:none;
                           border-radius:{size//2}px; font-size:{size//2-2}px; }}
            QPushButton:hover {{ background:rgba(255,255,255,15); color:white; }}
        """)
        return btn

    def _source_display(self) -> str:
        src = self._settings.get("sorter_source", "")
        return os.path.basename(src) if src else "Папка не выбрана"

    # ── Таблица ───────────────────────────────────────────────────────────

    def _refresh_table(self):
        rules = self.rm.load()
        self._table.setRowCount(0)
        for r in rules:
            row = self._table.rowCount()
            self._table.insertRow(row)
            type_lbl = "🔤 по слову" if r["type"] == "keyword" else "📎 по расш."
            self._table.setItem(row, 0, QTableWidgetItem(type_lbl))
            self._table.setItem(row, 1, QTableWidgetItem(", ".join(r["patterns"])))
            self._table.setItem(row, 2, QTableWidgetItem(os.path.basename(r["folder"])))

    # ── Действия ─────────────────────────────────────────────────────────

    def _sort_all(self):
        src = self._settings.get("sorter_source", "")
        if not src:
            self._log("⚠ Папка-источник не задана — укажи в настройках", error=True)
            return
        self.sort_folder_requested.emit(src)

    def _add_rule(self):
        from app.features.file_sorter.ui.add_rule_dialog import AddRuleDialog
        d = AddRuleDialog(self)
        if d.exec():
            res = d.get_result()
            if res:
                self.rm.add(res["folder"], res["type"], res["patterns"])
                self._refresh_table()

    def _del_rule(self):
        row = self._table.currentRow()
        if row >= 0:
            self.rm.delete(row)
            self._refresh_table()

    def _apply_settings(self, cfg: dict):
        self._settings = cfg
        self.setWindowOpacity(cfg.get("sorter_opacity", 100) / 100)
        self._lbl_source.setText(self._source_display())

    # ── Лог ──────────────────────────────────────────────────────────────

    def show_results(self, results: list):
        for ok, msg in results:
            self._log(f"{'✓' if ok else '✗'}  {msg}", error=not ok)
        QTimer.singleShot(50, lambda: self._log_area.verticalScrollBar().setValue(
            self._log_area.verticalScrollBar().maximum()
        ))

    def _log(self, text: str, error: bool = False):
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(
            f"color:{'#ff5555' if error else '#55cc88'}; background:transparent; padding:1px 0;"
        )
        lbl.setWordWrap(True)
        self._log_layout.insertWidget(self._log_layout.count() - 1, lbl)

    # ── События окна ──────────────────────────────────────────────────────

    def showEvent(self, e):
        super().showEvent(e)
        if hasattr(self, "_cfg_toggle"):
            self._cfg_toggle.show()
            self._cfg_toggle.reposition(self.geometry())

    def moveEvent(self, e):
        super().moveEvent(e)
        if hasattr(self, "_cfg_toggle"):
            self._cfg_toggle.reposition(self.geometry())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_cfg_toggle"):
            self._cfg_toggle.reposition(self.geometry())

    def closeEvent(self, e):
        if hasattr(self, "_cfg_toggle"): self._cfg_toggle.hide()
        e.accept()

    # ── Drag & Drop ───────────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            self._drop_frame.setStyleSheet(self._DROP_STYLE_ACTIVE)
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self._drop_frame.setStyleSheet(self._DROP_STYLE_IDLE)

    def dropEvent(self, e):
        self.dragLeaveEvent(e)
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile()]
        if paths: self.sort_files_requested.emit(paths)
        e.acceptProposedAction()

    # ── Мышь: resize + drag ───────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._resizing  = self._check_edge(e.pos())
            self._drag_pos  = e.globalPosition().toPoint()
            self._start_geo = self.geometry()

    def mouseMoveEvent(self, e):
        if not e.buttons() & Qt.LeftButton:
            self._update_cursor(e.pos()); return
        if self._drag_pos is None: return
        self._apply_mouse_move(e)

    def mouseReleaseEvent(self, e):
        self._resizing = None; self._drag_pos = None
        self.setCursor(Qt.ArrowCursor)

    def _apply_mouse_move(self, e):
        diff = e.globalPosition().toPoint() - self._drag_pos
        geo  = QRect(self._start_geo)
        if self._resizing:
            if "right"  in self._resizing: geo.setRight(self._start_geo.right()   + diff.x())
            if "left"   in self._resizing: geo.setLeft(self._start_geo.left()     + diff.x())
            if "bottom" in self._resizing: geo.setBottom(self._start_geo.bottom() + diff.y())
            if "top"    in self._resizing: geo.setTop(self._start_geo.top()       + diff.y())
            if geo.width() >= 420 and geo.height() >= 420:
                self.setGeometry(geo)
        else:
            self.move(self._start_geo.topLeft() + diff)

    def _check_edge(self, pos):
        r = self.rect(); m = self._border
        l = pos.x() < m; rr = pos.x() > r.width()  - m
        t = pos.y() < m; b  = pos.y() > r.height() - m
        if t and l:  return "top_left"
        if t and rr: return "top_right"
        if b and l:  return "bottom_left"
        if b and rr: return "bottom_right"
        if l: return "left"
        if rr: return "right"
        if t: return "top"
        if b:  return "bottom"
        return None

    def _update_cursor(self, pos):
        cursors = {
            "top_left":    Qt.SizeFDiagCursor, "bottom_right": Qt.SizeFDiagCursor,
            "top_right":   Qt.SizeBDiagCursor, "bottom_left":  Qt.SizeBDiagCursor,
            "left":        Qt.SizeHorCursor,   "right":        Qt.SizeHorCursor,
            "top":         Qt.SizeVerCursor,   "bottom":       Qt.SizeVerCursor,
        }
        self.setCursor(cursors.get(self._check_edge(pos), Qt.ArrowCursor))

    def _move_to_corner(self):
        s = QApplication.primaryScreen().availableGeometry()
        self.move(s.width() - self.width() - 20, s.height() - self.height() - 20)