"""Скачивание .traineddata из официального репозитория tessdata."""
from __future__ import annotations

import os
from typing import Callable

import requests

from app.features.ocr.core.tesseract_env import traineddata_path, user_tessdata_dir

_TESSDATA_RAW = (
    "https://github.com/tesseract-ocr/tessdata/raw/main/{code}.traineddata"
)
_TIMEOUT = (15, 120)


def download_traineddata(
    code: str,
    *,
    on_progress: Callable[[int, int], None] | None = None,
) -> str:
    """Скачивает пакет языка в папку EdgeTools. Возвращает путь к файлу."""
    code = str(code).strip()
    if not code or code == "osd":
        raise ValueError(f"Недопустимый код языка: {code!r}")

    dest = traineddata_path(code)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return dest

    url = _TESSDATA_RAW.format(code=code)
    os.makedirs(user_tessdata_dir(), exist_ok=True)
    tmp = dest + ".download"

    try:
        with requests.get(url, stream=True, timeout=_TIMEOUT) as resp:
            if resp.status_code == 404:
                raise FileNotFoundError(
                    f"Пакет «{code}» не найден в tessdata (404)."
                )
            resp.raise_for_status()
            total = int(resp.headers.get("content-length") or 0)
            done = 0
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(chunk_size=256 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    if on_progress:
                        on_progress(done, total)
        if os.path.getsize(tmp) < 1024:
            raise IOError(f"Слишком маленький файл для «{code}».")
        os.replace(tmp, dest)
    except Exception:
        if os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise

    return dest


def download_langs(
    codes: list[str],
    *,
    on_lang: Callable[[str], None] | None = None,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> list[str]:
    """Скачивает несколько языков. Возвращает список успешно установленных."""
    installed: list[str] = []
    for code in codes:
        if on_lang:
            on_lang(code)

        def _prog(done: int, total: int) -> None:
            if on_progress:
                on_progress(code, done, total)

        download_traineddata(code, on_progress=_prog)
        installed.append(code)
    return installed
