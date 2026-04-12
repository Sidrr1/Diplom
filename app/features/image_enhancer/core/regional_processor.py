"""
Региональный процессор для применения разных стратегий улучшения к разным частям изображения.
"""
import cv2
import numpy as np
from PIL import Image


class RegionalProcessor:
    """
    Применяет разные модели улучшения к разным регионам изображения.

    Стратегии:
    - Кожа лица: CodeFormer с высоким fidelity (0.8-0.9)
    - Глаза/рот: CodeFormer с сохранением деталей (fidelity 0.9-1.0)
    - Волосы: SwinIR с сохранением текстуры
    - Одежда: SwinIR с усилением деталей
    - Фон: стандартный SwinIR
    """

    def __init__(self, model_manager):
        self.model_manager = model_manager

    def process_regions(
        self,
        original: Image.Image,
        upscaled: Image.Image,
        face_bboxes: list,
        fidelity: float = 0.7
    ) -> Image.Image:
        """
        Обработка изображения с региональными стратегиями.

        Args:
            original: оригинальное изображение
            upscaled: изображение после SwinIR x4
            face_bboxes: список bbox лиц
            fidelity: базовый параметр fidelity для CodeFormer

        Returns:
            улучшенное изображение с региональной обработкой
        """
        if not face_bboxes:
            return upscaled.copy()

        result = np.array(upscaled, dtype=np.float32)
        h, w = result.shape[:2]

        # Получаем модели
        parser = self.model_manager.get_face_parser()
        enhancer = self.model_manager.get_face_enhancer()

        # Собираем все лица для батчинга
        face_data = []

        for bbox in face_bboxes:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)

            face_w = x2 - x1
            face_h = y2 - y1

            if face_w < 20 or face_h < 20:
                continue

            # Расширяем bbox на 20% для контекста
            expand_ratio = 0.2
            expand_w = int(face_w * expand_ratio / 2)
            expand_h = int(face_h * expand_ratio / 2)

            x1_exp = max(0, x1 - expand_w)
            y1_exp = max(0, y1 - expand_h)
            x2_exp = min(w, x2 + expand_w)
            y2_exp = min(h, y2 + expand_h)

            # Вырезаем расширенную область
            face_img = upscaled.crop((x1_exp, y1_exp, x2_exp, y2_exp))

            face_data.append({
                'img': face_img,
                'bbox_exp': (x1_exp, y1_exp, x2_exp, y2_exp),
                'bbox_orig': (x1, y1, x2, y2),
                'size': min(face_w, face_h)
            })

        if not face_data:
            return upscaled.copy()

        # Батчинг: обрабатываем все лица через CodeFormer сразу
        face_imgs = [fd['img'] for fd in face_data]
        enhanced_faces = enhancer.enhance_faces_batch(face_imgs, fidelity=fidelity)

        # ID preservation для каждого лица
        identity_preservor = self.model_manager.get_identity_preservor()
        preserved_faces = []
        for original_face, enhanced_face in zip(face_imgs, enhanced_faces):
            preserved = identity_preservor.preserve_identity(
                original=original_face,
                enhanced=enhanced_face,
                threshold=0.65
            )
            preserved_faces.append(preserved)

        # Применяем региональные улучшения к каждому лицу
        for face_info, enhanced_face in zip(face_data, preserved_faces):
            # Парсим лицо на регионы
            parsing = parser.parse_face(face_info['img'])
            regions = parser.get_face_regions(parsing)

            # Применяем региональные улучшения
            enhanced_arr = np.array(enhanced_face, dtype=np.float32)
            enhanced_arr = self._apply_regional_enhancements(
                face_img=face_info['img'],
                enhanced_face=enhanced_arr,
                regions=regions,
                fidelity=fidelity
            )

            # Композитинг с адаптивным feathering
            result = self._composite_face_region(
                result=result,
                enhanced_face=enhanced_arr,
                bbox=face_info['bbox_exp'],
                original_bbox=face_info['bbox_orig'],
                face_size=face_info['size']
            )

        result = np.clip(result, 0, 255).astype(np.uint8)
        return Image.fromarray(result)

    def _apply_regional_enhancements(
        self,
        face_img: Image.Image,
        enhanced_face: np.ndarray,
        regions: dict,
        fidelity: float
    ) -> np.ndarray:
        """
        Применяет специфичные улучшения к разным регионам лица.

        Args:
            face_img: оригинальное изображение лица
            enhanced_face: улучшенное лицо через CodeFormer
            regions: словарь масок регионов
            fidelity: параметр fidelity

        Returns:
            улучшенное изображение с региональными корректировками
        """
        result = enhanced_face.copy()
        original_arr = np.array(face_img, dtype=np.float32)

        # Глаза и рот: максимальное сохранение деталей (blend с оригиналом)
        eyes_mask = regions['eyes']
        mouth_mask = regions['mouth']
        detail_mask = cv2.bitwise_or(eyes_mask, mouth_mask)

        if detail_mask.max() > 0:
            # Размываем маску для плавного перехода
            detail_mask_blur = cv2.GaussianBlur(detail_mask, (15, 15), 5)
            detail_mask_norm = detail_mask_blur.astype(np.float32) / 255.0
            detail_mask_norm = detail_mask_norm[:, :, np.newaxis]

            # Blend: больше оригинала для сохранения деталей
            preservation_strength = 0.3  # 30% оригинала
            result = result * (1 - detail_mask_norm * preservation_strength) + \
                     original_arr * (detail_mask_norm * preservation_strength)

        # Кожа: лёгкое сглаживание для естественности
        skin_mask = regions['skin']
        if skin_mask.max() > 0:
            skin_mask_blur = cv2.GaussianBlur(skin_mask, (21, 21), 7)
            skin_mask_norm = skin_mask_blur.astype(np.float32) / 255.0

            # Лёгкое bilateral filter для сглаживания кожи
            skin_region = np.clip(result, 0, 255).astype(np.uint8)
            skin_smoothed = cv2.bilateralFilter(skin_region, 9, 75, 75)
            skin_smoothed = skin_smoothed.astype(np.float32)

            skin_mask_3ch = skin_mask_norm[:, :, np.newaxis]
            smoothing_strength = 0.2  # 20% сглаживания
            result = result * (1 - skin_mask_3ch * smoothing_strength) + \
                     skin_smoothed * (skin_mask_3ch * smoothing_strength)

        # Волосы: усиление текстуры
        hair_mask = regions['hair']
        if hair_mask.max() > 0:
            hair_mask_blur = cv2.GaussianBlur(hair_mask, (15, 15), 5)
            hair_mask_norm = hair_mask_blur.astype(np.float32) / 255.0

            # Unsharp mask для усиления текстуры волос
            hair_region = np.clip(result, 0, 255).astype(np.uint8)
            hair_blur = cv2.GaussianBlur(hair_region, (0, 0), 2.0)
            hair_sharp = cv2.addWeighted(hair_region, 1.5, hair_blur, -0.5, 0)
            hair_sharp = hair_sharp.astype(np.float32)

            hair_mask_3ch = hair_mask_norm[:, :, np.newaxis]
            result = result * (1 - hair_mask_3ch) + hair_sharp * hair_mask_3ch

        # Одежда: усиление деталей и контраста
        cloth_mask = regions['cloth']
        if cloth_mask.max() > 0:
            cloth_mask_blur = cv2.GaussianBlur(cloth_mask, (15, 15), 5)
            cloth_mask_norm = cloth_mask_blur.astype(np.float32) / 255.0

            # CLAHE для усиления деталей одежды
            cloth_region = np.clip(result, 0, 255).astype(np.uint8)
            cloth_lab = cv2.cvtColor(cloth_region, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(cloth_lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            cloth_enhanced = cv2.cvtColor(cv2.merge([l_enhanced, a, b]), cv2.COLOR_LAB2RGB)
            cloth_enhanced = cloth_enhanced.astype(np.float32)

            cloth_mask_3ch = cloth_mask_norm[:, :, np.newaxis]
            enhancement_strength = 0.4  # 40% усиления
            result = result * (1 - cloth_mask_3ch * enhancement_strength) + \
                     cloth_enhanced * (cloth_mask_3ch * enhancement_strength)

        return result

    def _composite_face_region(
        self,
        result: np.ndarray,
        enhanced_face: np.ndarray,
        bbox: tuple,
        original_bbox: tuple,
        face_size: int
    ) -> np.ndarray:
        """
        Композитинг улучшенного лица с адаптивным feathering.

        Args:
            result: результирующее изображение
            enhanced_face: улучшенное лицо
            bbox: расширенный bbox (x1_exp, y1_exp, x2_exp, y2_exp)
            original_bbox: оригинальный bbox (x1, y1, x2, y2)
            face_size: размер лица для адаптивного feathering

        Returns:
            результат с композитом
        """
        x1_exp, y1_exp, x2_exp, y2_exp = bbox
        x1, y1, x2, y2 = original_bbox

        h, w = result.shape[:2]

        # Адаптивный feathering: больше для больших лиц
        feather = max(10, min(int(face_size * 0.1), 40))

        # Создаём маску с центром на оригинальном bbox
        mask = np.zeros((h, w), dtype=np.float32)

        # Центральная область (оригинальный bbox) = 1.0
        mask[y1:y2, x1:x2] = 1.0

        # Размываем для плавного перехода
        kernel_size = feather * 2 + 1
        if kernel_size % 2 == 0:
            kernel_size += 1
        mask = cv2.GaussianBlur(mask, (kernel_size, kernel_size), feather / 2)
        mask = mask[:, :, np.newaxis]

        # Вставляем enhanced face в расширенную область
        enhanced_full = result.copy()
        face_h = y2_exp - y1_exp
        face_w = x2_exp - x1_exp

        if face_h > 0 and face_w > 0:
            # Resize enhanced face к размеру расширенного bbox
            enhanced_resized = cv2.resize(
                enhanced_face.astype(np.uint8),
                (face_w, face_h),
                interpolation=cv2.INTER_LANCZOS4
            ).astype(np.float32)

            enhanced_full[y1_exp:y2_exp, x1_exp:x2_exp] = enhanced_resized

        # Blend через маску
        result = result * (1 - mask) + enhanced_full * mask

        return result
