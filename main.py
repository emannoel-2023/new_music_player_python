import sys
import os
import curses

# Adiciona a pasta src ao path para importar módulos
# Considerando que a estrutura agora é:
# project_root/
# ├── main.py
# └── src/
#     ├── audio.py
#     ├── biblioteca.py
#     ├── playlist.py
#     ├── historico.py
#     ├── config_manager.py
#     ├── radio_terminal/
#     │   └── radio.py
#     └── ui/
#         ├── ui_core.py
#         ├── ui_components.py
#         ├── ui_state.py
#         └── ui_utils.py

# Garante que 'src' e 'src/ui' estão no PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'ui'))


# Importa a classe UIPlayer do novo local (ui_core.py)
from ui_core import UIPlayer

# Importa as outras classes de negócio que não foram modularizadas ainda
from audio import AudioPlayer
from biblioteca import Biblioteca
from playlist import PlaylistManager
from historico import Historico
from config_manager import ConfigManager # Adicionado, pois ConfigManager é usado na UIPlayer
# from comandos import Comandos # Comandos não foi fornecido/modularizado, mantido comentado se não for usado

def main(stdscr):
    # As instâncias de Biblioteca, PlaylistManager, AudioPlayer e Historico
    # são criadas aqui e passadas para UIPlayer se necessário,
    # ou UIPlayer as instancia internamente se for a responsabilidade dela.
    # No seu ui_core, elas são instanciadas dentro de UIPlayer, então não precisamos passar aqui.
    # No entanto, a forma como você organiza isso pode variar.

    # ui_core.py já instancia AudioPlayer, PlaylistManager, Historico, Biblioteca, ConfigManager
    # então você não precisa passá-las diretamente para o construtor de UIPlayer aqui,
    # a menos que você queira injetar essas dependências de fora.
    # Pelo código que você forneceu para ui_core.py, UIPlayer as cria internamente.

    ui = UIPlayer(stdscr)

    # Se a classe 'Comandos' ainda existir e for usada:
    # comandos = Comandos(ui.player, ui.playlist, ui, ui.historico)
    # ui.set_comandos(comandos) # Se você criar um método set_comandos em UIPlayer

    # Inicia o loop principal da interface
    ui.loop()

if __name__ == "__main__":
    # No Windows, certifique-se de ter instalado o windows-curses:
    # pip install windows-curses
    curses.wrapper(main)