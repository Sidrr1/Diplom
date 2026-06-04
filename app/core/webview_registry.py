"""Один profile_path — один webview_process (без lock-файлов)."""
from __future__ import annotations

import os
import time

_active: set[str] = set()


def norm(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def is_profile_in_use(profile_path: str) -> bool:
    return norm(profile_path) in _active


def claim_profile(profile_path: str) -> bool:
    key = norm(profile_path)
    if key in _active:
        return False
    _active.add(key)
    return True


def release_profile(profile_path: str) -> None:
    _active.discard(norm(profile_path))


def terminate_webview_processes_for_profile(profile_path: str) -> int:
    """Завершить другие webview_process.py с тем же каталогом профиля."""
    try:
        import psutil
    except ImportError:
        print("[webview_registry] psutil not installed")
        return 0

    key = norm(profile_path)
    killed = 0
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            joined = os.path.normcase(" ".join(cmdline))
            if "webview_process" not in joined:
                continue
            if key not in joined:
                continue
            proc.terminate()
            killed += 1
            print(f"[webview_registry] terminate pid={proc.pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if killed:
        time.sleep(0.5)
    return killed
