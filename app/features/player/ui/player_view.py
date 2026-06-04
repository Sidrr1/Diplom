# app/ui/player_view.py
import os
import sys

_project_root = os.path.dirname(  # Diplom/
    os.path.dirname(               # app/
        os.path.dirname(           # features/
            os.path.dirname(       # player/
                os.path.dirname(   # ui/
                    os.path.abspath(__file__)
                )
            )
        )
    )
)
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
    QComboBox, QLabel, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal, QRect, QTimer, QEvent
from PySide6.QtGui import QFont, QIcon

from app.features.player.core.webview_browser import WebViewBrowser


class PlayerView(QWidget):
    play_requested = Signal(str)
    url_changed    = Signal(str)

    def __init__(self, settings: dict = None):
        super().__init__()
        self._settings     = settings or {}
        self._resizing     = None
        self._drag_pos     = None
        self._start_geo    = None
        self._border       = 8
        self._mpv          = None
        self._mpv_alive    = False
        self._browser      = None
        self._browser_init = False

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(2500)
        self._hide_timer.timeout.connect(self._hide_controls)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(320, 180)
        self.resize(560, 340)
        self.setMouseTracking(True)
        self.setWindowOpacity(self._settings.get("player_opacity", 100) / 100)
        self._set_window_icon()

        self._build_ui()
        self._ct_toggle  = ClickThroughToggle(self)
        self._cfg_toggle = SettingsToggle(self, tab="player")
        self._move_to_corner()
        self.setAcceptDrops(True)

    def _set_window_icon(self):
        assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
        self.setWindowIcon(QIcon(os.path.join(assets, "player.jpeg")))

    # ── UI ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        self._card = self._make_card()
        root.addWidget(self._card)
        self._install_event_filters()

    def _make_card(self) -> QFrame:
        card = QFrame(); card.setObjectName("playerCard")
        card.setStyleSheet("""
            QFrame#playerCard { background:#000; border-radius:12px;
                                border:1px solid rgba(255,255,255,15); }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)

        from PySide6.QtWidgets import QStackedWidget
        self._view_stack = QStackedWidget()
        self._view_stack.addWidget(self._make_browser_area())  # 0
        self._view_stack.addWidget(self._make_video_frame())   # 1
        lay.addWidget(self._view_stack, stretch=1)

        # MPV контролы — показываются только в MPV режиме
        self._controls_widget = self._make_controls()
        lay.addWidget(self._controls_widget)
        self._make_show_progress_btn(card)
        return card

    def _make_video_frame(self) -> QFrame:
        self._video_frame = QFrame()
        self._video_frame.setStyleSheet("background:#000; border:none;")
        self._video_frame.setMouseTracking(True)
        return self._video_frame

    def _make_browser_area(self) -> QWidget:
        outer = QWidget()
        outer.setStyleSheet("background:#0a0a0a;")
        lay = QVBoxLayout(outer)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)

        # ── Навигационная панель браузера ─────────────────────────────────
        nav_frame = QFrame()
        nav_frame.setStyleSheet("""
            QFrame { background:#111; border-bottom:1px solid rgba(255,255,255,10); }
        """)
        nav = QHBoxLayout(nav_frame)
        nav.setContentsMargins(8, 5, 8, 5); nav.setSpacing(5)

        btn_back   = self._icon_btn("◀", 26)
        btn_fwd    = self._icon_btn("▶", 26)
        btn_reload = self._icon_btn("↺", 26, tooltip="Обновить")

        # Умная строка поиска/навигации
        self._browser_url = QLineEdit()
        self._browser_url.setPlaceholderText("🔍  Поиск или адрес сайта...")
        self._browser_url.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,8);
                color: white;
                border: 1px solid rgba(255,255,255,15);
                border-radius: 14px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #0078d7; background: rgba(255,255,255,12); }
        """)
        self._browser_url.returnPressed.connect(self._browser_search_or_navigate)

        # Переключатель режима + закрытие — прямо в навбаре
        self._btn_to_mpv = self._icon_btn("📺", 26, tooltip="Переключить в плеер MPV")
        self._btn_to_mpv.clicked.connect(self._switch_to_mpv_mode)

        btn_close_browser = self._icon_btn("✕", 26)
        btn_close_browser.setStyleSheet(
            btn_close_browser.styleSheet() +
            "QPushButton:hover{background:rgba(192,57,43,150);}"
        )
        btn_close_browser.clicked.connect(self.close)

        nav.addWidget(btn_back)
        nav.addWidget(btn_fwd)
        nav.addWidget(btn_reload)
        nav.addWidget(self._browser_url, stretch=1)
        nav.addWidget(self._btn_to_mpv)
        nav.addWidget(btn_close_browser)

        from app.core.paths import auth_profile_dir

        self._browser_stack = QStackedWidget()
        hint_page = QWidget()
        hint_page.setStyleSheet("background:#111;")
        hint_lay = QVBoxLayout(hint_page)
        hint_lay.setAlignment(Qt.AlignCenter)
        self._browser_hint = QLabel("Браузер загружается…")
        self._browser_hint.setStyleSheet("color:rgba(255,255,255,50);font-size:11px;")
        hint_lay.addWidget(self._browser_hint)

        self._webview_container = QWidget()
        self._webview_container.setAttribute(Qt.WA_NativeWindow, True)
        self._webview_container.setStyleSheet("background:#111;")

        self._browser_stack.addWidget(hint_page)
        self._browser_stack.addWidget(self._webview_container)

        google_profile = auth_profile_dir("google")
        self._browser = WebViewBrowser(
            self._webview_container,
            profile_path=google_profile,
        )
        self._browser.stream_found.connect(self._on_stream_found)
        self._browser.url_changed.connect(self._on_browser_url_changed)
        self._browser.embedded.connect(self._on_browser_embedded)
        self._auth_paused = False

        btn_back.clicked.connect(lambda: self._browser.go_back())
        btn_fwd.clicked.connect(lambda: self._browser.go_forward())
        btn_reload.clicked.connect(lambda: self._browser.reload())

        lay.addWidget(nav_frame)
        lay.addWidget(self._browser_stack, stretch=1)
        return outer

    def _browser_search_or_navigate(self):
        """Умный поиск: URL → навигация, текст → поиск в Google."""
        text = self._browser_url.text().strip()
        if not text:
            return
        self._ensure_browser_started()

        # Определяем URL или поисковый запрос
        is_url = (
            text.startswith("http://") or
            text.startswith("https://") or
            ("." in text and " " not in text and len(text) > 4)
        )
        if is_url:
            url = text if text.startswith("http") else "https://" + text
        else:
            import urllib.parse
            url = "https://www.google.com/search?q=" + urllib.parse.quote(text)

        self._browser.navigate(url)

    def _switch_to_mpv_mode(self):
        self._view_stack.setCurrentIndex(1)
        self._controls_widget.setVisible(True)
        self._browser.hide_browser()

    def _on_browser_embedded(self):
        if hasattr(self, "_browser_stack"):
            self._browser_stack.setCurrentWidget(self._webview_container)
        self._browser.show_browser()
        self._browser.sync_geometry()

    def pause_webview_for_auth(self):
        self._auth_paused = True
        if self._browser_init:
            self._browser.destroy()
            self._browser_init = False
            if hasattr(self, "_browser_stack"):
                self._browser_stack.setCurrentIndex(0)

    def resume_webview_after_auth(self):
        self._auth_paused = False
        if self._view_stack.currentIndex() != 0:
            return
        self._restart_browser_after_auth()

    def _restart_browser_after_auth(self):
        from app.core.paths import auth_profile_dir
        from app.core.webview_registry import release_profile, terminate_webview_processes_for_profile
        from app.features.accounts.account_login_window import AccountLoginWindow

        AccountLoginWindow.force_reset_stale()
        path = auth_profile_dir("google")
        terminate_webview_processes_for_profile(path)
        release_profile(path)

        if self._browser_init:
            self._browser.destroy()
            self._browser_init = False

        if hasattr(self, "_browser_stack"):
            self._browser_stack.setCurrentIndex(0)
            self._browser_hint.setText("Браузер загружается…")
            self._browser_hint.setVisible(True)

        self._ensure_browser_started()
        if self._browser_init:
            QTimer.singleShot(200, self._browser.show_browser)

    def _ensure_browser_started(self):
        from app.features.accounts.account_login_window import AccountLoginWindow

        if AccountLoginWindow.is_active():
            if hasattr(self, "_browser_hint"):
                self._browser_hint.setText(
                    "Закройте окно входа в аккаунт, затем снова откройте браузер."
                )
                if hasattr(self, "_browser_stack"):
                    self._browser_stack.setCurrentIndex(0)
            return

        self._auth_paused = False
        if self._browser_init and self._browser._proc and self._browser._proc.poll() is None:
            return
        if self._browser_init:
            self._browser.destroy()
            self._browser_init = False

        from app.core.paths import auth_profile_dir

        if self._browser.start(
            "https://www.youtube.com",
            profile_path=auth_profile_dir("google"),
        ):
            self._browser_init = True
        elif hasattr(self, "_browser_hint"):
            self._browser_hint.setText(
                "Браузер недоступен: профиль занят.\n"
                "Закройте окно входа или перезапустите EdgeTools."
            )
            if hasattr(self, "_browser_stack"):
                self._browser_stack.setCurrentIndex(0)

    def _on_stream_found(self, url: str):
        self.play_requested.emit(url)

    def _on_browser_url_changed(self, payload: str):
        url, title = payload, ""
        if payload and payload.startswith("{"):
            try:
                import json
                data = json.loads(payload)
                url = data.get("url", "") or ""
                title = data.get("title", "") or ""
            except json.JSONDecodeError:
                url = payload
        else:
            url = payload or ""
        if url:
            self._browser_url.setText(url)
            if hasattr(self, "_browser_stack"):
                self._browser_stack.setCurrentWidget(self._webview_container)
            self._browser_hint.setVisible(False)
            try:
                from app.core.database import db
                db.add_web_history(url, title)
            except Exception as e:
                print(f"[player] web history: {e}")
        self.url_changed.emit(url)

    # ── MPV Controls (только в MPV режиме) ───────────────────────────────

    def _make_controls(self) -> QFrame:
        panel = QFrame(); panel.setObjectName("controls")
        panel.setStyleSheet("""
            QFrame#controls {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 rgba(0,0,0,0), stop:1 rgba(0,0,0,210));
                border:none; border-radius:0 0 12px 12px;
            }
        """)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 6, 10, 8); lay.setSpacing(4)
        lay.addWidget(self._make_progress_row())
        lay.addLayout(self._make_bottom_row())
        self._controls = panel
        return panel

    def _make_progress_row(self) -> QWidget:
        self._progress_row = QWidget()
        row = QHBoxLayout(self._progress_row)
        row.setContentsMargins(0, 0, 0, 0); row.setSpacing(6)
        self._lbl_cur = self._make_time_label()
        self._progress = self._make_progress_slider()
        self._lbl_dur = self._make_time_label()
        self._btn_hide_progress = self._icon_btn("▾", 22, tooltip="Скрыть хронометраж")
        self._btn_hide_progress.clicked.connect(self._toggle_progress)
        row.addWidget(self._lbl_cur); row.addWidget(self._progress, stretch=1)
        row.addWidget(self._lbl_dur); row.addWidget(self._btn_hide_progress)
        return self._progress_row

    def _make_time_label(self) -> QLabel:
        lbl = QLabel("0:00"); lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet("color:rgba(255,255,255,160); min-width:32px;")
        return lbl

    def _make_progress_slider(self) -> QSlider:
        s = QSlider(Qt.Horizontal); s.setRange(0, 1000)
        s.setStyleSheet(self._slider_style("#0078d7"))
        s.sliderPressed.connect(lambda: setattr(self, '_slider_dragging', True))
        s.sliderReleased.connect(self._on_slider_released)
        return s

    def _on_slider_released(self):
        self._slider_dragging = False
        self._seek(self._progress.value())

    def _make_bottom_row(self) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(6)
        row.addWidget(self._make_play_btn())
        row.addWidget(self._make_browser_toggle_btn())
        row.addWidget(self._make_url_input(), stretch=1)
        row.addWidget(self._make_volume_btn())
        row.addWidget(self._make_volume_row())
        row.addWidget(self._make_quality_combo())
        row.addWidget(self._make_close_btn())
        return row

    def _make_play_btn(self) -> QPushButton:
        self._btn_play = self._icon_btn("▶", 32)
        self._btn_play.clicked.connect(self._toggle_play)
        return self._btn_play

    def _make_browser_toggle_btn(self) -> QPushButton:
        self._btn_browser_toggle = self._icon_btn("🌐", 28, tooltip="Режим браузера")
        self._btn_browser_toggle.clicked.connect(self._switch_to_browser_mode)
        return self._btn_browser_toggle

    def _switch_to_browser_mode(self):
        self._auth_paused = False
        self._view_stack.setCurrentIndex(0)
        self._controls_widget.setVisible(False)
        self._restart_browser_after_auth()

    def on_login_window_closed(self, _ok: bool = False):
        """После закрытия окна входа — сбросить паузу и перезапустить webview."""
        self._auth_paused = False
        if self._view_stack.currentIndex() == 0:
            self._restart_browser_after_auth()

    def _make_url_input(self) -> QLineEdit:
        self._input_url = QLineEdit()
        self._input_url.setPlaceholderText("Ссылка или файл → Enter (MPV/yt-dlp)")
        self._input_url.setStyleSheet("""
            QLineEdit { background:rgba(255,255,255,12); color:white;
                        border:1px solid rgba(255,255,255,20); border-radius:6px;
                        padding:4px 8px; font-size:12px; }
            QLineEdit:focus { border-color:#0078d7; }
        """)
        self._input_url.returnPressed.connect(self._on_play_clicked)
        return self._input_url

    def _make_volume_btn(self) -> QPushButton:
        self._btn_vol = self._icon_btn("🔊", 28)
        self._btn_vol.clicked.connect(self._toggle_volume_row)
        return self._btn_vol

    def _make_volume_row(self) -> QWidget:
        self._vol_row = QWidget()
        lay = QHBoxLayout(self._vol_row)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(4)
        self._volume = QSlider(Qt.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(self._settings.get("player_volume", 70))
        self._volume.setFixedWidth(70)
        self._volume.setStyleSheet(self._slider_style("#aaa"))
        self._volume.valueChanged.connect(self._set_volume)
        lay.addWidget(self._volume)
        self._vol_row.setVisible(False)
        return self._vol_row

    def _make_quality_combo(self) -> QComboBox:
        self._combo_quality = QComboBox()
        self._combo_quality.addItems(["Авто", "1080p", "720p", "480p", "360p"])
        idx = self._combo_quality.findText(self._settings.get("player_quality", "Авто"))
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
        return self._combo_quality

    def _make_close_btn(self) -> QPushButton:
        self._btn_close = self._icon_btn("✕", 28)
        self._btn_close.setStyleSheet(
            self._btn_close.styleSheet() + "QPushButton:hover{background:rgba(192,57,43,150);}")
        self._btn_close.clicked.connect(self.close)
        return self._btn_close

    def _make_show_progress_btn(self, parent: QFrame):
        self._btn_show_progress = QPushButton("▴  хронометраж")
        self._btn_show_progress.setParent(parent)
        self._btn_show_progress.setCursor(Qt.PointingHandCursor)
        self._btn_show_progress.setFixedHeight(22)
        self._btn_show_progress.setFont(QFont("Segoe UI", 8))
        self._btn_show_progress.setStyleSheet("""
            QPushButton { background:rgba(0,0,0,140); color:rgba(255,255,255,140);
                          border:1px solid rgba(255,255,255,20); border-radius:10px; padding:0 10px; }
            QPushButton:hover { background:rgba(0,120,215,160); color:white; }
        """)
        self._btn_show_progress.setVisible(False)
        self._btn_show_progress.clicked.connect(self._toggle_progress)

    def _install_event_filters(self):
        self._video_frame.installEventFilter(self)
        self._controls.installEventFilter(self)

    # ── MPV ──────────────────────────────────────────────────────────────

    def _ensure_mpv(self) -> bool:
        if self._mpv_alive: return True
        if not MPV_AVAILABLE: return False
        try:
            self._mpv = mpv.MPV(
            wid=str(int(self._video_frame.winId())),
            vo="gpu", hwdec="auto",
            keep_open=True, ytdl=False, hr_seek="yes",
            cache=True,
            demuxer_max_bytes="500MiB",       # ← было 200
            demuxer_readahead_secs=60,        # ← было 30
            demuxer_max_back_bytes="100MiB",  # ← новый: держим буфер назад для перемотки
            stream_lavf_o="reconnect=1,reconnect_streamed=1,reconnect_delay_max=5",
            audio_client_name="edgetools",
            video_sync="audio",               # ← синхронизация видео по аудио
            interpolation=False,
        )
            self._mpv.observe_property("time-pos",        self._on_time_pos)
            self._mpv.observe_property("duration",         self._on_duration)
            self._mpv.observe_property("paused-for-cache", self._on_buffering)
            self._mpv_alive    = True
            self._seek_pos     = None
            self._is_seeking   = False
            self._last_video_url = ""
            self._last_audio_url = ""

            self._seek_watchdog = QTimer(self)
            self._seek_watchdog.setSingleShot(True)
            self._seek_watchdog.setInterval(30000)
            self._seek_watchdog.timeout.connect(self._on_seek_timeout)

            QTimer.singleShot(200, self._set_initial_volume)
            return True
        except Exception as e:
            print(f"[mpv] init: {e}"); return False

    def _set_initial_volume(self):
        self._mpv_safe(lambda: setattr(self._mpv, "volume", self._settings.get("player_volume", 70)))

    def _mpv_safe(self, func):
        if not self._mpv_alive: return None
        try: return func()
        except Exception: self._mpv_alive = False; return None

    def _mpv_try(self, func) -> bool:
        if not self._mpv_alive:
            return False
        try:
            func()
            return True
        except Exception:
            self._mpv_alive = False
            return False

    def _on_time_pos(self, _name, value):
        if value is None or not self._mpv_alive: return
        if getattr(self, '_slider_dragging', False): return  # не двигаем пока тащим
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

    def _on_buffering(self, _name, value):
        # MPV колбэки идут из другого треда — диспатчим в Qt
        QTimer.singleShot(0, lambda: self._on_buffering_main(value))

    def _on_buffering_main(self, value: bool):
        if not self._is_seeking:
            return
        if value:
            print(f"[mpv] buffering (seek)... pos={self._seek_pos}")
            if self._seek_pos is not None and not self._seek_watchdog.isActive():
                self._seek_watchdog.start()
        else:
            print("[mpv] buffering done (seek)")
            if self._seek_pos is None:
                return
            try:
                current = self._mpv.time_pos
                if current is not None and abs(current - self._seek_pos) < 3.0:
                    print(f"[mpv] seek reached target {self._seek_pos:.1f}s")
                    self._seek_pos = None
                    self._is_seeking = False
                    QTimer.singleShot(0, self._seek_watchdog.stop)
            except Exception:
                pass

    def _on_seek_timeout(self):
        """Только для одиночного потока (без split)."""
        if not self._mpv_alive or self._seek_pos is None:
            return
        if self._last_audio_url:
            pos = self._seek_pos
            self._seek_pos = None
            self._is_seeking = False
            QTimer.singleShot(0, self._seek_watchdog.stop)
            url = self._original_url
            if url:
                print(f"[mpv] split seek timeout -> 720p extract at {pos:.1f}s")
                self.set_loading(True)
                self.play_requested.emit(f"__seek__{url}__at__{pos:.1f}")
            return
        try:
            current = self._mpv.time_pos
            if current is not None and abs(current - self._seek_pos) < 3.0:
                print("[mpv] seek_timeout but position is close enough, cancelling")
                self._seek_pos = None
                self._is_seeking = False
                QTimer.singleShot(0, self._seek_watchdog.stop)
                return
        except Exception:
            pass
        pos = self._seek_pos
        self._seek_pos = None
        self._is_seeking = False
        url = self._original_url
        print(f"[mpv] seek hung at {pos:.1f}s — reloading via yt-dlp")
        if url:
            self.play_requested.emit(f"__seek__{url}__at__{pos:.1f}")

    def play(self, video_url: str, audio_url: str = "", original_url: str = "", start_pos: float = 0.0):
        self._original_url = original_url or video_url
        if not self._ensure_mpv(): self.show_error("MPV недоступен"); return
        QTimer.singleShot(100, lambda: self._do_play(video_url, audio_url, start_pos))

    def _mpv_load(self, video_url: str, audio_url: str, start_pos: float = 0.0):
        start_sec = max(0, int(round(start_pos)))
        self._pending_load_seek = None
        if audio_url:
            options = f"audio-file={audio_url},audio-sync=display-resample"
            if start_sec > 0:
                options += f",start={start_sec}"
            self._mpv.command("loadfile", video_url, "replace", 0, options)
        elif start_sec > 0:
            # Единый HTTP: start= на googlevideo часто замирает кадр — seek после load
            self._pending_load_seek = start_pos
            self._mpv.command("loadfile", video_url, "replace")
        else:
            self._mpv.command("loadfile", video_url, "replace")

    def _do_play(self, video_url: str, audio_url: str, start_pos: float = 0.0):
        try:
            self._seek_pos = None
            self._is_seeking = False
            if hasattr(self, "_seek_watchdog"):
                self._seek_watchdog.stop()

            self._last_video_url = video_url
            self._last_audio_url = audio_url or ""
            self._mpv_load(video_url, self._last_audio_url, start_pos)

            pending = getattr(self, "_pending_load_seek", None)
            if pending is not None:
                self._pending_load_seek = None
                def _apply_start(p=pending):
                    if self._mpv_try(lambda: self._mpv.seek(p, "absolute")):
                        print(f"[mpv] post-load seek to {p:.1f}s")
                QTimer.singleShot(400, _apply_start)

            self._btn_play.setText("⏸")
            self._hide_timer.start()
        except Exception as e:
            print(f"[mpv] play: {e}"); self._mpv_alive = False

    def _reload_at_position(self, pos: float):
        """Split streams: loadfile с start= (mpv.seek на два HTTP-потока не работает)."""
        if not self._mpv_alive or not self._last_video_url:
            return
        try:
            print(f"[mpv] reload at {pos:.1f}s")
            self._mpv_load(self._last_video_url, self._last_audio_url, pos)
            self._seek_pos = None
            self._is_seeking = False
            QTimer.singleShot(0, self._seek_watchdog.stop)
            self._mpv.pause = False
            self._btn_play.setText("⏸")
        except Exception as e:
            print(f"[mpv] reload failed: {e}")

    def _toggle_play(self):
        if not self._mpv_alive: self._on_play_clicked(); return
        try:
            self._mpv.pause = not self._mpv.pause
            self._btn_play.setText("▶" if self._mpv.pause else "⏸")
        except Exception:
            self._mpv_alive = False; self._btn_play.setText("▶")

    def _seek(self, val: int):
        if not self._mpv_alive:
            return
        try:
            dur = self._mpv.duration
            if not dur:
                return
            pos = val / 1000 * dur
            print(f"[mpv] seeking to {pos:.1f}s")

            if self._last_audio_url:
                url = self._original_url
                if url and url.startswith("http"):
                    print(f"[mpv] split — seek muxed reload at {pos:.1f}s")
                    self.set_loading(True)
                    self._btn_play.setText("…")
                    self.play_requested.emit(f"__seek__{url}__at__{pos:.1f}")
                    return
                QTimer.singleShot(0, lambda p=pos: self._reload_at_position(p))
                return

            self._seek_pos = pos
            self._is_seeking = True
            if not self._mpv_try(lambda: self._mpv.seek(pos, "absolute")):
                url = self._original_url
                if url:
                    self.play_requested.emit(f"__seek__{url}__at__{pos:.1f}")
                return
            self._seek_watchdog.start()
        except Exception:
            self._mpv_alive = False

    def _set_volume(self, val: int):
        self._mpv_safe(lambda: setattr(self._mpv, "volume", val))

    # ── Прогресс / громкость ─────────────────────────────────────────────

    def _toggle_progress(self):
        visible = self._progress_row.isVisible()
        self._progress_row.setVisible(not visible)
        self._btn_show_progress.setVisible(visible)
        if visible: self._reposition_show_btn()

    def _reposition_show_btn(self):
        btn = self._btn_show_progress; btn.adjustSize()
        btn.move((self._card.width() - btn.width()) // 2, self._card.height() - btn.height() - 6)
        btn.raise_()

    def _toggle_volume_row(self):
        self._vol_row.setVisible(not self._vol_row.isVisible())

    def _show_controls(self):
        if self._view_stack.currentIndex() == 1:  # только в MPV режиме
            self._controls_widget.setVisible(True)
            self._hide_timer.start()

    def _hide_controls(self):
        if not self._mpv_alive: return
        try:
            if not self._mpv.pause: self._controls_widget.setVisible(False)
        except Exception: self._mpv_alive = False

    # ── Настройки ────────────────────────────────────────────────────────

    def _open_settings(self, tab: str = "player"):
        from app.features.settings.ui.settings_dialog import SettingsDialog
        d = SettingsDialog(initial_tab=tab)
        d.settings_changed.connect(self._apply_settings)
        d.open_auth_browser.connect(self._open_auth_browser)
        d.smart_position(self.geometry())
        d.show()

    def _open_auth_browser(self, service_id: str):
        from app.features.accounts.account_login_window import (
            AccountLoginWindow,
            logout_service,
        )

        if service_id.startswith("__logout_"):
            sid = service_id.replace("__logout_", "", 1)
            logout_service(sid, player_view=self)
            return
        win = AccountLoginWindow(self)
        win.finished.connect(lambda *_: None)
        win.start(service_id, player_view=self, parent_widget=self)

    def _apply_settings(self, cfg: dict):
        self.setWindowOpacity(cfg.get("player_opacity", 100) / 100)
        idx = self._combo_quality.findText(cfg.get("player_quality", "Авто"))
        if idx >= 0: self._combo_quality.setCurrentIndex(idx)

    # ── Публичные методы ─────────────────────────────────────────────────

    def switch_to_mpv(self):
        self._view_stack.setCurrentIndex(1)
        self._controls_widget.setVisible(True)
        self._progress_row.setVisible(True)
        self._btn_play.setVisible(True)
        self._combo_quality.setVisible(True)
        self._btn_vol.setVisible(True)
        self._browser.hide_browser()

    def switch_to_browser(self):
        self._view_stack.setCurrentIndex(0)
        self._controls_widget.setVisible(False)
        self._restart_browser_after_auth()

    def set_loading(self, loading: bool):
        self._btn_play.setEnabled(not loading)
        self._btn_play.setText("…" if loading else "▶")

    def show_error(self, msg: str):
        self._input_url.setPlaceholderText(f"Ошибка: {msg[:60]}")
        self._btn_play.setText("▶"); self._btn_play.setEnabled(True)

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

    # ── События окна ─────────────────────────────────────────────────────

    def showEvent(self, e):
        super().showEvent(e)
        self._ct_toggle.show()
        self._ct_toggle.reposition(self.geometry())
        self._cfg_toggle.show()
        self._cfg_toggle.reposition(self.geometry())
        QTimer.singleShot(100, self._force_topmost)

        if self._view_stack.currentIndex() == 0:
            self._ensure_browser_started()
            QTimer.singleShot(600, self._browser.re_embed)
            QTimer.singleShot(900, self._browser.show_browser)

    def hideEvent(self, e):
        super().hideEvent(e)
        self._browser.hide_browser()

    def moveEvent(self, e):
        super().moveEvent(e)
        if hasattr(self, "_ct_toggle"):
            self._ct_toggle.reposition(self.geometry())
        if hasattr(self, "_cfg_toggle"):
            self._cfg_toggle.reposition(self.geometry())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_ct_toggle"):
            self._ct_toggle.reposition(self.geometry())
        if hasattr(self, "_cfg_toggle"):
            self._cfg_toggle.reposition(self.geometry())
        if self._btn_show_progress.isVisible():
            self._reposition_show_btn()
        if self._browser and self._view_stack.currentIndex() == 0:
            self._browser.sync_geometry()

    def closeEvent(self, e):
        self._hide_timer.stop()
        if hasattr(self, "_ct_toggle"):  self._ct_toggle.hide()
        if hasattr(self, "_cfg_toggle"): self._cfg_toggle.hide()
        self._browser.hide_browser()
        if self._mpv_alive:
            try:
                self._mpv_alive = False
                self._mpv.terminate()
            except Exception: pass
        e.accept()

    def enterEvent(self, e): self._show_controls()
    def leaveEvent(self, e): self._hide_timer.start()

    def eventFilter(self, obj, event):
        if self._view_stack.currentIndex() == 0:
            if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick):
                return False
        if event.type() == QEvent.MouseButtonPress:      self.mousePressEvent(event)
        elif event.type() == QEvent.MouseMove:            self.mouseMoveEvent(event)
        elif event.type() == QEvent.MouseButtonRelease:   self.mouseReleaseEvent(event)
        elif event.type() == QEvent.MouseButtonDblClick:  self.mouseDoubleClickEvent(event)
        return super().eventFilter(obj, event)

    # ── Drag & Drop ───────────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
        else: e.ignore()

    def dragMoveEvent(self, e): e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            local = url.toLocalFile()
            if local and os.path.isfile(local):
                self._input_url.setText(local)
                self.play_requested.emit(local)
                e.acceptProposedAction()
                return
        e.ignore()

    # ── Мышь ─────────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            local = self._to_local(e)
            self._resizing  = self._check_edge(local)
            self._drag_pos  = e.globalPosition().toPoint()
            self._start_geo = self.geometry()
        self._show_controls()

    def mouseMoveEvent(self, e):
        self._show_controls()
        local = self._to_local(e)
        if not e.buttons() & Qt.LeftButton:
            self._update_cursor(local); return
        if self._drag_pos is None: return
        self._apply_mouse_move(e, local)

    def mouseReleaseEvent(self, e):
        self._resizing = None; self._drag_pos = None
        self.setCursor(Qt.ArrowCursor)

    def mouseDoubleClickEvent(self, e):
        if self._view_stack.currentIndex() == 1:
            self._toggle_play()

    def _to_local(self, e):
        try:    return self.mapFromGlobal(e.globalPosition().toPoint())
        except: return e.pos()

    def _apply_mouse_move(self, e, local):
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
        self._update_cursor(local)

    def _check_edge(self, pos):
        r = self.rect(); m = self._border
        l = pos.x() < m; rr = pos.x() > r.width()  - m
        t = pos.y() < m; b  = pos.y() > r.height() - m
        if t and l:  return "top_left"
        if t and rr: return "top_right"
        if b and l:  return "bottom_left"
        if b and rr: return "bottom_right"
        if l: return "left";
        if rr: return "right"
        if t: return "top";
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

    # ── Прочее ───────────────────────────────────────────────────────────

    def _on_play_clicked(self):
        url = self._input_url.text().strip()
        if url: self.play_requested.emit(url)

    def _move_to_corner(self):
        s = QApplication.primaryScreen().availableGeometry()
        self.move(s.width() - self.width() - 20, s.height() - self.height() - 20)

    def _force_topmost(self):
        try:
            import ctypes
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0010)
        except Exception as e:
            print(f"[topmost] {e}")

    @staticmethod
    def _slider_style(color: str) -> str:
        return f"""
            QSlider::groove:horizontal {{ height:3px; background:rgba(255,255,255,30); border-radius:2px; }}
            QSlider::sub-page:horizontal {{ background:{color}; border-radius:2px; }}
            QSlider::handle:horizontal {{ width:12px; height:12px; margin:-5px 0;
                                          background:{color}; border-radius:6px; }}
        """

    @staticmethod
    def _fmt_time(secs) -> str:
        if secs is None: return "0:00"
        s = int(secs); m = s // 60; s %= 60
        return f"{m}:{s:02d}"

    def _icon_btn(self, text: str, size: int = 28, tooltip: str = "") -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(size, size); btn.setCursor(Qt.PointingHandCursor)
        if tooltip: btn.setToolTip(tooltip)
        fs = max(1, size // 2 - 2)
        btn.setStyleSheet(f"""
            QPushButton {{ background:rgba(255,255,255,10); color:white; border:none;
                           border-radius:{size//2}px; font-size:{fs}px; }}
            QPushButton:hover   {{ background:rgba(255,255,255,22); }}
            QPushButton:pressed {{ background:rgba(255,255,255,35); }}
        """)
        return btn


# ── Click-through toggle ──────────────────────────────────────────────────────

class ClickThroughToggle(QWidget):
    def __init__(self, player: "PlayerView"):
        super().__init__()
        self._player = player; self._active = False; self._drag_pos = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(32, 72); self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(4)
        lay.addWidget(self._make_toggle_btn(), 0, Qt.AlignHCenter)
        lay.addWidget(self._make_dot(), 0, Qt.AlignHCenter)

    def _make_toggle_btn(self) -> QPushButton:
        self._btn = QPushButton("🖱"); self._btn.setFixedSize(28, 28)
        self._btn.setCursor(Qt.PointingHandCursor); self._btn.setCheckable(True)
        self._btn.setToolTip("Click-through режим")
        self._btn.clicked.connect(self._toggle)
        self._btn.setStyleSheet("""
            QPushButton { background:rgba(30,30,30,200); color:#aaa;
                          border:1px solid rgba(255,255,255,20); border-radius:8px; font-size:14px; }
            QPushButton:hover   { background:rgba(50,50,50,220); color:white; }
            QPushButton:checked { background:rgba(0,120,215,200); color:white; border-color:#0078d7; }
        """)
        return self._btn

    def _make_dot(self) -> QLabel:
        self._dot = QLabel("●"); self._dot.setAlignment(Qt.AlignCenter)
        self._dot.setFont(QFont("Segoe UI", 7))
        self._dot.setStyleSheet("color:#555; background:transparent; border:none;")
        return self._dot

    def _toggle(self):
        self._active = self._btn.isChecked()
        try:
            from app.core.window_manager import set_click_through
            set_click_through(int(self._player.winId()), self._active)
        except Exception as e: print(f"[click-through] {e}")
        color = "#0078d7" if self._active else "#555"
        self._dot.setStyleSheet(f"color:{color}; background:transparent; border:none;")

    def reposition(self, player_geo):
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        py = player_geo.top() + (player_geo.height() - h) // 2
        for x, y in [
            (player_geo.left() - w - 4, py),
            (player_geo.right() + 4, py),
            (player_geo.left() + (player_geo.width() - w) // 2, player_geo.bottom() + 4),
            (player_geo.left() + (player_geo.width() - w) // 2, player_geo.top() - h - 4),
        ]:
            if x >= screen.left() and x+w <= screen.right() and y >= screen.top() and y+h <= screen.bottom():
                self.move(x, y); return
        self.move(screen.left() + 4, py)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e): self._drag_pos = None


# ── Settings toggle (floating) ────────────────────────────────────────────────

class SettingsToggle(QWidget):
    """Плавающая кнопка настроек — позиционируется рядом с родительским окном."""

    def __init__(self, parent_window, tab: str = "general"):
        super().__init__()
        self._parent_win = parent_window
        self._tab        = tab
        self._drag_pos   = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(32, 32)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("⚙")
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Настройки")
        btn.clicked.connect(self._open)
        btn.setStyleSheet("""
            QPushButton { background:rgba(30,30,30,200); color:#aaa;
                          border:1px solid rgba(255,255,255,20); border-radius:8px;
                          font-size:14px; }
            QPushButton:hover   { background:rgba(50,50,50,220); color:white; }
            QPushButton:pressed { background:rgba(0,120,215,200); color:white; }
        """)
        lay.addWidget(btn, 0, Qt.AlignCenter)

    def _open(self):
        from app.features.settings.ui.settings_dialog import SettingsDialog
        d = SettingsDialog(initial_tab=self._tab)
        pw = self._parent_win
        if hasattr(pw, "_apply_settings"):
            d.settings_changed.connect(pw._apply_settings)
        if hasattr(pw, "_open_auth_browser"):
            d.open_auth_browser.connect(pw._open_auth_browser)
        d.smart_position(pw.geometry())
        d.show()

    def reposition(self, parent_geo):
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()

        ct_h = 72  # высота ClickThroughToggle
        gap  = 6

        candidates_left  = parent_geo.left() - w - 4
        candidates_right = parent_geo.right() + 4
        cy_left  = parent_geo.top() + (parent_geo.height() - ct_h) // 2 + ct_h + gap
        cy_right = cy_left

        candidates = [
            (candidates_left,  cy_left),
            (candidates_right, cy_right),
            (parent_geo.left() + (parent_geo.width() - w) // 2, parent_geo.bottom() + ct_h + gap + 4),
            (parent_geo.left() + (parent_geo.width() - w) // 2, parent_geo.top() - h - 4),
        ]
        for x, y in candidates:
            if (x >= screen.left() and x + w <= screen.right() and
                    y >= screen.top() and y + h <= screen.bottom()):
                self.move(x, y)
                return
        self.move(screen.left() + 4, parent_geo.top() + 80)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e): self._drag_pos = None