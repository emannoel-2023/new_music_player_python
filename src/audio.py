import pygame
import numpy as np
import os
import time
import math
import threading
import queue
from pydub import AudioSegment
try:
    from mutagen.mp3 import MP3
    from mutagen.wave import WAVE
    from mutagen.flac import FLAC
except ImportError:
    print("Mutagen não encontrado. A duração das músicas pode ser imprecisa para alguns formatos.")
    MP3 = WAVE = FLAC = None

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
        self._espectro_max = 1.0
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
        self._audio_segment = None
        self._espectro_anterior = None
        self._espectro_max = 1.0
        self._reset_counter = 0

        self.command_queue = queue.Queue()
        self._command_thread = threading.Thread(target=self._run_command_processor, daemon=True)
        self._command_thread.start()

    def add_observer(self, obs):
        self.observers.append(obs)

    def notify(self, evento):
        for obs in self.observers:
            obs.atualizar(evento)

    def _run_command_processor(self):
        """Loop que processa comandos da fila."""
        while True:
            command_item = None
            try:
                command, args, kwargs = self.command_queue.get(timeout=0.1)
                command_item = (command, args, kwargs)
                
                if command == 'load':
                    self._carregar_musica_internal(args[0])
                elif command == 'play':
                    self._play_internal()
                elif command == 'play_pause':
                    self._play_pause_internal()
                elif command == 'pause':
                    self._pause_internal()
                elif command == 'resume':
                    self._resume_internal()
                elif command == 'stop':
                    self._parar_internal()
                elif command == 'set_volume':
                    self._setar_volume_internal(args[0])
                elif command == 'set_equalizacao':
                    self._set_equalizacao_internal(args[0], args[1], args[2])
                elif command == 'quit': # Comando para parar o thread
                    return # Sai do loop do thread
            except queue.Empty:
                pass
            except Exception as e:
                print(f"Erro no thread de comando do áudio: {e}")
            finally:
                if command_item is not None:
                    self.command_queue.task_done()

    def _carregar_musica_internal(self, caminho):
        if os.path.exists(caminho):
            try:
                pygame.mixer.music.load(caminho)
                self.musica_atual = caminho
                self.tempo_inicio = time.time()
                self.pausado = False
                self._get_and_set_duration(caminho)
                try:
                    self._audio_segment = AudioSegment.from_file(caminho)
                except Exception as e:
                    print("Erro ao carregar AudioSegment (para espectro):", e)
                    self._audio_segment = None
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
        self.duracao = 0
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
            else:
                print(f"Formato de áudio para {caminho} não suportado por mutagen ou não especificado. Duração pode ser imprecisa.")
                if self._audio_segment:
                    self.duracao = len(self._audio_segment) / 1000.0
                else:
                    self.duracao = 0
        except Exception as e:
            print(f"Erro ao obter duração da música {caminho} com mutagen: {e}")
            self.duracao = 0

    def _play_internal(self):
        if self.musica_atual:
            if self.pausado:
                pygame.mixer.music.unpause()
                self.pausado = False
                self.notify('unpause')
            elif not pygame.mixer.music.get_busy():
                pygame.mixer.music.play()
                self.tempo_inicio = time.time()
                self.pausado = False
                self.notify('play')
        else:
            print("Nenhuma música carregada para tocar.")

    def _play_pause_internal(self):
        if self.musica_atual:
            if pygame.mixer.music.get_busy() and not self.pausado:
                self._pause_internal()
            elif self.pausado:
                self._resume_internal()
            elif not pygame.mixer.music.get_busy() and not self.pausado:
                self._play_internal()
            self.notify('play_pause')

    def _pause_internal(self):
        if pygame.mixer.music.get_busy() and not self.pausado:
            pygame.mixer.music.pause()
            self.pausado = True
            self.notify('pause')

    def _resume_internal(self):
        if self.pausado:
            pygame.mixer.music.unpause()
            self.pausado = False
            self.notify('unpause')

    def _parar_internal(self):
        pygame.mixer.music.stop()
        self.pausado = False
        self._espectro_anterior = None
        self._espectro_max = 1.0
        self._reset_counter = 0
        self.notify('parar')

    def _setar_volume_internal(self, vol):
        self.volume = max(0.0, min(1.0, float(vol)))
        pygame.mixer.music.set_volume(self.volume)
        self.notify('volume')

    def _set_equalizacao_internal(self, grave, medio, agudo):
        self.equalizacao = {'grave': grave, 'medio': medio, 'agudo': agudo}
        self.notify('equalizacao')


    def carregar_musica(self, caminho):
        self.command_queue.put(('load', (caminho,), {}))

    def play(self):
        self.command_queue.put(('play', (), {}))

    def play_pause(self):
        self.command_queue.put(('play_pause', (), {}))

    def pause(self):
        self.command_queue.put(('pause', (), {}))

    def resume(self):
        self.command_queue.put(('resume', (), {}))

    def parar(self):
        self.command_queue.put(('stop', (), {}))

    def setar_volume(self, vol):
        self.command_queue.put(('set_volume', (vol,), {}))

    def set_equalizacao(self, grave, medio, agudo):
        self.command_queue.put(('set_equalizacao', (grave, medio, agudo), {}))

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
        return pygame.mixer.music.get_busy() and not self.pausado

    def check_events(self):
        for event in pygame.event.get():
            if event.type == self.EVENTO_FIM_MUSICA:
                self.notify('musica_terminada')
                self.pausado = False
                
    def set_equalizacao(self, grave, medio, agudo):
        self.equalizacao = {'grave': grave, 'medio': medio, 'agudo': agudo}
        self.notify('equalizacao')

    def quit(self):
        """Envia um comando para o thread de áudio parar e desinicializa o pygame mixer."""
        self.command_queue.put(('quit', (), {}))
        self._command_thread.join(timeout=1)
        pygame.mixer.quit()
        pygame.quit()