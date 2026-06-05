"""
Semantic segmentation для зональной обработки изображений.
Использует DeepLabV3 MobileNetV3 из torchvision.
"""
import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import models, transforms


# Длинная сторона для inference — полный кадр 7k+ даёт CUDA OOM
_MAX_SEG_LONG_SIDE = 1280


class ImageSegmentor:
    """
    Семантическая сегментация изображения на зоны.

    Классы PASCAL VOC (21):
    0: background, 1: aeroplane, 2: bicycle, 3: bird, 4: boat, 5: bottle,
    6: bus, 7: car, 8: cat, 9: chair, 10: cow, 11: dining table,
    12: dog, 13: horse, 14: motorbike, 15: person, 16: potted plant,
    17: sheep, 18: sofa, 19: train, 20: tv/monitor
    """

    def __init__(self):
        self.net = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def load(self):
        """Lazy load модели."""
        if self.net is not None:
            return

        try:
            self.net = models.segmentation.deeplabv3_mobilenet_v3_large(weights='DEFAULT')
            self.net.eval()
            self.net = self.net.to(self.device)
            print("[segmentor] Loaded DeepLabV3 MobileNetV3")
        except Exception as e:
            print(f"[segmentor] Failed to load DeepLabV3: {e}")
            raise

    def segment(self, img: Image.Image) -> dict:
        """
        Сегментация изображения на зоны.

        Args:
            img: PIL Image

        Returns:
            dict с масками:
            {
                'person': np.ndarray (H, W) float32 [0-1],
                'background': np.ndarray (H, W) float32 [0-1],
                'sky': np.ndarray (H, W) float32 [0-1]
            }
        """
        self.load()

        orig_w, orig_h = img.size
        work_img = img
        long_side = max(orig_w, orig_h)
        if long_side > _MAX_SEG_LONG_SIDE:
            scale = _MAX_SEG_LONG_SIDE / long_side
            work_w = max(1, int(orig_w * scale))
            work_h = max(1, int(orig_h * scale))
            work_img = img.resize((work_w, work_h), Image.LANCZOS)
            print(f"[segmentor] downscale for inference: {orig_w}x{orig_h} -> {work_w}x{work_h}")

        input_tensor = self.transform(work_img).unsqueeze(0).to(self.device)

        # Inference
        with torch.no_grad():
            output = self.net(input_tensor)['out'][0]
            output = torch.nn.functional.softmax(output, dim=0)

        # Получаем маски классов
        person_mask = output[15].cpu().numpy()  # класс 15 = person
        background_mask = output[0].cpu().numpy()  # класс 0 = background

        # Resize к оригинальному размеру
        person_mask = cv2.resize(person_mask, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        background_mask = cv2.resize(background_mask, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

        # Softmax границы через Gaussian blur
        person_mask = cv2.GaussianBlur(person_mask, (21, 21), 10)
        background_mask = cv2.GaussianBlur(background_mask, (21, 21), 10)

        # Нормализация [0-1]
        person_mask = np.clip(person_mask, 0, 1)
        background_mask = np.clip(background_mask, 0, 1)

        # Sky маска — верхняя треть фона с высокой яркостью
        sky_mask = self._detect_sky(img, background_mask)

        return {
            'person': person_mask.astype(np.float32),
            'background': background_mask.astype(np.float32),
            'sky': sky_mask.astype(np.float32)
        }

    def _detect_sky(self, img: Image.Image, background_mask: np.ndarray) -> np.ndarray:
        """
        Детекция неба — верхняя треть + высокая яркость + фон.
        """
        arr = np.array(img)
        h, w = arr.shape[:2]

        # Яркость
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        brightness = gray.astype(np.float32) / 255.0

        # Верхняя треть изображения
        top_third_mask = np.zeros((h, w), dtype=np.float32)
        top_third_mask[:h // 3, :] = 1.0

        # Sky = фон + верхняя треть + яркость > 0.6
        sky_mask = background_mask * top_third_mask * (brightness > 0.6).astype(np.float32)

        # Размытие для плавных границ
        sky_mask = cv2.GaussianBlur(sky_mask, (31, 31), 15)
        sky_mask = np.clip(sky_mask, 0, 1)

        return sky_mask.astype(np.float32)

    def get_clothing_mask(self, person_mask: np.ndarray, face_bboxes: list, img_size: tuple) -> np.ndarray:
        """
        Маска одежды = person минус лица.

        Args:
            person_mask: маска человека
            face_bboxes: список bbox лиц [(x1, y1, x2, y2), ...]
            img_size: (width, height)

        Returns:
            маска одежды float32 [0-1]
        """
        w, h = img_size
        clothing_mask = person_mask.copy()

        # Вычитаем области лиц
        for bbox in face_bboxes:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)

            # Расширяем bbox на 30% для захвата шеи/волос
            expand_ratio = 0.3
            face_w = x2 - x1
            face_h = y2 - y1
            expand_w = int(face_w * expand_ratio / 2)
            expand_h = int(face_h * expand_ratio / 2)

            x1_exp = max(0, x1 - expand_w)
            y1_exp = max(0, y1 - expand_h)
            x2_exp = min(w, x2 + expand_w)
            y2_exp = min(h, y2 + expand_h)

            # Обнуляем область лица
            clothing_mask[y1_exp:y2_exp, x1_exp:x2_exp] = 0.0

        # Размытие границ
        clothing_mask = cv2.GaussianBlur(clothing_mask, (21, 21), 10)
        clothing_mask = np.clip(clothing_mask, 0, 1)

        return clothing_mask.astype(np.float32)

    def unload(self):
        """Выгрузка модели из памяти."""
        if self.net is not None:
            del self.net
            self.net = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[segmentor] Unloaded DeepLabV3")
