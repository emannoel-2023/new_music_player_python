import curses
import time
import os
import subprocess
import threading
import queue
import pathlib

from ui_utils import init_cores, uso_recursos, limpar_terminal, formatar_tempo
from ui_components import UIComponents
from constants import PASTA_DADOS

from audio import AudioPlayer
from playlist import PlaylistManager
from historico import Historico
from biblioteca import Biblioteca
from config_manager import ConfigManager
from radio_terminal.radio import RadioPlayer
from biblioteca import Musica

from youtube_integration import YouTubeIntegration

class UIPlayer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.player = AudioPlayer()
        self.playlist = PlaylistManager()
        self.historico = Historico()
        self.biblioteca = Biblioteca()
        self.config_manager = ConfigManager()
        self.radio_player_instance = None

        self.ui_components = UIComponents(stdscr)

        self.volume = self.player.get_volume()
        self.playlist_selecionada = 0
        self.playlist_offset = 0
        self.executando = True
        self.espectro_atual = [0] * 20
        self.radio_ativo = False
        self.youtube_ativo = False
        self.youtube_carregando = False # Esta flag não será mais usada para exibir o loading na UI Curses
        self.equalizacao = {'grave': 0, 'medio': 0, 'agudo': 0}
        self.modo_visualizacao = 'lista'
        self.filtro_atual = None
        self.termo_busca_atual = ""
        self.musica_pausada_para_radio = False
        self.musica_pausada_para_youtube = False

        self.curses_lines = curses.LINES
        self.curses_cols = curses.COLS

        init_cores()
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        curses.curs_set(0)

        self.playlist.playlist_atual = []

        self.player.add_observer(self)

        self.ui_message_queue = queue.Queue()
        self.youtube_integration = YouTubeIntegration(self.ui_message_queue)


    def atualizar(self, evento):
        if evento == 'carregar_musica':
            pass
        elif evento == 'play_pause':
            pass
        elif evento == 'volume':
            self.volume = self.player.get_volume()
        elif evento == 'equalizacao':
            pass
        elif evento == 'musica_terminada':
            if not self.radio_ativo and not self.youtube_ativo:
                self.proxima()

    def _display_ui_message(self, message):
        """Enfileira uma mensagem para ser mostrada na UI. Lida com mensagens longas."""
        try:
            self.ui_message_queue.put_nowait(message)
        except queue.Full:
            pass

    def buscar_musicas(self):
        self.stdscr.nodelay(False)
        termo = self.ui_components.solicitar_entrada("Digite o termo de busca: ", curses.LINES - 3)
        if termo:
            self.termo_busca_atual = termo
            resultados = self.biblioteca.buscar(termo)
            if resultados:
                self.playlist.playlist_atual = [m.caminho for m in resultados]
                self.playlist_selecionada = 0
                self.playlist_offset = 0
                self._display_ui_message(f"Encontradas {len(resultados)} músicas. Pressione qualquer tecla...")
            else:
                self._display_ui_message("Nenhuma música encontrada! Pressione qualquer tecla...")
        self.stdscr.nodelay(True)

    def filtrar_por_categoria(self):
        self.stdscr.nodelay(False)
        self.stdscr.clear()

        max_linhas_opcoes = curses.LINES - 5
        opcoes = ["1 - Artista", "2 - Álbum", "3 - Gênero", "4 - Limpar filtro"]

        try:
            self.stdscr.addstr(0, 2, "Filtrar por:", curses.color_pair(1) | curses.A_BOLD)
            for i, opcao in enumerate(opcoes[:max_linhas_opcoes]):
                self.stdscr.addstr(i + 2, 2, opcao[:curses.COLS - 4])

            prompt_y = min(len(opcoes) + 3, curses.LINES - 2)
            self.stdscr.addstr(prompt_y, 2, "Escolha uma opção: ")
            self.stdscr.refresh()

            key = self.stdscr.getch()
            if key == ord('1'):
                self._filtrar_por('artista')
            elif key == ord('2'):
                self._filtrar_por('album')
            elif key == ord('3'):
                self._filtrar_por('genero')
            elif key == ord('4'):
                self.filtro_atual = None
                self.playlist.playlist_atual = [m.caminho for m in self.biblioteca.musicas]
                self.playlist_selecionada = 0
                self.playlist_offset = 0
            else:
                self._display_ui_message("Opção inválida! Pressione qualquer tecla...")

        except curses.error:
            self._display_ui_message("Terminal muito pequeno para filtrar!")

        self.stdscr.nodelay(True)

    def _filtrar_por(self, categoria):
        grupos = self.biblioteca.listar_por(categoria)
        opcoes = list(grupos.keys())
        if not opcoes:
            self._display_ui_message("Nenhuma categoria encontrada! Pressione qualquer tecla...")
            return
        idx = 0
        while True:
            self.stdscr.clear()

            max_opcoes_visiveis = curses.LINES - 5

            try:
                self.stdscr.addstr(0, 2, f"Filtrar por {categoria} (↑↓ para navegar, Enter para selecionar, Q para sair):", curses.color_pair(1) | curses.A_BOLD)

                start_display_idx = max(0, idx - max_opcoes_visiveis // 2)
                end_display_idx = min(len(opcoes), start_display_idx + max_opcoes_visiveis)
                if end_display_idx - start_display_idx < max_opcoes_visiveis:
                    start_display_idx = max(0, end_display_idx - max_opcoes_visiveis)

                for i, opcao_idx in enumerate(range(start_display_idx, end_display_idx)):
                    opcao = opcoes[opcao_idx]
                    texto = f"> {opcao}" if opcao_idx == idx else f"  {opcao}"
                    maxlen = curses.COLS - 4
                    if len(texto) > maxlen:
                        texto = texto[:maxlen-3] + "..."

                    if opcao_idx == idx:
                        self.stdscr.attron(curses.color_pair(2))
                        self.stdscr.addstr(i + 2, 2, texto)
                        self.stdscr.attroff(curses.color_pair(2))
                    else:
                        self.stdscr.addstr(i + 2, 2, texto)
                self.stdscr.refresh()
            except curses.error:
                self._display_ui_message("Terminal muito pequeno para listar opções!")
                break

            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            elif key == curses.KEY_UP:
                idx = max(0, idx - 1)
            elif key == curses.KEY_DOWN:
                idx = min(len(opcoes) - 1, idx + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                self.filtro_atual = (categoria, opcoes[idx])
                self.playlist.playlist_atual = [m.caminho for m in grupos[opcoes[idx]]]
                self.playlist_selecionada = 0
                self.playlist_offset = 0
                break

    def _pre_processar_audio_com_eq(self, caminho_original):
        import tempfile
        from pydub import AudioSegment
        import numpy as np

        try:
            audio = AudioSegment.from_file(caminho_original)
            samples = audio.get_array_of_samples()
            arr = np.array(samples).astype(np.float32)

            if audio.channels == 2:
                left = arr[0::2]
                right = arr[1::2]
                arr_eq = arr
            else:
                arr_eq = arr

            arr_eq = np.clip(arr_eq, -32768, 32767).astype(np.int16)
            audio_eq = audio._spawn(arr_eq.tobytes())

            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio_eq.export(temp_file.name, format='wav')

            return temp_file.name
        except Exception as e:
            return caminho_original

    def controlar_equalizacao(self):
        self.stdscr.clear()
        controles = ['grave', 'medio', 'agudo']
        idx = 0
        while True:
            self.stdscr.clear()
            try:
                self.stdscr.addstr(0, 2, "Equalização (↑↓ para navegar, ←→ para ajustar, Q para sair)", curses.color_pair(1) | curses.A_BOLD)
                for i, controle in enumerate(controles):
                    valor = self.equalizacao[controle]
                    barra = self.ui_components.criar_barra_eq(valor)

                    line_text = f"  {controle.upper()}: {barra} ({valor:+.1f})"
                    if len(line_text) > curses.COLS - 4:
                        line_text = line_text[:curses.COLS - 7] + "..."

                    if i == idx:
                        self.stdscr.attron(curses.color_pair(2))
                        self.stdscr.addstr(i + 3, 2, f"> {line_text[2:]}")
                        self.stdscr.attroff(curses.color_pair(2))
                    else:
                        self.stdscr.addstr(i + 3, 2, line_text)
                self.stdscr.refresh()
            except curses.error:
                self._display_ui_message("Terminal muito pequeno para EQ!")
                break

            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            elif key == curses.KEY_UP and idx > 0:
                idx -= 1
            elif key == curses.KEY_DOWN and idx < len(controles) - 1:
                idx += 1
            elif key == curses.KEY_LEFT:
                controle = controles[idx]
                self.equalizacao[controle] = max(-10, self.equalizacao[controle] - 0.5)
                self.player.set_equalizacao(
                    self.equalizacao['grave'],
                    self.equalizacao['medio'],
                    self.equalizacao['agudo']
                )
            elif key == curses.KEY_RIGHT:
                controle = controles[idx]
                self.equalizacao[controle] = min(10, self.equalizacao[controle] + 0.5)
                self.player.set_equalizacao(
                    self.equalizacao['grave'],
                    self.equalizacao['medio'],
                    self.equalizacao['agudo']
                )

    def mostrar_estatisticas(self):
        self.stdscr.nodelay(False)
        self.stdscr.clear()

        y_offset = 2

        try:
            self.stdscr.addstr(0, 2, "Estatísticas de Reprodução", curses.color_pair(1) | curses.A_BOLD)

            stats = self.historico.estatisticas(10)

            max_lines_content = curses.LINES - (y_offset + 5)

            if max_lines_content > 0:
                self.stdscr.addstr(y_offset, 2, "Músicas mais tocadas:", curses.color_pair(3) | curses.A_BOLD)
                y_offset += 1
                if not stats:
                    self.stdscr.addstr(y_offset, 4, "Nenhuma música tocada ainda.")
                    y_offset += 1
                for i, (musica, count) in enumerate(stats):
                    if y_offset + i >= curses.LINES - 2:
                        break
                    nome = os.path.basename(musica)
                    display_text = f"{i+1}. {nome} ({count}x)"
                    if len(display_text) > curses.COLS - 6:
                        display_text = display_text[:curses.COLS - 9] + "..."
                    self.stdscr.addstr(y_offset + i, 4, display_text)

                y_offset += len(stats) + 2

                if y_offset < curses.LINES - 2:
                    self.stdscr.addstr(y_offset, 2, "Estatísticas Gerais:", curses.color_pair(3) | curses.A_BOLD)
                    y_offset += 1

                    if y_offset < curses.LINES - 2:
                        self.stdscr.addstr(y_offset, 4, f"Total de reproduções: {len(self.historico.pilha)}")
                        y_offset += 1
                    if y_offset < curses.LINES - 2:
                        self.stdscr.addstr(y_offset, 4, f"Músicas únicas: {len(set(self.historico.pilha))}")
                        y_offset += 1
                    if y_offset < curses.LINES - 2:
                        self.stdscr.addstr(y_offset, 4, f"Favoritos: {len(self.playlist.favoritos)}")
                        y_offset += 1
                    if y_offset < curses.LINES - 2:
                        self.stdscr.addstr(y_offset, 4, f"Playlists: {len(self.playlist.playlists)}")
                        y_offset += 1

                    if self.biblioteca.musicas and y_offset < curses.LINES - 2:
                        y_offset += 2
                        self.stdscr.addstr(y_offset, 2, "Biblioteca:", curses.color_pair(3) | curses.A_BOLD)
                        y_offset += 1
                        if y_offset < curses.LINES - 2:
                            self.stdscr.addstr(y_offset, 4, f"Total de músicas: {len(self.biblioteca.musicas)}")
                            y_offset += 1

                        generos = self.biblioteca.listar_por('genero')
                        if y_offset < curses.LINES - 2:
                            self.stdscr.addstr(y_offset, 4, f"Gêneros diferentes: {len(generos)}")
                            y_offset += 1

                        artistas = self.biblioteca.listar_por('artista')
                        if y_offset < curses.LINES - 2:
                            self.stdscr.addstr(y_offset, 4, f"Artistas diferentes: {len(artistas)}")
                            y_offset += 1

            prompt_message = "Pressione qualquer tecla para voltar..."
            prompt_y = curses.LINES - 2
            if prompt_y >= 0:
                self.stdscr.addstr(prompt_y, 2, prompt_message)
            self.stdscr.refresh()
            self.stdscr.getch()

        except curses.error:
            self._display_ui_message("Terminal muito pequeno para estatísticas!")

        self.stdscr.nodelay(True)

    def solicitar_entrada(self, prompt, y):
        return self.ui_components.solicitar_entrada(prompt, y)

    def abrir_diretorio(self):
        self.stdscr.nodelay(False)

        min_cols_for_input_window = 70
        if curses.COLS < min_cols_for_input_window:
            self._display_ui_message(
                f"Terminal muito estreito! Por favor, aumente a largura do terminal (min {min_cols_for_input_window} colunas) para usar a entrada de diretório. "
                "Pressione qualquer tecla..."
            )
            self.stdscr.nodelay(True)
            return

        prompt_text = "Cole o caminho do diretório (use '/' ou '\\'):"
        caminho_raw = self.ui_components.solicitar_entrada_em_janela(prompt_text, largura=min_cols_for_input_window)

        if caminho_raw:
            caminho_path = pathlib.Path(caminho_raw)
            try:
                caminho = str(caminho_path.resolve())
            except Exception as e:
                self._display_ui_message(f"Erro ao normalizar o caminho: {e}. Pressione qualquer tecla...")
                self.stdscr.nodelay(True)
                return

        self.stdscr.nodelay(True)
        if os.path.isdir(caminho):
            thread_carregar = threading.Thread(target=self._load_directory_and_play_first_threaded, args=(caminho,))
            thread_carregar.daemon = True
            thread_carregar.start()
        else:
            self._display_ui_message(
                "Caminho inválido ou inacessível. Verifique o caminho e as permissões. Pressione qualquer tecla..."
            )

    def _load_directory_and_play_first_threaded(self, caminho):
        self.biblioteca.carregar_diretorio(caminho)
        self.playlist.carregar_diretorio(caminho)
        if self.playlist.playlist_atual:
            self.playlist_selecionada = 0
            self.playlist_offset = 0
            self._tocar_selecionada()

        self._display_ui_message(f"Diretório '{caminho}' carregado! Pressione qualquer tecla...")


    def abrir_navegador_arquivos(self):
        self.stdscr.nodelay(False)
        curses.curs_set(1)

        current_path = os.path.expanduser('~')
        selected_item_index = 0
        scroll_offset = 0

        audio_extensions = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')

        while True:
            self.stdscr.clear()

            min_lines_browser = 10
            min_cols_browser = 40
            if curses.LINES < min_lines_browser or curses.COLS < min_cols_browser:
                self._display_ui_message("Terminal muito pequeno para o navegador de arquivos! Aumente a tela.")
                time.sleep(1)
                break

            try:
                self.stdscr.addstr(0, 2, "Navegador de Arquivos (↑↓ Enter Backspace Q)", curses.color_pair(1) | curses.A_BOLD)

                path_display_len = curses.COLS - 10
                display_path = current_path
                if len(display_path) > path_display_len:
                    display_path = "..." + display_path[-(path_display_len - 3):]
                self.stdscr.addstr(2, 2, f"Caminho: {display_path}")

            except curses.error:
                pass

            try:
                items = []
                if os.path.abspath(current_path) != os.path.abspath(os.path.dirname(current_path)):
                    items.append("..")

                dirs = []
                files = []

                for item in sorted(os.listdir(current_path)):
                    full_path = os.path.join(current_path, item)
                    if os.path.isdir(full_path):
                        dirs.append(f"{item}/")
                    elif os.path.isfile(full_path) and item.lower().endswith(audio_extensions):
                        files.append(item)

                items.extend(dirs)
                items.extend(files)

                if not items and current_path == os.path.expanduser('~'):
                     self.stdscr.addstr(4, 2, "O diretório inicial está vazio ou sem arquivos de áudio compatíveis.")
                elif not items:
                    self.stdscr.addstr(4, 2, "Diretório vazio ou sem arquivos de áudio compatíveis.")


                max_display_rows = curses.LINES - 6

                if selected_item_index < scroll_offset:
                    scroll_offset = selected_item_index
                elif selected_item_index >= scroll_offset + max_display_rows:
                    scroll_offset = selected_item_index - max_display_rows + 1

                for i, item_name in enumerate(items[scroll_offset : scroll_offset + max_display_rows]):
                    display_row = 4 + i
                    display_text = item_name

                    max_len = curses.COLS - 4
                    if len(display_text) > max_len:
                        display_text = display_text[:max_len - 3] + "..."

                    if i + scroll_offset == selected_item_index:
                        self.stdscr.attron(curses.color_pair(2))
                        self.stdscr.addstr(display_row, 2, f"> {display_text}")
                        self.stdscr.attroff(curses.color_pair(2))
                    else:
                        self.stdscr.addstr(display_row, 2, f"  {display_text}")

            except (FileNotFoundError, PermissionError) as e:
                self._display_ui_message(f"Erro de acesso: {e}. Voltando para o diretório inicial. Pressione qualquer tecla...")
                current_path = os.path.expanduser('~')
                selected_item_index = 0
                scroll_offset = 0
                continue
            except NotADirectoryError:
                self._display_ui_message("Erro: Caminho inválido. Voltando para o diretório inicial. Pressione qualquer tecla...")
                current_path = os.path.expanduser('~')
                selected_item_index = 0
                scroll_offset = 0
                continue
            except curses.error:
                self._display_ui_message("Erro de exibição: Terminal muito pequeno. Pressione qualquer tecla...")
                break

            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key == curses.KEY_UP:
                selected_item_index = max(0, selected_item_index - 1)
            elif key == curses.KEY_DOWN:
                selected_item_index = min(len(items) - 1, selected_item_index + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                if not items:
                    self._display_ui_message("Diretório vazio, nada para selecionar. Pressione qualquer tecla...")
                    continue

                chosen_item_name = items[selected_item_index]

                if chosen_item_name == "..":
                    new_path = os.path.dirname(current_path)
                    if os.path.abspath(new_path) != os.path.abspath(current_path):
                        current_path = new_path
                        selected_item_index = 0
                        scroll_offset = 0
                    else:
                        self._display_ui_message("Já no diretório raiz. Pressione qualquer tecla...")
                        continue

                elif chosen_item_name.endswith('/'):
                    new_path = os.path.join(current_path, chosen_item_name[:-1])
                    if os.path.isdir(new_path):
                        current_path = new_path
                        selected_item_index = 0
                        scroll_offset = 0
                    else:
                        self._display_ui_message(f"Não é um diretório válido: {chosen_item_name}. Pressione qualquer tecla...")
                        continue
                else:
                    selected_file_path = os.path.join(current_path, chosen_item_name)

                    threading.Thread(target=self._load_and_play_threaded_from_browser, args=(selected_file_path, current_path)).start()
                    break

            elif key in (ord('q'), ord('Q'), 27):
                break

        curses.curs_set(0)
        self.stdscr.nodelay(True)

    def _load_and_play_threaded_from_browser(self, selected_file_path, current_path):
        self.biblioteca.carregar_diretorio(current_path)
        self.playlist.carregar_diretorio(current_path)
        if self.playlist.playlist_atual:
            self.playlist_selecionada = 0
            self.playlist_offset = 0
            self._tocar_selecionada()

        self._display_ui_message(f"Tocando: {os.path.basename(selected_file_path)}")


    def listar_playlists(self):
        self.stdscr.nodelay(False)
        self.stdscr.clear()
        nomes = list(self.playlist.playlists.keys())
        if not nomes:
            self._display_ui_message("Nenhuma playlist encontrada.")
            self.stdscr.nodelay(True)
            return

        idx = 0
        while True:
            self.stdscr.clear()
            try:
                self.stdscr.addstr(0, 2, "Playlists salvas (Enter para carregar, Q para sair):", curses.color_pair(1) | curses.A_BOLD)

                max_playlists_visiveis = curses.LINES - 5

                start_display_idx = max(0, idx - max_playlists_visiveis // 2)
                end_display_idx = min(len(nomes), start_display_idx + max_playlists_visiveis)
                if end_display_idx - start_display_idx < max_playlists_visiveis:
                    start_display_idx = max(0, end_display_idx - max_playlists_visiveis)

                for i, nome_idx in enumerate(range(start_display_idx, end_display_idx)):
                    nome = nomes[nome_idx]
                    display_text = f"> {nome}" if nome_idx == idx else f"  {nome}"

                    if len(display_text) > curses.COLS - 4:
                        display_text = display_text[:curses.COLS - 7] + "..."

                    if nome_idx == idx:
                        self.stdscr.attron(curses.color_pair(2))
                        self.stdscr.addstr(2 + i, 2, display_text)
                        self.stdscr.attroff(curses.color_pair(2))
                    else:
                        self.stdscr.addstr(2 + i, 2, display_text)
                self.stdscr.refresh()
            except curses.error:
                self._display_ui_message("Terminal muito pequeno para listar playlists!")
                break

            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            elif key == curses.KEY_UP:
                idx = max(0, idx - 1)
            elif key == curses.KEY_DOWN:
                idx = min(len(nomes) - 1, idx + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                threading.Thread(target=self._load_playlist_and_play_threaded, args=(nomes[idx],)).start()
                break
        self.stdscr.nodelay(True)

    def _load_playlist_and_play_threaded(self, playlist_name):
        try:
            self.playlist.playlist_atual = self.playlist.playlists[playlist_name].copy()
            self.playlist_selecionada = 0
            self.playlist_offset = 0
            if self.playlist.playlist_atual:
                self.player.carregar_musica(self.playlist.playlist_atual[0])
                self.player.play()
                self.historico.adicionar(self.playlist.playlist_atual[0])
            self._display_ui_message(f"Playlist '{playlist_name}' carregada! Tocando a primeira música.")
        except Exception as e:
            self._display_ui_message(f"Erro ao carregar playlist '{playlist_name}': {e}")


    def criar_playlist(self):
        nome = self.ui_components.solicitar_entrada("Nome da nova playlist: ", curses.LINES - 3)
        if nome:
            if self.playlist.criar_playlist(nome):
                self._display_ui_message(f"Playlist '{nome}' criada! Pressione qualquer tecla...")
            else:
                self._display_ui_message(f"Playlist '{nome}' já existe! Pressione qualquer tecla...")

    def adicionar_musica_playlist(self):
        if not self.playlist.playlists:
            self._display_ui_message("Nenhuma playlist criada! Pressione qualquer tecla...")
            return
        nome = self.ui_components.solicitar_entrada("Digite o nome da playlist para adicionar: ", curses.LINES - 3)
        if nome not in self.playlist.playlists:
            self._display_ui_message("Playlist não existe! Pressione qualquer tecla...")
            return
        musica_atual = None
        if self.playlist.playlist_atual and 0 <= self.playlist_selecionada < len(self.playlist.playlist_atual):
            musica_atual = self.playlist.playlist_atual[self.playlist_selecionada]
        if musica_atual:
            if self.playlist.adicionar_na_playlist(nome, musica_atual):
                self._display_ui_message(f"Música '{os.path.basename(musica_atual)}' adicionada à playlist '{nome}'. Pressione qualquer tecla...")
            else:
                self._display_ui_message("Música já está na playlist! Pressione qualquer tecla...")
        else:
            self._display_ui_message("Nenhuma música selecionada para adicionar! Pressione qualquer tecla...")

    def remover_musica_playlist(self):
        nome = self.ui_components.solicitar_entrada("Nome da playlist para remover música: ", curses.LINES - 3)
        if nome not in self.playlist.playlists:
            self._display_ui_message("Playlist não existe! Pressione qualquer tecla...")
            return
        try:
            indice_str = self.ui_components.solicitar_entrada("Índice da música para remover (0-based): ", curses.LINES - 3)
            indice = int(indice_str)
        except ValueError:
            indice = -1
        if self.playlist.remover_da_playlist(nome, indice):
            self._display_ui_message("Música removida! Pressione qualquer tecla...")
        else:
            self._display_ui_message("Índice inválido! Pressione qualquer tecla...")

    def favoritar_desfavoritar(self):
        if not self.playlist.playlist_atual:
            return
        musica = self.playlist.playlist_atual[self.playlist_selecionada]
        if self.playlist.is_favorito(musica):
            self.playlist.remover_favorito(musica)
            self._display_ui_message(f"Música desfavoritada! Pressione qualquer tecla...")
        else:
            self.playlist.adicionar_favorito(musica)
            self._display_ui_message(f"Música favoritada! Pressione qualquer tecla...")

    def saltar_para_musica(self):
        try:
            num_str = self.ui_components.solicitar_entrada("Número da música para saltar (1-based): ", curses.LINES - 3)
            num = int(num_str)
        except ValueError:
            num = -1
        if 1 <= num <= len(self.playlist.playlist_atual):
            self.playlist_selecionada = num - 1
            self._tocar_selecionada()
        else:
            self._display_ui_message("Número inválido! Pressione qualquer tecla...")

    def ordenar_playlist(self):
        self.stdscr.nodelay(False)
        self.stdscr.clear()

        opcoes = [
            "1 - Nome do arquivo",
            "2 - Duração",
            "3 - Artista",
            "4 - Álbum",
            "5 - Título",
            "6 - Gênero",
            "7 - Data de adição"
        ]

        max_opcoes_visiveis = curses.LINES - 5

        try:
            self.stdscr.addstr(0, 2, "Ordenar playlist por:", curses.color_pair(1) | curses.A_BOLD)
            for i, opcao in enumerate(opcoes[:max_opcoes_visiveis]):
                self.stdscr.addstr(i + 2, 2, opcao[:curses.COLS - 4])

            prompt_y = min(len(opcoes) + 3, curses.LINES - 2)
            self.stdscr.addstr(prompt_y, 2, "Escolha uma opção: ")
            self.stdscr.refresh()

            key = self.stdscr.getch()
            if key == ord('1'):
                self.playlist.playlist_atual.sort(key=lambda x: os.path.basename(x).lower())
            elif key == ord('2'):
                self._ordenar_por_duracao()
            elif key == ord('3'):
                self._ordenar_por_metadado('artista')
            elif key == ord('4'):
                self._ordenar_por_metadado('album')
            elif key == ord('5'):
                self._ordenar_por_metadado('titulo')
            elif key == ord('6'):
                self._ordenar_por_metadado('genero')
            elif key == ord('7'):
                pass
            else:
                self._display_ui_message("Opção inválida! Pressione qualquer tecla...")
                self.stdscr.nodelay(True)
                return
            self.playlist_selecionada = 0
            self.playlist_offset = 0
            self._display_ui_message("Playlist ordenada! Pressione qualquer tecla...")
            self.playlist.salvar_estado()
        except curses.error:
            self._display_ui_message("Terminal muito pequeno para ordenar!")

        self.stdscr.nodelay(True)

    def _ordenar_por_metadado(self, metadado):
        self.playlist.playlist_atual.sort(
            key=lambda x: Musica(x).metadados.get(metadado, '').lower()
        )
        self.playlist.salvar_estado()

    def _ordenar_por_duracao(self):
        def get_duracao_da_musica(caminho_musica):
            musica_obj = Musica(caminho_musica)
            return musica_obj.metadados.get('duracao', 0)

        self.playlist.playlist_atual.sort(key=get_duracao_da_musica, reverse=True)
        self.playlist.salvar_estado()

    def play_pause(self):
        self.player.play_pause()

    def parar(self):
        self.player.parar()

    def proxima(self):
        if not self.playlist.playlist_atual:
            self._display_ui_message("Playlist vazia para ir para a próxima.")
            return
        self.playlist_selecionada = (self.playlist_selecionada + 1) % len(self.playlist.playlist_atual)
        self._tocar_selecionada()

    def anterior(self):
        if not self.playlist.playlist_atual:
            self._display_ui_message("Playlist vazia para ir para a anterior.")
            return
        self.playlist_selecionada = (self.playlist_selecionada - 1 + len(self.playlist.playlist_atual)) % len(self.playlist.playlist_atual)
        self._tocar_selecionada()
    def _tocar_selecionada(self):
        if self.playlist.playlist_atual:
            musica = self.playlist.playlist_atual[self.playlist_selecionada]
            self.player.carregar_musica(musica)
            self.player.play()
            self.historico.adicionar(musica)

            itens_por_coluna_real = self.ui_components.calcular_itens_por_coluna_playlist()
            if itens_por_coluna_real > 0:
                self.playlist_offset = self.playlist_selecionada // itens_por_coluna_real
            else:
                self.playlist_offset = 0
            self._display_ui_message(f"Tocando: {os.path.basename(musica)}")
        else:
            self._display_ui_message("Nenhuma música na playlist para tocar.")

    def aumentar_volume(self):
        vol_novo = min(1.0, self.player.get_volume() + 0.05)
        self.player.setar_volume(vol_novo)

    def diminuir_volume(self):
        vol_novo = max(0.0, self.player.get_volume() - 0.05)
        self.player.setar_volume(vol_novo)

    def mostrar_historico(self):
        self.stdscr.clear()

        try:
            self.stdscr.addstr(0, 2, "Histórico de Reprodução (Pressione Q para sair)", curses.color_pair(1) | curses.A_BOLD)

            max_linhas_historico = curses.LINES - 3

            historico_reverso = list(reversed(self.historico.pilha))
            for i, musica in enumerate(historico_reverso[:max_linhas_historico]):
                nome = os.path.basename(musica)
                display_text = f"{len(self.historico.pilha) - i}. {nome}"
                if len(display_text) > curses.COLS - 4:
                    display_text = display_text[:curses.COLS - 7] + "..."
                self.stdscr.addstr(i+2, 2, display_text)
            self.stdscr.refresh()
            while True:
                key = self.stdscr.getch()
                if key in (ord('q'), ord('Q')):
                    break
                time.sleep(0.1)
        except curses.error:
            self._display_ui_message("Terminal muito pequeno para histórico!")
            time.sleep(1)

    def abrir_radio(self):
        self.musica_pausada_para_radio = False
        if self.player.get_nome() and self.player.is_playing():
            try:
                self.player.pause()
                time.sleep(0.1)
                self.musica_pausada_para_radio = True
            except Exception as e:
                self.musica_pausada_para_radio = False

        self.radio_ativo = True # Ativa a flag ANTES de curses.endwin()
        curses.endwin()

        radio_dir = os.path.join(os.path.dirname(__file__), '..','..', 'radio_terminal')
        radio_script = os.path.join(radio_dir, 'radio.py')

        try:
            if os.name == 'nt':
                command = f'start "Rádio Terminal" /wait cmd /c python "{radio_script}"'
                subprocess.run(command, cwd=radio_dir, shell=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                terminal_emulator_found = False
                for term_cmd in ['x-terminal-emulator', 'gnome-terminal', 'konsole', 'xterm']:
                    try:
                        subprocess.run([term_cmd, '-e', f'python3 {radio_script}'],
                                         cwd=radio_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        terminal_emulator_found = True
                        break
                    except FileNotFoundError:
                        continue
                if not terminal_emulator_found:
                    # Se nenhum emulador de terminal for encontrado, ainda precisamos restaurar o curses.
                    self.stdscr = curses.initscr()
                    curses.noecho()
                    curses.cbreak()
                    self.stdscr.keypad(True)
                    curses.curs_set(0)
                    init_cores()
                    self.stdscr.clear()
                    self.stdscr.refresh()
                    self._display_ui_message("Nenhum emulador de terminal compatível encontrado.")
                    time.sleep(2)
        except Exception as e:
            # Em caso de erro ao iniciar o rádio, restaurar o curses também.
            self.stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            self.stdscr.keypad(True)
            curses.curs_set(0)
            init_cores()
            self.stdscr.clear()
            self.stdscr.refresh()
            self._display_ui_message(f"Erro ao iniciar rádio: {e}")
            time.sleep(2)

        # Re-inicializa o curses após o término do player externo (ou erro)
        # É importante que isso aconteça APÓS o subprocess.run() que bloqueia.
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)
        init_cores()
        self.stdscr.clear()
        self.stdscr.refresh()

        self.radio_ativo = False # Desativa a flag APÓS o subprocesso terminar

        if self.musica_pausada_para_radio:
            try:
                self.player.resume()
                time.sleep(0.1)
            except Exception as e:
                pass
            self.musica_pausada_para_radio = False

        self.stdscr.nodelay(True)

    def abrir_youtube(self):
        self.musica_pausada_para_youtube = False
        if self.player.get_nome() and self.player.is_playing():
            try:
                self.player.pause()
                time.sleep(0.1)
                self.musica_pausada_para_youtube = True
            except Exception as e:
                self.musica_pausada_para_youtube = False
                self._display_ui_message(f"Erro ao pausar música: {e}. Continuará.")

        # Altera para modo de entrada de texto e mostra cursor
        self.stdscr.nodelay(False)
        curses.curs_set(1)

        prompt_text = "Cole a URL do YouTube (vídeo ou playlist):"
        url = self.ui_components.solicitar_entrada_em_janela(prompt_text, largura=curses.COLS - 10)

        # Verifica se a URL foi fornecida ANTES de desativar o curses
        if not url:
            # Se não houver URL, reativamos o curses e retornamos à UI principal
            curses.curs_set(0) # Esconde o cursor
            self.stdscr.nodelay(True) # Reativa o nodelay
            self._display_ui_message("Nenhuma URL fornecida. Pressione qualquer tecla...")
            if self.musica_pausada_para_youtube:
                try:
                    self.player.resume()
                except Exception:
                    pass
                self.musica_pausada_para_youtube = False
            self.youtube_ativo = False # Garante que a flag está desligada
            self.youtube_carregando = False # Garante que a flag está desligada
            return
        
        # --- FLUXO PRINCIPAL: DESATIVAR CURSES E INICIAR MPV ---
        # 1. Ativa as flags DEPOIS de obter a URL, mas ANTES de curses.endwin()
        self.youtube_ativo = True
        self.youtube_carregando = True 

        # 2. Esconde a interface Curses AGORA.
        curses.endwin()

        # 3. Exibe mensagem de loading no console de execução.
        print(f"\n--- INICIANDO YOUTUBE ---")
        print(f"URL: {url[:80]}...") 
        print(f"Carregando MPV, por favor, aguarde a janela abrir...")
        
        # 4. Lança a reprodução do YouTube em uma thread separada.
        #    Esta thread BLOQUEIA ATÉ MPV ENCERRAR.
        threading.Thread(target=self._play_youtube_threaded, args=(url,)).start()

    def _play_youtube_threaded(self, url):
        # curses.endwin() já foi chamado em abrir_youtube, não é necessário aqui.
        
        # Chama o método de reprodução do módulo de integração.
        success = self.youtube_integration.play_url(url) # Não passa audio_only=True

        # A execução do código aqui continua SOMENTE DEPOIS que mpv encerra.
        # Isso garante que a UI do Curses só seja restaurada depois.

        # Re-inicializa o curses após o término do player externo (ou erro)
        # É importante que isso aconteça APÓS o mpv_process_handle.wait() que bloqueia.
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)
        init_cores()
        self.stdscr.clear()
        self.stdscr.refresh()

        # mpv_process terminou, então youtube_ativo e youtube_carregando devem ser False
        self.youtube_ativo = False
        self.youtube_carregando = False

        if success:
            self._display_ui_message(f"Reprodução do YouTube finalizada. Pressione qualquer tecla...")
        else:
            self._display_ui_message("Falha na reprodução do YouTube. Verifique o console para avisos/erros. Pressione qualquer tecla...")

        # Retoma a música pausada, se houver
        if self.musica_pausada_para_youtube:
            try:
                self.player.resume()
                time.sleep(0.1)
                self._display_ui_message("Música local retomada.")
            except Exception as e:
                self._display_ui_message(f"Erro ao retomar música: {e}.")
            self.musica_pausada_para_youtube = False

        self.stdscr.nodelay(True)

    def draw_interface(self):
        # NÃO DESENHA A INTERFACE SE O RÁDIO OU YOUTUBE ESTIVER ATIVO
        if self.radio_ativo or self.youtube_ativo:
            return

        self.stdscr.clear()

        min_linhas = 20
        min_colunas = 60

        if curses.LINES < min_linhas or curses.COLS < min_colunas:
            self.stdscr.clear()
            msg = "Terminal muito pequeno! Redimensione para pelo menos {} linhas e {} colunas.".format(min_linhas, min_colunas)
            try:
                self.stdscr.addstr(curses.LINES // 2, (curses.COLS - len(msg)) // 2, msg)
            except curses.error:
                pass
            self.stdscr.refresh()
            return

        self.ui_components.desenhar_borda()
        self.ui_components.desenhar_titulo()

        espectro_y = 7
        espectro_x = 2
        espectro_largura = curses.COLS - (espectro_x * 2)
        espectro_altura = 4

        menu_y = curses.LINES - 3
        status_y = menu_y - 3
        volume_y = status_y - 1
        recursos_y = volume_y - 1

        playlist_y = espectro_y + espectro_altura + 1
        altura_playlist_desejada = 9

        espaco_disponivel_para_playlist = recursos_y - (playlist_y + 1)
        if espaco_disponivel_para_playlist < 0:
            espaco_disponivel_para_playlist = 0

        altura_playlist = min(altura_playlist_desejada, espaco_disponivel_para_playlist)
        if altura_playlist < 3:
            altura_playlist = 3


        largura_playlist = curses.COLS - 4

        tocando = self.player.get_nome() and self.player.is_playing()

        num_barras_player = espectro_largura // 2
        if not hasattr(self, 'espectro_atual') or len(self.espectro_atual) != num_barras_player:
            self.espectro_atual = [0.0] * num_barras_player

        if tocando: # Não precisamos mais verificar radio_ativo ou youtube_ativo aqui, pois o draw_interface já é condicional
            try:
                espectro_raw = self.player.espectro(num_barras=num_barras_player)
                for i in range(min(len(espectro_raw), len(self.espectro_atual))):
                    atual = self.espectro_atual[i]
                    novo = espectro_raw[i] if i < len(espectro_raw) else 0
                    if novo > atual:
                        alpha = 0.8
                    else:
                        alpha = 0.5
                    self.espectro_atual[i] = alpha * novo + (1 - alpha) * atual
            except Exception:
                self.espectro_atual = [max(0, v * 0.75) for v in self.espectro_atual]
        else:
            self.espectro_atual = [max(0, v * 0.75) for v in self.espectro_atual]

        self.ui_components.desenhar_espectro(
            self.espectro_atual,
            y=espectro_y,
            x=espectro_x,
            largura=espectro_largura,
            altura=espectro_altura
        )
        self.ui_components.desenhar_playlist(
            self.playlist.playlist_atual,
            self.playlist_selecionada,
            self.playlist_offset,
            self.playlist.favoritos,
            y=playlist_y, x=2, altura=altura_playlist, largura=largura_playlist
        )

        cpu_usage, ram_usage = uso_recursos()
        self.ui_components.desenhar_recursos(cpu_usage, ram_usage, y=recursos_y, x=2)
        self.ui_components.desenhar_volume(self.volume, y=volume_y, x=2)

        # O status agora só será exibido se não estivermos em modo rádio/youtube
        self.ui_components.desenhar_status(
            self.player.get_nome(),
            self.player.get_progresso(),
            self.player.get_duracao(),
            y=status_y, x=2
        )

        try:
            message = self.ui_message_queue.get_nowait()
            self.ui_components.mostrar_mensagem(message, curses.LINES - 3)
        except queue.Empty:
            pass

        self.ui_components.desenhar_menu_inferior(menu_y, 2)
        self.stdscr.refresh()

    def loop(self):
        while self.executando:
            self.player.check_events()

            # A reprodução automática da próxima música só deve ocorrer se não estivermos no modo rádio/youtube
            if (not self.radio_ativo and
                not self.youtube_ativo and 
                not self.player.is_playing() and
                self.player.get_duracao() > 0 and
                (self.player.get_progresso() >= self.player.get_duracao() - 0.1) and
                not self.player.pausado and
                not self.musica_pausada_para_radio and
                not self.musica_pausada_para_youtube):
                self.proxima()


            current_lines = curses.LINES
            current_cols = curses.COLS

            # Ação de redimensionamento do terminal só deve acontecer se a UI Curses estiver ativa
            if not self.radio_ativo and not self.youtube_ativo:
                if current_lines != self.curses_lines or current_cols != self.curses_cols:
                    self.curses_lines = current_lines
                    self.curses_cols = current_cols
                    curses.resizeterm(current_lines, current_cols)
                    self.draw_interface() # Redesenha após redimensionamento

                self.draw_interface() # Desenha a interface no loop normal
            else:
                # Se rádio ou YouTube estiverem ativos, não redesenhe a UI Curses.
                # Apenas aguarde um pouco para não consumir CPU desnecessariamente.
                time.sleep(0.1)


            self.config_manager.set('volume', self.volume)
            self.config_manager.set('equalizacao', self.equalizacao)
            self.config_manager.set('modo_visualizacao', self.modo_visualizacao)
            self.playlist.salvar_estado()

            try:
                # Obter entrada APENAS se a UI Curses estiver ativa, ou se estivermos em modo "console livre"
                # para capturar um 'q' para sair ou teclas para interagir com o rádio/youtube
                if not self.radio_ativo and not self.youtube_ativo:
                    key = self.stdscr.getch()
                else:
                    # Quando o curses está desativado (endwin), getch() não funciona como esperado.
                    # As interações com o rádio/youtube acontecem no próprio subprocesso.
                    # Aqui, podemos adicionar um pequeno delay e, se necessário,
                    # uma forma de verificar a saída do subprocesso ou um sinal.
                    # Para este caso, o `subprocess.run` (ou `Popen.wait()`) já está bloqueando a thread
                    # então não haverá teclas Curses para pegar até que ele retorne.
                    key = -1 # Nenhuma tecla Curses lida se o curses está desativado
            except KeyboardInterrupt:
                break

            if key == -1:
                # Apenas continue o loop se nenhuma tecla foi pressionada
                # e se não estivermos em modo rádio/youtube (já tratado pelo time.sleep acima)
                continue

            # Não processe teclas se youtube_ativo ou radio_ativo estiverem True,
            # pois o terminal está sendo usado pelo subprocesso externo.
            if self.youtube_ativo or self.radio_ativo:
                continue

            itens_por_coluna = self.ui_components.calcular_itens_por_coluna_playlist()
            if itens_por_coluna == 0:
                itens_por_coluna = 1

            total_musicas = len(self.playlist.playlist_atual)
            if total_musicas > 0:
                max_col = (total_musicas - 1) // itens_por_coluna
            else:
                max_col = 0

            if key == curses.KEY_LEFT:
                if total_musicas == 0:
                    continue

                if self.playlist_offset > 0:
                    self.playlist_offset -= 1
                else:
                    self.playlist_offset = max_col

                self.playlist_selecionada = self.playlist_offset * itens_por_coluna
                self.playlist_selecionada = min(self.playlist_selecionada, total_musicas - 1)

            elif key == curses.KEY_RIGHT:
                if total_musicas == 0:
                    continue

                if self.playlist_offset < max_col:
                    self.playlist_offset += 1
                else:
                    self.playlist_offset = 0

                self.playlist_selecionada = self.playlist_offset * itens_por_coluna
                self.playlist_selecionada = min(self.playlist_selecionada, total_musicas - 1)

            elif key == curses.KEY_UP:
                if total_musicas == 0:
                    continue

                if self.playlist_selecionada % itens_por_coluna == 0:
                    if self.playlist_offset > 0:
                        self.playlist_offset -= 1
                        self.playlist_selecionada = (self.playlist_offset * itens_por_coluna) + itens_por_coluna - 1
                        self.playlist_selecionada = min(self.playlist_selecionada, total_musicas - 1)
                    else:
                        self.playlist_offset = max_col
                        self.playlist_selecionada = total_musicas - 1
                else:
                    self.playlist_selecionada = max(0, self.playlist_selecionada - 1)


            elif key == curses.KEY_DOWN:
                if total_musicas == 0:
                    continue

                if (self.playlist_selecionada % itens_por_coluna == itens_por_coluna - 1) or \
                   (self.playlist_selecionada == total_musicas - 1):
                    if self.playlist_offset < max_col:
                        self.playlist_offset += 1
                        self.playlist_selecionada = self.playlist_offset * itens_por_coluna
                    else:
                        self.playlist_offset = 0
                        self.playlist_selecionada = 0
                else:
                    self.playlist_selecionada = min(total_musicas - 1, self.playlist_selecionada + 1)


            elif key in (ord('q'), ord('Q')):
                self.executando = False
            elif key in (ord('r'), ord('R')):
                self.abrir_radio()
            elif key in (ord('y'), ord('Y')):
                self.abrir_youtube()
            elif key in (ord('h'), ord('H')):
                self.mostrar_historico()
            elif key in (ord('l'), ord('L')):
                self.listar_playlists()
            elif key in (ord('c'), ord('C')):
                self.criar_playlist()
            elif key in (ord('a'), ord('A')):
                self.adicionar_musica_playlist()
            elif key in (ord('d'), ord('D')):
                self.remover_musica_playlist()
            elif key in (ord('f'), ord('F')):
                self.favoritar_desfavoritar()
            elif key in (ord('s'), ord('S')):
                self.saltar_para_musica()
            elif key in (ord('o'), ord('O')):
                self.ordenar_playlist()
            elif key in (ord('1'), ):
                self.abrir_diretorio()
            elif key == ord('2'):
                self.play_pause()
            elif key in (curses.KEY_ENTER, 10, 13):
                if self.playlist.playlist_atual:
                    musica_selecionada_caminho = self.playlist.playlist_atual[self.playlist_selecionada]
                    musica_tocando_caminho = self.player.musica_atual

                    is_currently_loaded_and_selected = False
                    if musica_tocando_caminho:
                        try:
                            is_currently_loaded_and_selected = os.path.samefile(musica_selecionada_caminho, musica_tocando_caminho)
                        except FileNotFoundError:
                            is_currently_loaded_and_selected = False
                        except Exception:
                            is_currently_loaded_and_selected = False

                    if is_currently_loaded_and_selected:
                        self.play_pause()
                    else:
                        self._tocar_selecionada()
                else:
                    self.play_pause()

            elif key in (ord('3'), ):
                self.anterior()
            elif key in (ord('4'), ):
                self.proxima()
            elif key in (ord('='), ord('+'), ):
                self.aumentar_volume()
            elif key in (ord('-'), ):
                self.diminuir_volume()
            elif key in (ord('b'), ord('B')):
                self.buscar_musicas()
            elif key in (ord('t'), ord('T')):
                self.filtrar_por_categoria()
            elif key in (ord('e'), ord('E')):
                self.controlar_equalizacao()
            elif key in (ord('x'), ord('X')):
                self.mostrar_estatisticas()
            elif key == ord('i') or key == ord('I'):
                self.abrir_navegador_arquivos()

            # Pequeno delay no loop para evitar consumo excessivo de CPU.
            # Este sleep é mais importante quando a UI Curses está desativada.
            time.sleep(0.02)

    def __del__(self):
        if hasattr(self, 'player') and self.player is not None:
            self.player.quit()
        if hasattr(self, 'youtube_integration'):
            self.youtube_integration.stop_player()


def main(stdscr):
    player_ui = UIPlayer(stdscr)
    player_ui.loop()

if __name__ == '__main__':
    curses.wrapper(main)