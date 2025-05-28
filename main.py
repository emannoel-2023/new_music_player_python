import sys
import os
import curses
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'ui'))
from ui_core import UIPlayer
from audio import AudioPlayer
from biblioteca import Biblioteca
from playlist import PlaylistManager
from historico import Historico
from config_manager import ConfigManager

def main(stdscr):
    ui = UIPlayer(stdscr)
    ui.loop()

if __name__ == "__main__":

    curses.wrapper(main)