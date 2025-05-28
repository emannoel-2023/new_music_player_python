import curses
import os
import psutil
import math

def init_cores():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(6, curses.COLOR_BLUE, -1)
    curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLUE)
    curses.init_pair(8, curses.COLOR_YELLOW, -1)
    curses.init_pair(9, curses.COLOR_MAGENTA, -1)
    curses.init_pair(10, curses.COLOR_WHITE, -1)

def uso_recursos():
    p = psutil.Process(os.getpid())
    cpu = p.cpu_percent(interval=0.1)
    ram = p.memory_info().rss / (1024 * 1024)
    return cpu, ram

def limpar_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def formatar_tempo(segundos):
    if segundos is None:
        return "00:00"
    minutos = int(segundos // 60)
    segundos = int(segundos % 60)
    return f"{minutos:02}:{segundos:02}"