from audio import AudioPlayer
from biblioteca import Biblioteca
from playlist import PlaylistManager
from historico import Historico
from ui import UIPlayer
import curses

def main(stdscr):
    player = AudioPlayer()
    biblioteca = Biblioteca()
    playlist = PlaylistManager()
    historico = Historico()
    ui = UIPlayer(stdscr)
    # Se quiser, pode passar player, playlist, historico para UIPlayer via construtor
    # Mas no código que forneci, UIPlayer já instancia esses objetos internamente.
    ui.loop()

if __name__ == "__main__":
    curses.wrapper(main)
