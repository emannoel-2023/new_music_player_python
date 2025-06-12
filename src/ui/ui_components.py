import curses
import os
from pyfiglet import Figlet
import math
import time
import unicodedata
import pathlib

class UIComponents:
    def __init__(self, stdscr):
        self.stdscr = stdscr

    def desenhar_borda(self):
        self.stdscr.border()

    def desenhar_titulo(self):
        largura_tela = curses.COLS
        
        largura_figlet = max(20, largura_tela - 4) 

        fig = Figlet(font='slant', width=largura_figlet)
        titulo_ascii = fig.renderText('MUSGA')
        
        linhas = titulo_ascii.split('\n')
        
        num_linhas_titulo = min(len(linhas), 5) 

        for i in range(num_linhas_titulo):
            try:
                self.stdscr.move(i, 2)
                self.stdscr.clrtoeol()
            except curses.error:
                pass

        for idx, linha in enumerate(linhas[:num_linhas_titulo]):
            if linha.strip():
                x_pos = max(2, (largura_tela - len(linha)) // 2)
                
                if x_pos + len(linha) > largura_tela - 2:
                    linha = linha[:largura_tela - 2 - x_pos]
                
                self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
                try:
                    self.stdscr.addstr(idx, x_pos, linha)
                except curses.error:
                    pass 
                self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)

    def desenhar_espectro(self, espectro_atual, y, x, largura, altura):
        cores = [
            curses.color_pair(9),
            curses.color_pair(6),
            curses.color_pair(1),
            curses.color_pair(5),
            curses.color_pair(7),
        ]
        
        for j in range(altura):
            try:
                self.stdscr.move(y + j, x)
                self.stdscr.clrtoeol()
            except curses.error:
                pass
        
        if not espectro_atual:
            return

        num_barras_desejadas = largura // 2 
        num_barras_reais = min(len(espectro_atual), num_barras_desejadas)
        if num_barras_reais % 2 != 0:
            num_barras_reais -= 1 

        if num_barras_reais == 0:
            return

        barras_por_lado = num_barras_reais // 2
        
        start_x_centered = x + (largura - (num_barras_reais * 2)) // 2

        for i in range(barras_por_lado):
            idx_espectro = i 
            
            fator_ponderacao = 1.0 - (i / max(1, barras_por_lado - 1)) * 0.5 
            
            val = espectro_atual[idx_espectro] if idx_espectro < len(espectro_atual) else 0
            val *= fator_ponderacao 
            
            h = max(0, min(altura, int(val + 0.5))) 
            
            col_left = start_x_centered + (barras_por_lado - 1 - i) * 2

            col_right = start_x_centered + barras_por_lado * 2 + i * 2
            
            cor_idx_base = int((i / max(1, barras_por_lado - 1)) * (len(cores) - 1))
            cor = cores[len(cores) - 1 - cor_idx_base] if len(cores) > 0 else curses.color_pair(1)
            
            char = "  "
            if val > 5:
                char = "██"
            elif val > 4:
                char = "▓▓"
            elif val > 2:
                char = "▒▒"
            elif val > 0.5:
                char = "░░"
            
            for j in range(altura):
                if altura - j <= h and val > 0.05: 
                    try:
                        if col_left >= x and col_left + 1 < x + largura:
                            self.stdscr.addstr(y + j, col_left, char, cor)
                        
                        if col_right >= x and col_right + 1 < x + largura:
                            self.stdscr.addstr(y + j, col_right, char, cor)
                    except curses.error:
                        pass
                else:
                    try:
                        if col_left >= x and col_left + 1 < x + largura:
                            self.stdscr.addstr(y + j, col_left, "  ")
                        if col_right >= x and col_right + 1 < x + largura:
                            self.stdscr.addstr(y + j, col_right, "  ")
                    except curses.error:
                        pass

    def desenhar_volume(self, volume, y, x, largura=20):
        largura_disponivel = curses.COLS - x - 2 
        largura_barra = min(largura, largura_disponivel - len("Volume: [] 100%")) 
        if largura_barra < 5: 
            largura_barra = 5

        preenchido = int(volume * largura_barra)
        barra = "[" + "=" * preenchido + ">" + " " * (largura_barra - preenchido) + "]"
        
        texto_volume = f"Volume: {barra} {int(volume*100)}%"
        
        if len(texto_volume) > curses.COLS - x:
            texto_volume = texto_volume[:curses.COLS - x - 3] + "..."

        self.stdscr.attron(curses.color_pair(3))
        try:
            self.stdscr.addstr(y, x, texto_volume)
        except curses.error:
            pass
        self.stdscr.attroff(curses.color_pair(3))

    def calcular_itens_por_coluna_playlist(self):
        espectro_y = 7
        espectro_altura = 4
        menu_y = curses.LINES - 3
        status_y = menu_y - 3
        volume_y = status_y - 1
        recursos_y = volume_y - 1

        playlist_y_start = espectro_y + espectro_altura + 1
        playlist_y_end = recursos_y - 1

        altura_disponivel_area = playlist_y_end - playlist_y_start + 1

        linhas_usadas_para_info = 2

        itens_por_coluna_calculado = altura_disponivel_area - linhas_usadas_para_info

        MAX_ITENS_POR_COLUNA_DESEJADO = 6

        itens_por_coluna = max(1, min(itens_por_coluna_calculado, MAX_ITENS_POR_COLUNA_DESEJADO))

        return itens_por_coluna

    def desenhar_playlist(self, playlist_atual, playlist_selecionada, playlist_offset, favoritos, y, x, altura, largura):
        if altura < 1: 
            return

        self.stdscr.attron(curses.A_BOLD)
        try:
            self.stdscr.addstr(y, x, "Playlist Atual:")
        except curses.error:
                pass 
        self.stdscr.attroff(curses.A_BOLD)
        
        total = len(playlist_atual)
        itens_por_coluna = self.calcular_itens_por_coluna_playlist()
        
        total_colunas = (total + itens_por_coluna - 1) // itens_por_coluna
        
        coluna_atual = playlist_offset
        inicio = coluna_atual * itens_por_coluna
        fim = min(inicio + itens_por_coluna, total)

        for i in range(altura - 1):
            try:
                self.stdscr.move(y + 1 + i, x)
                self.stdscr.clrtoeol()
            except curses.error:
                pass

        for i, idx in enumerate(range(inicio, fim)):
            musica = os.path.basename(playlist_atual[idx])
            favorito = "★" if playlist_atual[idx] in favoritos else " "

            largura_disponivel_real = curses.COLS - x - 2
            largura_para_texto = largura_disponivel_real - len(favorito) - 2
            
            display_musica = f"{favorito} {musica}"
            if len(display_musica) > largura_para_texto:
                display_musica = display_musica[:largura_para_texto - 3] + "..."

            try:
                if idx == playlist_selecionada:
                    self.stdscr.attron(curses.color_pair(2))
                    self.stdscr.addstr(y + 1 + i, x, f"> {display_musica}")
                    self.stdscr.attroff(curses.color_pair(2))
                else:
                    self.stdscr.addstr(y + 1 + i, x, f"  {display_musica}")
            except curses.error:
                pass 

        if altura >= 2:
            try:
                coluna_info = f"Coluna {coluna_atual+1}/{total_colunas}"
                

                if len(coluna_info) > largura:
                    coluna_info = coluna_info[:largura - 3] + "..."

                self.stdscr.addstr(y + altura - 1, x, coluna_info)
            except curses.error:
                pass 
            
    def desenhar_status(self, nome_musica, progresso, duracao, y, x):
        # A importação de formatar_tempo deve vir do ui_utils
        from ui_utils import formatar_tempo

        largura_disponivel = curses.COLS - x * 2

        # Linha do nome da música
        texto_musica = f"Tocando: {nome_musica if nome_musica else 'Nenhuma música'}"
        if len(texto_musica) > largura_disponivel:
            texto_musica = texto_musica[:largura_disponivel - 3] + "..."

        try:
            self.stdscr.addstr(y, x, texto_musica)
            self.stdscr.clrtoeol() # Limpa o resto da linha

            # Linha de progresso/duração
            if isinstance(progresso, (int, float)) and isinstance(duracao, (int, float)):
                # Se forem números, formata usando formatar_tempo
                tempo_str = f"{formatar_tempo(progresso)} / {formatar_tempo(duracao)}"
            else:
                # Se forem strings (como "---"), usa-as diretamente
                tempo_str = f"{progresso} / {duracao}"

            if len(tempo_str) > largura_disponivel:
                tempo_str = tempo_str[:largura_disponivel - 3] + "..."

            self.stdscr.addstr(y + 1, x, tempo_str)
            self.stdscr.clrtoeol() # Limpa o resto da linha
        except curses.error:
            pass

    def desenhar_recursos(self, cpu, ram, y, x):
        texto = f"CPU: {cpu:.1f}% | RAM: {ram:.1f} MB"
        
        largura_disponivel = curses.COLS - x - 2
        if len(texto) > largura_disponivel:
            texto = texto[:largura_disponivel - 3] + "..."

        try:
            self.stdscr.addstr(y, x, texto)
        except curses.error:
            pass

    def desenhar_menu_inferior(self, y, x):
        menu_line1_base = "[1]Abrir [2]Play/Pause [3]Ant [4]Próx [+/-]Vol [C]Criar [A]Add [D]Rem [F]Fav"
        menu_line2_base = "[S]Saltar [O]Ordenar [H]Histórico [L]Listar [B]Buscar [T]Filtrar [E]EQ [X]Stats [Q]Sair [R]Rádio [Y]YouTube [I]Navegar" # Adicionado [Y]YouTube
        
        largura_disponivel = curses.COLS - x - 2 

        menu_line1 = menu_line1_base
        if len(menu_line1) > largura_disponivel:
            menu_line1 = menu_line1_base[:largura_disponivel - 3] + "..."
        
        menu_line2 = menu_line2_base
        if len(menu_line2) > largura_disponivel:
            menu_line2 = menu_line2_base[:largura_disponivel - 3] + "..."

        self.stdscr.attron(curses.A_REVERSE)
        try:
            self.stdscr.addstr(y, x, menu_line1)
            self.stdscr.addstr(y + 1, x, menu_line2)
        except curses.error:
            pass 
        self.stdscr.attroff(curses.A_REVERSE)

    def _clean_input_string(self, input_str):
        """
        Normaliza e limpa a string de entrada, removendo caracteres de controle
        e normalizando a representação Unicode para caminhos de arquivo.
        """
        normalized_str = unicodedata.normalize('NFC', input_str)

        clean_str_chars = []
        for char in normalized_str:
            if unicodedata.category(char).startswith('C') or char in ('\u200e', '\u200f', '\u200b'):
                continue
            clean_str_chars.append(char)
        
        final_str = "".join(clean_str_chars).strip()


        return final_str

    def solicitar_entrada(self, prompt, y):
        curses.echo()  
        
        largura_disponivel = curses.COLS - 4 
        if len(prompt) > largura_disponivel - 5: 
            prompt = prompt[:largura_disponivel - 8] + "..."

        self.stdscr.move(y, 2)
        self.stdscr.clrtoeol()  
        try:
            self.stdscr.addstr(y, 2, prompt)
            self.stdscr.refresh()
            curses.flushinp() 
            time.sleep(0.05) 
            
            max_input_len = curses.COLS - (2 + len(prompt)) - 1
            if max_input_len < 0: 
                max_input_len = 0 
            
            raw_entrada = self.stdscr.getstr(y, 2 + len(prompt), max(512, max_input_len)).decode("utf-8")
            entrada = self._clean_input_string(raw_entrada)
        except curses.error:
            entrada = "" 
        
        curses.noecho() 
        return entrada

    def mostrar_mensagem(self, mensagem, y):
        largura_disponivel = curses.COLS - 4 
        
        for i in range(3): 
            try:
                self.stdscr.move(y + i, 2)
                self.stdscr.clrtoeol()
            except curses.error:
                pass

        linhas_msg = []
        temp_mensagem = mensagem 
        while temp_mensagem:
            if len(temp_mensagem) > largura_disponivel:
                quebra = temp_mensagem[:largura_disponivel]
                ultimo_espaco = quebra.rfind(' ')
                if ultimo_espaco > largura_disponivel // 2: 
                    linhas_msg.append(temp_mensagem[:ultimo_espaco])
                    temp_mensagem = temp_mensagem[ultimo_espaco+1:]
                else:
                    linhas_msg.append(temp_mensagem[:largura_disponivel])
                    temp_mensagem = temp_mensagem[largura_disponivel:]
            else:
                linhas_msg.append(temp_mensagem)
                temp_mensagem = ""
        
        for i, linha in enumerate(linhas_msg):
            if y + i < curses.LINES - 1:
                try:
                    self.stdscr.addstr(y + i, 2, linha)
                except curses.error:
                    pass
            else:
                break 

        self.stdscr.refresh()
        self.stdscr.getch() 

        for i in range(len(linhas_msg)):
            if y + i < curses.LINES - 1:
                try:
                    self.stdscr.move(y + i, 2)
                    self.stdscr.clrtoeol() 
                except curses.error:
                    pass

    def criar_barra_eq(self, valor):
        pos = int((valor + 10) / 20 * 20)  
        largura_barra_max = curses.COLS - 10 
        if largura_barra_max < 20:
            largura_barra_max = 20 
        
        barra_str = "=" * pos + "|" + " " * (20 - pos)
        if len(barra_str) > largura_barra_max:
            barra_str = barra_str[:largura_barra_max - 3] + "..."

        barra = "[" + barra_str + "]"
        return barra

    def solicitar_entrada_em_janela(self, prompt, largura=60, altura=5):
        MAX_PATH_LENGTH = 2048 

        max_y, max_x = self.stdscr.getmaxyx()
        win_y = max(0, (max_y - altura) // 2)
        win_x = max(0, (max_x - largura) // 2)

        altura = min(altura, max_y)
        largura = min(largura, max_x)
        if win_y + altura > max_y: win_y = max_y - altura
        if win_x + largura > max_x: win_x = max_x - largura
        if win_y < 0: win_y = 0
        if win_x < 0: win_x = 0


        input_win = curses.newwin(altura, largura, win_y, win_x)
        input_win.box()
        input_win.keypad(True)
        curses.curs_set(1)

        input_win.addstr(1, 2, prompt)
        input_win.refresh()

        curses.echo() 

        entrada_str = ""
        while True:
            cursor_y = 3
            input_start_x = 2
            
            input_win.move(cursor_y, input_start_x)
            input_win.clrtoeol()
            
            display_entrada = entrada_str
            max_input_display_len = largura - input_start_x - 2 

            if len(display_entrada) > max_input_display_len:
                display_entrada = "..." + display_entrada[-(max_input_display_len - 3):] 

            input_win.box() 
            input_win.addstr(1, 2, prompt)
            input_win.addstr(cursor_y, input_start_x, display_entrada)
            input_win.move(cursor_y, input_start_x + len(display_entrada))
            input_win.refresh()

            try:
                key = input_win.getch()
            except curses.error:
                key = -1 

            if key == curses.KEY_ENTER or key == 10 or key == 13:
                break 
            elif key == curses.KEY_BACKSPACE or key == 127 or key == curses.KEY_DC:
                if entrada_str:
                    entrada_str = entrada_str[:-1]
            elif 32 <= key <= 126 or key > 255: 
                if len(entrada_str) < MAX_PATH_LENGTH: 
                    entrada_str += chr(key)
            elif key == curses.KEY_RESIZE:
                curses.endwin()
                self.stdscr = curses.initscr()
                self.stdscr.refresh()
                max_y, max_x = self.stdscr.getmaxyx()
                win_y = max(0, (max_y - altura) // 2)
                win_x = max(0, (max_x - largura) // 2)

                altura = min(altura, max_y)
                largura = min(largura, max_x)
                if win_y + altura > max_y: win_y = max_y - altura
                if win_x + largura > max_x: win_x = max_x - largura
                if win_y < 0: win_y = 0
                if win_x < 0: win_x = 0

                input_win.mvwin(win_y, win_x)
                input_win.clear()
                input_win.box()
                input_win.addstr(1, 2, prompt)
                display_entrada = entrada_str
                max_input_display_len = largura - input_start_x - 2
                if len(display_entrada) > max_input_display_len:
                    display_entrada = "..." + display_entrada[-(max_input_display_len - 3):]
                input_win.addstr(cursor_y, input_start_x, display_entrada)
                input_win.move(cursor_y, input_start_x + len(display_entrada))
                input_win.refresh()
                continue

        curses.noecho() 
        curses.curs_set(0) 
        input_win.clear() 
        input_win.refresh()
        del input_win 

        return self._clean_input_string(entrada_str)