import curses
import time
import os
import subprocess

# Importações de módulos de UI modularizados
from ui_utils import init_cores, uso_recursos, limpar_terminal
from ui_components import UIComponents
from ui_state import UIState

# Importações de módulos de negócio (mantidos na estrutura atual)
from audio import AudioPlayer
from playlist import PlaylistManager
from historico import Historico
from biblioteca import Biblioteca
from config_manager import ConfigManager
from radio_terminal.radio import RadioPlayer
from biblioteca import Musica # Necessário para o método de ordenação


class UIPlayer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.player = AudioPlayer()
        self.playlist = PlaylistManager()
        self.historico = Historico()
        self.biblioteca = Biblioteca()
        self.config_manager = ConfigManager()
        self.radio_player = RadioPlayer()

        # Instâncias dos módulos de UI modularizados
        self.ui_components = UIComponents(stdscr)
        # Definir a pasta de dados base para o UIState
        PASTA_DADOS = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.ui_state = UIState(PASTA_DADOS)

        # Estado da UI
        self.volume = self.player.get_volume()
        self.playlist_selecionada = 0
        self.playlist_offset = 0
        self.executando = True
        self.espectro_atual = [0] * 20 # Espectro para animação
        self.radio_ativo = False
        self.equalizacao = {'grave': 0, 'medio': 0, 'agudo': 0}
        self.modo_visualizacao = 'lista'
        self.filtro_atual = None
        self.termo_busca_atual = ""
        self.musica_pausada_para_radio = False

        # Carregar estados persistentes
        self.carregar_favoritos()
        self.carregar_historico()

        init_cores()
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        curses.curs_set(0)
        
        self.playlist.carregar_estado()
        if self.playlist.playlists:
            primeira = next(iter(self.playlist.playlists))
            self.playlist.playlist_atual = self.playlist.playlists[primeira].copy()
            self.playlist_selecionada = 0
            if self.playlist.playlist_atual:
                self.player.carregar_musica(self.playlist.playlist_atual[0])
                self.historico.adicionar(self.playlist.playlist_atual[0])
        
        self.player.add_observer(self)

    def atualizar(self, evento):
        """Método observer para atualizar a UI quando o player muda."""
        if evento == 'carregar_musica':
            pass
        elif evento == 'play_pause':
            pass
        elif evento == 'volume':
            self.volume = self.player.get_volume()
        elif evento == 'equalizacao':
            pass
        elif evento == 'musica_terminada': # Novo evento para música terminada
            if not self.radio_ativo: # Apenas avança se não estiver no modo rádio
                self.proxima()
    

    
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
                self.ui_components.mostrar_mensagem(f"Encontradas {len(resultados)} músicas. Pressione qualquer tecla...", curses.LINES - 3)
            else:
                self.ui_components.mostrar_mensagem("Nenhuma música encontrada! Pressione qualquer tecla...", curses.LINES - 3)
        self.stdscr.nodelay(True)

    def filtrar_por_categoria(self):
        self.stdscr.nodelay(False)
        self.stdscr.clear()
        self.stdscr.addstr(0, 2, "Filtrar por:", curses.color_pair(1) | curses.A_BOLD)
        opcoes = ["1 - Artista", "2 - Álbum", "3 - Gênero", "4 - Limpar filtro"]
        for i, opcao in enumerate(opcoes):
            self.stdscr.addstr(i + 2, 2, opcao)
        self.stdscr.addstr(len(opcoes) + 3, 2, "Escolha uma opção: ")
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
        self.stdscr.nodelay(True)

    def _filtrar_por(self, categoria):
        grupos = self.biblioteca.listar_por(categoria)
        opcoes = list(grupos.keys())
        if not opcoes:
            self.ui_components.mostrar_mensagem("Nenhuma categoria encontrada! Pressione qualquer tecla...", curses.LINES - 3)
            return
        idx = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 2, f"Filtrar por {categoria} (↑↓ para navegar, Enter para selecionar, Q para sair):", curses.color_pair(1) | curses.A_BOLD)
            for i, opcao in enumerate(opcoes):
                texto = f"> {opcao}" if i == idx else f"  {opcao}"
                maxlen = curses.COLS - 4
                if len(texto) > maxlen:
                    texto = texto[:maxlen-3] + "..."
                try:
                    if i == idx:
                        self.stdscr.attron(curses.color_pair(2))
                        self.stdscr.addstr(i + 2, 2, texto)
                        self.stdscr.attroff(curses.color_pair(2))
                    else:
                        self.stdscr.addstr(i + 2, 2, texto)
                except curses.error:
                    pass
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            elif key == curses.KEY_UP and idx > 0:
                idx -= 1
            elif key == curses.KEY_DOWN and idx < len(opcoes) - 1:
                idx += 1
            elif key in (curses.KEY_ENTER, 10, 13):
                self.filtro_atual = (categoria, opcoes[idx])
                self.playlist.playlist_atual = [m.caminho for m in grupos[opcoes[idx]]]
                self.playlist_selecionada = 0
                self.playlist_offset = 0
                break
    
    # Este método é um placeholder. A lógica de pré-processamento de áudio com EQ
    # deve idealmente estar em AudioPlayer ou em um módulo de processamento de áudio.
    # Mantido aqui para compatibilidade com a estrutura original por enquanto.
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
                left_eq = self._apply_equalizer(left, audio.frame_rate)
                right_eq = self._apply_equalizer(right, audio.frame_rate)
                arr_eq = np.empty(len(arr), dtype=np.float32)
                arr_eq[0::2] = left_eq
                arr_eq[1::2] = right_eq
            else:
                arr_eq = self._apply_equalizer(arr, audio.frame_rate)
            
            arr_eq = np.clip(arr_eq, -32768, 32767).astype(np.int16)
            audio_eq = audio._spawn(arr_eq.tobytes())
            
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio_eq.export(temp_file.name, format='wav')
            
            return temp_file.name
        except Exception as e:
            # print(f"Erro no pré-processamento: {e}")
            return caminho_original

    # _apply_equalizer não estava no código original ui.py,
    # presumo que seja um método auxiliar de _pre_processar_audio_com_eq,
    # mas sem a sua implementação, não posso incluí-lo aqui.
    # Se você tiver a implementação, por favor, forneça-a.
    # Por enquanto, _pre_processar_audio_com_eq pode gerar um erro se chamado.

    def controlar_equalizacao(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 2, "Equalização (↑↓ para navegar, ←→ para ajustar, Q para sair)", curses.color_pair(1) | curses.A_BOLD)
        controles = ['grave', 'medio', 'agudo']
        idx = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 2, "Equalização (↑↓ para navegar, ←→ para ajustar, Q para sair)", curses.color_pair(1) | curses.A_BOLD)
            for i, controle in enumerate(controles):
                valor = self.equalizacao[controle]
                barra = self.ui_components.criar_barra_eq(valor) # Usa o método do componente
                if i == idx:
                    self.stdscr.attron(curses.color_pair(2))
                    self.stdscr.addstr(i + 3, 2, f"> {controle.upper()}: {barra} ({valor:+.1f})")
                    self.stdscr.attroff(curses.color_pair(2))
                else:
                    self.stdscr.addstr(i + 3, 2, f"  {controle.upper()}: {barra} ({valor:+.1f})")
            self.stdscr.refresh()
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
        self.stdscr.addstr(0, 2, "Estatísticas de Reprodução", curses.color_pair(1) | curses.A_BOLD)
        stats = self.historico.estatisticas(10)
        self.stdscr.addstr(2, 2, "Músicas mais tocadas:", curses.color_pair(3) | curses.A_BOLD)
        for i, (musica, count) in enumerate(stats):
            nome = os.path.basename(musica)
            self.stdscr.addstr(3 + i, 4, f"{i+1}. {nome} ({count}x)")
        y_pos = 3 + len(stats) + 2
        self.stdscr.addstr(y_pos, 2, "Estatísticas Gerais:", curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y_pos + 1, 4, f"Total de reproduções: {len(self.historico.pilha)}")
        self.stdscr.addstr(y_pos + 2, 4, f"Músicas únicas: {len(set(self.historico.pilha))}")
        self.stdscr.addstr(y_pos + 3, 4, f"Favoritos: {len(self.favoritos)}")
        self.stdscr.addstr(y_pos + 4, 4, f"Playlists: {len(self.playlist.playlists)}")
        if self.biblioteca.musicas:
            y_pos += 6
            self.stdscr.addstr(y_pos, 2, "Biblioteca:", curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(y_pos + 1, 4, f"Total de músicas: {len(self.biblioteca.musicas)}")
            generos = self.biblioteca.listar_por('genero')
            self.stdscr.addstr(y_pos + 2, 4, f"Gêneros diferentes: {len(generos)}")
            artistas = self.biblioteca.listar_por('artista')
            self.stdscr.addstr(y_pos + 3, 4, f"Artistas diferentes: {len(artistas)}")
        self.ui_components.mostrar_mensagem("Pressione qualquer tecla para voltar...", curses.LINES - 2)
        self.stdscr.nodelay(True)

    def solicitar_entrada(self, prompt, y):
        return self.ui_components.solicitar_entrada(prompt, y)

    def salvar_historico(self):
        self.ui_state.salvar_historico(self.historico.pilha)

    def carregar_historico(self):
        self.historico.pilha = self.ui_state.carregar_historico()

    def salvar_favoritos(self):
        self.ui_state.salvar_favoritos(self.favoritos)

    def carregar_favoritos(self):
        self.favoritos = self.ui_state.carregar_favoritos()

    def abrir_diretorio(self):
        caminho = self.ui_components.solicitar_entrada("Cole o caminho do diretório: ", curses.LINES - 3)
        if os.path.isdir(caminho):
            self.biblioteca.carregar_diretorio(caminho)
            self.playlist.carregar_diretorio(caminho)
            if self.playlist.playlist_atual:
                self.playlist_selecionada = 0
                self.playlist_offset = 0
                self.player.carregar_musica(self.playlist.playlist_atual[0])
                self.player.play() # MUDANÇA AQUI: Chamar play()
                self.historico.adicionar(self.playlist.playlist_atual[0])
        else:
            self.ui_components.mostrar_mensagem("Diretório inválido! Pressione qualquer tecla...", curses.LINES - 3)

    def listar_playlists(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 2, "Playlists salvas (Enter para carregar, Q para sair):", curses.color_pair(1) | curses.A_BOLD)
        nomes = list(self.playlist.playlists.keys())
        if not nomes:
            self.ui_components.mostrar_mensagem("Nenhuma playlist encontrada.", 2)
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
                    self.player.play() # MUDANÇA AQUI: Chamar play()
                break

    def criar_playlist(self):
        nome = self.ui_components.solicitar_entrada("Nome da nova playlist: ", curses.LINES - 3)
        if nome:
            if self.playlist.criar_playlist(nome):
                self.ui_components.mostrar_mensagem(f"Playlist '{nome}' criada! Pressione qualquer tecla...", curses.LINES - 3)
            else:
                self.ui_components.mostrar_mensagem(f"Playlist '{nome}' já existe! Pressione qualquer tecla...", curses.LINES - 3)

    def adicionar_musica_playlist(self):
        if not self.playlist.playlists:
            self.ui_components.mostrar_mensagem("Nenhuma playlist criada! Pressione qualquer tecla...", curses.LINES - 3)
            return
        nome = self.ui_components.solicitar_entrada("Digite o nome da playlist para adicionar: ", curses.LINES - 3)
        if nome not in self.playlist.playlists:
            self.ui_components.mostrar_mensagem("Playlist não existe! Pressione qualquer tecla...", curses.LINES - 3)
            return
        musica_atual = None
        if self.playlist.playlist_atual and 0 <= self.playlist_selecionada < len(self.playlist.playlist_atual):
            musica_atual = self.playlist.playlist_atual[self.playlist_selecionada]
        if musica_atual:
            if self.playlist.adicionar_na_playlist(nome, musica_atual):
                self.ui_components.mostrar_mensagem(f"Música '{os.path.basename(musica_atual)}' adicionada à playlist '{nome}'. Pressione qualquer tecla...", curses.LINES - 3)
            else:
                self.ui_components.mostrar_mensagem("Música já está na playlist! Pressione qualquer tecla...", curses.LINES - 3)
        else:
            self.ui_components.mostrar_mensagem("Nenhuma música selecionada para adicionar! Pressione qualquer tecla...", curses.LINES - 3)

    def remover_musica_playlist(self):
        nome = self.ui_components.solicitar_entrada("Nome da playlist para remover música: ", curses.LINES - 3)
        if nome not in self.playlist.playlists:
            self.ui_components.mostrar_mensagem("Playlist não existe! Pressione qualquer tecla...", curses.LINES - 3)
            return
        try:
            indice_str = self.ui_components.solicitar_entrada("Índice da música para remover (0-based): ", curses.LINES - 3)
            indice = int(indice_str)
        except ValueError:
            indice = -1
        if self.playlist.remover_da_playlist(nome, indice):
            self.ui_components.mostrar_mensagem("Música removida! Pressione qualquer tecla...", curses.LINES - 3)
        else:
            self.ui_components.mostrar_mensagem("Índice inválido! Pressione qualquer tecla...", curses.LINES - 3)

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
            num_str = self.ui_components.solicitar_entrada("Número da música para saltar (1-based): ", curses.LINES - 3)
            num = int(num_str)
        except ValueError:
            num = -1
        if 1 <= num <= len(self.playlist.playlist_atual):
            self.playlist_selecionada = num - 1
            self._tocar_selecionada()
        else:
            self.ui_components.mostrar_mensagem("Número inválido! Pressione qualquer tecla...", curses.LINES - 3)

    def ordenar_playlist(self):
        self.stdscr.nodelay(False)
        self.stdscr.clear()
        self.stdscr.addstr(0, 2, "Ordenar playlist por:", curses.color_pair(1) | curses.A_BOLD)
        opcoes = [
            "1 - Nome do arquivo",
            "2 - Duração",
            "3 - Artista",
            "4 - Álbum",
            "5 - Título",
            "6 - Gênero",
            "7 - Data de adição"
        ]
        for i, opcao in enumerate(opcoes):
            self.stdscr.addstr(i + 2, 2, opcao)
        self.stdscr.addstr(len(opcoes) + 3, 2, "Escolha uma opção: ")
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
            # Ordenar por ordem de adição (reverso do histórico) - Isso precisa ser implementado na classe Historico ou aqui.
            # Por simplicidade, deixamos como está por enquanto, mas é um ponto de melhoria.
            pass
        else:
            self.ui_components.mostrar_mensagem("Opção inválida! Pressione qualquer tecla...", curses.LINES - 3)
            self.stdscr.nodelay(True)
            return
        self.playlist_selecionada = 0
        self.playlist_offset = 0
        self.ui_components.mostrar_mensagem("Playlist ordenada! Pressione qualquer tecla...", curses.LINES - 3)
        self.stdscr.nodelay(True)

    def _ordenar_por_metadado(self, metadado):
        self.playlist.playlist_atual.sort(
            key=lambda x: Musica(x).metadados.get(metadado, '').lower()
        )

    def _ordenar_por_duracao(self):
        # Primeiro, certifique-se de que todas as músicas na playlist atual
        # tenham seus metadados (incluindo duração) carregados.
        # Isso pode ser feito garantindo que a Biblioteca já processou essas músicas.
        # Uma abordagem mais robusta seria ter um cache de metadados na Biblioteca.

        # Para cada caminho de música na playlist atual, tente obter a duração.
        # Se a duração não estiver disponível, considere 0 para não quebrar a ordenação.
        def get_duracao_da_musica(caminho_musica):
            # Assumindo que Musica(caminho_musica) carrega os metadados
            # e 'duracao' é um metadado numérico (segundos, milissegundos, etc.)
            musica_obj = Musica(caminho_musica)
            return musica_obj.metadados.get('duracao', 0) # Retorna 0 se duração não for encontrada

        self.playlist.playlist_atual.sort(key=get_duracao_da_musica, reverse=True) # Adicionado reverse=True para ter as maiores durações primeiro

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
            self.player.play() # MUDANÇA AQUI: Chamar play() em vez de play_pause()
            self.historico.adicionar(musica)
        
        # Lógica de ajuste de offset da playlist para rolagem
        itens_por_coluna = 8 # Deve ser consistente com o desenhar_playlist em UIComponents
        altura_visivel = curses.LINES - 10 # Isso será recalculado no draw_interface
        if self.playlist_selecionada < self.playlist_offset * itens_por_coluna:
            self.playlist_offset = self.playlist_selecionada // itens_por_coluna
        elif self.playlist_selecionada >= (self.playlist_offset + 1) * itens_por_coluna:
            self.playlist_offset = self.playlist_selecionada // itens_por_coluna

    def aumentar_volume(self):
        vol_novo = min(1.0, self.player.get_volume() + 0.05)
        self.player.setar_volume(vol_novo)

    def diminuir_volume(self):
        vol_novo = max(0.0, self.player.get_volume() - 0.05)
        self.player.setar_volume(vol_novo)

    def mostrar_historico(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 2, "Histórico de Reprodução (Pressione Q para sair)", curses.color_pair(1) | curses.A_BOLD)
        # Exibe apenas as últimas N músicas que cabem na tela
        for i, musica in enumerate(reversed(self.historico.pilha[-(curses.LINES-3):])):
            nome = os.path.basename(musica)
            self.stdscr.addstr(i+2, 2, f"{len(self.historico.pilha) - i}. {nome}")
        self.stdscr.refresh()
        while True:
            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            time.sleep(0.1)

    def abrir_radio(self):
        """
        Starts the radio player in a separate terminal process.
        Properly manages curses terminal state before and after launching the radio.
        Temporarily stops the audio player if it's active.
        """
        # Store current music state if needed to resume later
        musica_carregada = self.player.get_nome()
        tocando = False
        if musica_carregada:
            tocando = self.player.is_playing()

        if musica_carregada and tocando:
            try:
                # Altera de parar() para pause() para manter o progresso da música
                self.player.pause()  # MODIFICAÇÃO CHAVE AQUI
                self.musica_pausada_para_radio = True
            except Exception:
                self.musica_pausada_para_radio = False
        else:
            self.musica_pausada_para_radio = False

        # END Curses mode before launching external process
        curses.endwin()

        # Corrigir o caminho para radio_terminal
        radio_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'radio_terminal') # Subir dois níveis
        radio_script = os.path.join(radio_dir, 'radio.py')

        # Use subprocess.run for simpler handling, and specify shell=True for 'start' on Windows
        # Use a more robust way to open a new terminal
        if os.name == 'nt':  # Windows
            command = ['cmd.exe', '/c', 'start', '/wait', 'cmd', '/c', 'python', radio_script]
        else:  # Linux/macOS
            # Para Linux, você pode precisar de um emulador de terminal como 'xterm', 'gnome-terminal', 'konsole'
            # Esta é uma maneira comum, mas os usuários podem precisar de uma configuração de terminal específica
            command = ['xterm', '-e', 'python3', radio_script] 
            # Ou: ['gnome-terminal', '--', 'python3', radio_script]
            # Ou: ['konsole', '-e', 'python3', radio_script]
            # Fallback para execução simples de python se nenhum emulador de terminal específico for desejado/configurado
            # Isso pode rodar na mesma janela, mas respeita curses.endwin()
            # command = ['python3', radio_script] 

        try:
            # Executa o script de rádio em um novo terminal, aguardando a conclusão
            subprocess.run(command, cwd=radio_dir)
        except FileNotFoundError as e:
            # Lida com casos em que 'xterm' ou 'gnome-terminal' etc. podem não ser encontrados
            self.ui_components.mostrar_mensagem(
                f"Erro: Emulador de terminal não encontrado ou script radio.py. Verifique sua instalação. {e}", 
                curses.LINES - 3
            )
            # Você pode querer fornecer um fallback ou apenas sair graciosamente aqui
            time.sleep(2) # Dá tempo para o usuário ler o erro
            # Re-initialize curses regardless
        except Exception as e:
            self.ui_components.mostrar_mensagem(f"Erro inesperado ao iniciar rádio: {e}", curses.LINES - 3)
            time.sleep(2) # Dá tempo para o usuário ler o erro


        # RE-INITIALIZE Curses mode after external process finishes
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0) # Hide cursor
        init_cores() # Re-initialize colors
        self.stdscr.clear() # Clear the screen
        self.stdscr.refresh() # Refresh to show a clean screen

        # Resume original music if it was paused
        if musica_carregada and self.musica_pausada_para_radio:
            try:
                # Altera de play() para resume()
                self.player.resume() # MODIFICAÇÃO CHAVE AQUI
            except Exception:
                pass
            self.musica_pausada_para_radio = False

        # Ensure nodelay is set back to True for the main loop's non-blocking input
        self.stdscr.nodelay(True)
        # You might also want to explicitly refresh the main interface
        # self.draw_interface() # This will be called by the main loop anyway

    def draw_interface(self):
        """Desenha todos os componentes da interface na tela."""
        self.stdscr.clear()
        self.ui_components.desenhar_borda()
        self.ui_components.desenhar_titulo()
        
        # Posições dos elementos na tela (AJUSTADAS)
        espectro_y = 7 # Abaixo do título
        espectro_x = 2
        espectro_largura = curses.COLS - (espectro_x * 2) # Usa a largura disponível
        espectro_altura = 4

        #largura_disponivel = curses.COLS - (espectro_x * 2) 
        #espectro_largura = min(largura_disponivel, 76) # Removido o 76 fixo para usar o disponível
        
        # Certifique-se de que self.player.pausado existe e é confiável
        # ou, alternativamente, confie apenas no is_playing()
        tocando = self.player.get_nome() and self.player.get_progresso() > 0 and self.player.is_playing()
        if tocando:
            try:
                num_barras_player = espectro_largura // 2
                espectro_raw = self.player.espectro(num_barras=num_barras_player)
                
                # Garante que espectro_atual tem o tamanho correto
                if not hasattr(self, 'espectro_atual') or len(self.espectro_atual) != num_barras_player:
                    self.espectro_atual = [0.0] * num_barras_player
                
                # Ajuste para suavização e movimento mais rápido
                for i in range(min(len(espectro_raw), len(self.espectro_atual))):
                    atual = self.espectro_atual[i]
                    novo = espectro_raw[i] if i < len(espectro_raw) else 0
                    
                    # Alpha para suavização:
                    # Um alpha mais alto (ex: 0.7 a 0.9) faz o espectro reagir mais rapidamente.
                    # Um alpha mais baixo (ex: 0.2 a 0.5) faz o espectro mais suave, mas lento.
                    # Podemos ter um alpha diferente para subida e descida para um efeito mais natural.
                    if novo > atual: # Subindo
                        alpha = 0.8
                    else: # Descendo
                        alpha = 0.5
                    
                    self.espectro_atual[i] = alpha * novo + (1 - alpha) * atual
            except Exception:
                # Se houver erro, decai o espectro suavemente
                self.espectro_atual = [max(0, v * 0.75) for v in self.espectro_atual]
        else:
            # Decai o espectro mais rapidamente quando não está tocando
            self.espectro_atual = [max(0, v * 0.75) for v in self.espectro_atual]

        self.ui_components.desenhar_espectro(
            self.espectro_atual,
            y=espectro_y,
            x=espectro_x,
            largura=espectro_largura,
            altura=espectro_altura
        )
        
        # Posições dos elementos de baixo para cima para garantir o layout correto
        menu_y = curses.LINES - 3 # Linha inicial do menu inferior (2 linhas de altura)
        
        status_y = menu_y - 3 # Status da música (2 linhas de altura) + 1 linha de espaçamento = 3 linhas acima do menu
        
        volume_y = status_y - 1 # Volume (1 linha de altura)
        
        recursos_y = volume_y - 1 # Uso de recursos (1 linha de altura)

        # Posição da playlist - LOGO ABAIXO DO ESPECTRO
        playlist_y = espectro_y + espectro_altura + 1 # Começa uma linha abaixo do espectro
        # A altura da playlist será o espaço entre playlist_y e recursos_y
        altura_playlist = recursos_y - (playlist_y + 1) # +1 para contar o título da playlist
        
        if altura_playlist < 0: 
            altura_playlist = 0 
        
        largura_playlist = curses.COLS - 4
        self.ui_components.desenhar_playlist(
            self.playlist.playlist_atual,
            self.playlist_selecionada,
            self.playlist_offset,
            self.favoritos,
            y=playlist_y, x=2, altura=altura_playlist, largura=largura_playlist
        )

        # Desenha os elementos de baixo para cima (já calculamos seus Y's)
        cpu_usage, ram_usage = uso_recursos()
        self.ui_components.desenhar_recursos(cpu_usage, ram_usage, y=recursos_y, x=2)
        self.ui_components.desenhar_volume(self.volume, y=volume_y, x=2)
        self.ui_components.desenhar_status(
            self.player.get_nome(),
            self.player.get_progresso(),
            self.player.get_duracao(),
            y=status_y, x=2
        )
        self.ui_components.desenhar_menu_inferior(menu_y, 2)
        self.stdscr.refresh()

    def loop(self):
        while self.executando:
            # Chame check_events() para processar eventos do Pygame, incluindo o de fim de música.
            # ESSENCIAL PARA O EVENTO 'musica_terminada' SER DISPARADO.
            self.player.check_events()
            
            # Verifica se a música atual terminou para avançar automaticamente
            # Isso requer que 'player' tenha um método para verificar se a música terminou
            # ou que 'atualizar' seja chamado pelo player no final da reprodução.
            # Por exemplo, se 'player.musica_atual_terminou()' retornar True.
            # Ou, como implementado no método 'atualizar', o player notifica a UI.
            
            # Uma verificação extra para garantir que o player não está tocando
            # e não está pausado, o que indicaria que a música terminou.
            if (not self.radio_ativo and 
                not self.player.is_playing() and 
                self.player.get_duracao() > 0 and 
                (self.player.get_progresso() >= self.player.get_duracao() - 0.1) and # Adiciona uma pequena margem de erro
                not getattr(self.player, 'pausado', False)): # Verifica se o player está explicitamente pausado
                self.proxima()

            self.draw_interface() # Agora a interface é desenhada por um método centralizado
            
            # Persistir estado
            self.config_manager.set('volume', self.volume)
            self.config_manager.set('equalizacao', self.equalizacao)
            self.config_manager.set('modo_visualizacao', self.modo_visualizacao)
            self.salvar_historico()
            self.salvar_favoritos()
            
            try:
                key = self.stdscr.getch()
            except KeyboardInterrupt:
                break
            
            if key == -1:
                time.sleep(0.02) # Reduzir o tempo de espera para mais fluidez
                continue
            
            itens_por_coluna = 8 # Deve ser consistente com o desenhar_playlist
            if self.playlist.playlist_atual:
                max_col = (len(self.playlist.playlist_atual) - 1) // itens_por_coluna
            else:
                max_col = 0
            
            # Lógica de navegação e controles
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
            elif key in (ord('q'), ord('Q')):
                self.executando = False
            elif key in (ord('r'), ord('R')):
                self.abrir_radio() # Chama o método abrir_radio
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
            elif key in (ord('2'), ):
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
            elif key in (curses.KEY_ENTER, 10, 13):
                self._tocar_selecionada()
            
            time.sleep(0.02) # Reduzir o tempo de espera para mais fluidez