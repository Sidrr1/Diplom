"""
Раскраска ч/б изображений через colorizers (siggraph17).

``is_grayscale`` используется UI для включения кнопки «Раскрасить».
"""
import os
import sys
import numpy as np
from PIL import Image

# Добавляем корень проекта в path чтобы найти локальную папку colorizers
_PROJECT_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", ".."
))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def is_grayscale(img: Image.Image) -> bool:
    """True, если каналы R/G/B почти совпадают (средняя разница < 8)."""
    arr = np.array(img.convert("RGB"))
    r = arr[:, :, 0].astype(int)
    g = arr[:, :, 1].astype(int)
    b = arr[:, :, 2].astype(int)
    diff = np.max([np.abs(r - g), np.abs(r - b), np.abs(g - b)], axis=0)
    return float(diff.mean()) < 8.0


def colorize(img: Image.Image, progress_cb=None) -> Image.Image:
    """Раскраска через colorizers (Zhang et al., Berkeley — siggraph17)."""
    try:
        import torch
        from colorizers import siggraph17, preprocess_img, postprocess_tens
    except ImportError as e:
        raise RuntimeError(
            f"Не найден модуль colorizers: {e}\n"
            "Скопируй папку colorizers/ в корень проекта."
        )

    if progress_cb:
        progress_cb(8)

    colorizer = siggraph17(pretrained=True).eval()
    if progress_cb:
        progress_cb(25)

    img_np = np.array(img.convert("RGB"))
    tens_l_orig, tens_l_rs = preprocess_img(img_np, HW=(256, 256))
    if progress_cb:
        progress_cb(40)

    with torch.no_grad():
        out_ab = colorizer(tens_l_rs).cpu()
    if progress_cb:
        progress_cb(70)

    out_np = postprocess_tens(tens_l_orig, out_ab)
    if progress_cb:
        progress_cb(88)

    result = Image.fromarray((out_np * 255).astype(np.uint8))
    if result.size != img.size:
        result = result.resize(img.size, Image.LANCZOS)

    if progress_cb:
        progress_cb(100)
    return result
