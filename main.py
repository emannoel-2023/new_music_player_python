import sys
import os
import curses

# Adiciona a pasta src ao path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from audio import AudioPlayer
from biblioteca import Biblioteca
from playlist import PlaylistManager
from historico import Historico
from ui import UIPlayer
from comandos import Comandos

def main(stdscr):
    # Inicializa os componentes principais
    biblioteca = Biblioteca()
    playlist_manager = PlaylistManager()
    player = AudioPlayer()
    historico = Historico()
    ui = UIPlayer(stdscr)

    # Cria o objeto Comandos passando as dependências necessárias
    comandos = Comandos(player, playlist_manager, ui, historico)

    # Se precisar, você pode passar o objeto comandos para a UI ou player
    # Exemplo: ui.set_comandos(comandos)  # se tiver esse método

    # Inicia o loop principal da interface
    ui.loop()

if __name__ == "__main__":
    # No Windows, certifique-se de ter instalado o windows-curses:
    # pip install windows-curses
    curses.wrapper(main)
