import os
import sys
import logging
import warnings

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app.features.edge_panel.ui.edge_panel_view import EdgePanelView
from app.features.player.ui.player_view import PlayerView
from app.features.file_sorter.ui.sorter_view import SorterView
from app.features.image_enhancer.ui.enhancer_view import EnhancerView
from app.controllers.player_controller import PlayerController
from app.controllers.sorter_controller import SorterController
from app.controllers.ocr_controller import OcrController
from app.controllers.enhancer_controller import EnhancerController
from app.core import config

logging.disable(logging.WARNING)
warnings.filterwarnings('ignore')

try:
    import setproctitle
    setproctitle.setproctitle('EdgeTools')
    print("[main] Process renamed to 'EdgeTools'")
except ImportError:
    print("[main] setproctitle not installed, using default process name")


def _patch_basicsr():
    if "torchvision.transforms.functional_tensor" not in sys.modules:
        import types
        import torchvision.transforms.functional as _F
        _mod = types.ModuleType("torchvision.transforms.functional_tensor")
        _mod.rgb_to_grayscale = _F.rgb_to_grayscale
        sys.modules["torchvision.transforms.functional_tensor"] = _mod


def _check_mem():
    try:
        import psutil
        proc  = psutil.Process(os.getpid())
        total = proc.memory_info().rss
        print(f"[mem] основной: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
        for child in proc.children(recursive=True):
            try:
                mb     = child.memory_info().rss / 1024 / 1024
                total += child.memory_info().rss
                print(f"[mem] {child.name()} (pid={child.pid}): {mb:.1f} MB")
            except Exception:
                pass
        print(f"[mem] ИТОГО: {total / 1024 / 1024:.1f} MB")
    except ImportError:
        print("[mem] pip install psutil")


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    cfg   = config.load()
    panel = EdgePanelView()
    from app.features.settings.ui.settings_dialog import SettingsDialog
    SettingsDialog.set_edge_panel(panel)

    print("[main] Starting global WindowTracker...")
    from app.features.todo.core.window_tracker import WindowTracker
    global_window_tracker = WindowTracker(interval_ms=1000)
    global_window_tracker.start()
    print(f"[main] WindowTracker started, current context: {global_window_tracker.get_current_context()}")

    _player_view  = None
    _player_ctrl  = None
    _sorter_view  = None
    _sorter_ctrl  = None
    _enhancer_view = None
    _enhancer_ctrl = None
    _todo_ctrl    = None

    from app.features.file_sorter.core.auto_watcher import get_auto_watcher
    _sorter_auto = get_auto_watcher()

    def _on_sorter_auto_sorted(ok, msg):
        if _sorter_view is not None:
            _sorter_view.show_results([(ok, msg)])

    _sorter_auto.sorted.connect(_on_sorter_auto_sorted)
    _sorter_auto.start()

    def cleanup_on_exit():
        print("[main] Cleanup on exit...")
        _sorter_auto.stop()
        if _todo_ctrl:
            _todo_ctrl.notes_container.cleanup()
        if _player_ctrl:
            try:
                _player_ctrl.cleanup()
            except Exception as e:
                print(f"[main] Player cleanup error: {e}")
        if _enhancer_ctrl:
            try:
                _enhancer_ctrl.cleanup()
            except Exception as e:
                print(f"[main] Enhancer cleanup error: {e}")
        try:
            from app.features.image_enhancer.core.model_manager import get_model_manager
            get_model_manager().unload_all()
        except Exception as e:
            print(f"[main] Model unload error: {e}")
        print("[main] Cleanup complete")

    app.aboutToQuit.connect(cleanup_on_exit)

    def _open_player():
        nonlocal _player_view, _player_ctrl
        if _player_view is None:
            panel.set_module_loading('player', True)
            try:
                _player_view = PlayerView(settings=cfg)
                _player_ctrl = PlayerController(_player_view)
                from app.features.settings.ui.settings_dialog import SettingsDialog
                SettingsDialog.set_player_view(_player_view)
                panel.set_module_loading('player', False)
            except Exception as e:
                panel.set_module_loading('player', False)
                from app.core.logger import log_error
                log_error("Ошибка загрузки плеера", "Не удалось загрузить медиаплеер.", e)
                return
        if not _player_view.isVisible():
            _player_view.show()
        _player_view.raise_()

    def _open_sorter():
        nonlocal _sorter_view, _sorter_ctrl
        if _sorter_view is None:
            panel.set_module_loading('sorter', True)
            try:
                _sorter_view = SorterView(settings=cfg)
                _sorter_ctrl = SorterController(_sorter_view)
                panel._sorter_view = _sorter_view
                panel.set_module_loading('sorter', False)
            except Exception as e:
                panel.set_module_loading('sorter', False)
                from app.core.logger import log_error
                log_error("Ошибка загрузки сортировщика", "Не удалось загрузить сортировщик.", e)
                return
        _sorter_view.refresh_source_label()
        if not _sorter_view.isVisible():
            _sorter_view.show()
        _sorter_view.raise_()

    def _open_enhancer():
        nonlocal _enhancer_view, _enhancer_ctrl
        if _enhancer_view is None:
            panel.set_module_loading('enhancer', True)
            try:
                from app.core.model_checker import check_and_warn
                check_and_warn()
                _enhancer_view = EnhancerView()
                _enhancer_ctrl = EnhancerController(_enhancer_view)
                panel.set_module_loading('enhancer', False)
            except Exception as e:
                panel.set_module_loading('enhancer', False)
                from app.core.logger import log_error
                log_error("Ошибка загрузки улучшателя", "Не удалось загрузить модуль улучшения.", e)
                return
        if not _enhancer_view.isVisible():
            _enhancer_view.show()
        _enhancer_view.raise_()

    def _open_todo():
        nonlocal _todo_ctrl

        # Первый запуск — создаём контроллер
        if _todo_ctrl is None:
            print("[main] Creating Smart Notes (lazy init)")
            panel.set_module_loading('todo', True)
            try:
                from app.controllers.todo_controller import TodoController
                _todo_ctrl = TodoController(window_tracker=global_window_tracker)
                panel.set_module_loading('todo', False)
                panel._todo_ctrl = _todo_ctrl
            except Exception as e:
                panel.set_module_loading('todo', False)
                panel.todo_btn.setChecked(False)
                from app.core.logger import log_error
                log_error("Ошибка загрузки заметок", "Не удалось загрузить Smart Notes.", e)
                return

        notes = _todo_ctrl.notes_container._notes
        is_visible = bool(notes) and any(n.isVisible() for n in notes)

        if is_visible:
            print("[main] Hiding todo")
            _todo_ctrl.hide()
            panel.todo_btn.setChecked(False)
        else:
            print("[main] Showing todo")
            _todo_ctrl.show()
            panel.todo_btn.setChecked(True)

    ocr_ctrl = OcrController()
    panel.set_ocr_controller(ocr_ctrl)

    panel.on_player_click.connect(_open_player)
    panel.on_sorter_click.connect(_open_sorter)
    panel.on_enhancer_click.connect(_open_enhancer)
    panel.on_todo_click.connect(_open_todo)
    panel.show()

    os.environ["QT_LOGGING_RULES"] = "*.debug=false"
    QTimer.singleShot(60000, _check_mem)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()