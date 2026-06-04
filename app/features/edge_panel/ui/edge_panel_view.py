import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
    QLabel, QFrame, QApplication)
from PySide6.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve, Signal, QSize, QTimer
from PySide6.QtGui import QColor, QPainter, QIcon, QFont, QPainterPath


class ToolButton(QWidget):
    clicked = Signal()

    def __init__(self, icon_path: str, label: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(62, 70)
        self.setCursor(Qt.PointingHandCursor)
        self._build_ui(icon_path, label)

    def _build_ui(self, icon_path: str, label: str):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 4); lay.setSpacing(3)
        lay.setAlignment(Qt.AlignHCenter)
        lay.addWidget(self._make_icon_btn(icon_path), 0, Qt.AlignHCenter)
        lay.addWidget(self._make_label(label),        0, Qt.AlignHCenter)

    def _make_icon_btn(self, icon_path: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(44, 44); btn.setIconSize(QSize(26, 26))
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.clicked)
        btn.setStyleSheet("""
            QPushButton { background:rgba(255,255,255,8); border-radius:13px;
                          border:1px solid rgba(255,255,255,12); }
            QPushButton:hover { background:rgba(0,120,215,60); border:1px solid #0078d7; }
            QPushButton:pressed { background:rgba(0,120,215,90); }
        """)
        return btn

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet("color:rgba(200,200,200,160); border:none; background:transparent;")
        return lbl


class EdgePanelView(QWidget):
    on_player_click   = Signal()
    on_sorter_click   = Signal()
    on_enhancer_click = Signal()
    on_todo_click     = Signal()

    HANDLE_W = 6
    PANEL_W  = 90
    H_RATIO  = 0.52

    def __init__(self):
        super().__init__()
        self._expanded    = False
        self._anim        = None
        self._settings_d  = None
        self._ocr_ctrl    = None

        # Ссылки на кнопки модулей для индикации загрузки
        self.player_btn = None
        self.sorter_btn = None
        self.enhancer_btn = None
        self.todo_btn = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui()
        self._init_geometry()

    def set_ocr_controller(self, ctrl):
        self._ocr_ctrl = ctrl
        ctrl.model_loading.connect(self._on_ocr_loading)
        ctrl.model_ready.connect(self._on_ocr_ready)
        ctrl.model_error.connect(self._on_ocr_error)
        ctrl._anim_timer.timeout.connect(self._ocr_anim_tick)

    # ── Построение UI ────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self._card = self._make_card()
        root.addWidget(self._card)

    def _make_card(self) -> QFrame:
        card = QFrame(); card.setObjectName("card")
        card.setStyleSheet("""
            QFrame#card { background:rgba(18,18,18,235); border-radius:18px;
                          border:1px solid rgba(255,255,255,10); }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(13, 18, 13, 14); lay.setSpacing(6)
        lay.setAlignment(Qt.AlignHCenter)

        lay.addWidget(self._make_header())
        lay.addSpacing(8)
        lay.addWidget(self._make_tool_btn("player.jpeg",      "Плеер",       self.on_player_click))
        lay.addWidget(self._make_tool_btn("auto_sorter.jpeg", "AutoSort", self.on_sorter_click))
        lay.addWidget(self._make_enhancer_btn())
        lay.addWidget(self._make_todo_btn())
        lay.addWidget(self._make_ocr_btn())
        lay.addStretch()
        lay.addWidget(self._make_separator())
        lay.addSpacing(4)
        lay.addWidget(self._make_settings_btn(), 0, Qt.AlignHCenter)
        lay.addWidget(self._make_quit_btn(),     0, Qt.AlignHCenter)
        return card

    def _make_header(self) -> QLabel:
        hdr = QLabel("TOOLS"); hdr.setAlignment(Qt.AlignCenter)
        hdr.setFont(QFont("Segoe UI Semibold", 8))
        hdr.setStyleSheet(
            "color:rgba(255,255,255,35); letter-spacing:2px;"
            " border:none; background:transparent;"
        )
        return hdr

    def _make_tool_btn(self, icon_file: str, label: str, signal: Signal) -> ToolButton:
        assets = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "..", "..", "..", "assets")
        btn = ToolButton(os.path.join(assets, icon_file), label)
        btn.clicked.connect(signal)

        # Сохраняем ссылки на кнопки
        if 'player' in icon_file:
            self.player_btn = btn
        elif 'sorter' in icon_file:
            self.sorter_btn = btn

        return btn

    def _make_enhancer_btn(self) -> QWidget:
        container = QWidget(); container.setFixedSize(62, 70)
        container.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 6, 0, 4); lay.setSpacing(3)
        lay.setAlignment(Qt.AlignHCenter)

        self.enhancer_btn = QPushButton("🖼")
        self.enhancer_btn.setFixedSize(44, 44)
        self.enhancer_btn.setFont(QFont("Segoe UI", 20))
        self.enhancer_btn.setCursor(Qt.PointingHandCursor)
        self.enhancer_btn.setToolTip("Улучшение и раскраска изображений")
        self.enhancer_btn.setStyleSheet("""
            QPushButton { background:rgba(255,255,255,8); border-radius:13px;
                          border:1px solid rgba(255,255,255,12); }
            QPushButton:hover   { background:rgba(0,120,215,60); border:1px solid #0078d7; }
            QPushButton:pressed { background:rgba(0,120,215,90); }
        """)
        self.enhancer_btn.clicked.connect(self.on_enhancer_click)

        lbl = QLabel("Фото"); lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet("color:rgba(200,200,200,160); border:none; background:transparent;")

        lay.addWidget(self.enhancer_btn, 0, Qt.AlignHCenter)
        lay.addWidget(lbl, 0, Qt.AlignHCenter)
        return container

    def _make_todo_btn(self) -> QWidget:
        container = QWidget(); container.setFixedSize(62, 70)
        container.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 6, 0, 4); lay.setSpacing(3)
        lay.setAlignment(Qt.AlignHCenter)

        self.todo_btn = QPushButton("📝")
        self.todo_btn.setFixedSize(44, 44)
        self.todo_btn.setFont(QFont("Segoe UI", 20))
        self.todo_btn.setCursor(Qt.PointingHandCursor)
        self.todo_btn.setCheckable(True)
        self.todo_btn.setToolTip("Smart Notes — контекстные заметки")
        self.todo_btn.setStyleSheet("""
            QPushButton {
                background:rgba(255,255,255,8);
                border-radius:13px;
                border:1px solid rgba(255,255,255,12);
            }
            QPushButton:hover {
                background:rgba(0,120,215,60);
                border:1px solid #0078d7;
            }
            QPushButton:checked {
                background:rgba(0,120,215,150);
                border:1px solid #0078d7;
            }
        """)
        self.todo_btn.clicked.connect(self.on_todo_click)

        lbl = QLabel("Notes"); lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet("color:rgba(200,200,200,160); border:none; background:transparent;")

        lay.addWidget(self.todo_btn, 0, Qt.AlignHCenter)
        lay.addWidget(lbl, 0, Qt.AlignHCenter)
        return container

    def _make_ocr_btn(self) -> QWidget:
        container = QWidget(); container.setFixedSize(62, 70)
        container.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 6, 0, 4); lay.setSpacing(3)
        lay.setAlignment(Qt.AlignHCenter)

        self._ocr_btn = QPushButton("🔍")
        self._ocr_btn.setFixedSize(44, 44)
        self._ocr_btn.setFont(QFont("Segoe UI", 20))
        self._ocr_btn.setCursor(Qt.PointingHandCursor)
        self._ocr_btn.setToolTip("OCR — распознать текст со скриншота")
        self._ocr_btn.setEnabled(False)
        self._ocr_btn.setStyleSheet("""
            QPushButton { background:rgba(255,255,255,8); border-radius:13px;
                          border:1px solid rgba(255,255,255,12); }
            QPushButton:hover   { background:rgba(0,120,215,60); border:1px solid #0078d7; }
            QPushButton:pressed { background:rgba(0,120,215,90); }
            QPushButton:disabled { color: rgba(255,255,255,40); }
        """)
        self._ocr_btn.clicked.connect(self._on_ocr_clicked)

        lbl = QLabel("OCR"); lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet("color:rgba(200,200,200,160); border:none; background:transparent;")

        lay.addWidget(self._ocr_btn, 0, Qt.AlignHCenter)
        lay.addWidget(lbl, 0, Qt.AlignHCenter)
        return container

    def _make_separator(self) -> QFrame:
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background:rgba(255,255,255,15);")
        return sep

    def _make_settings_btn(self) -> QPushButton:
        btn = QPushButton("⚙")
        btn.setFixedSize(44, 34); btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 14))
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:rgba(200,200,200,150);
                          border:none; border-radius:8px; }
            QPushButton:hover { background:rgba(255,255,255,10); color:white; }
        """)
        btn.clicked.connect(self._open_settings)
        return btn

    def _make_quit_btn(self) -> QPushButton:
        btn = QPushButton("✕")
        btn.setFixedSize(44, 30); btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 13))
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:rgba(255,85,85,140);
                          border:none; border-radius:8px; }
            QPushButton:hover { background:rgba(192,57,43,40); color:#ff5555; }
        """)
        btn.clicked.connect(QApplication.instance().quit)
        return btn

    # ── OCR состояния кнопки ─────────────────────────────────────────────

    def set_module_loading(self, module: str, loading: bool):
        """
        Установить состояние загрузки модуля.

        Args:
            module: 'player', 'sorter', 'enhancer', 'todo'
            loading: True — загружается (серая иконка), False — готов
        """
        btn = None
        if module == 'player' and self.player_btn:
            btn = self.player_btn
        elif module == 'sorter' and self.sorter_btn:
            btn = self.sorter_btn
        elif module == 'enhancer' and self.enhancer_btn:
            btn = self.enhancer_btn
        elif module == 'todo' and self.todo_btn:
            btn = self.todo_btn

        if btn:
            if loading:
                # Серая иконка + отключаем кнопку
                btn.setEnabled(False)
                btn.setStyleSheet("""
                    QPushButton {
                        background:rgba(80,80,80,50);
                        border-radius:13px;
                        border:1px solid rgba(255,255,255,5);
                        color: rgba(255,255,255,50);
                    }
                """)
                print(f"[edge_panel] Module '{module}' loading...")
            else:
                # Восстанавливаем нормальный стиль
                btn.setEnabled(True)
                btn.setStyleSheet("""
                    QPushButton {
                        background:rgba(255,255,255,8);
                        border-radius:13px;
                        border:1px solid rgba(255,255,255,12);
                    }
                    QPushButton:hover {
                        background:rgba(0,120,215,60);
                        border:1px solid #0078d7;
                    }
                    QPushButton:pressed {
                        background:rgba(0,120,215,90);
                    }
                    QPushButton:checked {
                        background:rgba(0,120,215,150);
                        border:1px solid #0078d7;
                    }
                """)
                print(f"[edge_panel] Module '{module}' ready!")

    def _on_ocr_loading(self):
        self._ocr_btn.setEnabled(False)
        self._ocr_btn.setToolTip("OCR: загрузка модели (~500MB, только первый раз)...")

    def _on_ocr_ready(self):
        self._ocr_btn.setEnabled(True)
        self._ocr_btn.setText("🔍")
        self._ocr_btn.setToolTip("OCR — распознать текст со скриншота")

    def _on_ocr_error(self, msg: str):
        self._ocr_btn.setEnabled(True)
        self._ocr_btn.setText("🔍")
        self._ocr_btn.setToolTip(f"OCR недоступен: {msg}")

    def _ocr_anim_tick(self):
        if self._ocr_ctrl:
            frames = ["⏳", "⌛"]
            self._ocr_btn.setText(frames[self._ocr_ctrl.anim_step % 2])

    def _on_ocr_clicked(self):
        if not self._ocr_ctrl:
            return
        if self._expanded:
            self._toggle()
        QTimer.singleShot(300, self._ocr_ctrl.launch)

    # ── Геометрия ────────────────────────────────────────────────────────

    def _init_geometry(self):
        s = QApplication.primaryScreen().geometry()
        h = int(s.height() * self.H_RATIO)
        y = (s.height() - h) // 2
        self._geo_closed = QRect(s.width() - self.HANDLE_W, y, self.PANEL_W, h)
        self._geo_open   = QRect(s.width() - self.PANEL_W,  y, self.PANEL_W, h)
        self.setGeometry(self._geo_closed)

    # ── Анимация ─────────────────────────────────────────────────────────

    def _toggle(self):
        if self._anim and self._anim.state() == QPropertyAnimation.Running:
            return
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QEasingCurve.OutExpo)
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(self._geo_closed if self._expanded else self._geo_open)
        self._expanded = not self._expanded
        self._anim.start()

    def collapse_for_overlay(self):
        """Свернуть панель, когда открыт диалог настроек или другое окно поверх."""
        if not self._expanded:
            return
        if self._anim and self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()
        self.setGeometry(self._geo_closed)
        self._expanded = False

    @staticmethod
    def is_overlay_blocking() -> bool:
        from app.features.settings.ui.settings_dialog import SettingsDialog
        return SettingsDialog.is_any_visible()

    # ── Настройки ────────────────────────────────────────────────────────

    def _open_settings(self):
        from app.features.settings.ui.settings_dialog import SettingsDialog
        if self._settings_d and self._settings_d.isVisible():
            return
        self._settings_d = SettingsDialog()
        d = self._settings_d

        # Подключаем сигнал для применения настроек
        d.settings_changed.connect(self._apply_settings_to_modules)

        if hasattr(d, 'smart_position'):
            d.smart_position(self.geometry())
        else:
            d.move(self.geometry().left() - d.width() - 12, self.geometry().top())
        d.show()
        self.collapse_for_overlay()

    def _apply_settings_to_modules(self, settings: dict):
        """Применить настройки ко всем модулям."""
        print(f"[edge_panel] Applying settings to modules: {settings}")

        # Применяем к Todo модулю
        if hasattr(self, '_todo_ctrl') and self._todo_ctrl:
            self._todo_ctrl._apply_settings(settings)

        if "sorter_source" in settings or "sorter_auto_enabled" in settings:
            from app.core import config
            from app.features.file_sorter.core.auto_watcher import get_auto_watcher

            get_auto_watcher().reload()
            sv = getattr(self, "_sorter_view", None)
            if sv is not None:
                sv._apply_settings(config.load())
                sv.refresh_source_label()

        # Здесь можно добавить применение настроек к другим модулям
        # if hasattr(self, '_player_ctrl') and self._player_ctrl:
        #     self._player_ctrl._apply_settings(settings)

    # ── Отрисовка ────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        if not self._expanded:
            self._draw_handle(p)

    def _draw_handle(self, p: QPainter):
        bw, bh = 4, 40
        bx = self.width() - bw
        by = (self.height() - bh) // 2
        path = QPainterPath()
        path.addRoundedRect(bx, by, bw, bh, 2, 2)
        p.fillPath(path, QColor(255, 255, 255, 70))

    # ── Мышь ─────────────────────────────────────────────────────────────

    def enterEvent(self, e):
        if self.is_overlay_blocking():
            return
        if not self._expanded:
            self._toggle()

    def leaveEvent(self, e):
        if self._expanded and not self.is_overlay_blocking():
            self._toggle()