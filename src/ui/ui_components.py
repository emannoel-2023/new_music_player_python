import curses
import os
from pyfiglet import Figlet
import math

class UIComponents:
    """
    Classe para agrupar métodos de desenho de componentes visuais da interface.
    """
    def __init__(self, stdscr):
        self.stdscr = stdscr

    def desenhar_borda(self):
        """Desenha uma borda ao redor da tela."""
        self.stdscr.border()

    def desenhar_titulo(self):
        """Desenha o título 'MUSGA' em ASCII Art."""
        fig = Figlet(font='slant', width=80)
        titulo_ascii = fig.renderText('MUSGA')
        # Limpa as linhas onde o título será desenhado
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

    def desenhar_espectro(self, espectro_atual, y, x, largura=80, altura=4):
        """
        Desenha o espectro de áudio na tela: frequências baixas no centro, altas nos cantos.
        O espectro se expande do centro para os cantos, e é centralizado na largura disponível.
        :param espectro_atual: Lista de valores representando a intensidade do espectro (grave para agudo).
        :param y: Posição Y inicial para o desenho.
        :param x: Posição X inicial para o desenho (canto superior esquerdo da área do espectro).
        :param largura: Largura máxima disponível para o espectro.
        :param altura: Altura máxima disponível para o espectro (número de linhas).
        """
        # Cores do espectro em tons de roxo, azul e ciano
        cores = [
            curses.color_pair(9),   # Roxo mais escuro (pode ser ajustado em ui_utils)
            curses.color_pair(6),   # Azul (conforme ui_utils)
            curses.color_pair(1),   # Ciano (conforme ui_utils)
            curses.color_pair(5),   # Magenta/Roxo (conforme ui_utils)
            curses.color_pair(7),   # Branco sobre azul (para maior destaque)
        ]
        
        # Limpa a área do espectro
        for j in range(altura):
            try:
                self.stdscr.move(y + j, x)
                self.stdscr.clrtoeol()
            except curses.error:
                pass
        
        if not espectro_atual:
            return

        num_barras_desejadas = largura // 2 # Cada barra ocupa 2 caracteres
        
        # Ajusta o número de barras para que seja par e caiba na largura
        num_barras_reais = min(len(espectro_atual), num_barras_desejadas)
        if num_barras_reais % 2 != 0:
            num_barras_reais -= 1 

        if num_barras_reais == 0:
            return

        barras_por_lado = num_barras_reais // 2
        
        # Calcular o ponto inicial X para centralizar o espectro
        start_x_centered = x + (largura - (num_barras_reais * 2)) // 2

        # Inverter e espelhar o espectro para o formato pirâmide (graves no centro)
        # O espectro_atual já vem do player com frequências graves para agudas.
        # Queremos o centro com as frequências graves, então pegamos o meio do espectro_atual.
        
        # A parte central do espectro (graves) estará no meio do array espectro_atual.
        # Precisamos mapear as barras do desenho para os índices corretos do espectro_atual.
        
        # O número de bandas de frequência do espectro de áudio deve ser mapeado para as barras visuais.
        # Se espectro_atual tem 20 valores (bandas), e queremos 40 barras (20 de cada lado),
        # precisaremos interpolar ou mapear. Assumimos que len(espectro_atual) é adequado.

        # Para um formato de pirâmide, o valor central do espectro deve ser o mais alto,
        # e diminuir em direção às extremidades.
        # O espectro_atual geralmente representa: [grave1, grave2, ..., agudoN]
        # Queremos que o centro da nossa UI seja o grave1, e as extremidades sejam os agudos.
        # A forma mais simples é pegar a parte central do espectro_atual para o centro da UI,
        # e as partes externas para as extremidades.

        # Vamos usar um fator de ponderação para enfatizar o centro.
        # Isso ajuda a criar o efeito de pirâmide e concentra o movimento.
        
        for i in range(barras_por_lado):
            # Mapeamento do índice 'i' para o índice do espectro.
            # O índice 0 no loop 'i' deve corresponder ao centro (graves).
            # O índice 'barras_por_lado - 1' deve corresponder às extremidades (agudos).

            # Ajuste para pegar as frequências do espectro_atual do centro para fora.
            # Se espectro_atual é [g1, g2, m1, m2, a1, a2] e barras_por_lado é 3:
            # i = 0: grave (idx 0 ou 1 de espectro_atual)
            # i = 1: médio (idx 2 ou 3 de espectro_atual)
            # i = 2: agudo (idx 4 ou 5 de espectro_atual)

            # Para que os graves fiquem no centro e os agudos nas pontas,
            # precisamos que as primeiras iterações de 'i' peguem os valores
            # do meio do array `espectro_atual`, e as últimas iterações peguem os valores das pontas.

            # Calcula o índice no espectro_atual para o lado esquerdo e direito,
            # de forma que os índices mais baixos (graves) estejam no centro das barras visuais.
            
            # Aqui, o índice `i` representa a "distância" do centro.
            # Quanto menor `i`, mais próximo do centro estamos.
            # Queremos que as frequências mais baixas de `espectro_atual` (que estão no início do array)
            # sejam usadas para as barras mais próximas do centro (i pequeno).
            
            # Mapeamento linear simples:
            # Pega uma fatia do espectro_atual que será usada para as barras visuais.
            # Se `espectro_atual` tem `N` elementos, e `num_barras_reais` barras visuais:
            # Precisa mapear `N` para `num_barras_reais`.
            
            # Ajuste de índice para que o centro receba os graves
            # Se espectro_atual é [grave1, grave2, medio1, medio2, agudo1, agudo2]
            # E barras_por_lado = 3.
            # A barra mais central (i=0) deve usar grave1 e grave2.
            # A barra do meio (i=1) deve usar medio1 e medio2.
            # A barra da ponta (i=2) deve usar agudo1 e agudo2.

            # Novo cálculo de índice:
            # 'j' é o índice da banda de frequência no array `espectro_atual`.
            # A barra `i` no lado esquerdo ou direito deve corresponder a uma banda de frequência específica.
            # As barras do meio (i=0) devem usar as bandas de frequência do meio de `espectro_atual`.
            # As barras das pontas (i = barras_por_lado - 1) devem usar as bandas das pontas de `espectro_atual`.
            
            # Vamos remapear 'i' para pegar as bandas de frequência de forma invertida para as extremidades.
            # O `espectro_atual` é grave -> agudo.
            # Queremos: [agudo, medio, grave] [grave, medio, agudo] na UI.
            
            # A barra mais à esquerda e mais à direita devem ser as frequências mais agudas.
            # A barra mais próxima do centro deve ser a frequência mais grave.
            
            # Então, para a barra 'i' (0 a barras_por_lado-1, onde 0 é a mais central):
            # O índice correspondente em espectro_atual seria:
            # `idx = i` (para ir do grave para o agudo)
            # Mas o espectro_atual já vem em ordem.
            # A gente tem que desenhar do centro pra fora.
            # O valor do espectro_atual[k] onde k é pequeno deve ser usado para as barras centrais.
            # O valor do espectro_atual[k] onde k é grande deve ser usado para as barras externas.

            # O `i` do loop `for i in range(barras_por_lado)` já representa a distância do centro.
            # i=0 é a barra adjacente ao centro.
            # i=barras_por_lado-1 é a barra mais externa.

            # Então, a barra 'i' no desenho deve usar o valor `espectro_atual[i]`
            # se quisermos os graves no centro.
            
            # Corrigido o mapeamento de índice:
            idx_espectro = i 
            
            # Fator de ponderação para dar mais destaque ao centro (efeito pirâmide)
            # Pode ser ajustado. Ex: centro = 1.5, extremidade = 0.5
            fator_ponderacao = 1.0 - (i / max(1, barras_por_lado - 1)) * 0.5 # Diminui para as pontas
            
            val = espectro_atual[idx_espectro] if idx_espectro < len(espectro_atual) else 0
            val *= fator_ponderacao # Aplica a ponderação

            # Altura da barra (usar o valor de 'val' para ambos os lados para simetria)
            h = max(0, min(altura, int(val + 0.5))) # Arredonda para o inteiro mais próximo

            # Posição da coluna no lado esquerdo do centro
            col_left = start_x_centered + (barras_por_lado - 1 - i) * 2

            # Posição da coluna no lado direito do centro
            col_right = start_x_centered + barras_por_lado * 2 + i * 2
            
            # A cor deve refletir a frequência. Cores mais vibrantes para o centro (graves).
            # Quanto menor 'i' (mais próximo do centro/grave), menor o índice de cor.
            # Inverte a ordem das cores para que as mais escuras/roxas fiquem nas pontas e as claras/brancas no centro.
            
            # Ajuste no cálculo da cor:
            # Queremos que as cores mais claras/vibrantes (maior índice na lista `cores`) fiquem no centro (i pequeno).
            # E as cores mais escuras/roxas (menor índice na lista `cores`) fiquem nas pontas (i grande).
            # Então, o índice da cor deve ser `len(cores) - 1 - cor_idx_base`.
            # `cor_idx_base` deve ser 0 para `i=0` (centro) e `len(cores)-1` para `i=barras_por_lado-1` (extremidade).
            cor_idx_base = int((i / max(1, barras_por_lado - 1)) * (len(cores) - 1))
            cor = cores[len(cores) - 1 - cor_idx_base] if len(cores) > 0 else curses.color_pair(1)
            
            # Caracteres para desenhar a barra
            char = "  "
            if val > 5:
                char = "██"
            elif val > 4:
                char = "▓▓"
            elif val > 2:
                char = "▒▒"
            elif val > 0.5:
                char = "░░"
            
            # Desenha a barra de baixo para cima nos dois lados
            for j in range(altura):
                # Desenha apenas se a barra tiver altura suficiente para a linha 'j'
                if altura - j <= h and val > 0.05: # Garante que só desenha se há algum valor
                    try:
                        # Desenha o lado esquerdo
                        if col_left >= x and col_left + 1 < x + largura:
                            self.stdscr.addstr(y + j, col_left, char, cor)
                        
                        # Desenha o lado direito
                        if col_right >= x and col_right + 1 < x + largura:
                            self.stdscr.addstr(y + j, col_right, char, cor)
                    except curses.error:
                        pass
                else:
                    # Limpa a área se a barra não deve ser desenhada
                    try:
                        if col_left >= x and col_left + 1 < x + largura:
                            self.stdscr.addstr(y + j, col_left, "  ")
                        if col_right >= x and col_right + 1 < x + largura:
                            self.stdscr.addstr(y + j, col_right, "  ")
                    except curses.error:
                        pass


    def desenhar_volume(self, volume, y, x, largura=20):
        """
        Desenha a barra de volume.
        :param volume: Valor do volume (0.0 a 1.0).
        :param y: Posição Y.
        :param x: Posição X.
        :param largura: Largura da barra de volume.
        """
        preenchido = int(volume * largura)
        barra = "[" + "=" * preenchido + ">" + " " * (largura - preenchido) + "]"
        self.stdscr.attron(curses.color_pair(3))
        self.stdscr.addstr(y, x, f"Volume: {barra} {int(volume*100)}%")
        self.stdscr.attroff(curses.color_pair(3))

    def desenhar_playlist(self, playlist_atual, playlist_selecionada, playlist_offset, favoritos, y, x, altura, largura):
        """
        Desenha a playlist atual.
        :param playlist_atual: Lista de músicas na playlist.
        :param playlist_selecionada: Índice da música selecionada.
        :param playlist_offset: Offset para rolagem da playlist.
        :param favoritos: Set de músicas favoritas.
        :param y: Posição Y.
        :param x: Posição X.
        :param altura: Altura da área da playlist.
        :param largura: Largura da área da playlist.
        """
        self.stdscr.attron(curses.A_BOLD)
        self.stdscr.addstr(y, x, "Playlist Atual:")
        self.stdscr.attroff(curses.A_BOLD)
        
        total = len(playlist_atual)
        itens_por_coluna = altura - 2 # Descontando o título e a linha do "Coluna X/Y"
        if itens_por_coluna <= 0: # Para evitar divisão por zero ou loop infinito se não houver espaço
            itens_por_coluna = 1
        total_colunas = (total + itens_por_coluna - 1) // itens_por_coluna
        
        coluna_atual = playlist_offset
        inicio = coluna_atual * itens_por_coluna
        fim = min(inicio + itens_por_coluna, total)

        # Limpa a área da playlist antes de redesenhar
        for i in range(altura - 1):
            try:
                self.stdscr.move(y + 1 + i, x)
                self.stdscr.clrtoeol()
            except curses.error:
                pass

        for i, idx in enumerate(range(inicio, fim)):
            musica = os.path.basename(playlist_atual[idx])
            favorito = "★" if playlist_atual[idx] in favoritos else " "
            # Limita o tamanho da string da música para caber na largura
            display_musica = f"{favorito} {musica}"
            if len(display_musica) > largura - 3: # -3 para "> " e espaço
                display_musica = display_musica[:largura - 6] + "..."

            if idx == playlist_selecionada:
                self.stdscr.attron(curses.color_pair(2))
                self.stdscr.addstr(y + 1 + i, x, f"> {display_musica}")
                self.stdscr.attroff(curses.color_pair(2))
            else:
                self.stdscr.addstr(y + 1 + i, x, f"  {display_musica}")
        
        # Desenha a informação da coluna
        try:
            self.stdscr.addstr(y + altura - 1, x, f"Coluna {coluna_atual+1}/{total_colunas}")
        except curses.error:
            pass # Ignora se não houver espaço para a linha da coluna

    def desenhar_status(self, nome_musica, progresso, duracao, y, x):
        """
        Desenha o status da música atual (nome, progresso/duração).
        :param nome_musica: Nome da música tocando.
        :param progresso: Progresso atual em segundos.
        :param duracao: Duração total em segundos.
        :param y: Posição Y.
        :param x: Posição X.
        """
        from ui_utils import formatar_tempo # Importa aqui para evitar dependência circular se utils usar UIComponents
        texto = f"Tocando: {nome_musica if nome_musica else 'Nenhuma música'}"
        self.stdscr.addstr(y, x, texto[:curses.COLS - 4])
        tempo_str = f"{formatar_tempo(progresso)} / {formatar_tempo(duracao)}"
        self.stdscr.addstr(y + 1, x, tempo_str)

    def desenhar_recursos(self, cpu, ram, y, x):
        """
        Desenha o uso de recursos (CPU e RAM).
        :param cpu: Uso da CPU em porcentagem.
        :param ram: Uso da RAM em MB.
        :param y: Posição Y.
        :param x: Posição X.
        """
        texto = f"CPU: {cpu:.1f}% | RAM: {ram:.1f} MB"
        self.stdscr.addstr(y, x, texto)

    def desenhar_menu_inferior(self, y, x):
        """
        Desenha as linhas do menu de atalhos na parte inferior da tela.
        :param y: Posição Y.
        :param x: Posição X.
        """
        menu_line1 = "[1]Abrir [2]Play/Pause [3]Ant [4]Próx [+/-]Vol [C]Criar [A]Add [D]Rem [F]Fav"
        menu_line2 = "[S]Saltar [O]Ordenar [H]Histórico [L]Listar [B]Buscar [T]Filtrar [E]EQ [X]Stats [Q]Sair [R]Rádio"
        
        self.stdscr.attron(curses.A_REVERSE)
        self.stdscr.addstr(y, x, menu_line1)
        self.stdscr.addstr(y + 1, x, menu_line2)
        self.stdscr.attroff(curses.A_REVERSE)

    def solicitar_entrada(self, prompt, y):
        """
        Solicita uma entrada de texto do usuário na interface curses.
        :param prompt: Mensagem a ser exibida ao usuário.
        :param y: Posição Y da linha de entrada.
        :return: String com a entrada do usuário.
        """
        curses.echo()  # Habilita o eco para que o usuário veja o que digita
        self.stdscr.move(y, 2)
        self.stdscr.clrtoeol()  # Limpa a linha
        self.stdscr.addstr(y, 2, prompt)
        self.stdscr.refresh()
        entrada = self.stdscr.getstr(y, 2 + len(prompt)).decode("utf-8").strip()
        curses.noecho() # Desabilita o eco
        return entrada

    def mostrar_mensagem(self, mensagem, y):
        """
        Exibe uma mensagem temporária na tela.
        :param mensagem: A mensagem a ser exibida.
        :param y: A linha Y onde a mensagem será exibida.
        """
        self.stdscr.move(y, 2)
        self.stdscr.clrtoeol()
        self.stdscr.addstr(y, 2, mensagem)
        self.stdscr.refresh()
        self.stdscr.getch() # Espera uma tecla para o usuário ler a mensagem
        self.stdscr.move(y, 2)
        self.stdscr.clrtoeol() # Limpa a mensagem

    def criar_barra_eq(self, valor):
        """Criar barra visual para equalização."""
        pos = int((valor + 10) / 20 * 20)  # Normalizar para 0-20
        barra = "[" + "=" * pos + "|" + " " * (20 - pos) + "]"
        return barra