"""
Детекция лиц с использованием RetinaFace (detection_Resnet50_Final.pth).
"""
import os
import cv2
import numpy as np
import torch
from PIL import Image


class FaceDetector:
    def __init__(self, model_path: str = None):
        """
        Args:
            model_path: путь к detection_Resnet50_Final.pth
        """
        if model_path is None:
            model_path = os.path.join("bin", "detection_Resnet50_Final.pth")

        self.model_path = model_path
        self.net = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load(self):
        """Lazy load модели."""
        if self.net is not None:
            return

        try:
            from facexlib.detection import init_detection_model
            self.net = init_detection_model('retinaface_resnet50',
                                            model_rootpath=os.path.dirname(self.model_path))

            # Загружаем веса
            state_dict = torch.load(self.model_path, map_location=self.device)

            # Убираем префикс "module." если есть (DataParallel)
            new_state_dict = {}
            for k, v in state_dict.items():
                name = k[7:] if k.startswith('module.') else k
                new_state_dict[name] = v

            self.net.load_state_dict(new_state_dict, strict=True)
            self.net.eval()
            print(f"[face_detector] Loaded RetinaFace from {self.model_path}")
        except Exception as e:
            print(f"[face_detector] Failed to load RetinaFace: {e}")
            raise

    def detect_faces(self, img: Image.Image, confidence_threshold: float = 0.8) -> list:
        """
        Детекция лиц на изображении.

        Args:
            img: PIL Image
            confidence_threshold: порог уверенности (0-1)

        Returns:
            list of dicts: [{'bbox': [x1, y1, x2, y2], 'confidence': float, 'landmarks': [...]}]
        """
        self.load()

        # Конвертируем PIL -> numpy BGR
        arr = np.array(img)
        arr_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        # Детекция
        with torch.no_grad():
            bboxes = self.net.detect_faces(arr_bgr, confidence_threshold)

        faces = []
        for bbox in bboxes:
            # bbox format: [x1, y1, x2, y2, confidence]
            if len(bbox) >= 5:
                x1, y1, x2, y2, conf = bbox[:5]
                faces.append({
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': float(conf),
                    'landmarks': bbox[5:] if len(bbox) > 5 else None
                })

        raw_count = len(faces)
        faces = self._dedupe_overlapping(faces)
        if raw_count != len(faces):
            print(f"[face_detector] Deduped {raw_count} -> {len(faces)} face(s)")
        print(f"[face_detector] Detected {len(faces)} face(s)")
        return faces

    @staticmethod
    def _box_iou(a: list, b: list) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        return inter / (area_a + area_b - inter)

    @classmethod
    def _dedupe_overlapping(cls, faces: list, iou_threshold: float = 0.45) -> list:
        """Схлопывает дубли одного лица (RetinaFace часто даёт 2 бокса на портрет)."""
        if len(faces) <= 1:
            return faces

        ordered = sorted(faces, key=lambda f: f['confidence'], reverse=True)
        kept = []
        for face in ordered:
            if all(cls._box_iou(face['bbox'], k['bbox']) < iou_threshold for k in kept):
                kept.append(face)
        return kept

    def unload(self):
        """Выгрузка модели из памяти."""
        if self.net is not None:
            del self.net
            self.net = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[face_detector] Unloaded RetinaFace")
