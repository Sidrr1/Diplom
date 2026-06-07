"""
Пути к данным и профилям EdgeTools.

Нормализация путей Windows, каталог AppData и каталоги WebView2 для авторизации.
"""
import os


def normalize_path(path: str) -> str:
    """
    Привести путь к единому формату Windows.

    Args:
        path: исходная строка пути.

    Returns:
        Нормализованный путь с обратными слэшами или пустая строка.
    """
    if not path or not str(path).strip():
        return ""
    return os.path.normpath(os.path.expanduser(str(path).strip()))


def project_root() -> str:
    """
    Корневая папка проекта EdgeTools (родитель app/).

    Returns:
        Абсолютный путь к корню репозитория.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_data_dir() -> str:
    """
    Каталог пользовательских данных EdgeTools в AppData.

    Путь %APPDATA%\\EdgeTools — Program Files только для чтения,
    поэтому настройки и профили хранятся здесь.

    Returns:
        Абсолютный путь к Roaming\\EdgeTools (создаётся при необходимости).
    """
    path = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "EdgeTools")
    os.makedirs(path, exist_ok=True)
    return path


def auth_profile_dir(service_id: str) -> str:
    """
    Постоянный профиль WebView2 для входа в сервис.

    Cookies и сессия сохраняются между запусками EdgeTools.

    Args:
        service_id: идентификатор сервиса (youtube, spotify и т.д.).

    Returns:
        Путь к каталогу profiles/<service_id>.
    """
    path = os.path.join(app_data_dir(), "profiles", service_id)
    os.makedirs(path, exist_ok=True)
    return path
