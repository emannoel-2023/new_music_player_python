# playlist.py
import os
import json
from constants import PASTA_DADOS # Importa PASTA_DADOS do arquivo centralizado

# Os caminhos agora usam a PASTA_DADOS centralizada
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
            self.salvar_estado() # Salva após a criação
            return True
        return False

    def adicionar_na_playlist(self, nome, caminho):
        if nome in self.playlists and caminho not in self.playlists[nome]:
            self.playlists[nome].append(caminho)
            self.salvar_estado() # Salva após adicionar
            return True
        return False

    def remover_da_playlist(self, nome, indice):
        if nome in self.playlists and 0 <= indice < len(self.playlists[nome]):
            del self.playlists[nome][indice]
            self.salvar_estado() # Salva após remover
            return True
        return False

    def ordenar_playlist(self, nome, criterio='titulo'):
        from biblioteca import Musica # Assumindo que Musica está disponível e é necessária
        if nome in self.playlists:
            self.playlists[nome].sort(key=lambda c: Musica(c).metadados.get(criterio, '').lower())
            self.salvar_estado() # Salva após ordenar

    def adicionar_favorito(self, caminho_musica):
        if caminho_musica not in self.favoritos:
            self.favoritos.append(caminho_musica)
            self.salvar_estado()
            return True
        return False

    def remover_favorito(self, caminho_musica):
        if caminho_musica in self.favoritos:
            self.favoritos.remove(caminho_musica)
            self.salvar_estado()
            return True
        return False

    def is_favorito(self, caminho_musica):
        return caminho_musica in self.favoritos

    def salvar_estado(self):
        try:
            os.makedirs(PASTA_DADOS, exist_ok=True) # Garante que a pasta de dados existe
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