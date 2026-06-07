"""
Менеджер памяти EdgeTools для ML-модулей.

Отслеживает загруженные модели, выгружает их из RAM/VRAM и очищает CUDA-кэш.
"""
import gc
import psutil
import os
from typing import Optional


class MemoryManager:
    """Singleton: учёт моделей и принудительная очистка памяти процесса."""

    _instance = None
    _loaded_models = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.process = psutil.Process(os.getpid())

    def get_memory_usage(self) -> dict:
        """
        Текущее потребление RAM процессом EdgeTools.

        Returns:
            Словарь с ram_mb и ram_percent.
        """
        mem_info = self.process.memory_info()
        return {
            'ram_mb': mem_info.rss / 1024 / 1024,
            'ram_percent': self.process.memory_percent(),
        }

    def register_model(self, name: str, model):
        """
        Зарегистрировать модель для последующей выгрузки.

        Args:
            name: уникальный идентификатор модели.
            model: ссылка на объект модели в памяти.
        """
        self._loaded_models[name] = model

    def unload_model(self, name: str):
        """
        Выгрузить одну модель и запустить cleanup.

        Args:
            name: идентификатор, переданный в register_model.
        """
        if name in self._loaded_models:
            model = self._loaded_models.pop(name)
            del model
            self.cleanup()

    def unload_all_models(self):
        """Выгрузить все зарегистрированные модели."""
        self._loaded_models.clear()
        self.cleanup()

    def cleanup(self):
        """Сборка мусора Python и очистка CUDA-кэша при наличии torch."""
        gc.collect()

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except ImportError:
            pass

    def get_optimal_device(self) -> str:
        """
        Выбрать устройство для инференса.

        Returns:
            'cuda' при доступной видеокарте, иначе 'cpu'.
        """
        try:
            import torch
            if torch.cuda.is_available():
                return 'cuda'
        except ImportError:
            pass
        return 'cpu'

    def get_vram_usage(self) -> Optional[dict]:
        """
        Использование видеопамяти (только CUDA).

        Returns:
            Словарь allocated_mb, reserved_mb, total_mb или None без CUDA.
        """
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
        """Вывести RAM и VRAM в консоль для отладки."""
        mem = self.get_memory_usage()
        print(f"[MemoryManager] RAM: {mem['ram_mb']:.1f} MB ({mem['ram_percent']:.1f}%)")

        vram = self.get_vram_usage()
        if vram:
            print(f"[MemoryManager] VRAM: {vram['allocated_mb']:.1f} / {vram['total_mb']:.1f} MB")


memory_manager = MemoryManager()
