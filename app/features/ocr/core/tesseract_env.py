"""Путь к Tesseract, tessdata EdgeTools и список языков."""

from __future__ import annotations



import os

import platform

import shutil

import subprocess



from app.core.paths import app_data_dir



_TESSERACT_CMD = (

    r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    if platform.system() == "Windows"

    else "tesseract"

)



_LANG_LABELS = {

    "rus": "Русский",

    "eng": "English",

    "kaz": "Қазақша",

    "ukr": "Українська",

    "bel": "Беларуская",

    "deu": "Deutsch",

    "fra": "Français",

    "spa": "Español",

    "ita": "Italiano",

    "por": "Português",

    "pol": "Polski",

    "tur": "Türkçe",

    "ara": "العربية",

    "hin": "हिन्दी",

    "jpn": "日本語",

    "kor": "한국어",

    "chi_sim": "中文 (简体)",

    "chi_tra": "中文 (繁體)",

    "osd": "OSD",

}



_BOOTSTRAP_LANGS = ("rus", "eng")





def configure_pytesseract() -> None:

    import pytesseract



    _apply_tessdata_prefix()

    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD





def lang_display(code: str) -> str:
    return _LANG_LABELS.get(code, code)


_LANG_TAGS = {
    "rus": "ru",
    "eng": "en",
    "kaz": "kaz",
    "ukr": "uk",
    "bel": "be",
    "deu": "de",
    "fra": "fr",
    "spa": "es",
    "ita": "it",
    "por": "pt",
    "pol": "pl",
    "tur": "tr",
    "ara": "ar",
    "hin": "hi",
    "jpn": "ja",
    "kor": "ko",
    "chi_sim": "zh",
    "chi_tra": "zht",
}


def lang_tag(code: str) -> str:
    """Короткий тег для UI (ru, en, kaz…)."""
    return _LANG_TAGS.get(code, code.replace("_", ""))





def system_tessdata_dir() -> str:

    return os.path.join(os.path.dirname(_TESSERACT_CMD), "tessdata")





def user_tessdata_dir() -> str:

    path = os.path.join(app_data_dir(), "tessdata")

    os.makedirs(path, exist_ok=True)

    return path





def tessdata_dir() -> str:

    """Папка, куда EdgeTools кладёт и откуда читает пакеты (без прав администратора)."""

    return user_tessdata_dir()





def traineddata_path(code: str) -> str:

    return os.path.join(user_tessdata_dir(), f"{code}.traineddata")





def _apply_tessdata_prefix() -> None:

    root = app_data_dir()

    os.makedirs(root, exist_ok=True)

    sep = os.sep if root.endswith(("\\", "/")) else ""

    os.environ["TESSDATA_PREFIX"] = root + sep

    bootstrap_user_tessdata()





def bootstrap_user_tessdata() -> None:

    """Копирует rus/eng из установки Tesseract, если их ещё нет в EdgeTools."""

    for code in _BOOTSTRAP_LANGS:

        dst = traineddata_path(code)

        if os.path.isfile(dst) and os.path.getsize(dst) > 0:

            continue

        src = os.path.join(system_tessdata_dir(), f"{code}.traineddata")

        if os.path.isfile(src):

            try:

                shutil.copy2(src, dst)

            except OSError as e:

                print(f"[ocr] copy {code}: {e}")





def list_catalog_langs() -> list[str]:

    return sorted(c for c in _LANG_LABELS if c != "osd")





def has_traineddata_file(code: str) -> bool:

    path = traineddata_path(code)

    if os.path.isfile(path) and os.path.getsize(path) > 1024:

        return True

    sys_path = os.path.join(system_tessdata_dir(), f"{code}.traineddata")

    return os.path.isfile(sys_path) and os.path.getsize(sys_path) > 1024





def list_installed_langs() -> list[str]:

    found: set[str] = set()

    for code in list_catalog_langs():

        if has_traineddata_file(code):

            found.add(code)



    try:

        configure_pytesseract()

        import pytesseract



        for code in pytesseract.get_languages(config=""):

            if code and code != "osd":

                found.add(code)

    except Exception as e:

        print(f"[ocr] pytesseract langs: {e}")



    try:

        out = subprocess.run(

            [_TESSERACT_CMD, "--list-langs"],

            capture_output=True,

            text=True,

            timeout=10,

            check=False,

            env=os.environ.copy(),

        )

        for line in (out.stdout or "").strip().splitlines()[1:]:

            code = line.strip()

            if code and code != "osd":

                found.add(code)

    except Exception as e:

        print(f"[ocr] --list-langs: {e}")



    if found:

        return sorted(found)

    return ["eng", "rus"]





def missing_lang_packs(codes: list[str]) -> list[str]:

    """Языки из списка, для которых нет .traineddata в EdgeTools (нужно скачать)."""

    missing = []

    for code in codes:

        c = str(code).strip()

        if not c or c == "osd":

            continue

        if not os.path.isfile(traineddata_path(c)) or os.path.getsize(traineddata_path(c)) < 1024:

            missing.append(c)

    return missing


