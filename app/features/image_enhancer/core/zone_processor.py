"""
Зональные процессоры — слой 4c: фон, небо, одежда без лиц.

Статические методы CLAHE, detailEnhance, bilateral и vibrance по маскам
из ``ImageSegmentor``; интенсивность масштабируется от ``effect`` пайплайна.
"""
import cv2
import numpy as np
from PIL import Image


class ZoneProcessor:
    """
    Применяет специфичные улучшения к разным зонам изображения.
    """

    @staticmethod
    def process_clothing(img_arr: np.ndarray, intensity: float = 1.0) -> np.ndarray:
        """
        Обработка одежды: усиление деталей и текстур.

        Args:
            img_arr: numpy array RGB uint8
            intensity: интенсивность эффекта [0-1]

        Returns:
            обработанный массив RGB uint8
        """
        result = img_arr.copy()

        # Detail enhance для текстур ткани
        result = cv2.detailEnhance(result, sigma_s=8, sigma_r=0.1)

        # Aggressive unsharp mask для чёткости
        blur = cv2.GaussianBlur(result, (0, 0), 2.0)
        strength = 1.3 * intensity
        result = cv2.addWeighted(result, 1.0 + strength * 0.5, blur, -strength * 0.5, 0)
        result = np.clip(result, 0, 255).astype(np.uint8)

        # CLAHE для локального контраста
        lab = cv2.cvtColor(result, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5 * intensity, tileGridSize=(4, 4))
        l = clahe.apply(l)
        result = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)

        return result

    @staticmethod
    def process_background(img_arr: np.ndarray, intensity: float = 1.0) -> np.ndarray:
        """
        Обработка фона: баланс между чёткостью и естественностью.

        Args:
            img_arr: numpy array RGB uint8
            intensity: интенсивность эффекта [0-1]

        Returns:
            обработанный массив RGB uint8
        """
        result = img_arr.copy()

        # CLAHE для контраста
        lab = cv2.cvtColor(result, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0 * intensity, tileGridSize=(8, 8))
        l = clahe.apply(l)
        result = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)

        # Лёгкий bilateral filter для сглаживания артефактов
        result = cv2.bilateralFilter(result, 5, int(50 * intensity), int(50 * intensity))

        # Лёгкий detail enhance
        result = cv2.detailEnhance(result, sigma_s=10, sigma_r=0.15)

        return result

    @staticmethod
    def process_sky(img_arr: np.ndarray, intensity: float = 1.0) -> np.ndarray:
        """
        Обработка неба: vibrance boost + сглаживание.

        Args:
            img_arr: numpy array RGB uint8
            intensity: интенсивность эффекта [0-1]

        Returns:
            обработанный массив RGB uint8
        """
        result = img_arr.copy()

        # Vibrance boost в HSV
        hsv = cv2.cvtColor(result, cv2.COLOR_RGB2HSV).astype(np.float32)
        h, s, v = cv2.split(hsv)

        # Увеличиваем насыщенность только для ненасыщенных пикселей
        boost = 1.0 + 0.2 * intensity
        mask = (s < 180).astype(np.float32)
        s = s * (1 + (boost - 1) * mask)
        s = np.clip(s, 0, 255)

        hsv = cv2.merge([h, s, v]).astype(np.uint8)
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        # Сглаживание для естественности неба
        result = cv2.bilateralFilter(result, 7, int(75 * intensity), int(75 * intensity))

        return result

    @staticmethod
    def process_hair(img_arr: np.ndarray, intensity: float = 1.0) -> np.ndarray:
        """
        Обработка волос: усиление текстуры.

        Args:
            img_arr: numpy array RGB uint8
            intensity: интенсивность эффекта [0-1]

        Returns:
            обработанный массив RGB uint8
        """
        result = img_arr.copy()

        # Unsharp mask для текстуры волос
        blur = cv2.GaussianBlur(result, (0, 0), 2.0)
        strength = 1.5 * intensity
        result = cv2.addWeighted(result, 1.0 + strength * 0.5, blur, -strength * 0.5, 0)
        result = np.clip(result, 0, 255).astype(np.uint8)

        # Detail enhance
        result = cv2.detailEnhance(result, sigma_s=8, sigma_r=0.1)

        return result

    @staticmethod
    def apply_zone_processing(
        base_img: Image.Image,
        zones: dict,
        masks: dict,
        intensity: float = 1.0
    ) -> Image.Image:
        """
        Применяет зональную обработку к изображению.

        Args:
            base_img: базовое изображение (после SwinIR)
            zones: словарь зон {'clothing': arr, 'background': arr, ...}
            masks: словарь масок {'clothing': mask, 'background': mask, ...}
            intensity: общая интенсивность

        Returns:
            обработанное изображение
        """
        result = np.array(base_img, dtype=np.float32)

        # Применяем каждую зону через маску
        for zone_name, zone_arr in zones.items():
            if zone_name not in masks:
                continue

            mask = masks[zone_name]
            if mask.max() < 0.01:  # Пустая маска
                continue

            # Расширяем маску до 3 каналов
            mask_3ch = mask[:, :, np.newaxis]

            # Blend зоны с базой
            zone_float = zone_arr.astype(np.float32)
            result = result * (1 - mask_3ch) + zone_float * mask_3ch

        result = np.clip(result, 0, 255).astype(np.uint8)
        return Image.fromarray(result)
