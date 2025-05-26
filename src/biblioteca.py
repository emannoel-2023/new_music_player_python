import os
from mutagen import File

class Musica:
    def __init__(self, caminho):
        self.caminho = caminho
        self.metadados = self.extrair_metadados()

    def extrair_metadados(self):
        try:
            audio = File(self.caminho, easy=True)
            duracao = 0
            audio_full = File(self.caminho)
            if audio_full and audio_full.info:
                duracao = audio_full.info.length
            return {
                'artista': audio.get('artist', ['Desconhecido'])[0],
                'album': audio.get('album', ['Desconhecido'])[0],
                'genero': audio.get('genre', ['Desconhecido'])[0],
                'titulo': audio.get('title', [os.path.basename(self.caminho)])[0],
                'duracao': duracao
            }
        except Exception:
            return {
                'artista': 'Desconhecido',
                'album': 'Desconhecido',
                'genero': 'Desconhecido',
                'titulo': os.path.basename(self.caminho),
                'duracao': 0
            }

class NodoMusica:
    def __init__(self, musica):
        self.musica = musica
        self.esq = None
        self.dir = None

class ArvoreMusicas:
    def __init__(self):
        self.raiz = None

    def inserir(self, musica):
        def _inserir(no, musica):
            if no is None:
                return NodoMusica(musica)
            if musica.metadados['titulo'] < no.musica.metadados['titulo']:
                no.esq = _inserir(no.esq, musica)
            else:
                no.dir = _inserir(no.dir, musica)
            return no
        self.raiz = _inserir(self.raiz, musica)

    def buscar(self, titulo):
        def _buscar(no, titulo):
            if no is None:
                return None
            if titulo == no.musica.metadados['titulo']:
                return no.musica
            elif titulo < no.musica.metadados['titulo']:
                return _buscar(no.esq, titulo)
            else:
                return _buscar(no.dir, titulo)
        return _buscar(self.raiz, titulo)

class Biblioteca:
    def __init__(self):
        self.musicas = []
        self.arvore = ArvoreMusicas()

    def carregar_diretorio(self, caminho):
        extensoes = ['.mp3', '.wav', '.flac', '.ogg']
        try:
            arquivos = os.listdir(caminho)
            self.musicas = [Musica(os.path.join(caminho, f))
                            for f in arquivos if os.path.splitext(f)[1].lower() in extensoes]
            for musica in self.musicas:
                self.arvore.inserir(musica)
            return self.musicas
        except Exception as e:
            print(f"Erro ao carregar diretório: {e}")
            return []

    def listar_musicas(self):
        return self.musicas

    def listar_por(self, chave):
        grupos = {}
        for musica in self.musicas:
            valor = musica.metadados.get(chave, 'Desconhecido')
            if not valor or not str(valor).strip():
                valor = 'Desconhecido'
            grupos.setdefault(valor, []).append(musica)
        return grupos

    def buscar(self, termo):
        return [m for m in self.musicas if termo.lower() in m.metadados['titulo'].lower()]

    def filtrar(self, chave, valor):
        return [m for m in self.musicas if m.metadados.get(chave, '').lower() == valor.lower()]

    def buscar_arvore(self, titulo):
        return self.arvore.buscar(titulo)
