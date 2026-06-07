"""
Реестр активных WebView2-профилей EdgeTools.

Гарантирует: один profile_path — один процесс webview_process (без lock-файлов).
"""
from __future__ import annotations

import os
import time

# Нормализованные пути профилей, занятых в текущем процессе
_active: set[str] = set()


def norm(path: str) -> str:
    """
    Нормализовать путь для сравнения (регистр и абсолютный путь).

    Args:
        path: путь к каталогу профиля WebView2.

    Returns:
        Ключ для множества _active.
    """
    return os.path.normcase(os.path.abspath(path))


def is_profile_in_use(profile_path: str) -> bool:
    """
    Проверить, занят ли профиль в текущем процессе EdgeTools.

    Args:
        profile_path: каталог профиля WebView2.

    Returns:
        True, если профиль уже зарегистрирован в _active.
    """
    return norm(profile_path) in _active


def claim_profile(profile_path: str) -> bool:
    """
    Зарезервировать профиль перед запуском webview_process.

    Args:
        profile_path: каталог профиля WebView2.

    Returns:
        True при успешной резервации, False если профиль уже занят.
    """
    key = norm(profile_path)
    if key in _active:
        return False
    _active.add(key)
    return True


def release_profile(profile_path: str) -> None:
    """
    Освободить профиль после завершения webview_process.

    Args:
        profile_path: каталог профиля WebView2.
    """
    _active.discard(norm(profile_path))


def kill_process_tree(pid: int, *, timeout: float = 2.0) -> None:
    """
    Завершить процесс и всех потомков (WebView2 / python-mpv зомби).

    Args:
        pid: идентификатор корневого процесса.
        timeout: секунды ожидания после terminate перед kill.
    """
    if not pid:
        return
    try:
        import psutil
    except ImportError:
        return
    try:
        root = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    procs = root.children(recursive=True) + [root]
    for p in procs:
        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _gone, alive = psutil.wait_procs(procs, timeout=timeout)
    for p in alive:
        try:
            p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def terminate_webview_processes_for_profile(profile_path: str) -> int:
    """
    Завершить webview_process.py с тем же каталогом профиля.

    Args:
        profile_path: каталог профиля, по которому ищутся процессы.

    Returns:
        Количество завершённых деревьев процессов.
    """
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
            kill_process_tree(proc.pid)
            killed += 1
            print(f"[webview_registry] terminate pid={proc.pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if killed:
        time.sleep(0.3)
    return killed
