"""
Постобработчик для коррекции артефактов после зональной обработки.
"""
import cv2
import numpy as np
from PIL import Image


class PostProcessor:
    """
    Автокоррекция артефактов: пересветы, тени, цветовой сдвиг, шероховатость.
    """

    @staticmethod
    def process(
        result: Image.Image,
        original: Image.Image,
        masks: dict = None,
        intensity: float = 1.0,
        tone_map: bool = True,
    ) -> Image.Image:
        """
        Полная постобработка с коррекцией артефактов.

        Args:
            result: результат после зональной обработки
            original: оригинальное изображение (апскейленное)
            masks: словарь масок зон (опционально)
            intensity: интенсивность коррекции [0-1]

        Returns:
            скорректированное изображение
        """
        result_arr = np.array(result)
        original_arr = np.array(original)

        # Resize оригинала если размеры не совпадают
        if result_arr.shape[:2] != original_arr.shape[:2]:
            original_arr = cv2.resize(
                original_arr,
                (result_arr.shape[1], result_arr.shape[0]),
                interpolation=cv2.INTER_LANCZOS4
            )

        # 1. Highlight recovery
        result_arr = PostProcessor._recover_highlights(result_arr, original_arr, intensity)

        # 2. Shadow recovery
        result_arr = PostProcessor._recover_shadows(result_arr, original_arr, intensity)

        # 3. Цветовое выравнивание зон
        if masks is not None:
            result_arr = PostProcessor._color_zone_matching(result_arr, original_arr, masks, intensity)

        # 4. Сглаживание шероховатости
        result_arr = PostProcessor._smooth_artifacts(result_arr, original_arr, intensity)

        # 5. Глобальный тонмаппинг (только при высокой интенсивности)
        if tone_map:
            result_arr = PostProcessor._tone_mapping(result_arr, intensity)

        return Image.fromarray(result_arr)

    @staticmethod
    def _recover_highlights(result: np.ndarray, original: np.ndarray, intensity: float) -> np.ndarray:
        """
        Восстановление деталей в пересвеченных областях.
        """
        # Конвертируем в LAB
        result_lab = cv2.cvtColor(result, cv2.COLOR_RGB2LAB).astype(np.float32)
        original_lab = cv2.cvtColor(original, cv2.COLOR_RGB2LAB).astype(np.float32)

        l_result = result_lab[:, :, 0]
        l_original = original_lab[:, :, 0]

        # Маска пересвета: L > 240 в результате но был < 220 в оригинале
        highlight_mask = ((l_result > 240) & (l_original < 220)).astype(np.float32)
        highlight_mask = cv2.GaussianBlur(highlight_mask, (15, 15), 5)

        # Восстанавливаем детали из оригинала
        strength = intensity * 0.6
        result_lab[:, :, 0] = l_result * (1 - highlight_mask * strength) + \
                               l_original * (highlight_mask * strength)

        result_corrected = cv2.cvtColor(result_lab.astype(np.uint8), cv2.COLOR_LAB2RGB)
        return result_corrected

    @staticmethod
    def _recover_shadows(result: np.ndarray, original: np.ndarray, intensity: float) -> np.ndarray:
        """
        Восстановление деталей в затемнённых областях.
        """
        # Конвертируем в LAB
        result_lab = cv2.cvtColor(result, cv2.COLOR_RGB2LAB).astype(np.float32)
        original_lab = cv2.cvtColor(original, cv2.COLOR_RGB2LAB).astype(np.float32)

        l_result = result_lab[:, :, 0]
        l_original = original_lab[:, :, 0]

        # Маска теней: L < 30 в результате но был > 20 в оригинале
        shadow_mask = ((l_result < 30) & (l_original > 20)).astype(np.float32)
        shadow_mask = cv2.GaussianBlur(shadow_mask, (15, 15), 5)

        # Восстанавливаем детали из оригинала
        strength = intensity * 0.5
        result_lab[:, :, 0] = l_result * (1 - shadow_mask * strength) + \
                               l_original * (shadow_mask * strength)

        result_corrected = cv2.cvtColor(result_lab.astype(np.uint8), cv2.COLOR_LAB2RGB)
        return result_corrected

    @staticmethod
    def _color_zone_matching(
        result: np.ndarray,
        original: np.ndarray,
        masks: dict,
        intensity: float
    ) -> np.ndarray:
        """
        Цветовое выравнивание зон через histogram matching.
        """
        try:
            from skimage.exposure import match_histograms
        except ImportError:
            print("[post_processor] skimage not available, skipping color matching")
            return result

        result_float = result.astype(np.float32)

        # Применяем histogram matching к каждой зоне
        for zone_name, mask in masks.items():
            if mask.max() < 0.01:
                continue

            # Расширяем маску до 3 каналов
            mask_3ch = mask[:, :, np.newaxis]

            # Histogram matching
            matched = match_histograms(result, original, channel_axis=-1)

            # Blend через маску
            strength = intensity * 0.4
            result_float = result_float * (1 - mask_3ch * strength) + \
                          matched.astype(np.float32) * (mask_3ch * strength)

        result_corrected = np.clip(result_float, 0, 255).astype(np.uint8)
        return result_corrected

    @staticmethod
    def _smooth_artifacts(result: np.ndarray, original: np.ndarray, intensity: float) -> np.ndarray:
        """
        Сглаживание шероховатости только в проблемных зонах.
        """
        # Конвертируем в LAB для анализа
        result_lab = cv2.cvtColor(result, cv2.COLOR_RGB2LAB)
        original_lab = cv2.cvtColor(original, cv2.COLOR_RGB2LAB)

        # Маска проблемных зон: разница по L каналу > 30
        l_diff = np.abs(result_lab[:, :, 0].astype(np.float32) -
                       original_lab[:, :, 0].astype(np.float32))
        artifact_mask = (l_diff > 30).astype(np.float32)
        artifact_mask = cv2.GaussianBlur(artifact_mask, (21, 21), 7)

        # Bilateral filter только на проблемных зонах
        smoothed = cv2.bilateralFilter(result, 7, 40, 40)

        # Blend через маску
        strength = intensity * 0.5
        artifact_mask_3ch = artifact_mask[:, :, np.newaxis]
        result_corrected = result.astype(np.float32) * (1 - artifact_mask_3ch * strength) + \
                          smoothed.astype(np.float32) * (artifact_mask_3ch * strength)

        result_corrected = np.clip(result_corrected, 0, 255).astype(np.uint8)
        return result_corrected

    @staticmethod
    def _tone_mapping(result: np.ndarray, intensity: float) -> np.ndarray:
        """
        Глобальный тонмаппинг с мягкой S-кривой.
        """
        # Конвертируем в LAB
        lab = cv2.cvtColor(result, cv2.COLOR_RGB2LAB).astype(np.float32)
        l = lab[:, :, 0]

        # Нормализация L канала
        l_min, l_max = l.min(), l.max()
        if l_max > l_min:
            l_norm = (l - l_min) / (l_max - l_min) * 255.0
        else:
            l_norm = l

        # S-кривая через LUT
        lut = np.arange(256, dtype=np.float32)
        # Мягкая S-кривая: y = x + (sin(2πx/255 - π/2) + 1) * strength
        strength = intensity * 15.0
        lut = lut + (np.sin(2 * np.pi * lut / 255.0 - np.pi / 2) + 1) * strength
        lut = np.clip(lut, 0, 255)

        # Применяем LUT
        l_mapped = cv2.LUT(l_norm.astype(np.uint8), lut.astype(np.uint8)).astype(np.float32)

        # Восстанавливаем диапазон
        if l_max > l_min:
            l_final = l_mapped / 255.0 * (l_max - l_min) + l_min
        else:
            l_final = l_mapped

        lab[:, :, 0] = l_final
        result_corrected = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB)

        return result_corrected
