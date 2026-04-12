import cv2
import numpy as np
from PIL import Image


def create_feathered_mask(shape: tuple, bbox: list, feather_amount: int = 20) -> np.ndarray:
    h, w = shape
    x1, y1, x2, y2 = [int(v) for v in bbox]

    x1 = max(0, x1 - feather_amount)
    y1 = max(0, y1 - feather_amount)
    x2 = min(w, x2 + feather_amount)
    y2 = min(h, y2 + feather_amount)

    mask = np.zeros((h, w), dtype=np.float32)
    mask[y1:y2, x1:x2] = 1.0

    kernel_size = feather_amount * 2 + 1
    mask = cv2.GaussianBlur(mask, (kernel_size, kernel_size), feather_amount / 2)
    return mask


def composite_faces(
    original: Image.Image,
    enhanced_faces: list,
    face_bboxes: list,
    intensity: float = 1.0,
    feather_amount: int = 20,
    adaptive_feather: bool = True
) -> Image.Image:
    if not enhanced_faces:
        return original.copy()

    original_arr = np.array(original, dtype=np.float32)
    result = original_arr.copy()
    h, w = result.shape[:2]

    for enhanced_face, bbox in zip(enhanced_faces, face_bboxes):
        x1, y1, x2, y2 = [int(v) for v in bbox]

        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        face_w = x2 - x1
        face_h = y2 - y1

        if face_w <= 0 or face_h <= 0:
            continue

        # Адаптивный feathering: больше для больших лиц
        if adaptive_feather:
            face_size = min(face_w, face_h)
            current_feather = max(10, min(int(face_size * 0.1), 40))
        else:
            current_feather = feather_amount

        # Resize улучшенного лица к размеру bbox
        enhanced_resized = enhanced_face.resize((face_w, face_h), Image.LANCZOS)
        enhanced_arr = np.array(enhanced_resized, dtype=np.float32)

        # Маска только для области лица
        face_region_mask = np.zeros((h, w), dtype=np.float32)
        face_region_mask[y1:y2, x1:x2] = 1.0
        kernel_size = max(3, current_feather * 2 + 1)
        if kernel_size % 2 == 0:
            kernel_size += 1
        face_region_mask = cv2.GaussianBlur(
            face_region_mask, (kernel_size, kernel_size), current_feather / 2
        )
        face_region_mask = face_region_mask[:, :, np.newaxis] * intensity

        # Вставляем enhanced только в область лица, остальное — оригинал
        enhanced_full = original_arr.copy()
        enhanced_full[y1:y2, x1:x2] = enhanced_arr

        # Blend: оригинал + улучшенное лицо через маску
        result = result * (1 - face_region_mask) + enhanced_full * face_region_mask

    result = np.clip(result, 0, 255).astype(np.uint8)
    return Image.fromarray(result)


def blend_images(img1: Image.Image, img2: Image.Image, alpha: float) -> Image.Image:
    arr1 = np.array(img1, dtype=np.float32)
    arr2 = np.array(img2, dtype=np.float32)
    result = np.clip(arr1 * (1 - alpha) + arr2 * alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(result)