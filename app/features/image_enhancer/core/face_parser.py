"""
Face parsing детектор для сегментации частей лица.
Использует parsing_parsenet.pth для определения: кожа, глаза, нос, рот, брови, волосы.
"""
import os
import cv2
import numpy as np
import torch
from PIL import Image


class FaceParser:
    """
    Сегментация лица на части.

    Классы (19 категорий):
    0: background, 1: skin, 2: l_brow, 3: r_brow, 4: l_eye, 5: r_eye,
    6: eye_g (glasses), 7: l_ear, 8: r_ear, 9: ear_r (earring),
    10: nose, 11: mouth, 12: u_lip, 13: l_lip, 14: neck,
    15: neck_l (necklace), 16: cloth, 17: hair, 18: hat
    """

    LABELS = {
        'background': 0, 'skin': 1, 'l_brow': 2, 'r_brow': 3,
        'l_eye': 4, 'r_eye': 5, 'eye_g': 6, 'l_ear': 7, 'r_ear': 8,
        'ear_r': 9, 'nose': 10, 'mouth': 11, 'u_lip': 12, 'l_lip': 13,
        'neck': 14, 'neck_l': 15, 'cloth': 16, 'hair': 17, 'hat': 18
    }

    def __init__(self, model_path: str = None):
        if model_path is None:
            bin_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
                "bin"
            )
            model_path = os.path.join(bin_dir, "parsing_parsenet.pth")

        self.model_path = model_path
        self.net = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load(self):
        """Lazy load модели."""
        if self.net is not None:
            return

        try:
            from facexlib.parsing import init_parsing_model
            self.net = init_parsing_model(
                model_name='parsenet',
                device=self.device
            )
            # Загружаем веса
            state_dict = torch.load(self.model_path, map_location=self.device)
            self.net.load_state_dict(state_dict, strict=True)
            self.net.eval()
            print(f"[face_parser] Loaded ParseNet from {self.model_path}")
        except Exception as e:
            print(f"[face_parser] Failed to load ParseNet: {e}")
            raise

    def parse_face(self, face_img: Image.Image) -> np.ndarray:
        """
        Парсинг лица на части.

        Args:
            face_img: PIL Image с лицом

        Returns:
            numpy array (H, W) с индексами классов (0-18)
        """
        self.load()

        # Конвертируем PIL -> numpy BGR
        arr = np.array(face_img)
        arr_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        # Resize до 512x512 для модели
        h, w = arr_bgr.shape[:2]
        arr_resized = cv2.resize(arr_bgr, (512, 512), interpolation=cv2.INTER_LINEAR)

        # Нормализация
        arr_norm = arr_resized.astype(np.float32) / 255.0
        arr_norm = ((arr_norm - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).astype(np.float32)

        # BGR -> RGB -> Tensor
        arr_rgb = cv2.cvtColor(arr_norm, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(arr_rgb).permute(2, 0, 1).unsqueeze(0).to(self.device)

        # Inference
        with torch.no_grad():
            out = self.net(tensor)[0]

        # Получаем маску классов
        parsing = out.squeeze(0).cpu().numpy().argmax(0)

        # Resize обратно к оригинальному размеру
        parsing = cv2.resize(
            parsing.astype(np.uint8),
            (w, h),
            interpolation=cv2.INTER_NEAREST
        )

        return parsing

    def get_region_mask(self, parsing: np.ndarray, regions: list) -> np.ndarray:
        """
        Получить бинарную маску для указанных регионов.

        Args:
            parsing: результат parse_face
            regions: список названий регионов (например, ['skin', 'nose'])

        Returns:
            бинарная маска (H, W) с 0/255
        """
        mask = np.zeros(parsing.shape, dtype=np.uint8)
        for region in regions:
            if region in self.LABELS:
                mask[parsing == self.LABELS[region]] = 255
        return mask

    def get_face_regions(self, parsing: np.ndarray) -> dict:
        """
        Получить все маски регионов лица.

        Returns:
            dict: {'skin': mask, 'eyes': mask, 'nose': mask, ...}
        """
        return {
            'skin': self.get_region_mask(parsing, ['skin', 'neck']),
            'eyes': self.get_region_mask(parsing, ['l_eye', 'r_eye']),
            'eyebrows': self.get_region_mask(parsing, ['l_brow', 'r_brow']),
            'nose': self.get_region_mask(parsing, ['nose']),
            'mouth': self.get_region_mask(parsing, ['mouth', 'u_lip', 'l_lip']),
            'hair': self.get_region_mask(parsing, ['hair']),
            'ears': self.get_region_mask(parsing, ['l_ear', 'r_ear']),
            'cloth': self.get_region_mask(parsing, ['cloth'])
        }

    def unload(self):
        """Выгрузка модели из памяти."""
        if self.net is not None:
            del self.net
            self.net = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[face_parser] Unloaded ParseNet")
