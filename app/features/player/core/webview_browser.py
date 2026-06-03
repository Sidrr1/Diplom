# app/features/player/core/webview_browser.py
import os
import sys
import json
import socket
import threading
import subprocess
import ctypes

from PySide6.QtCore import QObject, QTimer, Signal

user32 = ctypes.windll.user32

GWL_STYLE     = -16
WS_CHILD      = 0x40000000
WS_POPUP      = 0x80000000
WS_CAPTION    = 0x00C00000
WS_BORDER     = 0x00800000
WS_THICKFRAME = 0x00040000


class WebViewBrowser(QObject):
    stream_found = Signal(str)
    url_changed  = Signal(str)

    TITLE = "_EdgeToolsBrowser_"

    def __init__(self, container):
        super().__init__()
        self._container  = container
        self._proc       = None
        self._hwnd       = None
        self._server     = None
        self._conn       = None
        self._port       = 0
        self._started    = False
        self._embedded   = False
        self._visible    = False
        self._last_url   = None
        self._found      = set()
        self._all_procs  = []   # все запущенные процессы — для чистки

        self._find_timer = QTimer(self)
        self._find_timer.setInterval(200)
        self._find_timer.timeout.connect(self._try_embed)

        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(150)
        self._sync_timer.timeout.connect(self._sync)

    # ── Публичный API ─────────────────────────────────────────────────────

    def start(self, url: str = "https://www.google.com"):
        if self._started:
            return
        self._started = True
        self._start_server()
        self._start_process(url)
        self._find_timer.start()

    def show_browser(self):
        self._visible = True
        if self._embedded:
            user32.ShowWindow(self._hwnd, 5)
            self._sync()
            self._sync_timer.start()

    def hide_browser(self):
        self._visible = False
        self._sync_timer.stop()
        if self._hwnd:
            user32.ShowWindow(self._hwnd, 0)

    def navigate(self, url: str): self._send({"action": "navigate", "url": url})
    def go_back(self):             self._send({"action": "back"})
    def go_forward(self):          self._send({"action": "forward"})
    def reload(self):              self._send({"action": "reload"})

    def re_embed(self):
        if not self._started:
            return
        last_url = self._last_url or "https://www.google.com"

        self._sync_timer.stop()
        self._find_timer.stop()

        # Убиваем текущий процесс
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                try: self._proc.kill()
                except Exception: pass
            self._proc = None

        self._cleanup_zombies()

        if self._conn:
            try: self._conn.close()
            except Exception: pass
            self._conn = None

        self._hwnd     = None
        self._embedded = False

        # Небольшая пауза чтобы Edge успел полностью завершиться
        import time
        time.sleep(0.5)

        self._start_process(last_url)
        self._find_timer.start()

    def _cleanup_zombies(self):
        """Убиваем все старые накопившиеся процессы."""
        alive = []
        for proc in self._all_procs:
            if proc.poll() is None:  # ещё живой
                try:
                    proc.terminate()
                    proc.wait(timeout=1)
                except Exception:
                    try: proc.kill()
                    except Exception: pass
            alive_check = proc.poll()
            # Не добавляем в alive — все старые убиты
        self._all_procs = []
        print(f"[webview] cleaned up zombie processes")

    def destroy(self):
        self._find_timer.stop()
        self._sync_timer.stop()
        self._send({"action": "close"})
        self._cleanup_zombies()
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                try: self._proc.kill()
                except Exception: pass
        if self._server:
            try: self._server.close()
            except Exception: pass

    # ── IPC ───────────────────────────────────────────────────────────────

    def _start_server(self):
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
                    try: self._conn.close()
                    except Exception: pass
                self._conn = conn
                print("[webview] connected")
                threading.Thread(
                    target=self._read_loop,
                    args=(conn,),
                    daemon=True
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
                print(f"[webview] read: {e}"); break

    def _handle(self, msg: dict):
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
            self.url_changed.emit(json.dumps({"url": url, "title": title}, ensure_ascii=False))
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
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webview_process.py")
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        proc = subprocess.Popen(
            [sys.executable, script, str(self._port), url],
            **kwargs
        )
        self._proc = proc
        self._all_procs.append(proc)
        print(f"[webview] pid={proc.pid}")

    # ── SetParent встраивание ─────────────────────────────────────────────

    def _try_embed(self):
        hwnd = user32.FindWindowW(None, self.TITLE)
        if not hwnd:
            return
        self._find_timer.stop()
        self._hwnd = hwnd
        self._do_embed()
        self._embedded = True
        if self._visible:
            self._sync()
            user32.ShowWindow(self._hwnd, 5)
            self._sync_timer.start()
        else:
            user32.ShowWindow(self._hwnd, 0)
        print("[webview] embedded")

    def _do_embed(self):
        parent = int(self._container.winId())
        user32.SetParent(self._hwnd, parent)
        style = user32.GetWindowLongW(self._hwnd, GWL_STYLE)
        style = (style & ~WS_POPUP & ~WS_CAPTION & ~WS_BORDER & ~WS_THICKFRAME) | WS_CHILD
        user32.SetWindowLongW(self._hwnd, GWL_STYLE, style)
        self._sync()

    def _sync(self):
        if not self._hwnd or not self._container:
            return
        try:
            w = self._container.width()
            h = self._container.height()
            user32.MoveWindow(self._hwnd, 0, 0, w, h, True)
        except Exception as e:
            print(f"[webview] sync: {e}")