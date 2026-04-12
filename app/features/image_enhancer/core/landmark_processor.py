"""
Landmark-based зональная обработка лица.
Обрабатывает каждую зону лица отдельно по координатам из MediaPipe.
"""
import cv2
import numpy as np
from PIL import Image


class LandmarkProcessor:
    """
    Обработка зон лица по landmark координатам.
    """

    @staticmethod
    def process_face_zones(
        img: Image.Image,
        landmarks_data: dict,
        face_bbox: tuple,
        intensity: float = 1.0
    ) -> Image.Image:
        """
        Обработка зон лица по landmarks.

        Args:
            img: изображение с лицом
            landmarks_data: результат LandmarkAnalyzer.analyze()
            face_bbox: bbox лица (x1, y1, x2, y2)
            intensity: интенсивность обработки (0.0-1.0)

        Returns:
            обработанное изображение
        """
        if not landmarks_data['zones']:
            # Нет зон — возвращаем как есть
            return img

        base_arr = np.array(img)
        result = base_arr.astype(np.float32)

        zones = landmarks_data['zones']

        # Обрабатываем каждую зону
        if 'forehead' in zones:
            result = LandmarkProcessor._process_forehead(result, zones['forehead'], intensity)

        if 'left_eye' in zones:
            result = LandmarkProcessor._process_eye(result, zones['left_eye'], intensity)

        if 'right_eye' in zones:
            result = LandmarkProcessor._process_eye(result, zones['right_eye'], intensity)

        if 'nose' in zones:
            result = LandmarkProcessor._process_nose(result, zones['nose'], intensity)

        if 'mouth' in zones:
            result = LandmarkProcessor._process_mouth(result, zones['mouth'], intensity)

        if 'left_cheek' in zones:
            result = LandmarkProcessor._process_cheek(result, zones['left_cheek'], intensity)

        if 'right_cheek' in zones:
            result = LandmarkProcessor._process_cheek(result, zones['right_cheek'], intensity)

        if 'chin' in zones:
            result = LandmarkProcessor._process_chin(result, zones['chin'], intensity)

        result = np.clip(result, 0, 255).astype(np.uint8)
        return Image.fromarray(result)

    @staticmethod
    def _process_forehead(arr: np.ndarray, bbox: tuple, intensity: float) -> np.ndarray:
        """Обработка лба: лёгкое сглаживание + CLAHE."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(arr.shape[1], x2), min(arr.shape[0], y2)

        if x2 <= x1 or y2 <= y1:
            return arr

        zone = arr[y1:y2, x1:x2].copy()
        zone_uint8 = zone.astype(np.uint8)

        # Bilateral filter для сглаживания
        zone_bgr = cv2.cvtColor(zone_uint8, cv2.COLOR_RGB2BGR)
        zone_bgr = cv2.bilateralFilter(zone_bgr, 9, 40 * intensity, 40 * intensity)

        # CLAHE для выравнивания тона
        lab = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5 * intensity, tileGridSize=(4, 4))
        l = clahe.apply(l)
        zone_bgr = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        zone_processed = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)

        # Feathering
        mask = LandmarkProcessor._create_feather_mask(x2 - x1, y2 - y1, feather=10)
        arr[y1:y2, x1:x2] = arr[y1:y2, x1:x2] * (1 - mask) + zone_processed * mask

        return arr

    @staticmethod
    def _process_eye(arr: np.ndarray, bbox: tuple, intensity: float) -> np.ndarray:
        """Обработка глаз: sharpening + contrast."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(arr.shape[1], x2), min(arr.shape[0], y2)

        if x2 <= x1 or y2 <= y1:
            return arr

        zone = arr[y1:y2, x1:x2].copy()
        zone_uint8 = zone.astype(np.uint8)
        zone_bgr = cv2.cvtColor(zone_uint8, cv2.COLOR_RGB2BGR)

        # Unsharp mask для резкости
        blur = cv2.GaussianBlur(zone_bgr, (0, 0), 1.0)
        alpha = 1.0 + 0.5 * intensity
        beta = -0.5 * intensity
        zone_bgr = cv2.addWeighted(zone_bgr, alpha, blur, beta, 0)

        # CLAHE для контраста
        lab = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0 * intensity, tileGridSize=(4, 4))
        l = clahe.apply(l)
        zone_bgr = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        zone_processed = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)

        # Feathering
        mask = LandmarkProcessor._create_feather_mask(x2 - x1, y2 - y1, feather=8)
        arr[y1:y2, x1:x2] = arr[y1:y2, x1:x2] * (1 - mask) + zone_processed * mask

        return arr

    @staticmethod
    def _process_nose(arr: np.ndarray, bbox: tuple, intensity: float) -> np.ndarray:
        """Обработка носа: лёгкое сглаживание + sharpening."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(arr.shape[1], x2), min(arr.shape[0], y2)

        if x2 <= x1 or y2 <= y1:
            return arr

        zone = arr[y1:y2, x1:x2].copy()
        zone_uint8 = zone.astype(np.uint8)
        zone_bgr = cv2.cvtColor(zone_uint8, cv2.COLOR_RGB2BGR)

        # Bilateral + unsharp
        zone_bgr = cv2.bilateralFilter(zone_bgr, 5, 30 * intensity, 30 * intensity)
        blur = cv2.GaussianBlur(zone_bgr, (0, 0), 0.8)
        alpha = 1.0 + 0.3 * intensity
        beta = -0.3 * intensity
        zone_bgr = cv2.addWeighted(zone_bgr, alpha, blur, beta, 0)

        zone_processed = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)

        # Feathering
        mask = LandmarkProcessor._create_feather_mask(x2 - x1, y2 - y1, feather=8)
        arr[y1:y2, x1:x2] = arr[y1:y2, x1:x2] * (1 - mask) + zone_processed * mask

        return arr

    @staticmethod
    def _process_mouth(arr: np.ndarray, bbox: tuple, intensity: float) -> np.ndarray:
        """Обработка рта: sharpening + saturation boost."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(arr.shape[1], x2), min(arr.shape[0], y2)

        if x2 <= x1 or y2 <= y1:
            return arr

        zone = arr[y1:y2, x1:x2].copy()
        zone_uint8 = zone.astype(np.uint8)
        zone_bgr = cv2.cvtColor(zone_uint8, cv2.COLOR_RGB2BGR)

        # Unsharp mask
        blur = cv2.GaussianBlur(zone_bgr, (0, 0), 1.0)
        alpha = 1.0 + 0.4 * intensity
        beta = -0.4 * intensity
        zone_bgr = cv2.addWeighted(zone_bgr, alpha, blur, beta, 0)

        # Saturation boost
        hsv = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1.0 + 0.15 * intensity), 0, 255)
        zone_bgr = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        zone_processed = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)

        # Feathering
        mask = LandmarkProcessor._create_feather_mask(x2 - x1, y2 - y1, feather=8)
        arr[y1:y2, x1:x2] = arr[y1:y2, x1:x2] * (1 - mask) + zone_processed * mask

        return arr

    @staticmethod
    def _process_cheek(arr: np.ndarray, bbox: tuple, intensity: float) -> np.ndarray:
        """Обработка щёк: сглаживание + тонирование."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(arr.shape[1], x2), min(arr.shape[0], y2)

        if x2 <= x1 or y2 <= y1:
            return arr

        zone = arr[y1:y2, x1:x2].copy()
        zone_uint8 = zone.astype(np.uint8)
        zone_bgr = cv2.cvtColor(zone_uint8, cv2.COLOR_RGB2BGR)

        # Bilateral filter для гладкой кожи
        zone_bgr = cv2.bilateralFilter(zone_bgr, 9, 50 * intensity, 50 * intensity)

        # CLAHE для выравнивания тона
        lab = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5 * intensity, tileGridSize=(4, 4))
        l = clahe.apply(l)
        zone_bgr = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        zone_processed = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)

        # Feathering
        mask = LandmarkProcessor._create_feather_mask(x2 - x1, y2 - y1, feather=12)
        arr[y1:y2, x1:x2] = arr[y1:y2, x1:x2] * (1 - mask) + zone_processed * mask

        return arr

    @staticmethod
    def _process_chin(arr: np.ndarray, bbox: tuple, intensity: float) -> np.ndarray:
        """Обработка подбородка: сглаживание + контраст."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(arr.shape[1], x2), min(arr.shape[0], y2)

        if x2 <= x1 or y2 <= y1:
            return arr

        zone = arr[y1:y2, x1:x2].copy()
        zone_uint8 = zone.astype(np.uint8)
        zone_bgr = cv2.cvtColor(zone_uint8, cv2.COLOR_RGB2BGR)

        # Bilateral filter
        zone_bgr = cv2.bilateralFilter(zone_bgr, 7, 40 * intensity, 40 * intensity)

        # CLAHE
        lab = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.8 * intensity, tileGridSize=(4, 4))
        l = clahe.apply(l)
        zone_bgr = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        zone_processed = cv2.cvtColor(zone_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)

        # Feathering
        mask = LandmarkProcessor._create_feather_mask(x2 - x1, y2 - y1, feather=10)
        arr[y1:y2, x1:x2] = arr[y1:y2, x1:x2] * (1 - mask) + zone_processed * mask

        return arr

    @staticmethod
    def _create_feather_mask(width: int, height: int, feather: int) -> np.ndarray:
        """
        Создаёт маску с feathering по краям.

        Args:
            width, height: размер маски
            feather: размер feathering в пикселях

        Returns:
            маска (height, width, 3) float32 [0-1]
        """
        mask = np.ones((height, width), dtype=np.float32)

        # Feathering по краям
        for i in range(feather):
            alpha = i / feather
            # Верх
            if i < height:
                mask[i, :] *= alpha
            # Низ
            if height - i - 1 >= 0:
                mask[height - i - 1, :] *= alpha
            # Лево
            if i < width:
                mask[:, i] *= alpha
            # Право
            if width - i - 1 >= 0:
                mask[:, width - i - 1] *= alpha

        # Expand to 3 channels
        mask = mask[:, :, np.newaxis]
        return mask
