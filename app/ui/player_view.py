import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_bin_dir = os.path.join(_project_root, "bin")
os.environ["PATH"] = _bin_dir + os.pathsep + os.environ["PATH"]

try:
    import mpv
    MPV_AVAILABLE = True
except OSError:
    MPV_AVAILABLE = False

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QSlider, QFrame, QApplication,
    QComboBox, QLabel,
)
from PySide6.QtCore import Qt, Signal, QRect, QTimer, QPoint
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath


class PlayerView(QWidget):
    play_requested = Signal(str)

    def __init__(self, settings: dict = None):
        super().__init__()
        self._ct_toggle = ClickThroughToggle(self)
        from PySide6.QtGui import QIcon
        import os
        _assets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "assets")
        self.setWindowIcon(QIcon(os.path.join(_assets, "player.jpeg")))
        self._settings  = settings or {}
        self._resizing  = None
        self._drag_pos  = None
        self._start_geo = None
        self._border    = 8
        self._mpv       = None
        self._mpv_alive = False   # флаг — живой ли core

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(2500)
        self._hide_timer.timeout.connect(self._hide_controls)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(320, 180)
        self.resize(560, 315)
        self.setMouseTracking(True)
        self.setWindowOpacity(self._settings.get("player_opacity", 100) / 100)

        self._build_ui()
        self._move_to_corner()

    # ── MPV: ленивая инициализация ───────────────────────────────────────
    def _ensure_mpv(self):
        if self._mpv_alive:
            return True
        if not MPV_AVAILABLE:
            return False
        try:
            wid = int(self._video_frame.winId())
            self._mpv = mpv.MPV(
                wid=str(wid),
                vo="gpu",
                hwdec="auto",
                keep_open=True,
                ytdl=False,
                hr_seek="no",
            )
            # Сначала observe, потом ставим громкость
            self._mpv.observe_property("time-pos", self._on_time_pos)
            self._mpv.observe_property("duration", self._on_duration)
            # volume НЕ observe — сами управляем
            self._mpv_alive = True

            # Ставим громкость после небольшой задержки
            QTimer.singleShot(200, lambda: self._mpv_safe(
                lambda: setattr(self._mpv, "volume",
                                self._settings.get("player_volume", 70))
            ))
            return True
        except Exception as e:
            print(f"[mpv] init error: {e}")
            return False

    def _mpv_safe(self, func, *args, **kwargs):
        """Безопасный вызов любого метода/свойства MPV."""
        if not self._mpv_alive:
            return None
        try:
            return func(*args, **kwargs)
        except Exception:
            self._mpv_alive = False
            return None

    # ── UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._card = QFrame()
        self._card.setObjectName("playerCard")
        self._card.setStyleSheet("""
            QFrame#playerCard {
                background: #000;
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,15);
            }
        """)
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # Область видео
        self._video_frame = QFrame()
        self._video_frame.setStyleSheet("background:#000; border:none;")
        self._video_frame.setMouseTracking(True)
        card_lay.addWidget(self._video_frame, stretch=1)

        # Панель управления
        self._controls = self._build_controls()
        card_lay.addWidget(self._controls)

        # Кнопка «показать прогресс» — плавает снизу по центру,
        # видна только когда _progress_row скрыт
        self._btn_show_progress = QPushButton("▴  хронометраж")
        self._btn_show_progress.setCursor(Qt.PointingHandCursor)
        self._btn_show_progress.setFixedHeight(22)
        self._btn_show_progress.setFont(QFont("Segoe UI", 8))
        self._btn_show_progress.setStyleSheet("""
            QPushButton {
                background: rgba(0,0,0,140);
                color: rgba(255,255,255,140);
                border: 1px solid rgba(255,255,255,20);
                border-radius: 10px;
                padding: 0 10px;
            }
            QPushButton:hover { background: rgba(0,120,215,160); color: white; }
        """)
        self._btn_show_progress.setVisible(False)
        self._btn_show_progress.clicked.connect(self._toggle_progress)
        self._btn_show_progress.setParent(self._card)  # поверх карточки

        root.addWidget(self._card)

        self._video_frame.installEventFilter(self)
        self._card.installEventFilter(self)
        self._controls.installEventFilter(self)

    def _build_controls(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("controls")
        panel.setStyleSheet("""
            QFrame#controls {
                background: qlineargradient(
                    x1:0,y1:0, x2:0,y2:1,
                    stop:0 rgba(0,0,0,0),
                    stop:1 rgba(0,0,0,210)
                );
                border: none;
                border-radius: 0 0 12px 12px;
            }
        """)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 6, 10, 8)
        lay.setSpacing(4)

        # ── Прогресс ──
        self._progress_row = QWidget()
        pr = QHBoxLayout(self._progress_row)
        pr.setContentsMargins(0, 0, 0, 0); pr.setSpacing(6)

        self._lbl_cur = QLabel("0:00")
        self._lbl_cur.setFont(QFont("Segoe UI", 8))
        self._lbl_cur.setStyleSheet("color:rgba(255,255,255,160); min-width:32px;")

        self._progress = QSlider(Qt.Horizontal)
        self._progress.setRange(0, 1000)
        self._progress.setStyleSheet(self._slider_style("#0078d7"))
        self._progress.sliderMoved.connect(self._seek)

        self._lbl_dur = QLabel("0:00")
        self._lbl_dur.setFont(QFont("Segoe UI", 8))
        self._lbl_dur.setStyleSheet("color:rgba(255,255,255,160); min-width:32px;")

        # Кнопка скрыть прогресс
        self._btn_hide_progress = self._icon_btn("▾", 22, tooltip="Скрыть хронометраж")
        self._btn_hide_progress.clicked.connect(self._toggle_progress)

        pr.addWidget(self._lbl_cur)
        pr.addWidget(self._progress, stretch=1)
        pr.addWidget(self._lbl_dur)
        pr.addWidget(self._btn_hide_progress)
        lay.addWidget(self._progress_row)

        # ── Нижняя строка ──
        bottom = QHBoxLayout(); bottom.setSpacing(6)

        self._btn_play = self._icon_btn("▶", 32)
        self._btn_play.clicked.connect(self._toggle_play)

        self._input_url = QLineEdit()
        self._input_url.setPlaceholderText("Ссылка или путь к файлу...")
        self._input_url.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,12); color: white;
                border: 1px solid rgba(255,255,255,20);
                border-radius: 6px; padding: 4px 8px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #0078d7; }
        """)
        self._input_url.returnPressed.connect(self._on_play_clicked)

        self._btn_vol = self._icon_btn("🔊", 28)
        self._btn_vol.clicked.connect(self._toggle_volume_row)

        self._vol_row = QWidget()
        vl = QHBoxLayout(self._vol_row)
        vl.setContentsMargins(0,0,0,0); vl.setSpacing(4)
        self._volume = QSlider(Qt.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(self._settings.get("player_volume", 70))
        self._volume.setFixedWidth(70)
        self._volume.setStyleSheet(self._slider_style("#aaa"))
        self._volume.valueChanged.connect(self._set_volume)
        vl.addWidget(self._volume)
        self._vol_row.setVisible(False)

        self._combo_quality = QComboBox()
        self._combo_quality.addItems(["Авто", "1080p", "720p", "480p", "360p"])
        default_q = self._settings.get("player_quality", "Авто")
        idx = self._combo_quality.findText(default_q)
        if idx >= 0: self._combo_quality.setCurrentIndex(idx)
        self._combo_quality.setFixedWidth(70)
        self._combo_quality.setStyleSheet("""
            QComboBox { background:rgba(255,255,255,12); color:white;
                        border:1px solid rgba(255,255,255,20); border-radius:6px;
                        padding:3px 6px; font-size:11px; }
            QComboBox::drop-down { border:none; }
            QComboBox QAbstractItemView { background:#1a1a1a; color:white;
                selection-background-color:#0078d7; border:1px solid #333; }
        """)

        self._btn_cfg = self._icon_btn("⚙", 28, tooltip="Настройки плеера")
        self._btn_cfg.clicked.connect(self._open_settings)

        self._btn_close = self._icon_btn("✕", 28)
        self._btn_close.setStyleSheet(
            self._btn_close.styleSheet() +
            "QPushButton:hover{background:rgba(192,57,43,150);}"
        )
        self._btn_close.clicked.connect(self.close)

        bottom.addWidget(self._btn_play)
        bottom.addWidget(self._input_url, stretch=1)
        bottom.addWidget(self._btn_vol)
        bottom.addWidget(self._vol_row)
        bottom.addWidget(self._combo_quality)
        bottom.addWidget(self._btn_cfg)
        bottom.addWidget(self._btn_close)
        lay.addLayout(bottom)
        return panel
        
    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.MouseButtonPress:
            self.mousePressEvent(event)
        elif event.type() == QEvent.MouseMove:
            self.mouseMoveEvent(event)
        elif event.type() == QEvent.MouseButtonRelease:
            self.mouseReleaseEvent(event)
        elif event.type() == QEvent.MouseButtonDblClick:
            self.mouseDoubleClickEvent(event)
        return super().eventFilter(obj, event)

    # ── Показ/скрытие прогресса ──────────────────────────────────────────
    def _toggle_progress(self):
        visible = self._progress_row.isVisible()
        self._progress_row.setVisible(not visible)
        # Кнопка «показать» появляется снизу по центру карточки
        self._btn_show_progress.setVisible(visible)
        if visible:
            self._reposition_show_btn()

    def _force_topmost(self):
        """Принудительный HWND_TOPMOST через WinAPI — работает для borderless fullscreen."""
        try:
            import ctypes
            import ctypes.wintypes as wt

            HWND_TOPMOST   = -1
            SWP_NOMOVE     = 0x0002
            SWP_NOSIZE     = 0x0001
            SWP_NOACTIVATE = 0x0010

            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            )
        except Exception as e:
            print(f"[topmost] {e}")

    def showEvent(self, e):
        super().showEvent(e)
        self._ct_toggle.show()
        self._ct_toggle.reposition(self.geometry())
        QTimer.singleShot(100, self._force_topmost)

    def _reposition_show_btn(self):
        """Позиционируем кнопку по центру снизу карточки."""
        btn = self._btn_show_progress
        btn.adjustSize()
        x = (self._card.width() - btn.width()) // 2
        y = self._card.height() - btn.height() - 6
        btn.move(x, y)
        btn.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_ct_toggle"):
            self._ct_toggle.reposition(self.geometry())
        if self._btn_show_progress.isVisible():
            self._reposition_show_btn()
        
    def moveEvent(self, e):
        super().moveEvent(e)
        if hasattr(self, "_ct_toggle"):
            self._ct_toggle.reposition(self.geometry())

    # ── Вспомогательные ──────────────────────────────────────────────────
    def _icon_btn(self, text: str, size: int = 28, tooltip: str = "") -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(size, size)
        btn.setCursor(Qt.PointingHandCursor)
        if tooltip: btn.setToolTip(tooltip)
        fs = max(1, size // 2 - 2)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,10); color: white;
                border: none; border-radius: {size//2}px; font-size: {fs}px;
            }}
            QPushButton:hover  {{ background: rgba(255,255,255,22); }}
            QPushButton:pressed{{ background: rgba(255,255,255,35); }}
        """)
        return btn

    @staticmethod
    def _slider_style(color: str) -> str:
        return f"""
            QSlider::groove:horizontal {{
                height:3px; background:rgba(255,255,255,30); border-radius:2px;
            }}
            QSlider::sub-page:horizontal {{ background:{color}; border-radius:2px; }}
            QSlider::handle:horizontal {{
                width:12px; height:12px; margin:-5px 0;
                background:{color}; border-radius:6px;
            }}
        """

    @staticmethod
    def _fmt_time(secs) -> str:
        if secs is None: return "0:00"
        s = int(secs); m = s // 60; s %= 60
        return f"{m}:{s:02d}"

    # ── MPV callbacks ────────────────────────────────────────────────────
    def _on_time_pos(self, _name, value):
        if value is None or not self._mpv_alive: return
        try:
            dur = self._mpv.duration or 0
            if dur > 0:
                self._progress.blockSignals(True)
                self._progress.setValue(int(value / dur * 1000))
                self._progress.blockSignals(False)
            self._lbl_cur.setText(self._fmt_time(value))
        except Exception:
            self._mpv_alive = False

    def _on_duration(self, _name, value):
        self._lbl_dur.setText(self._fmt_time(value))

    def _on_volume_changed(self, _name, value):
        if value is not None:
            self._volume.blockSignals(True)
            self._volume.setValue(int(value))
            self._volume.blockSignals(False)

    # ── Управление воспроизведением ──────────────────────────────────────
    def play(self, video_url: str, audio_url: str = ""):
        if not self._ensure_mpv():
            self.show_error("MPV недоступен")
            return

        def _do_play():
            try:
                if audio_url:
                    # Передаём аудио как per-file опцию прямо в loadfile
                    self._mpv.command(
                        "loadfile", video_url,
                        "replace", 0,
                        f"audio-file={audio_url}"
                    )
                else:
                    self._mpv.command("loadfile", video_url, "replace")

                self._btn_play.setText("⏸")
                self._hide_timer.start()
            except Exception as e:
                print(f"[mpv] play error: {e}")
                self._mpv_alive = False

        QTimer.singleShot(100, _do_play)


    def _toggle_play(self):
        print(f"[view] _toggle_play called, mpv_alive={self._mpv_alive}")
        if not self._mpv_alive:
            self._on_play_clicked()
            return
        try:
            self._mpv.pause = not self._mpv.pause
            self._btn_play.setText("▶" if self._mpv.pause else "⏸")
        except Exception:
            self._mpv_alive = False
            self._btn_play.setText("▶")

    def _seek(self, val: int):
        if not self._mpv_alive: return
        try:
            dur = self._mpv.duration
            if dur:
                target = val / 1000 * dur
                # "keyframes" — прыгаем только до ближайшего keyframe, не зависаем
                self._mpv.seek(target, "absolute+keyframes")
        except Exception:
            self._mpv_alive = False

    def _set_volume(self, val: int):
        self._mpv_safe(lambda: setattr(self._mpv, "volume", val))

    def _toggle_volume_row(self):
        self._vol_row.setVisible(not self._vol_row.isVisible())

    # ── Загрузка / ошибки ────────────────────────────────────────────────
    def set_loading(self, loading: bool):
        self._btn_play.setEnabled(not loading)
        self._btn_play.setText("…" if loading else "▶")

    def show_error(self, msg: str):
        self._input_url.setPlaceholderText(f"Ошибка: {msg[:60]}")
        self._btn_play.setText("▶")
        self._btn_play.setEnabled(True)

    def current_quality(self) -> str:
        return self._combo_quality.currentText()

    def update_qualities(self, qualities: list):
        cur = self._combo_quality.currentText()
        self._combo_quality.blockSignals(True)
        self._combo_quality.clear()
        self._combo_quality.addItems(qualities)
        idx = self._combo_quality.findText(cur)
        self._combo_quality.setCurrentIndex(max(0, idx))
        self._combo_quality.blockSignals(False)

    # ── Настройки ────────────────────────────────────────────────────────
    def _open_settings(self):
        from app.ui.settings_dialog import SettingsDialog
        d = SettingsDialog(initial_tab="player")
        d.settings_changed.connect(self._apply_settings)
        g = self.geometry()
        d.move(g.left() - d.width() - 12, g.top())
        d.exec()

    def _apply_settings(self, cfg: dict):
        self.setWindowOpacity(cfg.get("player_opacity", 100) / 100)
        idx = self._combo_quality.findText(cfg.get("player_quality", "Авто"))
        if idx >= 0: self._combo_quality.setCurrentIndex(idx)

    # ── Показ/скрытие панели управления ──────────────────────────────────
    def _show_controls(self):
        self._controls.setVisible(True)
        self._hide_timer.start()

    def _hide_controls(self):
        if not self._mpv_alive: return
        try:
            if not self._mpv.pause:
                self._controls.setVisible(False)
        except Exception:
            self._mpv_alive = False

    # ── Мышь: resize + drag ──────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._resizing  = self._check_edge(e.pos())
            self._drag_pos  = e.globalPosition().toPoint()
            self._start_geo = self.geometry()
        self._show_controls()

    def mouseMoveEvent(self, e):
        self._show_controls()
        if not e.buttons() & Qt.LeftButton:
            self._update_cursor(e.pos()); return
        diff = e.globalPosition().toPoint() - self._drag_pos
        geo  = QRect(self._start_geo)
        if self._resizing:
            if "right"  in self._resizing: geo.setRight(self._start_geo.right()   + diff.x())
            if "left"   in self._resizing: geo.setLeft(self._start_geo.left()     + diff.x())
            if "bottom" in self._resizing: geo.setBottom(self._start_geo.bottom() + diff.y())
            if "top"    in self._resizing: geo.setTop(self._start_geo.top()       + diff.y())
            if geo.width() >= 320 and geo.height() >= 180:
                self.setGeometry(geo)
        else:
            self.move(self._start_geo.topLeft() + diff)

    def mouseReleaseEvent(self, e):
        self._resizing = None; self._drag_pos = None
        self.setCursor(Qt.ArrowCursor)

    def mouseDoubleClickEvent(self, e):
        self._toggle_play()

    def _check_edge(self, pos):
        r = self.rect(); m = self._border
        l = pos.x() < m; rr = pos.x() > r.width() - m
        t = pos.y() < m; b  = pos.y() > r.height() - m
        if t and l:  return "top_left"
        if t and rr: return "top_right"
        if b and l:  return "bottom_left"
        if b and rr: return "bottom_right"
        if l:  return "left"
        if rr: return "right"
        if t:  return "top"
        if b:  return "bottom"
        return None

    def _update_cursor(self, pos):
        cursors = {
            "top_left": Qt.SizeFDiagCursor,  "bottom_right": Qt.SizeFDiagCursor,
            "top_right": Qt.SizeBDiagCursor, "bottom_left":  Qt.SizeBDiagCursor,
            "left": Qt.SizeHorCursor, "right": Qt.SizeHorCursor,
            "top":  Qt.SizeVerCursor, "bottom": Qt.SizeVerCursor,
        }
        self.setCursor(cursors.get(self._check_edge(pos), Qt.ArrowCursor))

    def enterEvent(self, e): self._show_controls()
    def leaveEvent(self, e): self._hide_timer.start()

    def _on_play_clicked(self):
        url = self._input_url.text().strip()
        print(f"[view] _on_play_clicked called, url='{url}'")
        if url:
            print(f"[view] emitting play_requested")
            self.play_requested.emit(url)

    def _move_to_corner(self):
        s = QApplication.primaryScreen().availableGeometry()
        self.move(s.width() - self.width() - 20, s.height() - self.height() - 20)

        
    def closeEvent(self, e):
        self._hide_timer.stop()
        if hasattr(self, "_ct_toggle"):
            self._ct_toggle.close()
        if self._mpv_alive:
            try:
                self._mpv_alive = False
                self._mpv.terminate()
            except Exception:
                pass
        e.accept()
    
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            # Переводим в координаты self если событие пришло от дочернего виджета
            try:
                local_pos = self.mapFromGlobal(e.globalPosition().toPoint())
            except Exception:
                local_pos = e.pos()

            self._resizing  = self._check_edge(local_pos)
            self._drag_pos  = e.globalPosition().toPoint()
            self._start_geo = self.geometry()
        self._show_controls()

    def mouseMoveEvent(self, e):
        self._show_controls()
        try:
            local_pos = self.mapFromGlobal(e.globalPosition().toPoint())
        except Exception:
            local_pos = e.pos()

        if not e.buttons() & Qt.LeftButton:
            self._update_cursor(local_pos)
            return

        if self._drag_pos is None:
            return

        diff = e.globalPosition().toPoint() - self._drag_pos
        geo  = QRect(self._start_geo)

        if self._resizing:
            if "right"  in self._resizing: geo.setRight(self._start_geo.right()   + diff.x())
            if "left"   in self._resizing: geo.setLeft(self._start_geo.left()     + diff.x())
            if "bottom" in self._resizing: geo.setBottom(self._start_geo.bottom() + diff.y())
            if "top"    in self._resizing: geo.setTop(self._start_geo.top()       + diff.y())
            if geo.width() >= 320 and geo.height() >= 180:
                self.setGeometry(geo)
        else:
            self.move(self._start_geo.topLeft() + diff)

        self._update_cursor(local_pos) 

class ClickThroughToggle(QWidget):
    """Маленькая кнопка-переключатель click-through режима.
       Живёт отдельным окном — всегда кликабельна."""

    def __init__(self, player: "PlayerView"):
        super().__init__()
        self._player   = player
        self._active   = False
        self._drag_pos = None

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(32, 72)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        # Иконка курсора — показывает режим
        self._btn = QPushButton("🖱")
        self._btn.setFixedSize(28, 28)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setCheckable(True)
        self._btn.setToolTip("Click-through режим (мышь сквозь плеер)")
        self._btn.clicked.connect(self._toggle)
        self._btn.setStyleSheet("""
            QPushButton {
                background: rgba(30,30,30,200);
                color: #aaa;
                border: 1px solid rgba(255,255,255,20);
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover { background: rgba(50,50,50,220); color: white; }
            QPushButton:checked {
                background: rgba(0,120,215,200);
                color: white;
                border-color: #0078d7;
            }
        """)

        # Маленький индикатор
        self._dot = QLabel("●")
        self._dot.setAlignment(Qt.AlignCenter)
        self._dot.setFont(QFont("Segoe UI", 7))
        self._dot.setStyleSheet("color: #555; background:transparent; border:none;")

        lay.addWidget(self._btn, 0, Qt.AlignHCenter)
        lay.addWidget(self._dot, 0, Qt.AlignHCenter)

    def _toggle(self):
        self._active = self._btn.isChecked()
        try:
            from app.core.window_manager import set_click_through
            set_click_through(int(self._player.winId()), self._active)
        except Exception as e:
            print(f"[click-through] {e}")

        self._dot.setText("●")
        self._dot.setStyleSheet(
            f"color: {'#0078d7' if self._active else '#555'};"
            " background:transparent; border:none;"
        )
        self._btn.setToolTip(
            "Click-through ВКЛЮЧЁН (нажми чтобы выключить)"
            if self._active else
            "Click-through режим (мышь сквозь плеер)"
        )

    def reposition(self, player_geo):
        """Прилипаем к левому краю плеера по центру."""
        x = player_geo.left() - self.width() - 4
        y = player_geo.top() + (player_geo.height() - self.height()) // 2
        self.move(x, y)

    # Перетаскивание самой кнопки если надо
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
