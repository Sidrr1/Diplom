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

        print(f"[face_detector] Detected {len(faces)} faces")
        return faces

    def unload(self):
        """Выгрузка модели из памяти."""
        if self.net is not None:
            del self.net
            self.net = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[face_detector] Unloaded RetinaFace")
