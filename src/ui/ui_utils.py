import curses
import os
import psutil
import math

def init_cores():
    """Inicializa os pares de cores para a interface curses."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)     # Ciano
    curses.init_pair(2, curses.COLOR_YELLOW, -1)   # Amarelo (para seleção de playlist, etc.)
    curses.init_pair(3, curses.COLOR_GREEN, -1)    # Verde (para volume, etc.)
    curses.init_pair(4, curses.COLOR_RED, -1)      # Vermelho (mantido para avisos se necessário)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Magenta (para título, e agora também para espectro)
    curses.init_pair(6, curses.COLOR_BLUE, -1)     # Azul (para espectro)
    curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLUE) # Branco sobre azul (para maior destaque no espectro)
    curses.init_pair(8, curses.COLOR_YELLOW, -1)   # Amarelo (mantido, talvez para médio-graves)
    curses.init_pair(9, curses.COLOR_MAGENTA, -1)  # Roxo/Magenta mais escuro (para espectro - se COLOR_MAGENTA for muito claro, você pode tentar definir uma cor customizada se o terminal suportar)
    curses.init_pair(10, curses.COLOR_WHITE, -1)   # Branco

    # Se seu terminal suportar mais cores e você quiser tons de roxo mais específicos:
    # try:
    #     curses.init_color(200, 500, 0, 500) # Exemplo: Roxo mais escuro (RGB 50%, 0%, 50%)
    #     curses.init_pair(9, 200, -1)
    # except curses.error:
    #     pass # Terminal não suporta init_color

def uso_recursos():
    """Retorna o uso de CPU e RAM do processo atual."""
    p = psutil.Process(os.getpid())
    cpu = p.cpu_percent(interval=0.1)
    ram = p.memory_info().rss / (1024 * 1024)
    return cpu, ram

def limpar_terminal():
    """Limpa a tela do terminal, compatível com Windows e sistemas Unix."""
    os.system('cls' if os.name == 'nt' else 'clear')

def formatar_tempo(segundos):
    """Formata um tempo em segundos para o formato MM:SS."""
    if segundos is None:
        return "00:00"
    minutos = int(segundos // 60)
    segundos = int(segundos % 60)
    return f"{minutos:02}:{segundos:02}"