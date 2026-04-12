"""
Анализатор качества изображений.
Определяет параметры для адаптивной обработки.
"""

import cv2
import numpy as np
from PIL import Image


def analyze_image(img: Image.Image) -> dict:
    """
    Анализирует изображение и возвращает параметры для обработки.

    Returns:
        dict: {
            'sharpness': float (0-100),
            'noise_level': float (0-100),
            'contrast': float (0-100),
            'brightness': float (0-100),
            'quality_score': float (0-10),
            'denoise_strength': int (0-15),
            'clahe_clip': float (1.0-3.0),
            'sharpen_strength': float (0.0-2.0),
            'needs_denoise': bool,
            'needs_contrast_boost': bool,
            'needs_sharpen': bool
        }
    """
    # Конвертируем в numpy
    arr = np.array(img)
    arr_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(arr_bgr, cv2.COLOR_BGR2GRAY)

    # === 1. РЕЗКОСТЬ (Laplacian variance) ===
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness_raw = laplacian.var()
    sharpness = min(sharpness_raw / 10.0, 100.0)

    # === 2. ШУМ (через high-pass filter) ===
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    noise_raw = np.std(gray.astype(np.float32) - blur.astype(np.float32))
    noise_level = min(noise_raw * 2.0, 100.0)

    # === 3. КОНТРАСТ (стандартное отклонение) ===
    contrast_raw = gray.std()
    contrast = min(contrast_raw, 100.0)

    # === 4. ЯРКОСТЬ (средняя яркость) ===
    brightness = gray.mean()

    # === 5. ДЕТАЛИЗАЦИЯ (edge density) ===
    edges = cv2.Canny(gray, 50, 150)
    edge_density = (edges > 0).sum() / edges.size * 100.0

    # === 6. ЦВЕТОВАЯ НАСЫЩЕННОСТЬ ===
    hsv = cv2.cvtColor(arr_bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].mean()

    # === ОБЩАЯ ОЦЕНКА КАЧЕСТВА (0-10) ===
    quality_score = (
        (sharpness / 100.0) * 3.0 +           # резкость важнее всего
        (1 - noise_level / 100.0) * 2.5 +     # отсутствие шума
        (contrast / 100.0) * 2.0 +            # контраст
        (edge_density / 100.0) * 1.5 +        # детализация
        (saturation / 255.0) * 1.0            # насыщенность
    )

    # === АДАПТИВНЫЕ ПАРАМЕТРЫ ОБРАБОТКИ ===

    # Denoise strength (0-15)
    # Чем больше шума, тем сильнее denoise
    denoise_strength = int(np.clip(noise_raw / 2.0, 0, 15))

    # CLAHE clip limit (1.0-3.0)
    # Чем меньше контраст, тем сильнее усиление
    clahe_clip = float(np.clip(3.0 - (contrast_raw / 50.0), 1.0, 3.0))

    # Sharpen strength (0.0-2.0)
    # Чем меньше резкость, тем сильнее sharpen
    sharpen_strength = float(np.clip(2.0 - (sharpness_raw / 100.0), 0.0, 2.0))

    # === ФЛАГИ НЕОБХОДИМОСТИ ОБРАБОТКИ ===
    needs_denoise = noise_level > 20.0
    needs_contrast_boost = contrast < 40.0
    needs_sharpen = sharpness < 50.0

    return {
        # Метрики
        'sharpness': float(sharpness),
        'noise_level': float(noise_level),
        'contrast': float(contrast),
        'brightness': float(brightness),
        'edge_density': float(edge_density),
        'saturation': float(saturation),
        'quality_score': float(quality_score),

        # Параметры обработки
        'denoise_strength': denoise_strength,
        'clahe_clip': clahe_clip,
        'sharpen_strength': sharpen_strength,

        # Флаги
        'needs_denoise': needs_denoise,
        'needs_contrast_boost': needs_contrast_boost,
        'needs_sharpen': needs_sharpen
    }


def get_processing_summary(stats: dict) -> str:
    """
    Генерирует человекочитаемое описание обработки.
    """
    lines = []
    lines.append(f"Качество: {stats['quality_score']:.1f}/10")

    if stats['needs_denoise']:
        lines.append(f"Шумоподавление: {stats['denoise_strength']}")

    if stats['needs_contrast_boost']:
        lines.append(f"Усиление контраста: {stats['clahe_clip']:.1f}")

    if stats['needs_sharpen']:
        lines.append(f"Повышение резкости: {stats['sharpen_strength']:.1f}")

    return " | ".join(lines)
