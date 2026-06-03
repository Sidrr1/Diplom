from PySide6.QtCore import QObject, QTimer
from PIL import Image

# Задержки гибридной выгрузки (после простоя)
_IDLE_GPU_TO_CPU_MS = 120_000   # 2 мин: GPU → CPU
_IDLE_HEAVY_UNLOAD_MS = 600_000  # 10 мин: выгрузка SwinIR + CodeFormer
_DEFER_WHILE_BUSY_MS = 30_000    # повтор, если воркер ещё крутится


class EnhancerController(QObject):
    def __init__(self, view):
        super().__init__()
        self._view       = view
        self._worker     = None

        # Таймер 1: GPU -> CPU через 2 минуты простоя
        self._cpu_timer = QTimer(self)
        self._cpu_timer.setSingleShot(True)
        self._cpu_timer.timeout.connect(self._move_to_cpu)

        # Таймер 2: Выгрузка тяжёлых моделей через 10 минут простоя
        self._unload_timer = QTimer(self)
        self._unload_timer.setSingleShot(True)
        self._unload_timer.timeout.connect(self._unload_heavy)

        view.enhance_requested.connect(self._on_enhance)
        view.colorize_requested.connect(self._on_colorize)

    def _on_enhance(self, img: Image.Image):
        # Получаем параметры из UI
        fidelity = self._view._fidelity_slider.value() / 100.0
        intensity = self._view._intensity_slider.value() / 100.0
        self._run("enhance", img, None, fidelity, intensity)

    def _on_colorize(self, img: Image.Image, skin_bgr):
        self._run("colorize", img, skin_bgr, 0.7, 1.0)

    def _run(self, task: str, img: Image.Image, skin_bgr, fidelity: float, intensity: float):
        if self._worker and self._worker.isRunning():
            return

        self._cancel_idle_unload_timers()

        # Если модели были перемещены на CPU, возвращаем их на GPU
        self._ensure_models_on_gpu()

        from app.features.image_enhancer.core.enhance_worker import EnhanceWorker
        self._worker = EnhanceWorker(task, img, skin_bgr, fidelity, intensity)
        self._worker.progress.connect(self._view.set_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._view.show_error)
        self._worker.error.connect(self._on_worker_failed)
        self._worker.start()

    def _cancel_idle_unload_timers(self):
        """Остановить отложенную выгрузку (новый запуск или выход)."""
        self._cpu_timer.stop()
        self._unload_timer.stop()

    def _worker_busy(self) -> bool:
        w = self._worker
        return w is not None and w.isRunning()

    def _schedule_idle_unload(self):
        """Запланировать GPU→CPU и heavy unload после простоя."""
        if self._worker_busy():
            return
        print(
            f"[controller] Scheduling idle unload: GPU->CPU in "
            f"{_IDLE_GPU_TO_CPU_MS // 1000}s, heavy in {_IDLE_HEAVY_UNLOAD_MS // 1000}s"
        )
        self._cpu_timer.start(_IDLE_GPU_TO_CPU_MS)
        self._unload_timer.start(_IDLE_HEAVY_UNLOAD_MS)

    def _on_worker_finished(self, res: Image.Image, info: str):
        """Обработка завершения работы воркера."""
        self._view.show_result(res, info)
        self._schedule_idle_unload()

    def _on_worker_failed(self, _msg: str):
        """После ошибки тоже планируем выгрузку — модели могли занять VRAM."""
        self._schedule_idle_unload()

    def _move_to_cpu(self):
        """Переместить модели с GPU на CPU (освобождает VRAM). Только в простое."""
        if self._worker_busy():
            print("[controller] Worker busy — defer GPU->CPU")
            self._cpu_timer.start(_DEFER_WHILE_BUSY_MS)
            return
        try:
            print("[controller] Moving models from GPU to CPU")
            from app.features.image_enhancer.core.model_manager import get_model_manager
            import gc

            manager = get_model_manager()
            manager.move_to_cpu()
            gc.collect()
            print("[controller] Models moved to CPU, VRAM freed")
        except Exception as e:
            print(f"[controller] Failed to move to CPU: {e}")

    def _unload_heavy(self):
        """Выгрузить тяжёлые модели (SwinIR + CodeFormer). Только в простое."""
        if self._worker_busy():
            print("[controller] Worker busy — defer heavy unload")
            self._unload_timer.start(_DEFER_WHILE_BUSY_MS)
            return
        try:
            print("[controller] Unloading heavy models (SwinIR + CodeFormer)")
            from app.features.image_enhancer.core.model_manager import get_model_manager
            import gc

            manager = get_model_manager()
            manager.unload_heavy_models()
            gc.collect()
            print("[controller] Heavy models unloaded (~500MB freed)")
        except Exception as e:
            print(f"[controller] Failed to unload heavy models: {e}")

    def cleanup(self):
        """Остановить воркер и отменить таймеры выгрузки при выходе из приложения."""
        print("[controller] Cleanup enhancer")
        self._cancel_idle_unload_timers()
        w = self._worker
        if w is None:
            return
        try:
            w.progress.disconnect()
            w.finished.disconnect()
            w.error.disconnect()
        except (TypeError, RuntimeError):
            pass
        if w.isRunning():
            w.wait(10_000)
        self._worker = None

    def _ensure_models_on_gpu(self):
        """Убедиться что модели на GPU (если были перемещены на CPU)."""
        try:
            import torch
            if not torch.cuda.is_available():
                return

            from app.features.image_enhancer.core.model_manager import get_model_manager
            manager = get_model_manager()

            # Проверяем и перемещаем модели обратно на GPU
            moved = []
            if manager._face_detector is not None and hasattr(manager._face_detector, 'net'):
                if hasattr(manager._face_detector.net, 'to'):
                    device = next(manager._face_detector.net.parameters()).device
                    if device.type == 'cpu':
                        manager._face_detector.net = manager._face_detector.net.to('cuda')
                        moved.append('FaceDetector')

            if manager._face_enhancer is not None and hasattr(manager._face_enhancer, 'net'):
                if hasattr(manager._face_enhancer.net, 'to'):
                    device = next(manager._face_enhancer.net.parameters()).device
                    if device.type == 'cpu':
                        manager._face_enhancer.net = manager._face_enhancer.net.to('cuda')
                        manager._face_enhancer.device = torch.device('cuda')
                        moved.append('CodeFormer')

            if manager._swinir_upscaler is not None and hasattr(manager._swinir_upscaler, 'net'):
                if hasattr(manager._swinir_upscaler.net, 'to'):
                    device = next(manager._swinir_upscaler.net.parameters()).device
                    if device.type == 'cpu':
                        manager._swinir_upscaler.net = manager._swinir_upscaler.net.to('cuda')
                        manager._swinir_upscaler.device = torch.device('cuda')
                        moved.append('SwinIR')

            if manager._segmentor is not None and hasattr(manager._segmentor, 'model'):
                if hasattr(manager._segmentor.model, 'to'):
                    device = next(manager._segmentor.model.parameters()).device
                    if device.type == 'cpu':
                        manager._segmentor.model = manager._segmentor.model.to('cuda')
                        moved.append('Segmentor')

            if moved:
                print(f"[controller] Moved back to GPU: {', '.join(moved)}")
        except Exception as e:
            print(f"[controller] Failed to move models to GPU: {e}")