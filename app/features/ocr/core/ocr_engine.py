"""
Движок OCR на базе Tesseract.

Перебирает режимы сегментации страницы (PSM) для UI-скриншотов,
выбирает лучший результат по уверенности и количеству слов,
при необходимости применяет постобработку текста.
"""
from __future__ import annotations

from collections import defaultdict

from app.features.ocr.core.ocr_settings import is_postprocess_enabled, langs_tesseract_str
from app.features.ocr.core.postprocess import postprocess_ocr_text
from app.features.ocr.core.tesseract_env import configure_pytesseract

# Режимы сегментации для UI-скриншотов
_PSM_MODES = (6, 4, 11)
_MIN_WORD_CONF = 25


def _words_from_data(data: dict) -> tuple[str, float, int]:
    """
    Собрать текст из словаря image_to_data и вычислить среднюю уверенность.

    Args:
        data: результат pytesseract.image_to_data (Output.DICT)

    Returns:
        кортеж (текст построчно, средняя уверенность %, число принятых слов)
    """
    n = len(data.get("text", []))
    line_map: dict[tuple, list[tuple[int, str, int]]] = defaultdict(list)
    confs: list[int] = []

    for i in range(n):
        word = (data["text"][i] or "").strip()
        if not word:
            continue
        try:
            conf = int(float(data["conf"][i]))
        except (TypeError, ValueError):
            continue
        if conf < 0:
            continue
        if conf < _MIN_WORD_CONF:
            continue
        confs.append(conf)
        key = (
            data.get("block_num", [0])[i],
            data.get("par_num", [0])[i],
            data.get("line_num", [0])[i],
        )
        left = int(data.get("left", [0])[i] or 0)
        line_map[key].append((left, word, conf))

    lines_out: list[str] = []
    for key in sorted(line_map.keys()):
        words = sorted(line_map[key], key=lambda x: x[0])
        lines_out.append(" ".join(w[1] for w in words))

    text = "\n".join(lines_out).strip()
    avg = sum(confs) / len(confs) if confs else 0.0
    return text, avg, len(confs)


def recognize(pil_img, lang_str: str | None = None) -> tuple[str, int, str]:
    """
    Распознать текст на изображении с автоподбором PSM.

    Args:
        pil_img: изображение PIL (RGB)
        lang_str: строка языков Tesseract (например «rus+eng»); по умолчанию из настроек

    Returns:
        кортеж (распознанный текст, средняя уверенность %, выбранный PSM)
    """
    import pytesseract
    from pytesseract import Output

    configure_pytesseract()
    lang_str = lang_str or langs_tesseract_str()

    best_text = ""
    best_conf = -1.0
    best_psm = 6
    best_words = 0

    for psm in _PSM_MODES:
        config = f"--psm {psm} --oem 3"
        try:
            data = pytesseract.image_to_data(
                pil_img,
                lang=lang_str,
                config=config,
                output_type=Output.DICT,
            )
        except Exception:
            continue
        text, avg, wc = _words_from_data(data)
        if not text:
            continue
        # предпочитаем выше conf; при равенстве — больше слов
        score = avg + min(wc, 20) * 0.05
        if score > best_conf or (score == best_conf and wc > best_words):
            best_conf = score
            best_text = text
            best_psm = psm
            best_words = wc

    if not best_text:
        config = "--psm 6 --oem 3"
        best_text = pytesseract.image_to_string(
            pil_img, lang=lang_str, config=config
        ).strip()
        best_conf = 0.0

    if is_postprocess_enabled():
        best_text = postprocess_ocr_text(best_text)

    return best_text, int(round(best_conf)), str(best_psm)
