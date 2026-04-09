import os
import sys

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
    player = PlayerView(settings=cfg)
    sorter = SorterView(settings=cfg)

    # EnhancerView создаётся лениво — только при первом клике
    _enhancer_view = None
    _enhancer_ctrl = None

    def _open_enhancer():
        nonlocal _enhancer_view, _enhancer_ctrl
        if _enhancer_view is None:
            _enhancer_view = EnhancerView()
            _enhancer_ctrl = EnhancerController(_enhancer_view)
        if not _enhancer_view.isVisible():
            _enhancer_view.show()
        _enhancer_view.raise_()

    p_ctrl   = PlayerController(player)
    s_ctrl   = SorterController(sorter)
    ocr_ctrl = OcrController()

    panel.set_ocr_controller(ocr_ctrl)

    print(f"[main] PlayerController created: {p_ctrl}")
    print(f"[main] play_requested connected: {player.play_requested}")

    panel.on_player_click.connect(lambda: (player.show(), player.raise_()))
    panel.on_sorter_click.connect(lambda: (sorter.show(), sorter.raise_()))
    panel.on_enhancer_click.connect(_open_enhancer)
    panel.show()

    os.environ["QT_LOGGING_RULES"] = "*.debug=false"

    QTimer.singleShot(60000, _check_mem)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()