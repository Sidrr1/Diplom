# app/features/player/core/webview_process.py
import sys
import json
import socket
import threading


def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    port      = int(sys.argv[1])
    start_url = sys.argv[2]

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", port))
    except Exception as e:
        print(f"[wv_proc] connect: {e}"); sys.exit(1)

    def send(event: str, data: str = ""):
        try:
            sock.sendall((json.dumps({"event": event, "data": data}) + "\n").encode())
        except Exception:
            pass

    import webview

    edge_args = [
        "--disable-features=msSmartScreenProtection",
        "--disable-extensions",
        "--process-per-site",
        "--disable-background-networking",
        "--disable-default-apps",
        "--no-first-run",
        "--js-flags=--max-old-space-size=128",  # ограничиваем V8 heap до 128MB
    ]

    window = webview.create_window(
        "_EdgeToolsBrowser_",
        start_url,
        frameless=False,
        easy_drag=False,
        hidden=True,
        min_size=(320, 180),
    )

    def on_loaded():
        try:
            url = window.get_current_url() or ""
            send("url_changed", url)
            window.evaluate_js("""
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
            """)
        except Exception as e:
            print(f"[wv_proc] loaded: {e}")

    class Api:
        def on_stream(self, url): send("stream_found", url)

    window.events.loaded += on_loaded
    window.expose(Api().on_stream)

    def listen():
        buf = ""
        while True:
            try:
                data = sock.recv(4096).decode()
                if not data: break
                buf += data
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line: continue
                    cmd = json.loads(line)
                    a   = cmd.get("action")
                    if   a == "navigate": window.load_url(cmd.get("url", ""))
                    elif a == "back":     window.evaluate_js("history.back()")
                    elif a == "forward":  window.evaluate_js("history.forward()")
                    elif a == "reload":   window.evaluate_js("location.reload()")
                    elif a == "close":    window.destroy(); return
            except Exception as e:
                print(f"[wv_proc] listen: {e}"); break

    threading.Thread(target=listen, daemon=True).start()

    # Передаём флаги Edge через аргументы chromium
    try:
        webview.start(chromium_args=edge_args)
    except TypeError:
        # Старые версии pywebview не поддерживают chromium_args
        webview.start()

    sock.close()


if __name__ == "__main__":
    main()