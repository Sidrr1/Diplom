import os, sys
os.environ["PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin") + os.pathsep + os.environ["PATH"]

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

    p_ctrl = PlayerController(player)   # ← обязательно в переменную
    s_ctrl = SorterController(sorter)   # ← иначе GC удалит

    print(f"[main] PlayerController created: {p_ctrl}")
    print(f"[main] play_requested connected: {player.play_requested}")

    panel.on_player_click.connect(lambda: (player.show(), player.raise_()))
    panel.on_sorter_click.connect(lambda: (sorter.show(), sorter.raise_()))
    panel.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()