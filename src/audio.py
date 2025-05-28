import pygame
import numpy as np
import os
import time
import math
import threading
from pydub import AudioSegment
# Importe mutagen para obter a duração real da música
try:
    from mutagen.mp3 import MP3
    from mutagen.wave import WAVE
    from mutagen.flac import FLAC
    # Adicione outros formatos se necessário (e.g., Ogg for .ogg, etc.)
except ImportError:
    print("Mutagen não encontrado. A duração das músicas pode ser imprecisa para alguns formatos.")
    MP3 = WAVE = FLAC = None # Define como None se não estiver disponível

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
        self.duracao = 0 # Duração da música em segundos (obtida por mutagen)
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
                    
                    self._get_and_set_duration(caminho) # Obtém a duração usando mutagen ou similar
                    
                    # Carrega o AudioSegment para espectro
                    try:
                        self._audio_segment = AudioSegment.from_file(caminho)
                    except Exception as e:
                        print("Erro ao carregar AudioSegment (para espectro):", e)
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

    def _get_and_set_duration(self, caminho):
        """Tenta obter a duração da música usando mutagen."""
        self.duracao = 0 # Reseta a duração
        try:
            if caminho.lower().endswith('.mp3') and MP3:
                audio = MP3(caminho)
                self.duracao = audio.info.length
            elif caminho.lower().endswith('.wav') and WAVE:
                audio = WAVE(caminho)
                self.duracao = audio.info.length
            elif caminho.lower().endswith('.flac') and FLAC:
                audio = FLAC(caminho)
                self.duracao = audio.info.length
            # Adicione outros formatos que você quer suportar com mutagen
            else:
                # Fallback se mutagen não pode ler ou formato não é explicitamente tratado
                # Aqui você pode tentar uma estimativa ou deixar como 0
                print(f"Formato de áudio para {caminho} não suportado por mutagen ou não especificado. Duração pode ser imprecisa.")
                # Se não puder obter a duração exata, uma alternativa é tentar usar pydub para isso
                if self._audio_segment:
                    self.duracao = len(self._audio_segment) / 1000.0
                else:
                    self.duracao = 0 # Duração desconhecida
        except Exception as e:
            print(f"Erro ao obter duração da música {caminho} com mutagen: {e}")
            self.duracao = 0 # Em caso de erro, define como 0

    def play(self):
        """Inicia a reprodução da música carregada. Se estiver pausada, despausa. Se não estiver tocando, inicia."""
        with self.lock:
            if self.musica_atual:
                if self.pausado: # Se está pausado, despausa
                    pygame.mixer.music.unpause()
                    self.pausado = False
                    self.notify('unpause')
                elif not pygame.mixer.music.get_busy(): # Se não está tocando, inicia
                    pygame.mixer.music.play()
                    self.tempo_inicio = time.time()
                    self.pausado = False
                    self.notify('play')
            else:
                print("Nenhuma música carregada para tocar.")

    def play_pause(self):
        with self.lock:
            if self.musica_atual:
                if pygame.mixer.music.get_busy() and not self.pausado:
                    self.pause() # Chama o novo método pause
                elif self.pausado:
                    self.resume() # Chama o novo método resume
                elif not pygame.mixer.music.get_busy() and not self.pausado:
                    # Se não está tocando e não está pausado (pode ter sido parado ou recém carregado)
                    # Chamar play() para iniciar do zero.
                    self.play() 
                self.notify('play_pause')

    def pause(self): # Método explícito para pausar
        with self.lock:
            if pygame.mixer.music.get_busy() and not self.pausado:
                pygame.mixer.music.pause()
                self.pausado = True
                self.notify('pause')

    def resume(self): # Método explícito para resumir
        with self.lock:
            if self.pausado:
                pygame.mixer.music.unpause()
                self.pausado = False
                self.notify('unpause')
            # Se não estava pausado, não faz nada ou inicia do zero se a intenção for essa
            # A lógica atual do play() já lida com iniciar se não estiver tocando.

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
        
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms == -1: 
            return 0
        return pos_ms / 1000.0 

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
        
        progresso_segundos = self.get_progresso()
        ms_pos = int(progresso_segundos * 1000)

        sample_length_ms = int(1000 * num_samples / self._audio_segment.frame_rate)
        start_ms = max(0, ms_pos - sample_length_ms)
        end_ms = ms_pos
        
        segmento = self._audio_segment[start_ms:end_ms]
        
        if len(segmento) == 0:
            return None
        
        samples = segmento.get_array_of_samples()
        arr = np.array(samples).astype(np.float32)
        
        if self._audio_segment.channels > 1:
            arr = arr[::self._audio_segment.channels] 
        
        if len(arr) > num_samples:
            arr = arr[-num_samples:] 
        elif len(arr) < num_samples:
            arr = np.pad(arr, (num_samples - len(arr), 0))
            
        return arr

    def espectro(self, num_barras=40):
        try:
            samples = self.get_audio_samples(4096)
            if samples is not None and len(samples) > 0:
                window = np.hanning(len(samples))
                windowed_samples = samples * window
                
                fft = np.abs(np.fft.rfft(windowed_samples))
                
                freqs = np.fft.rfftfreq(len(samples), 1/44100) 
                
                barras = self._get_spectrum_bands(fft, freqs, num_barras)
                
                self._reset_counter += 1
                if self._reset_counter > 200:  
                    self._espectro_max = 1.0
                    self._espectro_anterior = None
                    self._reset_counter = 0
                
                if self._espectro_anterior is None or len(self._espectro_anterior) != num_barras:
                    self._espectro_anterior = np.zeros(num_barras)
                
                alpha_suavizacao = 0.6 
                barras_suavizadas = alpha_suavizacao * barras + (1 - alpha_suavizacao) * self._espectro_anterior
                self._espectro_anterior = barras_suavizadas.copy()
                
                current_max = np.max(barras_suavizadas)
                if current_max > self._espectro_max:
                    self._espectro_max = current_max
                else:
                    self._espectro_max *= 0.98 
                
                if self._espectro_max > 0:
                    barras_norm = barras_suavizadas / self._espectro_max
                else:
                    barras_norm = barras_suavizadas
                
                barras_final = np.power(np.clip(barras_norm, 0, 1), 0.5) 
                
                barras_final = barras_final * 6
                
                return barras_final.tolist() 
            else:
                return [0] * num_barras 
                
        except Exception as e:
            print(f"Erro no espectro: {e}")
            return [0] * num_barras

    def _get_spectrum_bands(self, fft_data, freqs, num_bands):
        """
        Agrupa os dados da FFT em bandas de frequência para o espectro visual.
        Usa uma escala logarítmica para as frequências para melhor percepção humana.
        """
        if num_bands == 0:
            return np.array([])

        min_freq = 20     
        max_freq = 20000  
        
        freq_indices = np.where((freqs >= min_freq) & (freqs <= max_freq))[0]
        if len(freq_indices) == 0:
            return np.zeros(num_bands)

        log_min_freq = np.log10(min_freq)
        log_max_freq = np.log10(max_freq)
        log_steps = np.log10(np.linspace(10**log_min_freq, 10**log_max_freq, num_bands + 1))
        
        bands_output = np.zeros(num_bands)
        
        for i in range(num_bands):
            f_low = 10**log_steps[i]
            f_high = 10**log_steps[i+1]
            
            band_freq_indices = np.where((freqs >= f_low) & (freqs < f_high))[0]
            
            if len(band_freq_indices) > 0:
                bands_output[i] = np.sum(fft_data[band_freq_indices])
            else:
                bands_output[i] = 0
        
        for i in range(num_bands):
            f_center = 10**((log_steps[i] + log_steps[i+1])/2)
            if 250 <= f_center <= 4000:
                bands_output[i] *= 1.5 
        
        return bands_output

    def is_playing(self):
        """
        Verifica se a música está tocando ativamente (não pausada e o mixer está busy).
        """
        return pygame.mixer.music.get_busy() and not self.pausado

    def check_events(self):
        """
        Processa eventos do Pygame, como o evento de fim de música.
        Este método DEVE ser chamado no loop principal da UI.
        """
        for event in pygame.event.get():
            if event.type == self.EVENTO_FIM_MUSICA:
                self.notify('musica_terminada')
                self.pausado = False
                
    def set_equalizacao(self, grave, medio, agudo):
        self.equalizacao = {'grave': grave, 'medio': medio, 'agudo': agudo}
        self.notify('equalizacao')