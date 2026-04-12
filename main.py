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

# Отключаем предупреждения
logging.disable(logging.WARNING)
warnings.filterwarnings('ignore')


def _patch_basicsr():
    """Патч совместимости basicsr + torchvision (вызывается лениво)."""
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

    cfg    = config.load()
    panel  = EdgePanelView()

    # Ленивая инициализация всех окон — создаются только при первом клике
    _player_view = None
    _player_ctrl = None
    _sorter_view = None
    _sorter_ctrl = None
    _enhancer_view = None
    _enhancer_ctrl = None
    _todo_view = None
    _todo_ctrl = None

    def _open_player():
        nonlocal _player_view, _player_ctrl
        if _player_view is None:
            print("[main] Creating PlayerView (lazy init)")
            _player_view = PlayerView(settings=cfg)
            _player_ctrl = PlayerController(_player_view)
        if not _player_view.isVisible():
            _player_view.show()
        _player_view.raise_()

    def _open_sorter():
        nonlocal _sorter_view, _sorter_ctrl
        if _sorter_view is None:
            print("[main] Creating SorterView (lazy init)")
            _sorter_view = SorterView(settings=cfg)
            _sorter_ctrl = SorterController(_sorter_view)
        if not _sorter_view.isVisible():
            _sorter_view.show()
        _sorter_view.raise_()

    def _open_enhancer():
        nonlocal _enhancer_view, _enhancer_ctrl
        if _enhancer_view is None:
            print("[main] Creating EnhancerView (lazy init)")
            _enhancer_view = EnhancerView()
            _enhancer_ctrl = EnhancerController(_enhancer_view)
        if not _enhancer_view.isVisible():
            _enhancer_view.show()
        _enhancer_view.raise_()

    def _open_todo():
        nonlocal _todo_view, _todo_ctrl
        if _todo_view is None:
            print("[main] Creating TodoView (lazy init)")
            from app.features.todo.ui.todo_view import TodoView
            from app.controllers.todo_controller import TodoController
            _todo_view = TodoView()
            _todo_ctrl = TodoController(_todo_view)
        if not _todo_view.isVisible():
            _todo_view.show()
        _todo_view.raise_()

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