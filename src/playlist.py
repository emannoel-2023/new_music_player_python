import os
import json

PASTA_DADOS = os.path.join(os.path.dirname(__file__), '..', 'data')
ESTADO_PLAYER = os.path.join(PASTA_DADOS, 'estado_player.json')

class PlaylistManager:
    def __init__(self):
        self.playlists = {}
        self.favoritos = []
        self.playlist_atual = []
        self.indice_atual = 0
        self.carregar_estado()

    def carregar_diretorio(self, caminho):
        extensoes = ['.mp3', '.wav', '.flac', '.ogg']
        try:
            arquivos = os.listdir(caminho)
            self.playlist_atual = sorted(
                [os.path.join(caminho, f) for f in arquivos if os.path.splitext(f)[1].lower() in extensoes]
            )
            self.indice_atual = 0
            return self.playlist_atual
        except Exception as e:
            print(f"Erro ao carregar diretório: {str(e)}")
            return []

    def criar_playlist(self, nome):
        if nome not in self.playlists:
            self.playlists[nome] = []
            return True
        return False

    def adicionar_na_playlist(self, nome, caminho):
        if nome in self.playlists and caminho not in self.playlists[nome]:
            self.playlists[nome].append(caminho)
            return True
        return False

    def remover_da_playlist(self, nome, indice):
        if nome in self.playlists and 0 <= indice < len(self.playlists[nome]):
            del self.playlists[nome][indice]
            return True
        return False

    def ordenar_playlist(self, nome, criterio='titulo'):
        from biblioteca import Musica
        if nome in self.playlists:
            self.playlists[nome].sort(key=lambda c: Musica(c).metadados.get(criterio, '').lower())

    def salvar_estado(self):
        try:
            with open(ESTADO_PLAYER, 'w', encoding='utf-8') as f:
                json.dump({
                    'playlists': self.playlists,
                    'favoritos': self.favoritos
                }, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao salvar estado: {str(e)}")
            return False

    def carregar_estado(self):
        try:
            with open(ESTADO_PLAYER, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            self.playlists = dados.get('playlists', {})
            self.favoritos = dados.get('favoritos', [])
            return True
        except FileNotFoundError:
            self.playlists = {}
            self.favoritos = []
            return False
        except Exception as e:
            print(f"Erro ao carregar estado: {str(e)}")
            self.playlists = {}
            self.favoritos = []
            return False
