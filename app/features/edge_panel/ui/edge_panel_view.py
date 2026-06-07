"""
UI боковой панели инструментов EdgeTools.

Свёрнутая полоска у правого края экрана; при наведении разворачивается
карточка TOOLS с кнопками модулей (Плеер, AutoSort, Фото, Notes, OCR).
"""
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QApplication,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt, QRect, QPoint, QPointF, QPropertyAnimation, QEasingCurve, Signal, QSize, QTimer,
    QParallelAnimationGroup, QAbstractAnimation,
)
from PySide6.QtGui import QColor, QPainter, QFont, QPainterPath, QCursor

from app.core.ui_scale import screen_scale, scale_font, scale_px
from app.features.edge_panel.ui.tool_button import ToolButton
from app.features.edge_panel.ui.edge_panel_hover import EdgePanelHoverFilter


class EdgePanelView(QWidget):
    """
    Главная точка входа EdgeTools: launcher модулей и настройки.

    Сигналы on_*_click — для main.py / оркестратора приложения.
    """

    on_player_click   = Signal()
    on_sorter_click   = Signal()
    on_enhancer_click = Signal()
    on_todo_click     = Signal()

    # Визуал свёрнутой полоски — как было (не масштабируем)
    HANDLE_VIS_W = 4
    HANDLE_VIS_H = 40
    PANEL_W = 90
    # Невидимая зона наведения (только свёрнутый режим)
    HITBOX_W = 90
    HITBOX_H_RATIO = 0.65
    H_RATIO = 0.52  # высота развёрнутой панели
    ANIM_OPEN_MS = 460
    ANIM_CLOSE_MS = 340
    HOVER_POLL_MS = 25
    CARD_HOVER_MARGIN = 10

    def __init__(self):
        """Сборка UI, геометрия у правого края, глобальный hover-filter."""
        super().__init__()
        self._scale = screen_scale()
        self._hitbox_w = self.HITBOX_W

        self._expanded    = False
        self._anim_group  = None
        self._card_fx     = None
        self._settings_d  = None
        self._ocr_ctrl    = None

        self.player_btn = None
        self.sorter_btn = None
        self.enhancer_btn = None
        self.todo_btn = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._build_ui()
        self._init_geometry()
        self._card.setVisible(False)

        self._hover_poll = QTimer(self)
        self._hover_poll.setInterval(self.HOVER_POLL_MS)
        self._hover_poll.timeout.connect(self._sync_hover_state)

        self._global_hover_filter = EdgePanelHoverFilter(self)
        QApplication.instance().installEventFilter(self._global_hover_filter)

    def set_ocr_controller(self, ctrl):
        """
        Подключить OcrController для индикации загрузки Tesseract на кнопке OCR.

        Args:
            ctrl: OcrController
        """
        self._ocr_ctrl = ctrl
        ctrl.model_loading.connect(self._on_ocr_loading)
        ctrl.model_ready.connect(self._on_ocr_ready)
        ctrl.model_error.connect(self._on_ocr_error)
        ctrl._anim_timer.timeout.connect(self._ocr_anim_tick)

    def _px(self, value: float) -> int:
        """Масштабирование пикселей под DPI экрана."""
        return scale_px(value, self._scale)

    def _build_ui(self):
        """Корневой layout и карточка TOOLS."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._card = self._make_card()
        root.addWidget(self._card)

    def _make_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        r = self._px(18)
        card.setStyleSheet(f"""
            QFrame#card {{ background:rgba(18,18,18,235); border-radius:{r}px;
                          border:1px solid rgba(255,255,255,10); }}
        """)
        lay = QVBoxLayout(card)
        m = self._px(13)
        lay.setContentsMargins(m, self._px(18), m, self._px(14))
        lay.setSpacing(self._px(6))
        lay.setAlignment(Qt.AlignHCenter)

        lay.addWidget(self._make_header())
        lay.addSpacing(self._px(8))
        lay.addWidget(self._make_tool_btn("player.jpeg", "Плеер", self.on_player_click))
        lay.addWidget(self._make_tool_btn("auto_sorter.jpeg", "AutoSort", self.on_sorter_click))
        lay.addWidget(self._make_enhancer_btn())
        lay.addWidget(self._make_todo_btn())
        lay.addWidget(self._make_ocr_btn())
        lay.addStretch()
        lay.addWidget(self._make_separator())
        lay.addSpacing(self._px(4))
        lay.addWidget(self._make_settings_btn(), 0, Qt.AlignHCenter)
        lay.addWidget(self._make_quit_btn(), 0, Qt.AlignHCenter)
        return card

    def _make_header(self) -> QLabel:
        hdr = QLabel("TOOLS")
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setFont(QFont("Segoe UI Semibold", scale_font(8, self._scale)))
        hdr.setStyleSheet(
            "color:rgba(255,255,255,35); letter-spacing:2px;"
            " border:none; background:transparent;"
        )
        return hdr

    def _assets_dir(self) -> str:
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "assets",
        )

    def _make_tool_btn(self, icon_file: str, label: str, signal: Signal) -> ToolButton:
        btn = ToolButton(os.path.join(self._assets_dir(), icon_file), label, self._scale)
        btn.clicked.connect(signal)
        if "player" in icon_file:
            self.player_btn = btn
        elif "sorter" in icon_file:
            self.sorter_btn = btn
        return btn

    def _make_module_btn_container(self, emoji: str, label: str, signal, checkable: bool = False):
        container = QWidget()
        container.setFixedSize(self._px(62), self._px(70))
        container.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, self._px(6), 0, self._px(4))
        lay.setSpacing(self._px(3))
        lay.setAlignment(Qt.AlignHCenter)

        side = self._px(44)
        btn = QPushButton(emoji)
        btn.setFixedSize(side, side)
        btn.setFont(QFont("Segoe UI", scale_font(20, self._scale)))
        btn.setCursor(Qt.PointingHandCursor)
        if checkable:
            btn.setCheckable(True)
        r = self._px(13)
        base_style = f"""
            QPushButton {{ background:rgba(255,255,255,8); border-radius:{r}px;
                          border:1px solid rgba(255,255,255,12); }}
            QPushButton:hover {{ background:rgba(0,120,215,60); border:1px solid #0078d7; }}
            QPushButton:pressed {{ background:rgba(0,120,215,90); }}
        """
        if checkable:
            base_style += """
            QPushButton:checked {
                background:rgba(0,120,215,150); border:1px solid #0078d7;
            }
            """
        btn.setStyleSheet(base_style)
        btn.clicked.connect(signal)

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Segoe UI", scale_font(8, self._scale)))
        lbl.setStyleSheet("color:rgba(200,200,200,160); border:none; background:transparent;")

        lay.addWidget(btn, 0, Qt.AlignHCenter)
        lay.addWidget(lbl, 0, Qt.AlignHCenter)
        return container, btn

    def _make_enhancer_btn(self) -> QWidget:
        container, btn = self._make_module_btn_container(
            "🖼", "Фото", self.on_enhancer_click,
        )
        btn.setToolTip("Улучшение и раскраска изображений")
        self.enhancer_btn = btn
        return container

    def _make_todo_btn(self) -> QWidget:
        container, btn = self._make_module_btn_container(
            "📝", "Notes", self.on_todo_click, checkable=True,
        )
        btn.setToolTip("Smart Notes — контекстные заметки")
        self.todo_btn = btn
        return container

    def _make_ocr_btn(self) -> QWidget:
        container, btn = self._make_module_btn_container("🔍", "OCR", self._on_ocr_clicked)
        btn.setToolTip("OCR — распознать текст со скриншота")
        btn.setEnabled(False)
        btn.setStyleSheet(btn.styleSheet() + """
            QPushButton:disabled { color: rgba(255,255,255,40); }
        """)
        self._ocr_btn = btn
        return container

    def _make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:rgba(255,255,255,15);")
        return sep

    def _make_settings_btn(self) -> QPushButton:
        side = self._px(44)
        btn = QPushButton("⚙")
        btn.setFixedSize(side, self._px(34))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", scale_font(14, self._scale)))
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:rgba(200,200,200,150);
                          border:none; border-radius:8px; }
            QPushButton:hover { background:rgba(255,255,255,10); color:white; }
        """)
        btn.clicked.connect(self._open_settings)
        return btn

    def _make_quit_btn(self) -> QPushButton:
        side = self._px(44)
        btn = QPushButton("✕")
        btn.setFixedSize(side, self._px(30))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", scale_font(13, self._scale)))
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:rgba(255,85,85,140);
                          border:none; border-radius:8px; }
            QPushButton:hover { background:rgba(192,57,43,40); color:#ff5555; }
        """)
        btn.clicked.connect(QApplication.instance().quit)
        return btn

    def set_module_loading(self, module: str, loading: bool):
        """
        Визуально заблокировать кнопку модуля на время инициализации.

        Args:
            module: "player" | "sorter" | "enhancer" | "todo"
            loading: True — disabled + приглушённый стиль
        """
        btn = None
        if module == "player" and self.player_btn:
            inner = self.player_btn.findChild(QPushButton)
            btn = inner
        elif module == "sorter" and self.sorter_btn:
            inner = self.sorter_btn.findChild(QPushButton)
            btn = inner
        elif module == "enhancer" and self.enhancer_btn:
            btn = self.enhancer_btn
        elif module == "todo" and self.todo_btn:
            btn = self.todo_btn

        if not btn:
            return

        r = self._px(13)
        if loading:
            btn.setEnabled(False)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:rgba(80,80,80,50);
                    border-radius:{r}px;
                    border:1px solid rgba(255,255,255,5);
                    color: rgba(255,255,255,50);
                }}
            """)
        else:
            btn.setEnabled(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:rgba(255,255,255,8);
                    border-radius:{r}px;
                    border:1px solid rgba(255,255,255,12);
                }}
                QPushButton:hover {{
                    background:rgba(0,120,215,60);
                    border:1px solid #0078d7;
                }}
                QPushButton:pressed {{
                    background:rgba(0,120,215,90);
                }}
                QPushButton:checked {{
                    background:rgba(0,120,215,150);
                    border:1px solid #0078d7;
                }}
            """)

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
            self._run_panel_animation(False)
        QTimer.singleShot(300, self._ocr_ctrl.launch)

    def _init_geometry(self):
        """Позиции свёрнутой (хитбокс) и развёрнутой (карточка) панели."""
        s = QApplication.primaryScreen().geometry()
        hit_h = int(s.height() * self.HITBOX_H_RATIO)
        hit_y = (s.height() - hit_h) // 2
        panel_h = int(s.height() * self.H_RATIO)
        panel_y = (s.height() - panel_h) // 2
        # Свёрнуто: невидимый хитбокс 50×65% экрана; полоска — справа в этой зоне
        self._geo_closed = QRect(s.width() - self._hitbox_w, hit_y, self.PANEL_W, hit_h)
        self._geo_open = QRect(s.width() - self.PANEL_W, panel_y, self.PANEL_W, panel_h)
        self.setGeometry(self._geo_closed)

    @staticmethod
    def _smooth_ease_out() -> QEasingCurve:
        # cubic-bezier(0.22, 1, 0.36, 1) — мягкое замедление в конце
        curve = QEasingCurve(QEasingCurve.BezierSpline)
        curve.addCubicBezierSegment(
            QPointF(0.22, 1.0), QPointF(0.36, 1.0), QPointF(1.0, 1.0),
        )
        return curve

    def _ensure_card_fx(self) -> QGraphicsOpacityEffect:
        if self._card_fx is None:
            self._card_fx = QGraphicsOpacityEffect(self._card)
            self._card.setGraphicsEffect(self._card_fx)
        return self._card_fx

    def _is_animating(self) -> bool:
        return (
            self._anim_group is not None
            and self._anim_group.state() == QAbstractAnimation.Running
        )

    def _trigger_zone_global(self) -> QRect:
        """Свёрнутый режим: невидимый триггер у правого края (экранные координаты)."""
        geo = self.frameGeometry()
        w = min(self._hitbox_w, geo.width())
        return QRect(geo.right() - w + 1, geo.top(), w, geo.height())

    def _expanded_work_zone_global(self) -> QRect:
        """Развёрнутый режим: карточка TOOLS + небольшой отступ (экранные координаты)."""
        if not self._card.isVisible():
            return QRect()
        m = self.CARD_HOVER_MARGIN
        tl = self._card.mapToGlobal(QPoint(0, 0))
        sz = self._card.size()
        return QRect(
            tl.x() - m, tl.y() - m,
            sz.width() + 2 * m, sz.height() + 2 * m,
        )

    def _pointer_in_work_zone(self) -> bool:
        if not self.isVisible():
            return False
        pos = QCursor.pos()
        if not self._expanded:
            return self._trigger_zone_global().contains(pos)
        if self._is_animating():
            return self.frameGeometry().contains(pos)
        zone = self._expanded_work_zone_global()
        return not zone.isNull() and zone.contains(pos)

    def _force_collapse(self) -> None:
        if self._expanded:
            self._run_panel_animation(False)

    def _sync_hover_state(self) -> None:
        if not self._expanded:
            self._hover_poll.stop()
            return
        if not self._pointer_in_work_zone():
            self._force_collapse()

    def _on_open_animation_finished(self) -> None:
        self._sync_hover_state()

    def _run_panel_animation(self, opening: bool) -> None:
        """Анимация geometry + fade карточки при открытии/закрытии."""
        if self._is_animating():
            self._anim_group.stop()
            self._anim_group = None

        self._expanded = opening
        if opening:
            self._hover_poll.start()
        else:
            self._hover_poll.stop()
        duration = self.ANIM_OPEN_MS if opening else self.ANIM_CLOSE_MS
        fx = self._ensure_card_fx()

        geo = QPropertyAnimation(self, b"geometry", self)
        geo.setDuration(duration)
        geo.setEasingCurve(
            self._smooth_ease_out() if opening else QEasingCurve(QEasingCurve.InOutCubic)
        )
        geo.setStartValue(self.geometry())
        geo.setEndValue(self._geo_open if opening else self._geo_closed)

        fade = QPropertyAnimation(fx, b"opacity", self)
        fade.setEasingCurve(
            QEasingCurve(QEasingCurve.OutCubic if opening else QEasingCurve.Type.InCubic)
        )

        if opening:
            self._card.setVisible(True)
            fx.setOpacity(0.0)
            fade.setDuration(int(duration * 0.7))
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
        else:
            fx.setOpacity(1.0)
            fade.setDuration(int(duration * 0.5))
            fade.setStartValue(1.0)
            fade.setEndValue(0.0)

        group = QParallelAnimationGroup(self)
        group.addAnimation(geo)
        group.addAnimation(fade)
        if opening:
            group.finished.connect(self._on_open_animation_finished)
        else:
            group.finished.connect(lambda: self._card.setVisible(False))

        self._anim_group = group
        group.start()

    def collapse_for_overlay(self):
        """Свернуть панель, когда открыт модальный оверлей (OCR, настройки)."""
        if not self._expanded:
            return
        if self._is_animating():
            self._anim_group.stop()
        self._run_panel_animation(False)

    @staticmethod
    def is_overlay_blocking() -> bool:
        """True, если открыт SettingsDialog — не мешать модальным окнам."""
        from app.features.settings.ui.settings_dialog import SettingsDialog
        return SettingsDialog.is_any_visible()

    def _open_settings(self):
        from app.features.settings.ui.settings_dialog import SettingsDialog
        if self._settings_d is None:
            self._settings_d = SettingsDialog(parent=self)
            self._settings_d.settings_changed.connect(self._apply_settings_to_modules)
        d = self._settings_d
        if d.isVisible():
            d.raise_()
            d.activateWindow()
            return
        d.show_near(self.geometry())

    def _apply_settings_to_modules(self, settings: dict):
        if hasattr(self, "_todo_ctrl") and self._todo_ctrl:
            self._todo_ctrl._apply_settings(settings)

        if "sorter_source" in settings or "sorter_auto_enabled" in settings:
            from app.core import config
            from app.features.file_sorter.core.auto_watcher import get_auto_watcher

            get_auto_watcher().reload()
            sv = getattr(self, "_sorter_view", None)
            if sv is not None:
                sv._apply_settings(config.load())
                sv.refresh_source_label()

    def paintEvent(self, event):
        """В свёрнутом режиме — невидимый хитбокс и визуальная полоска-handle."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self._expanded:
            # Windows не ловит мышь в полностью прозрачных пикселях — alpha=1, глазу не видно
            p.fillRect(0, 0, self._hitbox_w, self.height(), QColor(0, 0, 0, 1))
            self._draw_handle(p)

    def _draw_handle(self, p: QPainter):
        bw = self.HANDLE_VIS_W
        bh = self.HANDLE_VIS_H
        # Полоска у правого края хитбокса, не у края всего окна (90px)
        bx = self._hitbox_w - bw
        by = (self.height() - bh) // 2
        path = QPainterPath()
        path.addRoundedRect(bx, by, bw, bh, 2, 2)
        p.fillPath(path, QColor(255, 255, 255, 70))

    def enterEvent(self, e):
        """Наведение на триггер — развернуть панель."""
        super().enterEvent(e)
        if not self._expanded and self._pointer_in_work_zone():
            self._run_panel_animation(True)

    def leaveEvent(self, e):
        super().leaveEvent(e)
        if self._expanded:
            self._sync_hover_state()

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        if self._expanded:
            self._sync_hover_state()
