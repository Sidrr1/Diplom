"""
Landmark analyzer — слой 3.5: MediaPipe FaceMesh или антропометрический fallback.

Возвращает bbox зон лица (лоб, глаза, рот…) для ``LandmarkProcessor`` (слой 4b).
"""
import cv2
import numpy as np
from PIL import Image


class LandmarkAnalyzer:
    """
    Анализ лица через MediaPipe 468 точек с fallback на антропометрические пропорции.
    """

    def __init__(self):
        """MediaPipe загружается лениво в ``load()``; при ошибке — anthropometric fallback."""
        self.face_mesh = None
        self.available = False

    def load(self):
        """Lazy load MediaPipe."""
        if self.face_mesh is not None:
            return

        try:
            import mediapipe as mp
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5
            )
            self.available = True
            print("[landmark] Loaded MediaPipe FaceMesh")
        except Exception as e:
            self.available = False
            # Тихий fallback

    def analyze(self, img: Image.Image, face_bbox: tuple = None) -> dict:
        """
        Анализ лица с получением координат всех элементов.

        Args:
            img: PIL Image с лицом
            face_bbox: (x1, y1, x2, y2) bbox лица от RetinaFace (опционально)

        Returns:
            dict с zones, confidence, inferred
        """
        self.load()

        w, h = img.size
        result = {
            'found': False,
            'landmarks': {},
            'zones': {},
            'confidence': 0.0,
            'inferred': []
        }

        if not self.available:
            # Fallback: антропометрические пропорции
            if face_bbox:
                result['zones'] = self._anthropometric_fallback(face_bbox, w, h)
                result['inferred'] = list(result['zones'].keys())
                result['confidence'] = 0.3
            return result

        # MediaPipe детекция
        arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        results = self.face_mesh.process(arr)

        if not results.multi_face_landmarks:
            # Нет лица — fallback
            if face_bbox:
                result['zones'] = self._anthropometric_fallback(face_bbox, w, h)
                result['inferred'] = list(result['zones'].keys())
                result['confidence'] = 0.3
                print("[landmark] No landmarks found, using anthropometric fallback")
            return result

        # Извлекаем landmarks
        face_landmarks = results.multi_face_landmarks[0]
        landmarks = {}
        for idx, landmark in enumerate(face_landmarks.landmark):
            landmarks[idx] = (int(landmark.x * w), int(landmark.y * h))

        result['found'] = True
        result['landmarks'] = landmarks
        result['confidence'] = 0.9  # MediaPipe не даёт confidence, ставим высокий

        # Извлекаем зоны из landmarks
        result['zones'] = self._extract_zones(landmarks, w, h)

        print(f"[landmark] Found {len(landmarks)} landmarks, confidence: {result['confidence']:.2f}")
        return result

    def _extract_zones(self, landmarks: dict, w: int, h: int) -> dict:
        """Извлечение зон из MediaPipe landmarks."""
        zones = {}

        # Ключевые индексы MediaPipe
        LEFT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133]
        RIGHT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263]
        NOSE = [1, 2, 98, 327, 168, 5, 4, 19, 94]
        MOUTH = [61, 84, 17, 314, 405, 321, 375, 291, 308]
        CHIN = [152, 148, 176, 149, 150, 136, 172]
        LEFT_EYEBROW = [70, 63, 105, 66, 107]
        RIGHT_EYEBROW = [336, 296, 334, 293, 300]

        # Извлекаем bbox для каждой зоны
        for zone_name, indices in [
            ('left_eye', LEFT_EYE),
            ('right_eye', RIGHT_EYE),
            ('nose', NOSE),
            ('mouth', MOUTH),
            ('chin', CHIN),
            ('left_eyebrow', LEFT_EYEBROW),
            ('right_eyebrow', RIGHT_EYEBROW)
        ]:
            points = [landmarks[i] for i in indices if i in landmarks]
            if points:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                zones[zone_name] = (min(xs), min(ys), max(xs), max(ys))

        # Лоб (над бровями)
        if 'left_eyebrow' in zones and 'right_eyebrow' in zones:
            brow_top = min(zones['left_eyebrow'][1], zones['right_eyebrow'][1])
            brow_left = zones['left_eyebrow'][0]
            brow_right = zones['right_eyebrow'][2]
            forehead_height = int((brow_top - 0) * 0.8)  # 80% до верха
            zones['forehead'] = (brow_left, 0, brow_right, brow_top)

        # Щёки (между глазами и ртом)
        if 'left_eye' in zones and 'mouth' in zones:
            eye_bottom = zones['left_eye'][3]
            mouth_top = zones['mouth'][1]
            mouth_left = zones['mouth'][0]
            eye_left = zones['left_eye'][0]
            zones['left_cheek'] = (eye_left, eye_bottom, mouth_left, mouth_top)

        if 'right_eye' in zones and 'mouth' in zones:
            eye_bottom = zones['right_eye'][3]
            mouth_top = zones['mouth'][1]
            mouth_right = zones['mouth'][2]
            eye_right = zones['right_eye'][2]
            zones['right_cheek'] = (mouth_right, eye_bottom, eye_right, mouth_top)

        return zones

    def _anthropometric_fallback(self, face_bbox: tuple, img_w: int, img_h: int) -> dict:
        """
        Восстановление зон по антропометрическим пропорциям (золотое сечение лица).

        Пропорции:
        - Лоб: верхние 30% bbox
        - Глаза: 25-45% высоты bbox
        - Нос: 40-65% высоты bbox
        - Рот: 60-80% высоты bbox
        - Подбородок: нижние 20% bbox
        """
        x1, y1, x2, y2 = face_bbox
        face_w = x2 - x1
        face_h = y2 - y1

        zones = {}

        # Лоб (верхние 30%)
        zones['forehead'] = (
            x1,
            y1,
            x2,
            int(y1 + face_h * 0.30)
        )

        # Левый глаз (25-45% высоты, левая половина)
        zones['left_eye'] = (
            int(x1 + face_w * 0.15),
            int(y1 + face_h * 0.25),
            int(x1 + face_w * 0.45),
            int(y1 + face_h * 0.45)
        )

        # Правый глаз (25-45% высоты, правая половина)
        zones['right_eye'] = (
            int(x1 + face_w * 0.55),
            int(y1 + face_h * 0.25),
            int(x1 + face_w * 0.85),
            int(y1 + face_h * 0.45)
        )

        # Нос (40-65% высоты, центр 40% ширины)
        zones['nose'] = (
            int(x1 + face_w * 0.30),
            int(y1 + face_h * 0.40),
            int(x1 + face_w * 0.70),
            int(y1 + face_h * 0.65)
        )

        # Рот (60-80% высоты, центр 50% ширины)
        zones['mouth'] = (
            int(x1 + face_w * 0.25),
            int(y1 + face_h * 0.60),
            int(x1 + face_w * 0.75),
            int(y1 + face_h * 0.80)
        )

        # Подбородок (нижние 20%)
        zones['chin'] = (
            int(x1 + face_w * 0.20),
            int(y1 + face_h * 0.80),
            int(x1 + face_w * 0.80),
            y2
        )

        # Левая щека
        zones['left_cheek'] = (
            x1,
            int(y1 + face_h * 0.45),
            int(x1 + face_w * 0.40),
            int(y1 + face_h * 0.70)
        )

        # Правая щека
        zones['right_cheek'] = (
            int(x1 + face_w * 0.60),
            int(y1 + face_h * 0.45),
            x2,
            int(y1 + face_h * 0.70)
        )

        return zones

    def unload(self):
        """Выгрузка модели."""
        if self.face_mesh is not None:
            self.face_mesh.close()
            self.face_mesh = None
            self.available = False
            print("[landmark] Unloaded MediaPipe")
