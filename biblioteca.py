import os

class Biblioteca:
    def __init__(self):
        self.musicas = []

    def carregar_diretorio(self, caminho):
        extensoes = ['.mp3', '.wav', '.flac', '.ogg']
        try:
            arquivos = os.listdir(caminho)
            self.musicas = [os.path.join(caminho, f) for f in arquivos if os.path.splitext(f)[1].lower() in extensoes]
            self.musicas.sort()
            return self.musicas
        except Exception as e:
            print(f"Erro ao carregar diretório: {e}")
            return []

    def listar_musicas(self):
        return self.musicas
