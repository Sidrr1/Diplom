"""
Встроенный WebView2-браузер для плеера EdgeTools.

Запускает отдельный процесс pywebview, встраивает HWND в Qt-контейнер,
обменивается командами через локальный TCP-сокет (IPC).
"""
import os
import sys
import json
import socket
import threading
import subprocess
import ctypes

from PySide6.QtCore import QObject, QTimer, Signal

user32 = ctypes.windll.user32

# Win32-стили окна для embed (дочернее окно без рамки)
GWL_STYLE = -16
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_BORDER = 0x00800000
WS_THICKFRAME = 0x00040000


class WebViewBrowser(QObject):
    """
    Менеджер subprocess WebView2 + Win32 embed + IPC.

    Сигналы:
        stream_found — перехвачен .m3u8/.mp4 из JS-хуков страницы
        url_changed — навигация (JSON с url и title)
        embedded — HWND успешно встроен в container
    """

    stream_found = Signal(str)
    url_changed = Signal(str)
    embedded = Signal()

    DEFAULT_TITLE = "_EdgeToolsBrowser_"

    def __init__(
        self,
        container,
        *,
        profile_path: str = "",
        window_title: str = "",
    ):
        """
        Args:
            container: Qt-виджет-родитель для SetParent (нативное окно)
            profile_path: папка профиля WebView2 (cookies, сессии)
            window_title: заголовок окна subprocess для FindWindowW
        """
        super().__init__()
        self._container = container
        self._profile_path = profile_path or ""
        self._window_title = window_title or self.DEFAULT_TITLE
        self._proc = None
        self._hwnd = None
        self._server = None
        self._conn = None
        self._port = 0
        self._started = False
        self._embedded = False
        self._visible = False
        self._last_url = None
        self._found = set()
        self._all_procs = []

        self._find_timer = QTimer(self)
        self._find_timer.setInterval(200)
        self._find_timer.timeout.connect(self._try_embed)

        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(150)
        self._sync_timer.timeout.connect(self._sync)

    def start(self, url: str = "https://www.google.com", profile_path: str = "") -> bool:
        """
        Запустить subprocess и начать поиск HWND для embed.

        Returns:
            False, если профиль занят или profile_path пуст.
        """
        if profile_path:
            self._profile_path = profile_path
        if not self._profile_path:
            print("[webview] profile_path required")
            return False

        if self._proc and self._proc.poll() is None:
            self.navigate(url)
            return True
        if self._started and self._proc:
            return True

        from app.core.webview_registry import (
            claim_profile,
            is_profile_in_use,
            release_profile,
            terminate_webview_processes_for_profile,
        )
        from app.features.accounts.account_login_window import AccountLoginWindow

        AccountLoginWindow.force_reset_stale()
        terminate_webview_processes_for_profile(self._profile_path)
        import time
        time.sleep(0.3)

        if is_profile_in_use(self._profile_path):
            release_profile(self._profile_path)

        if not claim_profile(self._profile_path):
            print("[webview] profile busy, skip start")
            return False

        self._started = True
        if not self._server:
            self._start_server()
        self._start_process(url)
        self._find_timer.start()
        return True

    def show_browser(self):
        """Показать встроенное окно и синхронизировать размер с container."""
        self._visible = True
        if self._embedded and self._hwnd:
            user32.ShowWindow(self._hwnd, 5)
            self._sync()
            self._sync_timer.start()

    def hide_browser(self):
        """Скрыть HWND и остановить таймер синхронизации геометрии."""
        self._visible = False
        self._sync_timer.stop()
        if self._hwnd:
            user32.ShowWindow(self._hwnd, 0)

    def sync_geometry(self):
        """Подогнать размер/позицию HWND под container (MoveWindow)."""
        self._sync()

    def run_when_connected(self, cmd: dict, retries: int = 60, interval_ms: int = 250):
        """
        Отправить IPC-команду, когда сокет подключён (с повторами).

        Args:
            cmd: dict с полем action (navigate, back, reload, close)
        """
        def attempt(left: int):
            if self._conn:
                self._send(cmd)
                return
            if left <= 0:
                print(f"[webview] IPC timeout: {cmd.get('action')}")
                return
            QTimer.singleShot(interval_ms, lambda: attempt(left - 1))

        attempt(retries)

    def navigate(self, url: str):
        """IPC: загрузить URL в subprocess."""
        self.run_when_connected({"action": "navigate", "url": url})

    def go_back(self):
        """IPC: history.back() в subprocess."""
        self.run_when_connected({"action": "back"})

    def go_forward(self):
        """IPC: history.forward() в subprocess."""
        self.run_when_connected({"action": "forward"})

    def reload(self):
        """IPC: location.reload() в subprocess."""
        self.run_when_connected({"action": "reload"})

    def re_embed(self):
        """Перезапустить subprocess (после смены режима или сбоя embed)."""
        if not self._started:
            return
        last_url = self._last_url or "https://www.youtube.com"

        self._sync_timer.stop()
        self._find_timer.stop()

        if self._proc:
            self._terminate_proc(self._proc)
            self._proc = None

        self._cleanup_zombies()

        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

        self._hwnd = None
        self._embedded = False

        import time
        time.sleep(0.5)

        self._start_process(last_url)
        self._find_timer.start()

    def _terminate_proc(self, proc) -> None:
        if not proc or proc.poll() is not None:
            return
        self._send({"action": "close"})
        try:
            from app.core.webview_registry import kill_process_tree
            kill_process_tree(proc.pid)
        except Exception as e:
            print(f"[webview] kill tree: {e}")
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    def _cleanup_zombies(self):
        for proc in self._all_procs:
            self._terminate_proc(proc)
        self._all_procs = []

    def _stop_server(self):
        srv = self._server
        self._server = None
        if not srv:
            return
        try:
            srv.close()
        except Exception:
            pass

    def destroy(self):
        """Полная остановка: subprocess, IPC, освобождение профиля."""
        print("[webview] destroy")
        self._find_timer.stop()
        self._sync_timer.stop()
        self._visible = False

        if self._hwnd:
            try:
                user32.ShowWindow(self._hwnd, 0)
            except Exception:
                pass

        self._send({"action": "close"})

        if self._proc:
            self._terminate_proc(self._proc)
        self._cleanup_zombies()
        self._proc = None

        if self._profile_path:
            from app.core.webview_registry import (
                release_profile,
                terminate_webview_processes_for_profile,
            )
            terminate_webview_processes_for_profile(self._profile_path)
            release_profile(self._profile_path)

        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

        self._stop_server()

        self._hwnd = None
        self._embedded = False
        self._started = False

    def _start_server(self):
        """Локальный TCP-сервер для приёма подключения от webview_process."""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._port = self._server.getsockname()[1]
        self._server.listen(5)
        print(f"[webview] server :{self._port}")
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while True:
            try:
                conn, _ = self._server.accept()
                if self._conn:
                    try:
                        self._conn.close()
                    except Exception:
                        pass
                self._conn = conn
                print("[webview] connected")
                threading.Thread(
                    target=self._read_loop,
                    args=(conn,),
                    daemon=True,
                ).start()
            except Exception as e:
                print(f"[webview] accept loop ended: {e}")
                break

    def _read_loop(self, conn):
        buf = ""
        while True:
            try:
                data = conn.recv(4096).decode()
                if not data:
                    break
                buf += data
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        self._handle(json.loads(line))
            except Exception as e:
                print(f"[webview] read: {e}")
                break

    def _handle(self, msg: dict):
        """Разбор JSON-событий от subprocess (url_changed, stream_found)."""
        ev, data = msg.get("event"), msg.get("data", "")
        if ev == "url_changed":
            url, title = data, ""
            if isinstance(data, str) and data.startswith("{"):
                try:
                    payload = json.loads(data)
                    url = payload.get("url", "") or ""
                    title = payload.get("title", "") or ""
                except json.JSONDecodeError:
                    url = data
            else:
                url = data or ""
            self._last_url = url
            self.url_changed.emit(
                json.dumps({"url": url, "title": title}, ensure_ascii=False)
            )
        elif ev == "stream_found":
            if data and data not in self._found:
                self._found.add(data)
                print(f"[webview] stream: {data[:80]}")
                self.stream_found.emit(data)

    def _send(self, cmd: dict):
        if not self._conn:
            return
        try:
            self._conn.sendall((json.dumps(cmd) + "\n").encode())
        except Exception:
            pass

    def _start_process(self, url: str):
        """Popen webview_process.py с портом IPC и путём профиля."""
        from app.core.paths import project_root

        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "webview_process.py"
        )
        profile = os.path.abspath(self._profile_path)
        args = [
            sys.executable,
            script,
            str(self._port),
            url,
            profile,
            "embed",
            self._window_title,
        ]
        kwargs = {"cwd": project_root()}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000
        proc = subprocess.Popen(args, **kwargs)
        self._proc = proc
        self._all_procs.append(proc)
        print(f"[webview] pid={proc.pid} profile={self._profile_path}")

    def _try_embed(self):
        """FindWindowW + SetParent: встроить HWND браузера в Qt container."""
        hwnd = user32.FindWindowW(None, self._window_title)
        if not hwnd:
            return
        w = max(self._container.width(), 0)
        h = max(self._container.height(), 0)
        if w < 80 or h < 80:
            return

        self._find_timer.stop()
        self._hwnd = hwnd
        parent = int(self._container.winId())
        user32.SetParent(self._hwnd, parent)
        style = user32.GetWindowLongW(self._hwnd, GWL_STYLE)
        style = (
            (style & ~WS_POPUP & ~WS_CAPTION & ~WS_BORDER & ~WS_THICKFRAME)
            | WS_CHILD
        )
        user32.SetWindowLongW(self._hwnd, GWL_STYLE, style)
        self._embedded = True
        if self._visible:
            user32.ShowWindow(self._hwnd, 5)
            self._sync()
            self._sync_timer.start()
        else:
            user32.ShowWindow(self._hwnd, 0)
        print("[webview] embedded")
        self.embedded.emit()

    def _sync(self):
        if not self._hwnd or not self._container:
            return
        try:
            user32.MoveWindow(
                self._hwnd,
                0,
                0,
                self._container.width(),
                self._container.height(),
                True,
            )
        except Exception as e:
            print(f"[webview] sync: {e}")
