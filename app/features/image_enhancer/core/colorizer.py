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
    arr = np.array(img.convert("RGB"))
    r = arr[:, :, 0].astype(int)
    g = arr[:, :, 1].astype(int)
    b = arr[:, :, 2].astype(int)
    diff = np.max([np.abs(r - g), np.abs(r - b), np.abs(g - b)], axis=0)
    return float(diff.mean()) < 8.0


def skin_confidence(img: Image.Image) -> float:
    arr = np.array(img.convert("L"))
    h, w = arr.shape
    cy, cx = h // 2, w // 2
    region = arr[cy - h // 6:cy + h // 6, cx - w // 6:cx + w // 6]
    if region.size == 0:
        return 0.0
    mid = region.mean()
    return 1.0 if 90 < mid < 210 else 0.0


def colorize(img: Image.Image, skin_bgr: tuple | None = None,
             progress_cb=None) -> Image.Image:
    """
    Раскраска через colorizers (Zhang et al., Berkeley — siggraph17).
    skin_bgr оставлен для совместимости с UI, модель сама определяет цвета.
    """
    try:
        import torch
        from colorizers import siggraph17, preprocess_img, postprocess_tens
    except ImportError as e:
        raise RuntimeError(
            f"Не найден модуль colorizers: {e}\n"
            "Скопируй папку colorizers/ в корень проекта."
        )

    if progress_cb: progress_cb(8)

    # Загрузка модели
    colorizer = siggraph17(pretrained=True).eval()
    if progress_cb: progress_cb(25)

    # Подготовка входного изображения
    img_np = np.array(img.convert("RGB"))

    # preprocess_img принимает numpy HWC uint8
    tens_l_orig, tens_l_rs = preprocess_img(img_np, HW=(256, 256))
    if progress_cb: progress_cb(40)

    # Инференс
    with torch.no_grad():
        out_ab = colorizer(tens_l_rs).cpu()
    if progress_cb: progress_cb(70)

    # Сборка полноразмерного результата
    out_np = postprocess_tens(tens_l_orig, out_ab)  # float32 HWC [0,1]
    if progress_cb: progress_cb(88)

    result = Image.fromarray((out_np * 255).astype(np.uint8))

    # Приводим к размеру оригинала
    if result.size != img.size:
        result = result.resize(img.size, Image.LANCZOS)

    if progress_cb: progress_cb(100)
    return result