import sys
import os
 
from PySide6.QtWidgets import QApplication
from app.ui.edge_panel_view import EdgePanelView
from app.ui.player_view import PlayerView
from app.ui.sorter_view import SorterView
from app.controllers.player_controller import PlayerController
from app.controllers.sorter_controller import SorterController
from app.core import config
 
def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
 
    cfg    = config.load()
    panel  = EdgePanelView()
    player = PlayerView(settings=cfg)
    sorter = SorterView(settings=cfg)
 
    p_ctrl = PlayerController(player)
    s_ctrl = SorterController(sorter)
 
    print(f"[main] PlayerController created: {p_ctrl}")
    print(f"[main] play_requested connected: {player.play_requested}")
 
    panel.on_player_click.connect(lambda: (player.show(), player.raise_()))
    panel.on_sorter_click.connect(lambda: (sorter.show(), sorter.raise_()))
    panel.show()
 
    os.environ["QT_LOGGING_RULES"] = "*.debug=false"
    sys.exit(app.exec())
 
 
if __name__ == "__main__":
    main()
 