"""
Менеджер памяти для управления моделями и очистки ресурсов.
Автоматически выгружает модели из RAM/VRAM после использования.
"""
import gc
import psutil
import os
from typing import Optional


class MemoryManager:
    """Управление памятью и моделями."""

    _instance = None
    _loaded_models = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.process = psutil.Process(os.getpid())

    def get_memory_usage(self) -> dict:
        """Возвращает текущее использование памяти."""
        mem_info = self.process.memory_info()
        return {
            'ram_mb': mem_info.rss / 1024 / 1024,
            'ram_percent': self.process.memory_percent(),
        }

    def register_model(self, name: str, model):
        """Регистрирует модель для отслеживания."""
        self._loaded_models[name] = model

    def unload_model(self, name: str):
        """Выгружает модель из памяти."""
        if name in self._loaded_models:
            model = self._loaded_models.pop(name)
            del model
            self.cleanup()

    def unload_all_models(self):
        """Выгружает все модели."""
        self._loaded_models.clear()
        self.cleanup()

    def cleanup(self):
        """Очищает память: Python GC + CUDA cache."""
        # Python garbage collection
        gc.collect()

        # Очистка CUDA кэша если доступно
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except ImportError:
            pass

    def get_optimal_device(self) -> str:
        """Определяет оптимальное устройство для вычислений."""
        try:
            import torch
            if torch.cuda.is_available():
                return 'cuda'
        except ImportError:
            pass
        return 'cpu'

    def get_vram_usage(self) -> Optional[dict]:
        """Возвращает использование VRAM (только для CUDA)."""
        try:
            import torch
            if torch.cuda.is_available():
                return {
                    'allocated_mb': torch.cuda.memory_allocated() / 1024 / 1024,
                    'reserved_mb': torch.cuda.memory_reserved() / 1024 / 1024,
                    'total_mb': torch.cuda.get_device_properties(0).total_memory / 1024 / 1024,
                }
        except ImportError:
            pass
        return None

    def print_memory_stats(self):
        """Выводит статистику использования памяти."""
        mem = self.get_memory_usage()
        print(f"[MemoryManager] RAM: {mem['ram_mb']:.1f} MB ({mem['ram_percent']:.1f}%)")

        vram = self.get_vram_usage()
        if vram:
            print(f"[MemoryManager] VRAM: {vram['allocated_mb']:.1f} / {vram['total_mb']:.1f} MB")


# Глобальный экземпляр
memory_manager = MemoryManager()
