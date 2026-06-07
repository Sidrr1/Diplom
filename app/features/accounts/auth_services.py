"""Сервисы для привязки аккаунтов (WebView2-профиль на сервис)."""

from app.core.paths import auth_profile_dir

# YouTube использует профиль Google (общая сессия).
AUTH_SERVICES = {
    "google": {
        "title": "Google",
        "subtitle": "Вход для YouTube и сервисов Google",
        "profile_id": "google",
        "login_url": "https://www.google.com/",
        "player_profile": True,
    },
    "youtube": {
        "title": "YouTube",
        "subtitle": "Тот же профиль WebView2, что и Google",
        "profile_id": "google",
        "login_url": "https://www.youtube.com/",
        "player_profile": True,
    },
}


def profile_id_for_service(service_id: str) -> str:
    """ID профиля WebView2 для сервиса (YouTube → общий google)."""
    meta = AUTH_SERVICES.get(service_id) or {}
    return meta.get("profile_id", service_id)


def list_account_services() -> list[dict]:
    """Список сервисов для UI привязки с путями к профилям."""
    out = []
    for sid, meta in AUTH_SERVICES.items():
        pid = meta["profile_id"]
        row = dict(meta)
        row["service_id"] = sid
        row["profile_path"] = auth_profile_dir(pid)
        out.append(row)
    return out


def profile_id_for_url(url: str) -> str | None:
    """Определить профиль по URL (google/youtube → google)."""
    u = (url or "").lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "google"
    if "google.com" in u:
        return "google"
    return None


def is_login_success(service_id: str, url: str) -> bool:
    """Проверить, что URL означает успешный вход (не страница signin)."""
    u = (url or "").lower()
    if not u or u in ("about:blank",):
        return False

    if service_id not in ("google", "youtube"):
        return False

    if (
        "signin" in u
        or "servicelogin" in u
        or "accountchooser" in u
        or "gds.google.com" in u
        or "recoveryoptions" in u
    ):
        return False
    if "accounts.google.com" in u:
        return False
    if "myaccount.google.com" in u:
        return True
    if "mail.google.com" in u:
        return True
    if "youtube.com" in u:
        if service_id == "youtube" and u.rstrip("/").endswith("youtube.com"):
            return False
        return True
    if "google.com" in u:
        if "pli=1" in u or "authuser=" in u:
            return True
        if "/signout" in u:
            return True
    return False
