import curses
import time
import os
import json
import psutil
import math
from pyfiglet import Figlet

from audio import AudioPlayer
from playlist import PlaylistManager
from historico import Historico
from utils import formatar_tempo

# Importação do módulo do rádio
from radio_terminal.radio import RadioPlayer

PASTA_DADOS = os.path.join(os.path.dirname(__file__), '..', 'data')
ESTADO_PLAYLIST_ARQUIVO = os.path.join(PASTA_DADOS, 'estado_playlist.json')
HISTORICO_ARQUIVO = os.path.join(PASTA_DADOS, 'historico.json')
FAVORITOS_ARQUIVO = os.path.join(PASTA_DADOS, 'favoritos.json')

def init_cores():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(6, curses.COLOR_BLUE, -1)
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(8, curses.COLOR_YELLOW, -1)
    curses.init_pair(9, curses.COLOR_CYAN, -1)
    curses.init_pair(10, curses.COLOR_WHITE, -1)

def uso_recursos():
    p = psutil.Process(os.getpid())
    cpu = p.cpu_percent(interval=0.1)
    ram = p.memory_info().rss / (1024 * 1024)
    return cpu, ram

class UIPlayer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.player = AudioPlayer()
        self.playlist = PlaylistManager()
        self.historico = Historico()
        self.volume = self.player.get_volume()
        self.playlist_selecionada = 0
        self.playlist_offset = 0
        self.executando = True
        self.favoritos = set()
        self.espectro_atual = [0] * 20

        # Rádio
        self.radio_ativo = False
        self.radio_player = RadioPlayer()
        self.musica_pausada_para_radio = False

        init_cores()
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        curses.curs_set(0)

        self.carregar_historico()
        self.carregar_favoritos()
        self.playlist.carregar_estado()

        if self.playlist.playlists:
            primeira = next(iter(self.playlist.playlists))
            self.playlist.playlist_atual = self.playlist.playlists[primeira].copy()
            self.playlist_selecionada = 0
            if self.playlist.playlist_atual:
                self.player.carregar_musica(self.playlist.playlist_atual[0])
                self.historico.adicionar(self.playlist.playlist_atual[0])

    def solicitar_entrada(self, prompt, y):
        curses.echo()
        self.stdscr.move(y, 2)
        self.stdscr.clrtoeol()
        self.stdscr.addstr(y, 2, prompt)
        self.stdscr.refresh()
        entrada = self.stdscr.getstr(y, 2 + len(prompt)).decode("utf-8").strip()
        curses.noecho()
        return entrada

    def salvar_historico(self):
        try:
            with open(HISTORICO_ARQUIVO, 'w', encoding='utf-8') as f:
                json.dump(self.historico.pilha, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar histórico: {e}")

    def carregar_historico(self):
        try:
            if os.path.exists(HISTORICO_ARQUIVO):
                with open(HISTORICO_ARQUIVO, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    self.historico.pilha = dados if isinstance(dados, list) else []
            else:
                self.historico.pilha = []
        except Exception as e:
            print(f"Erro ao carregar histórico: {e}")
            self.historico.pilha = []

    def salvar_favoritos(self):
        try:
            with open(FAVORITOS_ARQUIVO, 'w', encoding='utf-8') as f:
                json.dump(list(self.favoritos), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar favoritos: {e}")

    def carregar_favoritos(self):
        try:
            if os.path.exists(FAVORITOS_ARQUIVO):
                with open(FAVORITOS_ARQUIVO, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    self.favoritos = set(dados) if isinstance(dados, list) else set()
            else:
                self.favoritos = set()
        except Exception as e:
            print(f"Erro ao carregar favoritos: {e}")
            self.favoritos = set()

    def desenhar_borda(self):
        self.stdscr.border()

    def desenhar_titulo(self):
        fig = Figlet(font='slant', width=80)
        titulo_ascii = fig.renderText('MUSGA')
        for i in range(5):
            self.stdscr.move(i, 2)
            self.stdscr.clrtoeol()
        linhas = titulo_ascii.split('\n')
        for idx, linha in enumerate(linhas[:5]):
            if linha.strip():
                self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
                x_pos = max(2, (curses.COLS - len(linha)) // 2)
                self.stdscr.addstr(idx, x_pos, linha)
                self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)

    def desenhar_espectro(self, y, x, largura=20, altura=4):
        num_barras = 20
        progresso = self.player.get_progresso()
        tocando = self.player.get_nome() and self.player.get_progresso() > 0 and not getattr(self.player, 'pausado', False)
        if not tocando:
            self.espectro_atual = [max(0, v - 0.2) for v in self.espectro_atual]
        else:
            self.espectro_atual = [min(altura-1, abs(math.sin(progresso * 3 + i * 0.5)) * (altura-1)) for i in range(num_barras)]
        cores = [
            curses.color_pair(4), curses.color_pair(5), curses.color_pair(6),
            curses.color_pair(8), curses.color_pair(9), curses.color_pair(10)
        ]
        for j in range(altura):
            self.stdscr.move(y + j, x)
            self.stdscr.clrtoeol()
        for i, val in enumerate(self.espectro_atual):
            col = x + i * 4
            h = int(val)
            cor = cores[i % len(cores)]
            for j in range(altura):
                if col + 2 < curses.COLS:
                    char = "██" if altura - j <= h else " "
                    if altura - j <= h:
                        self.stdscr.addstr(y + j, col, char, cor)
                    else:
                        self.stdscr.addstr(y + j, col, " ")

    def desenhar_volume(self, y, x, largura=20):
        vol = self.player.get_volume()
        preenchido = int(vol * largura)
        barra = "[" + "=" * preenchido + ">" + " " * (largura - preenchido) + "]"
        self.stdscr.attron(curses.color_pair(3))
        self.stdscr.addstr(y, x, f"Volume: {barra} {int(vol*100)}%")
        self.stdscr.attroff(curses.color_pair(3))

    def desenhar_playlist(self, y, x, altura, largura):
        self.stdscr.attron(curses.A_BOLD)
        self.stdscr.addstr(y, x, "Playlist Atual:")
        self.stdscr.attroff(curses.A_BOLD)
        playlist = self.playlist.playlist_atual
        total = len(playlist)
        itens_por_coluna = 10
        total_colunas = (total + itens_por_coluna - 1) // itens_por_coluna
        coluna_atual = self.playlist_offset
        inicio = coluna_atual * itens_por_coluna
        fim = min(inicio + itens_por_coluna, total)
        for i, idx in enumerate(range(inicio, fim)):
            musica = os.path.basename(playlist[idx])
            favorito = "★" if playlist[idx] in self.favoritos else " "
            if idx == self.playlist_selecionada:
                self.stdscr.attron(curses.color_pair(2))
                self.stdscr.addstr(y + 1 + i, x, f"> {favorito} {musica}")
                self.stdscr.attroff(curses.color_pair(2))
            else:
                self.stdscr.addstr(y + 1 + i, x, f" {favorito} {musica}")
        self.stdscr.addstr(y + altura - 1, x, f"Coluna {coluna_atual+1}/{total_colunas}")

    def desenhar_status(self, y, x):
        nome = self.player.get_nome()
        progresso = self.player.get_progresso()
        duracao = self.player.get_duracao()
        texto = f"Tocando: {nome if nome else 'Nenhuma música'}"
        self.stdscr.addstr(y, x, texto[:curses.COLS - 4])
        tempo_str = f"{formatar_tempo(progresso)} / {formatar_tempo(duracao)}"
        self.stdscr.addstr(y + 1, x, tempo_str)

    def desenhar_recursos(self, y, x):
        cpu, ram = uso_recursos()
        texto = f"CPU: {cpu:.1f}% | RAM: {ram:.1f} MB"
        self.stdscr.addstr(y, x, texto)

    def abrir_diretorio(self):
        caminho = self.solicitar_entrada("Cole o caminho do diretório: ", curses.LINES - 3)
        if os.path.isdir(caminho):
            self.playlist.carregar_diretorio(caminho)
            if self.playlist.playlist_atual:
                self.playlist_selecionada = 0
                self.playlist_offset = 0
                self.player.carregar_musica(self.playlist.playlist_atual[0])
                self.player.play_pause()
                self.historico.adicionar(self.playlist.playlist_atual[0])
        else:
            self.stdscr.addstr(curses.LINES - 3, 2, "Diretório inválido! Pressione qualquer tecla...")
            self.stdscr.getch()

    def listar_playlists(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 2, "Playlists salvas (Enter para carregar, Q para sair):", curses.color_pair(1) | curses.A_BOLD)
        nomes = list(self.playlist.playlists.keys())
        if not nomes:
            self.stdscr.addstr(2, 2, "Nenhuma playlist encontrada.")
            self.stdscr.refresh()
            self.stdscr.getch()
            return
        idx = 0
        while True:
            for i, nome in enumerate(nomes):
                if i == idx:
                    self.stdscr.attron(curses.color_pair(2))
                    self.stdscr.addstr(2 + i, 2, f"> {nome}")
                    self.stdscr.attroff(curses.color_pair(2))
                else:
                    self.stdscr.addstr(2 + i, 2, f" {nome}")
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            elif key == curses.KEY_UP and idx > 0:
                idx -= 1
            elif key == curses.KEY_DOWN and idx < len(nomes) - 1:
                idx += 1
            elif key in (curses.KEY_ENTER, 10, 13):
                self.playlist.playlist_atual = self.playlist.playlists[nomes[idx]].copy()
                self.playlist_selecionada = 0
                self.playlist_offset = 0
                if self.playlist.playlist_atual:
                    self.player.carregar_musica(self.playlist.playlist_atual[0])
                break

    def criar_playlist(self):
        nome = self.solicitar_entrada("Nome da nova playlist: ", curses.LINES - 3)
        if nome:
            if self.playlist.criar_playlist(nome):
                self.stdscr.addstr(curses.LINES - 3, 2, f"Playlist '{nome}' criada! Pressione qualquer tecla...")
            else:
                self.stdscr.addstr(curses.LINES - 3, 2, f"Playlist '{nome}' já existe! Pressione qualquer tecla...")
            self.stdscr.getch()

    def adicionar_musica_playlist(self):
        if not self.playlist.playlists:
            self.stdscr.addstr(curses.LINES - 3, 2, "Nenhuma playlist criada! Pressione qualquer tecla...")
            self.stdscr.getch()
            return
        nome = self.solicitar_entrada("Digite o nome da playlist para adicionar: ", curses.LINES - 3)
        if nome not in self.playlist.playlists:
            self.stdscr.addstr(curses.LINES - 3, 2, "Playlist não existe! Pressione qualquer tecla...")
            self.stdscr.getch()
            return
        musica_atual = None
        if self.playlist.playlist_atual and 0 <= self.playlist_selecionada < len(self.playlist.playlist_atual):
            musica_atual = self.playlist.playlist_atual[self.playlist_selecionada]
        if musica_atual:
            if self.playlist.adicionar_na_playlist(nome, musica_atual):
                self.stdscr.addstr(curses.LINES - 3, 2, f"Música '{os.path.basename(musica_atual)}' adicionada à playlist '{nome}'. Pressione qualquer tecla...")
            else:
                self.stdscr.addstr(curses.LINES - 3, 2, "Música já está na playlist! Pressione qualquer tecla...")
            self.stdscr.getch()
        else:
            self.stdscr.addstr(curses.LINES - 3, 2, "Nenhuma música selecionada para adicionar! Pressione qualquer tecla...")
            self.stdscr.getch()

    def remover_musica_playlist(self):
        nome = self.solicitar_entrada("Nome da playlist para remover música: ", curses.LINES - 3)
        if nome not in self.playlist.playlists:
            self.stdscr.addstr(curses.LINES - 3, 2, "Playlist não existe! Pressione qualquer tecla...")
            self.stdscr.getch()
            return
        try:
            indice_str = self.solicitar_entrada("Índice da música para remover (0-based): ", curses.LINES - 3)
            indice = int(indice_str)
        except:
            indice = -1
        if self.playlist.remover_da_playlist(nome, indice):
            self.stdscr.addstr(curses.LINES - 3, 2, "Música removida! Pressione qualquer tecla...")
        else:
            self.stdscr.addstr(curses.LINES - 3, 2, "Índice inválido! Pressione qualquer tecla...")
        self.stdscr.getch()

    def favoritar_desfavoritar(self):
        if not self.playlist.playlist_atual:
            return
        musica = self.playlist.playlist_atual[self.playlist_selecionada]
        if musica in self.favoritos:
            self.favoritos.remove(musica)
        else:
            self.favoritos.add(musica)
        self.salvar_favoritos()

    def saltar_para_musica(self):
        try:
            num_str = self.solicitar_entrada("Número da música para saltar (1-based): ", curses.LINES - 3)
            num = int(num_str)
        except:
            num = -1
        if 1 <= num <= len(self.playlist.playlist_atual):
            self.playlist_selecionada = num - 1
            self._tocar_selecionada()
        else:
            self.stdscr.addstr(curses.LINES - 3, 2, "Número inválido! Pressione qualquer tecla...")
            self.stdscr.getch()

    def ordenar_playlist(self):
        opcao = self.solicitar_entrada("Ordenar por (n)ome ou (d)uração? ", curses.LINES - 3).lower()
        if opcao == 'n':
            self.playlist.playlist_atual.sort()
        elif opcao == 'd':
            import pygame
            def duracao(musica):
                try:
                    som = pygame.mixer.Sound(musica)
                    return som.get_length()
                except:
                    return 0
            self.playlist.playlist_atual.sort(key=duracao)
        else:
            self.stdscr.addstr(curses.LINES - 3, 2, "Opção inválida! Pressione qualquer tecla...")
            self.stdscr.getch()

    def play_pause(self):
        self.player.play_pause()

    def parar(self):
        self.player.parar()

    def proxima(self):
        if not self.playlist.playlist_atual:
            return
        self.playlist_selecionada = (self.playlist_selecionada + 1) % len(self.playlist.playlist_atual)
        self._tocar_selecionada()

    def anterior(self):
        if not self.playlist.playlist_atual:
            return
        self.playlist_selecionada = (self.playlist_selecionada - 1) % len(self.playlist.playlist_atual)
        self._tocar_selecionada()

    def _tocar_selecionada(self):
        if self.playlist.playlist_atual:
            musica = self.playlist.playlist_atual[self.playlist_selecionada]
            self.player.carregar_musica(musica)
            self.player.play_pause()
            self.historico.adicionar(musica)
            altura_visivel = curses.LINES - 10
            if self.playlist_selecionada < self.playlist_offset * 10:
                self.playlist_offset = self.playlist_selecionada // 10
            elif self.playlist_selecionada >= (self.playlist_offset + 1) * 10:
                self.playlist_offset = self.playlist_selecionada // 10

    def aumentar_volume(self):
        vol_novo = min(1.0, self.player.get_volume() + 0.05)
        self.player.setar_volume(vol_novo)

    def diminuir_volume(self):
        vol_novo = max(0.0, self.player.get_volume() - 0.05)
        self.player.setar_volume(vol_novo)

    def mostrar_historico(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 2, "Histórico de Reprodução (Pressione Q para sair)", curses.color_pair(1) | curses.A_BOLD)
        for i, musica in enumerate(reversed(self.historico.pilha[-(curses.LINES-3):])):
            nome = os.path.basename(musica)
            self.stdscr.addstr(i+2, 2, f"{len(self.historico.pilha) - i}. {nome}")
        self.stdscr.refresh()
        while True:
            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            time.sleep(0.1)

    def loop(self):
        while self.executando:
            if self.radio_ativo:
                self.radio_player.draw_interface(self.stdscr)  # Limita a 2 colunas dentro do radio.py
                self.stdscr.refresh()
                key = self.stdscr.getch()
                if key in (ord('b'), ord('B')):
                    # Voltar para player
                    self.radio_player.stop()
                    self.radio_ativo = False
                    if self.musica_pausada_para_radio:
                        self.player.play_pause()
                        self.musica_pausada_para_radio = False
                    continue
                else:
                    # Passar comando para rádio
                    self.radio_player.handle_input(key)
                    time.sleep(0.05)
                    continue

            self.stdscr.erase()
            self.desenhar_borda()
            self.desenhar_titulo()
            y_pos = 6
            self.desenhar_espectro(y_pos, 2, largura=80, altura=4)
            y_pos += 5
            altura_playlist = 10
            self.desenhar_playlist(y_pos, 2, altura_playlist, 60)
            y_pos += altura_playlist + 1
            self.desenhar_volume(y_pos, 2)
            y_pos += 2
            self.desenhar_status(y_pos, 2)
            y_pos += 2
            self.desenhar_recursos(curses.LINES - 4, 2)

            menu_line1 = "[1]Abrir [2]Play/Pause [3]Ant [4]Próx [+/-]Vol [C]Criar [A]Add [D]Rem [F]Fav"
            menu_line2 = "[S]Saltar [O]Ordenar [H]Histórico [L]Listar [Enter]Tocar [Q]Sair [R]Rádio"
            self.stdscr.attron(curses.A_REVERSE)
            self.stdscr.addstr(curses.LINES - 3, 2, menu_line1)
            self.stdscr.addstr(curses.LINES - 2, 2, menu_line2)
            self.stdscr.attroff(curses.A_REVERSE)
            self.stdscr.refresh()

            try:
                key = self.stdscr.getch()
            except KeyboardInterrupt:
                break

            if key == -1:
                time.sleep(0.05)
                continue

            itens_por_coluna = 10
            if self.playlist.playlist_atual:
                max_col = (len(self.playlist.playlist_atual) - 1) // itens_por_coluna
            else:
                max_col = 0

            if key == curses.KEY_LEFT:
                if self.playlist_offset > 0:
                    self.playlist_offset -= 1
                    self.playlist_selecionada = self.playlist_offset * itens_por_coluna
            elif key == curses.KEY_RIGHT:
                if self.playlist_offset < max_col:
                    self.playlist_offset += 1
                    self.playlist_selecionada = self.playlist_offset * itens_por_coluna
            elif key == curses.KEY_UP:
                if self.playlist_selecionada > 0:
                    self.playlist_selecionada -= 1
                    if self.playlist_selecionada < self.playlist_offset * itens_por_coluna:
                        self.playlist_offset -= 1
            elif key == curses.KEY_DOWN:
                if self.playlist_selecionada < len(self.playlist.playlist_atual) - 1:
                    self.playlist_selecionada += 1
                    if self.playlist_selecionada >= (self.playlist_offset + 1) * itens_por_coluna:
                        self.playlist_offset += 1
            elif key == ord('1'):
                self.abrir_diretorio()
            elif key == ord('2'):
                self.play_pause()
            elif key == ord('3'):
                self.anterior()
            elif key == ord('4'):
                self.proxima()
            elif key == ord('+') or key == ord('='):
                self.aumentar_volume()
            elif key == ord('-'):
                self.diminuir_volume()
            elif key == ord('c') or key == ord('C'):
                self.criar_playlist()
            elif key == ord('a') or key == ord('A'):
                self.adicionar_musica_playlist()
            elif key == ord('d') or key == ord('D'):
                self.remover_musica_playlist()
            elif key == ord('f') or key == ord('F'):
                self.favoritar_desfavoritar()
            elif key == ord('s') or key == ord('S'):
                self.saltar_para_musica()
            elif key == ord('o') or key == ord('O'):
                self.ordenar_playlist()
            elif key == ord('h') or key == ord('H'):
                self.mostrar_historico()
            elif key == ord('l') or key == ord('L'):
                self.listar_playlists()
            elif key in (curses.KEY_ENTER, 10, 13):
                self._tocar_selecionada()
            elif key == ord('q') or key == ord('Q'):
                self.executando = False
            elif key == ord('r'):
                # Ativar rádio
                if self.player.get_nome() and self.player.get_progresso() > 0 and not getattr(self.player, 'pausado', False):
                    self.player.play_pause()
                    self.musica_pausada_para_radio = True
                self.radio_ativo = True
            else:
                pass  # Outros comandos

            time.sleep(0.05)
