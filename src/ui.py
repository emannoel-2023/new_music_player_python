import curses
import time
import os
import json
import psutil
import math
import subprocess
from pyfiglet import Figlet
from audio import AudioPlayer
from playlist import PlaylistManager
from historico import Historico
from utils import formatar_tempo
from radio_terminal.radio import RadioPlayer
from playlist import PlaylistManager
from historico import Historico
from biblioteca import Biblioteca
from config_manager import ConfigManager

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

def limpar_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

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
        self.radio_ativo = False
        self.radio_player = RadioPlayer()
        self.biblioteca = Biblioteca()
        self.config_manager = ConfigManager()
        self.equalizacao = {'grave': 0, 'medio': 0, 'agudo': 0}
        self.modo_visualizacao = 'lista'  # 'lista', 'artista', 'album', 'genero'
        self.filtro_atual = None
        self.termo_busca_atual = ""
        self.player.add_observer(self)  # Registrar UI como observadora do player
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

    def atualizar(self, evento):
        """Método observer para atualizar a UI quando o player muda"""
        if evento == 'carregar_musica':
            # Atualizar display da música atual
            pass
        elif evento == 'play_pause':
            # Atualizar status play/pause
            pass
        elif evento == 'volume':
            self.volume = self.player.get_volume()
        elif evento == 'equalizacao':
            # Atualizar display da equalização
            pass
    
    def buscar_musicas(self):
        self.stdscr.nodelay(False)  # Torna getch() bloqueante
        """Interface para buscar músicas"""
        termo = self.solicitar_entrada("Digite o termo de busca: ", curses.LINES - 3)
        if termo:
            self.termo_busca_atual = termo
            resultados = self.biblioteca.buscar(termo)
            if resultados:
                self.playlist.playlist_atual = [m.caminho for m in resultados]
                self.playlist_selecionada = 0
                self.playlist_offset = 0
                self.stdscr.addstr(curses.LINES - 3, 2, f"Encontradas {len(resultados)} músicas. Pressione qualquer tecla...")
            else:
                self.stdscr.addstr(curses.LINES - 3, 2, "Nenhuma música encontrada! Pressione qualquer tecla...")
            self.stdscr.getch()
            self.stdscr.nodelay(True)  # Torna getch() bloqueante

    def filtrar_por_categoria(self):
        self.stdscr.nodelay(False)  # Torna getch() bloqueante
        """Interface para filtrar por categoria"""
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
        self.stdscr.nodelay(True)  # Torna getch() bloqueante

    def _filtrar_por(self, categoria):
        """Filtrar músicas por categoria específica"""
        grupos = self.biblioteca.listar_por(categoria)
        opcoes = list(grupos.keys())
        if not opcoes:
            self.stdscr.addstr(curses.LINES - 3, 2, "Nenhuma categoria encontrada! Pressione qualquer tecla...")
            self.stdscr.getch()
            return
        self.stdscr.clear()
        self.stdscr.addstr(0, 2, f"Filtrar por {categoria}:", curses.color_pair(1) | curses.A_BOLD)
        idx = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 2, f"Filtrar por {categoria} (↑↓ para navegar, Enter para selecionar, Q para sair):", curses.color_pair(1) | curses.A_BOLD)
            for i, opcao in enumerate(opcoes):
                texto = f"> {opcao}" if i == idx else f"  {opcao}"
                texto = str(texto)
                maxlen = curses.COLS - 4  # 2 de margem de cada lado
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
                    pass  # Ignora linhas que não cabem
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
    

    def _pre_processar_audio_com_eq(self, caminho_original):
        """
        Pré-processa o áudio aplicando equalização e salva temporariamente
        """
        import tempfile
        
        try:
            # Carrega o áudio original
            audio = AudioSegment.from_file(caminho_original)
            
            # Converte para array numpy
            samples = audio.get_array_of_samples()
            arr = np.array(samples).astype(np.float32)
            
            # Se estéreo, processa ambos os canais
            if audio.channels == 2:
                # Separa canais
                left = arr[0::2]
                right = arr[1::2]
                
                # Aplica equalização em cada canal
                left_eq = self._apply_equalizer(left, audio.frame_rate)
                right_eq = self._apply_equalizer(right, audio.frame_rate)
                
                # Reconstrói áudio estéreo
                arr_eq = np.empty(len(arr), dtype=np.float32)
                arr_eq[0::2] = left_eq
                arr_eq[1::2] = right_eq
            else:
                # Mono
                arr_eq = self._apply_equalizer(arr, audio.frame_rate)
            
            # Converte de volta para AudioSegment
            arr_eq = np.clip(arr_eq, -32768, 32767).astype(np.int16)
            audio_eq = audio._spawn(arr_eq.tobytes())
            
            # Salva temporariamente
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio_eq.export(temp_file.name, format='wav')
            
            return temp_file.name
        except Exception as e:
            print(f"Erro no pré-processamento: {e}")
            return caminho_original



    def controlar_equalizacao(self):
        """Interface para controlar equalização"""
        self.stdscr.clear()
        self.stdscr.addstr(0, 2, "Equalização (↑↓ para navegar, ←→ para ajustar, Q para sair)", curses.color_pair(1) | curses.A_BOLD)
        controles = ['grave', 'medio', 'agudo']
        idx = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 2, "Equalização (↑↓ para navegar, ←→ para ajustar, Q para sair)", curses.color_pair(1) | curses.A_BOLD)
            for i, controle in enumerate(controles):
                valor = self.equalizacao[controle]
                barra = self._criar_barra_eq(valor)
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
                # CORRETO: passar os valores separadamente
                self.player.set_equalizacao(
                    self.equalizacao['grave'], 
                    self.equalizacao['medio'], 
                    self.equalizacao['agudo']
                )
            elif key == curses.KEY_RIGHT:
                controle = controles[idx]
                self.equalizacao[controle] = min(10, self.equalizacao[controle] + 0.5)
                # CORRETO: passar os valores separadamente  
                self.player.set_equalizacao(
                    self.equalizacao['grave'], 
                    self.equalizacao['medio'], 
                    self.equalizacao['agudo']
                )

    def _criar_barra_eq(self, valor):
        """Criar barra visual para equalização"""
        pos = int((valor + 10) / 20 * 20)  # Normalizar para 0-20
        barra = "[" + "=" * pos + "|" + " " * (20 - pos) + "]"
        return barra

    def mostrar_estatisticas(self):
        self.stdscr.nodelay(False)  # Torna getch() bloqueante
        """Mostrar estatísticas detalhadas de reprodução"""
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
        self.stdscr.addstr(curses.LINES - 2, 2, "Pressione qualquer tecla para voltar...")
        self.stdscr.refresh()
        self.stdscr.getch()
        self.stdscr.nodelay(True)  # Torna getch() bloqueante







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

    def desenhar_espectro(self, y, x, largura=80, altura=4):
        # Calcular número de barras baseado na largura disponível
        # Cada barra ocupa 2 caracteres, então num_barras = largura // 2
        num_barras = min(40, largura // 2)  # Máximo 40 barras para performance
        
        tocando = self.player.get_nome() and self.player.get_progresso() > 0 and not getattr(self.player, 'pausado', False)
        
        if tocando:
            try:
                espectro = self.player.espectro(num_barras=num_barras)
                
                # Inicializa espectro atual se não existir ou tamanho mudou
                if not hasattr(self, 'espectro_atual') or len(self.espectro_atual) != num_barras:
                    self.espectro_atual = [0.0] * num_barras
                
                # Suavização mais responsiva
                for i in range(min(len(espectro), len(self.espectro_atual))):
                    atual = self.espectro_atual[i]
                    novo = espectro[i] if i < len(espectro) else 0
                    
                    # Subida muito rápida, descida moderada
                    if novo > atual:
                        alpha = 0.9  # Subida quase instantânea
                    else:
                        alpha = 0.6  # Descida mais rápida também
                    
                    self.espectro_atual[i] = alpha * novo + (1 - alpha) * atual
                    
            except Exception as e:
                # Em caso de erro, usa valores padrão
                if not hasattr(self, 'espectro_atual'):
                    self.espectro_atual = [0.0] * num_barras
        else:
            # Decaimento quando pausado/parado
            if not hasattr(self, 'espectro_atual'):
                self.espectro_atual = [0.0] * num_barras
            
            # Decaimento mais rápido quando pausado
            self.espectro_atual = [max(0, v * 0.75) for v in self.espectro_atual]
        
        # Cores do espectro (do grave para agudo)
        cores = [
            curses.color_pair(4),   # Graves - vermelho
            curses.color_pair(5),   # Médio-graves - laranja  
            curses.color_pair(6),   # Médios - amarelo
            curses.color_pair(8),   # Médio-agudos - verde
            curses.color_pair(9),   # Agudos - azul
            curses.color_pair(10)   # Super agudos - magenta
        ]
        
        # Limpa a área do espectro
        for j in range(altura):
            try:
                self.stdscr.move(y + j, x)
                self.stdscr.clrtoeol()
            except curses.error:
                pass
        
        # Desenha as barras ocupando toda a largura disponível
        for i, val in enumerate(self.espectro_atual):
            if i >= num_barras:
                break
                
            col = x + i * 2  # Espaçamento entre barras
            
            # Verifica se ainda está dentro dos limites
            if col >= curses.COLS - 1:
                break
                
            h = max(0, min(altura, int(val + 0.5)))  # Arredondamento melhor
            
            # Escolhe cor baseada na posição (frequência)
            if len(cores) > 0:
                cor_idx = int((i / max(1, num_barras - 1)) * (len(cores) - 1))
                cor = cores[min(cor_idx, len(cores) - 1)]
            else:
                cor = curses.color_pair(1)  # Cor padrão
            
            # Desenha a barra de baixo para cima
            for j in range(altura):
                if col < curses.COLS - 1:  # Verifica limite da tela
                    if altura - j <= h:
                        # Diferentes caracteres para diferentes intensidades
                        if val > 5:
                            char = "██"
                        elif val > 4:
                            char = "▓▓"
                        elif val > 2:
                            char = "▒▒"
                        elif val > 0.5:
                            char = "░░"
                        else:
                            char = "  "
                        
                        if altura - j <= h and val > 0.3:  # Threshold menor
                            try:
                                self.stdscr.addstr(y + j, col, char, cor)
                            except curses.error:
                                pass  # Ignora erros de posição
                        else:
                            try:
                                self.stdscr.addstr(y + j, col, "  ")
                            except curses.error:
                                pass

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
        itens_por_coluna = 8
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
            self.biblioteca.carregar_diretorio(caminho)
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
        from biblioteca import Musica
        self.stdscr.nodelay(False)  # Torna getch() bloqueante
        """Interface para ordenar playlist com múltiplos critérios"""
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
            self.playlist.playlist_atual.sort(key=lambda x: Musica(x).metadados.get('duracao', 0))
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
            # Ordenar por ordem de adição (reverso do histórico)
            pass
        else:
            self.stdscr.addstr(curses.LINES - 3, 2, "Opção inválida! Pressione qualquer tecla...")
            self.stdscr.getch()
            return
        self.playlist_selecionada = 0
        self.playlist_offset = 0
        self.stdscr.addstr(curses.LINES - 3, 2, "Playlist ordenada! Pressione qualquer tecla...")
        self.stdscr.getch()
        self.stdscr.nodelay(True)  # Torna getch() bloqueante

    def _ordenar_por_metadado(self, metadado):
        """Ordenar playlist por metadado específico"""
        from biblioteca import Musica
        self.playlist.playlist_atual.sort(
            key=lambda x: Musica(x).metadados.get(metadado, '').lower()
        )

    def _ordenar_por_duracao(self):
        """
        Ordenar playlist por duração (usando metadados já carregados)
        """
        def get_duracao(caminho):
            for m in self.biblioteca.musicas:
                if m.caminho == caminho:
                    return m.metadados.get('duracao', 0)
            return 0
        self.playlist.playlist_atual.sort(key=get_duracao)

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


    def draw_interface(self, stdscr):
        self.stdscr = stdscr  # garante que o stdscr está atualizado
        self.stdscr.clear()
        self.desenhar_borda()
        self.desenhar_titulo()
        
        # Calcula largura disponível para o espectro (considerando bordas)
        largura_disponivel = curses.COLS - 6  # margem de 3 em cada lado
        largura_espectro = min(76, largura_disponivel)  # máximo 76 ou o que couber
        
        self.desenhar_espectro(y=7, x=2, largura=largura_espectro, altura=4)
        self.desenhar_volume(y=12, x=2)
        self.desenhar_playlist(y=14, x=2, altura=12, largura=40)
        self.desenhar_status(y=curses.LINES - 5, x=2)
        self.desenhar_recursos(y=curses.LINES - 3, x=2)
        self.stdscr.refresh()
    
    
    def abrir_radio(self):
        musica_carregada = getattr(self.player, 'get_nome', lambda: None)()
        tocando = False
        if musica_carregada:
            if hasattr(self.player, 'is_playing'):
                tocando = self.player.is_playing()
            elif hasattr(self.player, 'pausado'):
                tocando = not self.player.pausado
            else:
                tocando = True

        if musica_carregada and tocando:
            try:
                self.player.play_pause()
                self.musica_pausada_para_radio = True
            except Exception:
                self.musica_pausada_para_radio = False
        else:
            self.musica_pausada_para_radio = False

        curses.endwin()
        radio_dir = os.path.join(os.getcwd(), 'radio_terminal')
        radio_script = os.path.join(radio_dir, 'radio.py')

        try:
            proc = subprocess.Popen([
                'cmd.exe', '/c', 'start', '/wait', 'cmd', '/c',
                'python', radio_script
            ], cwd=radio_dir)
            proc.wait()  # Aguarda o rádio fechar
        except FileNotFoundError:
            subprocess.call(['python3', radio_script], cwd=radio_dir)

        time.sleep(0.1)

        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)
        init_cores()
        self.stdscr.clear()
        self.stdscr.refresh()

        if musica_carregada and self.musica_pausada_para_radio:
            try:
                self.player.play_pause()
            except Exception:
                pass
            self.musica_pausada_para_radio = False

        self.draw_interface(self.stdscr)

    def loop(self):
        while self.executando:
            self.stdscr.erase()
            self.desenhar_borda()
            self.desenhar_titulo()
            y_pos = 6
            self.desenhar_espectro(y_pos, 2, largura=76, altura=4)
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
            menu_line2 = "[S]Saltar [O]Ordenar [H]Histórico [L]Listar [B]Buscar [T]Filtrar [E]EQ [X]Stats [Q]Sair [R]Rádio"
            self.stdscr.attron(curses.A_REVERSE)
            self.stdscr.addstr(curses.LINES - 3, 2, menu_line1)
            self.stdscr.addstr(curses.LINES - 2, 2, menu_line2)
            self.stdscr.attroff(curses.A_REVERSE)
            self.config_manager.set('volume', self.volume)
            self.config_manager.set('equalizacao', self.equalizacao)
            self.config_manager.set('modo_visualizacao', self.modo_visualizacao)
            self.salvar_historico()
            self.salvar_favoritos()
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
            elif key in (ord('q'), ord('Q')):
                self.executando = False
                break
            elif key in (ord('r'), ord('R')):
                self.abrir_radio()
                continue
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
            elif key in (ord('='), ord('+'), ):  # Aumentar volume
                self.aumentar_volume()
            elif key in (ord('-'), ):
                self.diminuir_volume()
            elif key in (ord('b'), ord('B')):  # Buscar
                self.buscar_musicas()
            elif key in (ord('t'), ord('T')):  # Filtrar (fiT)
                self.filtrar_por_categoria()
            elif key in (ord('e'), ord('E')):  # Equalização
                self.controlar_equalizacao()
            elif key in (ord('x'), ord('X')):  # Estatísticas (eXtra)
                self.mostrar_estatisticas()
            elif key in (curses.KEY_ENTER, 10, 13):
                self._tocar_selecionada()
            else:
                pass
            time.sleep(0.05)

def main(stdscr):
    limpar_terminal()
    ui = UIPlayer(stdscr)
    ui.loop()

if __name__ == "__main__":
    curses.wrapper(main)
