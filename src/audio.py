import pygame
import numpy as np
import os
import time
import math
import threading

class AudioPlayer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioPlayer, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'inicializado'):
            return
        pygame.mixer.init(frequency=44100)
        self.musica_atual = None
        self.pausado = False
        self.volume = 0.5
        self.tempo_inicio = 0
        self.duracao = 0
        self.lock = threading.Lock()
        pygame.init()
        self.EVENTO_FIM_MUSICA = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.EVENTO_FIM_MUSICA)
        pygame.mixer.music.set_volume(self.volume)
        self.inicializado = True

    def carregar_musica(self, caminho):
        with self.lock:
            if os.path.exists(caminho):
                try:
                    pygame.mixer.music.load(caminho)
                    self.musica_atual = caminho
                    self.tempo_inicio = time.time()
                    self.pausado = False
                    som = pygame.mixer.Sound(caminho)
                    self.duracao = som.get_length()
                    return True
                except Exception as e:
                    print(f"Erro ao carregar música: {e}")
            else:
                print("Arquivo não encontrado:", caminho)
            return False

    def play_pause(self):
        with self.lock:
            if not pygame.mixer.music.get_busy() and not self.pausado:
                pygame.mixer.music.play()
                self.tempo_inicio = time.time()
            elif self.pausado:
                pygame.mixer.music.unpause()
                self.pausado = False
            else:
                pygame.mixer.music.pause()
                self.pausado = True

    def parar(self):
        with self.lock:
            pygame.mixer.music.stop()
            self.pausado = False

    def setar_volume(self, vol):
        with self.lock:
            self.volume = max(0.0, min(1.0, float(vol)))
            pygame.mixer.music.set_volume(self.volume)
            return self.volume

    def get_volume(self):
        return self.volume

    def get_progresso(self):
        if not self.musica_atual:
            return 0
        if self.pausado:
            pos = pygame.mixer.music.get_pos()
            if pos == -1:
                return 0
            return pos / 1000
        if pygame.mixer.music.get_busy():
            elapsed = time.time() - self.tempo_inicio
            return min(elapsed, self.duracao)
        return 0

    def get_duracao(self):
        return self.duracao

    def get_nome(self):
        if not self.musica_atual:
            return ""
        return os.path.basename(self.musica_atual)

    def espectro(self):
        progresso = self.get_progresso()
        base = np.linspace(0, 10, 10)
        data = np.zeros(10)
        for i in range(10):
            freq1 = 0.5 + 0.5 * math.sin(progresso * 0.2 + i * 0.3)
            freq2 = 0.7 + 0.3 * math.cos(progresso * 0.1 + i * 0.5)
            amp1 = 0.6 + 0.4 * math.sin(progresso * 0.3 + i * 0.2)
            amp2 = 0.5 + 0.5 * math.cos(progresso * 0.4 + i * 0.1)
            data[i] = abs(amp1 * math.sin(freq1 * progresso + i) + amp2 * math.cos(freq2 * progresso + i * 2))
        max_val = np.max(data)
        if max_val > 0:
            data = 5 * data / max_val
        return data

    def terminou(self):
        for event in pygame.event.get():
            if event.type == self.EVENTO_FIM_MUSICA:
                return True
        return False
