class Comandos:
    def __init__(self, player, playlist, ui, historico):
        self.player = player
        self.playlist = playlist
        self.ui = ui
        self.historico = historico

    def executar(self, comando):
        cmd = comando.strip().lower()

        if cmd in ["play", "p"]:
            self.player.play_pause()
        elif cmd == "pause":
            self.player.play_pause()
        elif cmd == "stop":
            self.player.parar()
        elif cmd in ["prox", "next"]:
            self.proxima()
        elif cmd in ["ant", "prev"]:
            self.anterior()
        elif cmd in ["+", "="]:
            vol_novo = self.player.get_volume() + 0.1
            self.player.setar_volume(vol_novo)
        elif cmd in ["-", "vol-"]:
            vol_novo = self.player.get_volume() - 0.1
            self.player.setar_volume(vol_novo)
        elif cmd.startswith("vol"):
            partes = cmd.split()
            if len(partes) == 2:
                try:
                    valor = float(partes[1])
                    self.player.setar_volume(valor)
                except:
                    print("Uso correto: vol <0.0 a 1.0>")
            else:
                print("Uso correto: vol <0.0 a 1.0>")
        elif cmd.startswith("dir"):
            caminho = input("Cole o caminho do diretório de músicas: ")
            playlist_carregada = self.playlist.carregar_diretorio(caminho)
            if playlist_carregada:
                self.player.carregar_musica(self.playlist.playlist_atual[0])
                self.player.play_pause()
                self.historico.adicionar(self.playlist.playlist_atual[0])
            else:
                print("Não foi possível carregar o diretório.")
        elif cmd == "sair":
            self.player.parar()
            self.playlist.salvar_estado()
            self.ui.executando = False
        else:
            print("Comando não reconhecido.")

    def proxima(self):
        self.playlist.indice_atual += 1
        if self.playlist.indice_atual >= len(self.playlist.playlist_atual):
            self.playlist.indice_atual = 0
        musica = self.playlist.playlist_atual[self.playlist.indice_atual]
        self.player.carregar_musica(musica)
        self.player.play_pause()
        self.historico.adicionar(musica)

    def anterior(self):
        self.playlist.indice_atual -= 1
        if self.playlist.indice_atual < 0:
            self.playlist.indice_atual = len(self.playlist.playlist_atual) - 1
        musica = self.playlist.playlist_atual[self.playlist.indice_atual]
        self.player.carregar_musica(musica)
        self.player.play_pause()
        self.historico.adicionar(musica)
