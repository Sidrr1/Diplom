"""
Identity preservation для лиц через ArcFace (onnxruntime).
Сохраняет похожесть на оригинал после CodeFormer.
"""
import os
import cv2
import numpy as np
from PIL import Image


class IdentityPreservor:
    """
    Проверка и сохранение идентичности лица через ArcFace (w600k_mbf.onnx).
    """

    def __init__(self):
        self.session = None
        self.available = False
        self.model_path = None

    def load(self):
        """Lazy load ArcFace ONNX модели."""
        if self.session is not None:
            return

        try:
            import onnxruntime as ort

            # Ищем модель в bin/
            possible_paths = [
                os.path.join("bin", "arcface.onnx"),
                os.path.join("bin", "w600k_mbf.onnx"),
                os.path.join("bin", "w600k_r50.onnx"),
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    self.model_path = path
                    break

            if self.model_path is None:
                self.available = False
                return

            # Создаём ONNX Runtime сессию
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self._has_cuda() else ['CPUExecutionProvider']
            self.session = ort.InferenceSession(self.model_path, providers=providers)
            self.available = True
            print(f"[identity] Loaded ArcFace from {self.model_path}")

        except Exception as e:
            self.available = False
            # Тихий fallback — не логируем ошибку

    def _has_cuda(self):
        """Проверка доступности CUDA."""
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False

    def get_embedding(self, face_img: Image.Image) -> np.ndarray:
        """
        Извлечь 512-мерный вектор идентичности лица через ArcFace.

        Args:
            face_img: PIL Image с лицом

        Returns:
            embedding вектор (512,) или None если модель недоступна
        """
        self.load()

        if not self.available:
            return None

        try:
            # Препроцессинг для ArcFace:
            # 1. Resize до 112x112
            face_resized = face_img.resize((112, 112), Image.LANCZOS)

            # 2. Конвертируем в numpy RGB float32
            arr = np.array(face_resized, dtype=np.float32)

            # 3. Normalize: (arr/255 - 0.5) / 0.5
            arr = (arr / 255.0 - 0.5) / 0.5

            # 4. Transpose to NCHW (batch, channels, height, width)
            arr = np.transpose(arr, (2, 0, 1))  # HWC -> CHW
            arr = np.expand_dims(arr, axis=0)   # CHW -> NCHW

            # 5. Inference
            input_name = self.session.get_inputs()[0].name
            output_name = self.session.get_outputs()[0].name
            embedding = self.session.run([output_name], {input_name: arr})[0]

            # 6. L2 normalization
            embedding = embedding.flatten()
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding

        except Exception as e:
            return None

    def similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Cosine similarity между двумя эмбеддингами.

        Args:
            emb1, emb2: embedding векторы (512,)

        Returns:
            similarity [0-1], где 1 = идентичные лица
        """
        if emb1 is None or emb2 is None:
            return 1.0  # Fallback: считаем что всё ок

        # Cosine similarity
        dot = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot / (norm1 * norm2)
        # Нормализуем в [0, 1]
        similarity = (similarity + 1) / 2

        return float(similarity)

    def preserve_identity(
        self,
        original: Image.Image,
        enhanced: Image.Image,
        threshold: float = 0.85
    ) -> Image.Image:
        """
        Сохранить идентичность лица через adaptive blend.

        Args:
            original: оригинальное лицо
            enhanced: улучшенное лицо (CodeFormer)
            threshold: порог similarity (0.85 = строгая проверка)

        Returns:
            лицо с сохранённой идентичностью
        """
        self.load()

        if not self.available:
            # Fallback: простой texture overlay без проверки similarity
            return self._simple_texture_overlay(original, enhanced, strength=0.15)

        # Получаем эмбеддинги
        emb_original = self.get_embedding(original)
        emb_enhanced = self.get_embedding(enhanced)

        if emb_original is None or emb_enhanced is None:
            print("[identity] Failed to extract embeddings, using simple overlay")
            return self._simple_texture_overlay(original, enhanced, strength=0.15)

        # Считаем similarity
        sim = self.similarity(emb_original, emb_enhanced)
        print(f"[identity] Similarity: {sim:.3f}", end="")

        if sim >= threshold:
            print(" — OK")
            return enhanced

        print(f" — LOW (threshold={threshold}), applying preservation")

        # Adaptive blend: чем меньше похожесть, тем больше берём от оригинала
        alpha = 1.0 - sim  # 0.35 если sim=0.65, 0.6 если sim=0.4

        # 1. Histogram matching
        result = self._histogram_matching(enhanced, original)

        # 2. Texture overlay
        result = self._texture_overlay(original, result, strength=alpha * 0.3)

        # 3. Финальный blend
        result_arr = np.array(result, dtype=np.float32)
        original_arr = np.array(original, dtype=np.float32)
        blend_strength = alpha * 0.4

        result_arr = result_arr * (1 - blend_strength) + original_arr * blend_strength
        result = Image.fromarray(np.clip(result_arr, 0, 255).astype(np.uint8))

        return result

    def _histogram_matching(self, source: Image.Image, reference: Image.Image) -> Image.Image:
        """Histogram matching для цветовой коррекции."""
        try:
            from skimage.exposure import match_histograms
            source_arr = np.array(source)
            reference_arr = np.array(reference)
            matched = match_histograms(source_arr, reference_arr, channel_axis=-1)
            return Image.fromarray(matched.astype(np.uint8))
        except ImportError:
            print("[identity] skimage not available, skipping histogram matching")
            return source

    def _texture_overlay(
        self,
        original: Image.Image,
        enhanced: Image.Image,
        strength: float
    ) -> Image.Image:
        """
        Наложение текстуры оригинала на улучшенное лицо.
        """
        original_arr = np.array(original).astype(np.float32)
        enhanced_arr = np.array(enhanced).astype(np.float32)

        # Извлекаем высокочастотные детали (текстуру) из оригинала
        original_blur = cv2.GaussianBlur(original_arr, (0, 0), 2.0)
        texture = original_arr - original_blur

        # Добавляем текстуру к улучшенному
        result = enhanced_arr + texture * strength
        result = np.clip(result, 0, 255).astype(np.uint8)

        return Image.fromarray(result)

    def _simple_texture_overlay(
        self,
        original: Image.Image,
        enhanced: Image.Image,
        strength: float
    ) -> Image.Image:
        """Простой texture overlay без проверки similarity (fallback)."""
        return self._texture_overlay(original, enhanced, strength)

    def unload(self):
        """Выгрузка модели из памяти."""
        if self.session is not None:
            del self.session
            self.session = None
            self.available = False
            print("[identity] Unloaded ArcFace")
