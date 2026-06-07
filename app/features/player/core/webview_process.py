"""
Subprocess WebView2 для плеера EdgeTools (pywebview).

Запускается из WebViewBrowser: подключается к родителю по TCP,
отправляет события url_changed/stream_found, принимает navigate/back/reload/close.
В режиме embed перехватывает XHR/fetch на .m3u8/.mp4 для автозапуска плеера.
"""
import json
import os
import socket
import sys
import threading
import time

# Корень проекта для import app.* при запуске как script
_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    )
)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main():
    """
    Точка входа subprocess.

    argv: port start_url profile_path [embed|standalone] [window_title]
    """
    if len(sys.argv) < 4:
        print(
            "[wv_proc] usage: port start_url profile_path "
            "[embed|standalone] [window_title]"
        )
        sys.exit(1)

    port = int(sys.argv[1])
    start_url = sys.argv[2]
    profile_path = os.path.abspath(sys.argv[3])
    mode = sys.argv[4] if len(sys.argv) > 4 else "standalone"
    window_title = sys.argv[5] if len(sys.argv) > 5 else "EdgeTools — Вход"

    os.makedirs(profile_path, exist_ok=True)
    os.environ["WEBVIEW2_USER_DATA_FOLDER"] = profile_path
    print(f"[wv_proc] profile: {profile_path}")
    print(f"[wv_proc] WEBVIEW2_USER_DATA_FOLDER={os.environ.get('WEBVIEW2_USER_DATA_FOLDER')}")
    print(f"[wv_proc] mode={mode}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", port))
    except Exception as e:
        print(f"[wv_proc] connect: {e}")
        sys.exit(1)

    def send(event: str, data: str = ""):
        """Отправить JSON-событие родительскому процессу."""
        try:
            sock.sendall(
                (json.dumps({"event": event, "data": data}) + "\n").encode()
            )
        except Exception:
            pass

    import webview

    embed = mode == "embed"
    window = webview.create_window(
        window_title,
        start_url,
        width=960 if not embed else 800,
        height=640 if not embed else 600,
        frameless=False,
        easy_drag=False,
        hidden=embed,
        min_size=(400, 300),
    )

    def notify_url():
        """Сообщить родителю текущий URL и document.title."""
        try:
            url = window.get_current_url() or ""
            title = ""
            try:
                title = window.evaluate_js("document.title") or ""
            except Exception:
                pass
            send(
                "url_changed",
                json.dumps({"url": url, "title": title}, ensure_ascii=False),
            )
        except Exception as e:
            print(f"[wv_proc] url notify: {e}")

    def on_loaded():
        """После load: URL + JS-хуки XHR/fetch для перехвата медиа-потоков."""
        notify_url()
        if not embed:
            return
        try:
            window.evaluate_js(
                """
            (function() {
                if (window.__et__) return; window.__et__ = true;
                function notify(u) {
                    if (!u) return;
                    if (u.indexOf('.m3u8') !== -1 ||
                        (u.indexOf('.mp4') !== -1 && u.indexOf('http') === 0))
                        pywebview.api.on_stream(u);
                }
                var _o = XMLHttpRequest.prototype.open;
                XMLHttpRequest.prototype.open = function(m, u) {
                    notify(typeof u === 'string' ? u : '');
                    return _o.apply(this, arguments);
                };
                var _f = window.fetch;
                if (_f) window.fetch = function(i, o) {
                    notify(typeof i === 'string' ? i : '');
                    return _f.apply(this, arguments);
                };
            })();
            """
            )
        except Exception as e:
            print(f"[wv_proc] hooks: {e}")

    class Api:
        """Мост pywebview.api.on_stream → IPC stream_found."""

        def on_stream(self, url):
            send("stream_found", url)

    window.events.loaded += on_loaded
    if embed:
        window.expose(Api().on_stream)

    def listen():
        """Фоновый приём IPC-команд от WebViewBrowser."""
        buf = ""
        while True:
            try:
                data = sock.recv(4096).decode()
                if not data:
                    break
                buf += data
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    cmd = json.loads(line)
                    a = cmd.get("action")
                    if a == "navigate":
                        window.load_url(cmd.get("url", ""))
                    elif a == "back":
                        window.evaluate_js("history.back()")
                    elif a == "forward":
                        window.evaluate_js("history.forward()")
                    elif a == "reload":
                        window.evaluate_js("location.reload()")
                    elif a == "close":
                        window.destroy()
                        return
            except Exception as e:
                print(f"[wv_proc] listen: {e}")
                break

    threading.Thread(target=listen, daemon=True).start()

    time.sleep(0.3)
    max_retries = 3
    last_err = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"[wv_proc] retry webview.start {attempt + 1}/{max_retries}")
                time.sleep(1)
            try:
                webview.start(private_mode=False, storage_path=profile_path)
            except TypeError:
                webview.start(private_mode=False)
            break
        except Exception as e:
            last_err = e
            print(f"[wv_proc] webview.start attempt {attempt + 1} failed: {e}")
            if attempt >= max_retries - 1:
                import traceback
                traceback.print_exc()
                sys.exit(2)
    else:
        if last_err:
            print(f"[wv_proc] webview.start failed: {last_err}")
            sys.exit(2)

    sock.close()


if __name__ == "__main__":
    main()
