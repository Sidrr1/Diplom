"""
Frequency separation — слой 6: текстура оригинала + тон/форма улучшенного.

Разделение на низкие (цвет) и высокие (детали) частоты; ``adaptive_*``
разная сила для лица и фона по ``face_mask``.
"""
import cv2
import numpy as np
from PIL import Image


def frequency_separation(
    original: Image.Image,
    enhanced: Image.Image,
    blur_radius: float = 3.0,
    detail_strength: float = 0.8
) -> Image.Image:
    """
    Применяет frequency separation: детали оригинала + улучшенная форма/цвет.

    Args:
        original: оригинальное изображение
        enhanced: улучшенное изображение (SwinIR + CodeFormer)
        blur_radius: радиус размытия для разделения частот (3.0 = хороший баланс)
        detail_strength: сила деталей оригинала (0.0-1.0)

    Returns:
        изображение с деталями оригинала и улучшенной формой
    """
    # Конвертируем в numpy float32
    orig_arr = np.array(original).astype(np.float32)
    enh_arr = np.array(enhanced).astype(np.float32)

    # Resize enhanced к размеру original если нужно
    if orig_arr.shape[:2] != enh_arr.shape[:2]:
        enh_arr = cv2.resize(
            enh_arr,
            (orig_arr.shape[1], orig_arr.shape[0]),
            interpolation=cv2.INTER_LANCZOS4
        )

    # === ОРИГИНАЛ: Извлекаем высокие частоты (текстура, детали) ===
    # Низкие частоты = размытие
    orig_low = cv2.GaussianBlur(orig_arr, (0, 0), blur_radius)
    # Высокие частоты = оригинал - низкие
    orig_high = orig_arr - orig_low

    # === ENHANCED: Извлекаем низкие частоты (форма, цвет) ===
    enh_low = cv2.GaussianBlur(enh_arr, (0, 0), blur_radius)

    # === КОМПОЗИТ: Низкие частоты enhanced + Высокие частоты original ===
    result = enh_low + orig_high * detail_strength

    # Clip и конвертация обратно
    result = np.clip(result, 0, 255).astype(np.uint8)
    return Image.fromarray(result)


def adaptive_frequency_separation(
    original: Image.Image,
    enhanced: Image.Image,
    face_mask: np.ndarray = None,
    face_detail_strength: float = 0.6,
    background_detail_strength: float = 0.9,
    blur_radius: float = 3.0
) -> Image.Image:
    """
    Адаптивный frequency separation с разной силой для лица и фона.

    Args:
        original: оригинальное изображение
        enhanced: улучшенное изображение
        face_mask: маска лица (0-1 float), если None — uniform strength
        face_detail_strength: сила деталей для лица (меньше = больше улучшения)
        background_detail_strength: сила деталей для фона (больше = больше оригинала)
        blur_radius: радиус размытия

    Returns:
        изображение с адаптивным frequency separation
    """
    # Конвертируем в numpy float32
    orig_arr = np.array(original).astype(np.float32)
    enh_arr = np.array(enhanced).astype(np.float32)

    # Resize enhanced к размеру original если нужно
    if orig_arr.shape[:2] != enh_arr.shape[:2]:
        enh_arr = cv2.resize(
            enh_arr,
            (orig_arr.shape[1], orig_arr.shape[0]),
            interpolation=cv2.INTER_LANCZOS4
        )

    # Извлекаем частоты
    orig_low = cv2.GaussianBlur(orig_arr, (0, 0), blur_radius)
    orig_high = orig_arr - orig_low
    enh_low = cv2.GaussianBlur(enh_arr, (0, 0), blur_radius)

    if face_mask is None:
        # Uniform strength
        result = enh_low + orig_high * face_detail_strength
    else:
        # Адаптивная сила: лицо меньше деталей, фон больше
        # Resize маски если нужно
        if face_mask.shape[:2] != orig_arr.shape[:2]:
            face_mask = cv2.resize(
                face_mask,
                (orig_arr.shape[1], orig_arr.shape[0]),
                interpolation=cv2.INTER_LINEAR
            )

        # Создаём карту силы деталей
        face_mask_3ch = face_mask[:, :, np.newaxis]
        detail_strength_map = (
            face_mask_3ch * face_detail_strength +
            (1 - face_mask_3ch) * background_detail_strength
        )

        # Применяем адаптивно
        result = enh_low + orig_high * detail_strength_map

    result = np.clip(result, 0, 255).astype(np.uint8)
    return Image.fromarray(result)
