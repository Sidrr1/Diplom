import os
import sys

from PySide6.QtWidgets import QApplication
from app.features.edge_panel.ui.edge_panel_view import EdgePanelView
from app.features.player.ui.player_view import PlayerView
from app.features.file_sorter.ui.sorter_view import SorterView
from app.controllers.player_controller import PlayerController
from app.controllers.sorter_controller import SorterController
from app.controllers.ocr_controller import OcrController
from app.core import config

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    cfg    = config.load()
    panel  = EdgePanelView()
    player = PlayerView(settings=cfg)
    sorter = SorterView(settings=cfg)

    p_ctrl   = PlayerController(player)
    s_ctrl   = SorterController(sorter)
    ocr_ctrl = OcrController()          

    panel.set_ocr_controller(ocr_ctrl)  

    print(f"[main] PlayerController created: {p_ctrl}")
    print(f"[main] play_requested connected: {player.play_requested}")

    panel.on_player_click.connect(lambda: (player.show(), player.raise_()))
    panel.on_sorter_click.connect(lambda: (sorter.show(), sorter.raise_()))
    panel.show()

    os.environ["QT_LOGGING_RULES"] = "*.debug=false"
    sys.exit(app.exec())


if __name__ == "__main__":
    main()