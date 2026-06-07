"""
Менеджер ML-моделей пайплайна: lazy load, пути в bin/, выгрузка VRAM.

Единая точка доступа к RetinaFace, CodeFormer, SwinIR, DeepLabV3, ParseNet,
ArcFace через ``get_model_manager()``.
"""
import os
import sys
from typing import Optional
from .face_detector import FaceDetector
from .face_enhancer import FaceEnhancer
from .face_parser import FaceParser
from .swinir_upscaler import SwinIRUpscaler
from .segmentor import ImageSegmentor
from .identity_preservor import IdentityPreservor


def _patch_basicsr():
    """Патч совместимости basicsr + torchvision."""
    if "torchvision.transforms.functional_tensor" not in sys.modules:
        import types
        import torchvision.transforms.functional as _F
        _mod = types.ModuleType("torchvision.transforms.functional_tensor")
        _mod.rgb_to_grayscale = _F.rgb_to_grayscale
        sys.modules["torchvision.transforms.functional_tensor"] = _mod


class ModelManager:
    """
    Централизованное управление моделями ML.
    Lazy loading + автоматическая выгрузка при нехватке памяти.
    """

    def __init__(self):
        """Пути к весам в bin/; модели создаются при первом get_*()."""
        self._face_detector: Optional[FaceDetector] = None
        self._face_enhancer: Optional[FaceEnhancer] = None
        self._face_parser: Optional[FaceParser] = None
        self._swinir_upscaler: Optional[SwinIRUpscaler] = None
        self._segmentor: Optional[ImageSegmentor] = None
        self._identity_preservor: Optional[IdentityPreservor] = None

        # Пути к моделям в bin/
        self.bin_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
        "bin"
    )
        self.detection_path = os.path.join(self.bin_dir, "detection_Resnet50_Final.pth")
        self.codeformer_path = os.path.join(self.bin_dir, "codeformer.pth")
        self.parsing_path = os.path.join(self.bin_dir, "parsing_parsenet.pth")
        self.swinir_x4_path = os.path.join(self.bin_dir, "003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth")
        self.swinir_x2_path = os.path.join(self.bin_dir, "001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth")

    def get_face_detector(self) -> FaceDetector:
        """Получить детектор лиц (lazy load)."""
        if self._face_detector is None:
            self._face_detector = FaceDetector(model_path=self.detection_path)
        return self._face_detector

    def get_face_enhancer(self) -> FaceEnhancer:
        """Получить улучшатель лиц (lazy load)."""
        if self._face_enhancer is None:
            _patch_basicsr()
            self._face_enhancer = FaceEnhancer(
                model_path=self.codeformer_path,
                parsing_path=self.parsing_path
            )
        return self._face_enhancer

    def get_face_parser(self) -> FaceParser:
        """Получить face parser (lazy load)."""
        if self._face_parser is None:
            self._face_parser = FaceParser(model_path=self.parsing_path)
        return self._face_parser

    def get_swinir_upscaler(self, scale: int = 4) -> SwinIRUpscaler:
        """Получить SwinIR upscaler (lazy load)."""
        if self._swinir_upscaler is None or self._swinir_upscaler.scale != scale:
            _patch_basicsr()
            model_path = self.swinir_x4_path if scale == 4 else self.swinir_x2_path
            self._swinir_upscaler = SwinIRUpscaler(model_path=model_path, scale=scale)
        return self._swinir_upscaler

    def get_segmentor(self) -> ImageSegmentor:
        """Получить semantic segmentor (lazy load)."""
        if self._segmentor is None:
            self._segmentor = ImageSegmentor()
        return self._segmentor

    def get_identity_preservor(self) -> IdentityPreservor:
        """Получить identity preservor (lazy load)."""
        if self._identity_preservor is None:
            self._identity_preservor = IdentityPreservor()
        return self._identity_preservor

    def unload_all(self):
        """Выгрузить все модели из памяти."""
        if self._face_detector is not None:
            self._face_detector.unload()
            self._face_detector = None

        if self._face_enhancer is not None:
            self._face_enhancer.unload()
            self._face_enhancer = None

        if self._face_parser is not None:
            self._face_parser.unload()
            self._face_parser = None

        if self._swinir_upscaler is not None:
            self._swinir_upscaler.unload()
            self._swinir_upscaler = None

        if self._segmentor is not None:
            self._segmentor.unload()
            self._segmentor = None

        if self._identity_preservor is not None:
            self._identity_preservor.unload()
            self._identity_preservor = None

        print("[model_manager] All models unloaded")

    def move_to_cpu(self):
        """Переместить модели с GPU на CPU (освобождает VRAM, но оставляет в RAM)."""
        try:
            import torch
            if not torch.cuda.is_available():
                return

            moved = []
            if self._face_detector is not None and hasattr(self._face_detector, 'net'):
                if hasattr(self._face_detector.net, 'to'):
                    self._face_detector.net = self._face_detector.net.to('cpu')
                    moved.append('FaceDetector')

            if self._face_enhancer is not None and hasattr(self._face_enhancer, 'net'):
                if hasattr(self._face_enhancer.net, 'to'):
                    self._face_enhancer.net = self._face_enhancer.net.to('cpu')
                    self._face_enhancer.device = torch.device('cpu')
                    moved.append('CodeFormer')

            if self._swinir_upscaler is not None and hasattr(self._swinir_upscaler, 'net'):
                if hasattr(self._swinir_upscaler.net, 'to'):
                    self._swinir_upscaler.net = self._swinir_upscaler.net.to('cpu')
                    self._swinir_upscaler.device = torch.device('cpu')
                    moved.append('SwinIR')

            if self._segmentor is not None and hasattr(self._segmentor, 'model'):
                if hasattr(self._segmentor.model, 'to'):
                    self._segmentor.model = self._segmentor.model.to('cpu')
                    moved.append('Segmentor')

            torch.cuda.empty_cache()
            if moved:
                print(f"[model_manager] Moved to CPU: {', '.join(moved)}")
        except Exception as e:
            print(f"[model_manager] Failed to move to CPU: {e}")

    def unload_heavy_models(self):
        """Выгрузить только тяжёлые модели (SwinIR + CodeFormer), оставить лёгкие."""
        if self._swinir_upscaler is not None:
            self._swinir_upscaler.unload()
            self._swinir_upscaler = None
            print("[model_manager] Unloaded SwinIR (136MB)")

        if self._face_enhancer is not None:
            self._face_enhancer.unload()
            self._face_enhancer = None
            print("[model_manager] Unloaded CodeFormer (360MB)")

        print("[model_manager] Heavy models unloaded (~500MB freed)")

    def unload_detector(self):
        """Выгрузить только детектор."""
        if self._face_detector is not None:
            self._face_detector.unload()
            self._face_detector = None

    def unload_enhancer(self):
        """Выгрузить только улучшатель."""
        if self._face_enhancer is not None:
            self._face_enhancer.unload()
            self._face_enhancer = None

    def unload_swinir(self):
        """Выгрузить только SwinIR."""
        if self._swinir_upscaler is not None:
            self._swinir_upscaler.unload()
            self._swinir_upscaler = None

    def check_models_exist(self) -> dict:
        """
        Проверить наличие всех моделей.

        Returns:
            dict: {'detection': bool, 'codeformer': bool, 'parsing': bool, 'swinir_x4': bool, 'swinir_x2': bool}
        """
        return {
            'detection': os.path.exists(self.detection_path),
            'codeformer': os.path.exists(self.codeformer_path),
            'parsing': os.path.exists(self.parsing_path),
            'swinir_x4': os.path.exists(self.swinir_x4_path),
            'swinir_x2': os.path.exists(self.swinir_x2_path)
        }


# Глобальный экземпляр
_model_manager = None


def get_model_manager() -> ModelManager:
    """Получить глобальный экземпляр ModelManager."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
