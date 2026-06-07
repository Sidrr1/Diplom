"""Постобработка OCR: латиница, похожая на кириллицу, в русском контексте."""
from __future__ import annotations

import re

# Латинские символы → кириллица (визуально похожие)
_LATIN_IN_CYR_WORD = str.maketrans({
    "A": "А", "a": "а",
    "B": "В", "b": "в",
    "C": "С", "c": "с",
    "E": "Е", "e": "е",
    "H": "Н", "h": "н",
    "K": "К", "k": "к",
    "M": "М", "m": "м",
    "O": "О", "o": "о",
    "P": "Р", "p": "р",
    "T": "Т", "t": "т",
    "X": "Х", "x": "х",
    "Y": "У", "y": "у",
    "R": "Р", "r": "р",
    "N": "Н", "n": "н",
    "I": "І", "i": "і",
    "L": "Л", "l": "л",
    "D": "Д", "d": "д",
    "G": "Г", "g": "г",
    "F": "Г",  # частая путаница с Г
})

# Частые ошибки целых слов (UI / коммиты)
_WORD_FIXES = {
    "NO": "по",
    "He": "не",
    "he": "не",
    "Ho": "по",
    "Еаве": "Edge",
    "Гручной": "ручной",
    "Гучной": "ручной",
    "авто]": "авто]",
    "[авто": "[авто",
    "правилам,": "правилам,",
}

_CYR_RE = re.compile(r"[\u0400-\u04FF]")
_LAT_RE = re.compile(r"[A-Za-z]")


def _has_cyrillic(s: str) -> bool:
    return bool(_CYR_RE.search(s))


def _fix_word(word: str) -> str:
    if word in _WORD_FIXES:
        return _WORD_FIXES[word]
    if not _has_cyrillic(word):
        return word
    if _LAT_RE.search(word):
        return word.translate(_LATIN_IN_CYR_WORD)
    return word


def postprocess_ocr_text(text: str) -> str:
    """Исправить латиницу, похожую на кириллицу, в словах с русским контекстом."""
    if not text or not text.strip():
        return text

    lines = []
    for line in text.splitlines():
        parts = re.split(r"(\s+)", line)
        fixed = []
        for p in parts:
            if p.isspace() or not p:
                fixed.append(p)
            else:
                # разбить пунктуацию по краям
                m = re.match(r"^([^\w\u0400-\u04FF]*)([\w\u0400-\u04FF]+)([^\w\u0400-\u04FF]*)$", p)
                if m:
                    pre, core, suf = m.groups()
                    fixed.append(pre + _fix_word(core) + suf)
                else:
                    fixed.append(_fix_word(p))
        lines.append("".join(fixed))
    return "\n".join(lines)
