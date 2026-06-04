"""Отдельное нативное окно WebView2 для входа (без Qt/SetParent)."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox

from app.core.database import db
from app.core.paths import auth_profile_dir, project_root
import time

from app.core.webview_registry import (
    claim_profile,
    is_profile_in_use,
    release_profile,
    terminate_webview_processes_for_profile,
)
from app.features.accounts.auth_services import (
    AUTH_SERVICES,
    is_login_success,
    profile_id_for_service,
)


class AccountLoginWindow(QObject):
    """Запускает webview_process.py и завершается при успешном URL."""

    finished = Signal(str, bool)

    _running: AccountLoginWindow | None = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service_id = ""
        self._profile_path = ""
        self._proc: subprocess.Popen | None = None
        self._server: socket.socket | None = None
        self._conn: socket.socket | None = None
        self._port = 0
        self._closed = False
        self._success = False
        self._proc_log: list[str] = []
        self._parent_widget = None
        self._login_url = ""
        self._login_title = ""
        self._start_attempt = 0
        self._retry_pending = False
        self._ignore_proc_exit = False
        self._accept_thread_started = False
        self._last_url = ""
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(800)
        self._watch_timer.timeout.connect(self._watch_proc)

    @classmethod
    def is_active(cls) -> bool:
        cls.force_reset_stale()
        return cls._running is not None

    @classmethod
    def force_reset_stale(cls) -> None:
        """Сброс, если окно входа закрыли вручную, а _running остался."""
        r = cls._running
        if r is None:
            return
        proc_dead = r._proc is None or r._proc.poll() is not None
        if proc_dead and not r._closed:
            print("[account_login] stale session cleanup")
            r._cleanup(False)

    def start(self, service_id: str, *, player_view=None, parent_widget=None) -> bool:
        AccountLoginWindow.force_reset_stale()
        if AccountLoginWindow._running is not None:
            QMessageBox.information(
                parent_widget,
                "Вход",
                "Окно входа уже открыто.",
            )
            return False

        meta = AUTH_SERVICES.get(service_id)
        if not meta:
            return False
        if not meta.get("enabled", True):
            QMessageBox.information(
                parent_widget,
                meta.get("title", service_id),
                "Сервис пока недоступен.",
            )
            return False

        profile_id = profile_id_for_service(service_id)
        profile_path = os.path.abspath(auth_profile_dir(profile_id))
        login_url = meta.get("login_url", "https://www.google.com/")
        title = meta.get("title", service_id)

        if player_view and hasattr(player_view, "pause_webview_for_auth"):
            player_view.pause_webview_for_auth()

        n = terminate_webview_processes_for_profile(profile_path)
        if n:
            print(f"[account_login] terminated {n} stale webview process(es)")
        time.sleep(0.5)

        if is_profile_in_use(profile_path):
            QMessageBox.warning(
                parent_widget,
                "Профиль занят",
                "Этот профиль WebView2 уже используется.\n"
                "Закройте браузер в плеере и повторите вход.",
            )
            return False

        if not claim_profile(profile_path):
            return False

        self._service_id = service_id
        self._profile_path = profile_path
        self._parent_widget = parent_widget
        self._login_url = login_url
        self._login_title = title
        self._start_attempt = 0
        self._finalized = False
        AccountLoginWindow._running = self

        try:
            self._start_server()
            self._start_process(login_url, profile_path, title)
        except Exception as e:
            print(f"[account_login] start: {e}")
            self._cleanup(False)
            QMessageBox.critical(
                parent_widget,
                "Вход",
                f"Не удалось открыть браузер:\n{e}",
            )
            return False

        print(f"[account_login] {service_id} -> {login_url}")
        return True

    def _start_server(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._port = self._server.getsockname()[1]
        self._server.listen(5)
        if not self._accept_thread_started:
            self._accept_thread_started = True
            threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while not self._closed and self._server:
            try:
                conn, _ = self._server.accept()
                if self._conn:
                    try:
                        self._conn.close()
                    except Exception:
                        pass
                self._conn = conn
                print("[account_login] connected")
                threading.Thread(
                    target=self._read_loop, args=(conn,), daemon=True
                ).start()
            except OSError:
                break
            except Exception as e:
                if not self._closed:
                    print(f"[account_login] accept: {e}")
                break

    def _read_loop(self, conn: socket.socket):
        buf = ""
        while not self._closed:
            try:
                data = conn.recv(4096).decode()
                if not data:
                    break
                buf += data
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        self._on_message(json.loads(line))
            except Exception as e:
                print(f"[account_login] read: {e}")
                break
        if not self._closed and not self._retry_pending:
            QTimer.singleShot(0, self._finalize_after_proc_exit)

    def _on_message(self, msg: dict):
        if msg.get("event") != "url_changed":
            return
        data = msg.get("data", "")
        url = data
        if isinstance(data, str) and data.startswith("{"):
            try:
                url = json.loads(data).get("url", "") or ""
            except json.JSONDecodeError:
                url = data
        if not url:
            return
        self._last_url = url
        print(f"[account_login] url: {url[:100]}")
        if is_login_success(self._service_id, url):
            self._on_success()

    def _mark_connected(self):
        profile_id = profile_id_for_service(self._service_id)
        db.upsert_linked_account(
            profile_id,
            self._profile_path,
            status="connected",
            display_name="",
        )
        if profile_id == "google":
            db.set_setting("player_web_google_connected", "1", "player")

    def _on_success(self):
        if self._success:
            return
        self._success = True
        self._mark_connected()
        print(f"[account_login] success {self._service_id}")
        self._send_close()
        QTimer.singleShot(300, lambda: self._cleanup(True))

    def _try_success_from_last_url(self):
        if self._success or not self._last_url:
            return
        if is_login_success(self._service_id, self._last_url):
            self._success = True
            self._mark_connected()
            print(f"[account_login] success on close: {self._last_url[:80]}")

    def _send_close(self):
        if not self._conn:
            return
        try:
            self._conn.sendall(b'{"action":"close"}\n')
        except Exception:
            pass

    def _start_process(self, url: str, profile_path: str, title: str):
        profile_path = os.path.abspath(profile_path)
        print(f"[account_login] spawn profile={profile_path}")
        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "player",
            "core",
            "webview_process.py",
        )
        script = os.path.normpath(script)
        args = [
            sys.executable,
            script,
            str(self._port),
            url,
            profile_path,
            "standalone",
            f"EdgeTools — {title}",
        ]
        kwargs = {
            "cwd": project_root(),
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000
        self._proc = subprocess.Popen(args, **kwargs)
        self._watch_timer.start()
        threading.Thread(target=self._drain_proc_output, daemon=True).start()
        threading.Thread(target=self._wait_proc, daemon=True).start()

    def _watch_proc(self):
        if self._closed or not self._proc:
            self._watch_timer.stop()
            return
        if self._proc.poll() is not None:
            self._watch_timer.stop()
            if not self._closed and not self._ignore_proc_exit:
                self._finalize_after_proc_exit()

    def _finalize_after_proc_exit(self):
        if self._closed or self._finalized:
            return
        self._finalized = True
        self._try_success_from_last_url()
        if self._profile_path:
            terminate_webview_processes_for_profile(self._profile_path)
            release_profile(self._profile_path)
        ok = self._success
        QTimer.singleShot(0, lambda: self._cleanup(ok))

    def _drain_proc_output(self):
        if not self._proc or not self._proc.stdout:
            return
        try:
            for line in self._proc.stdout:
                line = line.rstrip()
                if line:
                    self._proc_log.append(line)
                    print(f"[wv_proc] {line}")
                    if (
                        "WebView2 initialization failed" in line
                        or "8007139F" in line
                    ):
                        QTimer.singleShot(0, self._schedule_webview2_retry)
        except Exception:
            pass

    def _schedule_webview2_retry(self):
        if self._closed or self._success or self._retry_pending:
            return
        if self._start_attempt >= 2:
            return
        self._retry_pending = True
        self._start_attempt += 1
        print(f"[account_login] WebView2 retry {self._start_attempt}/2")
        self._kill_proc_only()
        terminate_webview_processes_for_profile(self._profile_path)
        time.sleep(1)
        self._retry_pending = False
        self._start_process(self._login_url, self._profile_path, self._login_title)

    def _kill_proc_only(self):
        self._ignore_proc_exit = True
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None

    def _wait_proc(self):
        if not self._proc:
            return
        code = self._proc.wait()
        if self._ignore_proc_exit:
            self._ignore_proc_exit = False
            return
        print(f"[account_login] process exit {code}")
        if code not in (0, None) and not self._success:
            QTimer.singleShot(0, self._show_proc_error)
        if not self._closed and not self._retry_pending:
            self._finalize_after_proc_exit()

    def _show_proc_error(self):
        log = "\n".join(self._proc_log[-8:])
        hint = "Не удалось открыть окно браузера."
        if "8007139F" in log or "WebView2 initialization failed" in log:
            hint = (
                "Профиль WebView2 занят или повреждён.\n\n"
                "1. Полностью закройте EdgeTools (и режим 🌐 в плеере).\n"
                "2. При необходимости удалите папку профиля:\n"
                f"{self._profile_path}\n"
                "3. Запустите вход снова."
            )
        elif "chromium_args" in log:
            hint = "Устаревший вызов webview — обновите EdgeTools (уже исправлено в коде)."
        QMessageBox.warning(self._parent_widget, "Вход", hint)

    def _cleanup(self, ok: bool):
        if self._closed:
            return
        self._closed = True
        self._watch_timer.stop()
        if self._profile_path:
            terminate_webview_processes_for_profile(self._profile_path)
            release_profile(self._profile_path)
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
            self._server = None
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None
        if AccountLoginWindow._running is self:
            AccountLoginWindow._running = None
        self._notify_player()
        self.finished.emit(self._service_id, ok)

    def _notify_player(self):
        try:
            from app.features.settings.ui.settings_dialog import SettingsDialog

            pv = SettingsDialog._player_view_ref
            if pv and hasattr(pv, "on_login_window_closed"):
                QTimer.singleShot(0, lambda: pv.on_login_window_closed(self._success))
        except Exception as e:
            print(f"[account_login] notify player: {e}")


def logout_service(service_id: str, *, player_view=None, parent_widget=None) -> None:
    import shutil

    meta = AUTH_SERVICES.get(service_id) or {}
    profile_id = profile_id_for_service(service_id)
    path = os.path.abspath(auth_profile_dir(profile_id))

    if AccountLoginWindow.is_active():
        print("[account_login] logout blocked: login window open")
        return

    if player_view and hasattr(player_view, "pause_webview_for_auth"):
        player_view.pause_webview_for_auth()

    terminate_webview_processes_for_profile(path)
    time.sleep(0.3)

    if is_profile_in_use(path):
        QMessageBox.warning(
            parent_widget,
            "Выход",
            "Профиль ещё используется. Закройте браузер в плеере.",
        )
        return

    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception as e:
        print(f"[account_login] logout rmtree: {e}")
    os.makedirs(path, exist_ok=True)

    try:
        db.set_linked_account_status(profile_id, "disconnected", "")
        if profile_id == "google":
            db.set_setting("player_web_google_connected", "0", "player")
    except Exception as e:
        print(f"[account_login] logout db: {e}")
    print(f"[account_login] logout {service_id} (profile cleared: {path})")
