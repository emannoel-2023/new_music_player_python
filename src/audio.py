import pygame
import numpy as np
import os
import time
import math
import threading
from pydub import AudioSegment

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
        self._espectro_max = 1.0  # máximo histórico para normalização adaptativa
        self.volume = 0.5
        self.tempo_inicio = 0
        self.duracao = 0
        self.lock = threading.Lock()
        self.observers = []
        self.equalizacao = {'grave': 0, 'medio': 0, 'agudo': 0}
        pygame.init()
        self.EVENTO_FIM_MUSICA = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.EVENTO_FIM_MUSICA)
        pygame.mixer.music.set_volume(self.volume)
        self.inicializado = True
        self._audio_segment = None  # Para cache do AudioSegment
        
        # Inicializar variáveis do espectro
        self._espectro_anterior = None
        self._espectro_max = 1.0
        self._reset_counter = 0

    def add_observer(self, obs):
        self.observers.append(obs)

    def notify(self, evento):
        for obs in self.observers:
            obs.atualizar(evento)

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
                    # Carrega o AudioSegment para espectro
                    try:
                        self._audio_segment = AudioSegment.from_file(caminho)
                    except Exception as e:
                        print("Erro ao carregar AudioSegment:", e)
                        self._audio_segment = None
                    
                    # Reset das variáveis do espectro ao carregar nova música
                    self._espectro_anterior = None
                    self._espectro_max = 1.0
                    self._reset_counter = 0
                    
                    self.notify('carregar_musica')
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
            self.notify('play_pause')

    def parar(self):
        with self.lock:
            pygame.mixer.music.stop()
            self.pausado = False
            # Reset das variáveis do espectro ao parar
            self._espectro_anterior = None
            self._espectro_max = 1.0
            self._reset_counter = 0
            self.notify('parar')

    def setar_volume(self, vol):
        with self.lock:
            self.volume = max(0.0, min(1.0, float(vol)))
            pygame.mixer.music.set_volume(self.volume)
            self.notify('volume')
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

    def get_audio_samples(self, num_samples=2048):
        """
        Retorna um array numpy de samples do ponto atual da música, para FFT do espectro.
        Suporta qualquer formato de áudio lido pelo pydub/ffmpeg.
        """
        if self._audio_segment is None:
            return None
        progresso = self.get_progresso()
        ms_pos = int(progresso * 1000)
        frame_rate = self._audio_segment.frame_rate
        start_ms = max(0, ms_pos - int(1000 * num_samples / frame_rate))
        end_ms = ms_pos
        segmento = self._audio_segment[start_ms:end_ms]
        if len(segmento) == 0:
            return None
        samples = segmento.get_array_of_samples()
        arr = np.array(samples).astype(np.float32)
        if self._audio_segment.channels > 1:
            arr = arr[::self._audio_segment.channels]  # Pega só um canal
        if len(arr) > num_samples:
            arr = arr[-num_samples:]
        elif len(arr) < num_samples:
            arr = np.pad(arr, (num_samples - len(arr), 0))
        return arr

    def espectro(self, num_barras=40):
        try:
            samples = self.get_audio_samples(4096)
            if samples is not None and len(samples) > 0:
                # Aplica janela Hanning
                window = np.hanning(len(samples))
                windowed_samples = samples * window
                
                # FFT
                fft = np.abs(np.fft.rfft(windowed_samples))
                
                # Melhora detecção de voz (faixa 300Hz-3kHz mais sensível)
                freqs = np.fft.rfftfreq(len(samples), 1/44100)  # Assumindo 44.1kHz
                
                # Agrupa em bandas mais inteligentes
                # Graves: 20-250Hz, Médios: 250Hz-4kHz (voz), Agudos: 4kHz+
                bandas = []
                
                # Distribui as barras: 30% graves, 50% médios (voz), 20% agudos
                graves_barras = int(num_barras * 0.3)
                medios_barras = int(num_barras * 0.5) 
                agudos_barras = num_barras - graves_barras - medios_barras
                
                # Graves (20-250Hz)
                graves_idx = np.where((freqs >= 20) & (freqs <= 250))[0]
                if len(graves_idx) > 0:
                    step = max(1, len(graves_idx) // graves_barras)
                    for i in range(graves_barras):
                        start = i * step
                        end = min((i + 1) * step, len(graves_idx))
                        if start < len(graves_idx):
                            banda = np.mean(fft[graves_idx[start:end]]) if end > start else 0
                            bandas.append(banda)
                
                # Médios/Voz (250Hz-4kHz) - Mais sensível
                medios_idx = np.where((freqs >= 250) & (freqs <= 4000))[0]
                if len(medios_idx) > 0:
                    step = max(1, len(medios_idx) // medios_barras)
                    for i in range(medios_barras):
                        start = i * step
                        end = min((i + 1) * step, len(medios_idx))
                        if start < len(medios_idx):
                            banda = np.mean(fft[medios_idx[start:end]]) * 1.5  # Amplifica voz
                            bandas.append(banda)
                
                # Agudos (4kHz+)
                agudos_idx = np.where(freqs >= 4000)[0]
                if len(agudos_idx) > 0:
                    step = max(1, len(agudos_idx) // agudos_barras)
                    for i in range(agudos_barras):
                        start = i * step
                        end = min((i + 1) * step, len(agudos_idx))
                        if start < len(agudos_idx):
                            banda = np.mean(fft[agudos_idx[start:end]]) if end > start else 0
                            bandas.append(banda)
                
                # Garante o número correto de barras
                while len(bandas) < num_barras:
                    bandas.append(0)
                bandas = np.array(bandas[:num_barras])
                
                # Reset periódico para evitar lentidão acumulada
                self._reset_counter += 1
                if self._reset_counter > 1000:  # Reset a cada ~30 segundos
                    self._espectro_max = 1.0
                    self._espectro_anterior = None
                    self._reset_counter = 0
                
                # Inicializa _espectro_anterior se não existir
                if self._espectro_anterior is None:
                    self._espectro_anterior = np.zeros(num_barras)
                
                # Suavização mínima para máxima responsividade
                # Quase sem suavização - máxima responsividade
                alpha = 0.95
                bandas = alpha * bandas + (1 - alpha) * self._espectro_anterior
                
                self._espectro_anterior = bandas.copy()
                
                # Normalização simplificada e rápida
                bloco_max = np.max(bandas)
                # Atualização muito rápida do máximo
                self._espectro_max = max(bloco_max, self._espectro_max * 0.98)
                
                # Normalização direta
                if self._espectro_max > 0:
                    bandas_norm = bandas / self._espectro_max
                else:
                    bandas_norm = bandas
                
                # Compressão suave para melhor visibilidade
                bandas_norm = np.power(np.clip(bandas_norm, 0, 1), 0.6)
                
                # Scaling para altura 6
                barras = bandas_norm * 6
                barras = np.clip(barras, 0, 6)
                
                return barras
            else:
                # Fallback silencioso
                return np.zeros(num_barras)
                
        except Exception as e:
            print(f"Erro no espectro: {e}")
            # Em caso de erro, retorna array vazio
            return np.zeros(num_barras)

    def terminou(self):
        for event in pygame.event.get():
            if event.type == self.EVENTO_FIM_MUSICA:
                return True
        return False

    def set_equalizacao(self, grave, medio, agudo):
        self.equalizacao = {'grave': grave, 'medio': medio, 'agudo': agudo}
        # Equalização real só é possível processando o áudio antes de tocar.
        # Aqui apenas armazena os valores para visualização.
        self.notify('equalizacao')