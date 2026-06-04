"""Пути данных EdgeTools."""
import os


def normalize_path(path: str) -> str:
    """Единый формат пути для Windows (обратные слэши), без лишних пробелов."""
    if not path or not str(path).strip():
        return ""
    return os.path.normpath(os.path.expanduser(str(path).strip()))


def project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_data_dir() -> str:
    path = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "EdgeTools")
    os.makedirs(path, exist_ok=True)
    return path


def auth_profile_dir(service_id: str) -> str:
    """Постоянный профиль WebView2 для входа (cookies сохраняются между запусками)."""
    path = os.path.join(app_data_dir(), "profiles", service_id)
    os.makedirs(path, exist_ok=True)
    return path
