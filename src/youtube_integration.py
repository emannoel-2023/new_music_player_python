# youtube_integration.py
import subprocess
import os
import threading
import queue
import time

class YouTubeIntegration:
    def __init__(self, ui_message_queue):
        self.ui_message_queue = ui_message_queue
        self.mpv_process_handle = None 
        self._check_dependencies()

    def _display_message(self, message):
        """Enfileira uma mensagem para ser exibida na UI principal."""
        try:
            self.ui_message_queue.put_nowait(message)
        except queue.Full:
            pass

    def _check_dependencies(self):
        """Verifica se mpv e yt-dlp estão instalados e no PATH."""
        self.mpv_available = False
        self.ytdlp_available = False

        try:
            subprocess.run(['mpv', '--version'], capture_output=True, check=True, timeout=5)
            self.mpv_available = True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self._display_message("AVISO: 'mpv' não encontrado ou inacessível. Instale 'mpv' para reprodução do YouTube.")
            print("AVISO: 'mpv' não encontrado ou inacessível. Instale 'mpv' para reprodução do YouTube.")

        try:
            subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True, timeout=5)
            self.ytdlp_available = True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self._display_message("AVISO: 'yt-dlp' não encontrado ou inacessível. Instale 'yt-dlp' para reprodução do YouTube.")
            print("AVISO: 'yt-dlp' não encontrado ou inacessível. Instale 'yt-dlp' para reprodução do YouTube.")

    def play_url(self, url): 
        """
        Reproduz uma URL do YouTube (ou outra plataforma suportada pelo yt-dlp)
        usando mpv. Esta função BLOQUEIA o thread atual até que mpv encerre.
        """
        if not self.mpv_available:
            self._display_message("Erro: 'mpv' não está instalado ou não está no PATH. Não é possível reproduzir YouTube.")
            return False
        
        if not self.ytdlp_available:
            self._display_message("Erro: 'yt-dlp' não está instalado ou não está no PATH. Não é possível reproduzir YouTube.")
            return False

        # Define as dimensões da janela desejada.
        # Tente usar uma proporção 16:9 (por exemplo, 640x360, 800x450, 960x540)
        # para evitar distorção visual, já que --geometry não a mantém automaticamente.
        window_width = 800
        window_height = 450 

        command = ['mpv', url]
        # Usando --geometry para forçar o tamanho da janela
        # O '!' no final de WxH força a janela a ter EXATAMENTE este tamanho,
        # ignorando a proporção do vídeo. Se você preferir que a proporção seja mantida
        # dentro de uma caixa WxH, remova o '!'.
        command.append(f'--geometry={window_width}x{window_height}')
        # Se você quiser que a janela apareça em uma posição específica (por exemplo, centro)
        # pode adicionar um offset. Ex: `--geometry=800x450+C` para centralizar.
        # Ou `--geometry=800x450+50+50` para 50 pixels da borda superior e esquerda.


        try:
            self.mpv_process_handle = subprocess.Popen(command)
            self.mpv_process_handle.wait()
            return True
        except FileNotFoundError:
            self._display_message("Erro: 'mpv' não encontrado. Certifique-se de que está instalado e no PATH.")
        except Exception as e:
            self._display_message(f"Erro ao reproduzir URL do YouTube: {e}")
        finally:
            self.mpv_process_handle = None
        return False

    def stop_player(self):
        """Tenta parar o processo mpv se ainda estiver ativo (para encerramento do app)."""
        if self.mpv_process_handle and self.mpv_process_handle.poll() is None:
            try:
                self.mpv_process_handle.terminate()
                self.mpv_process_handle.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.mpv_process_handle.kill()
            except Exception as e:
                print(f"Erro ao encerrar mpv: {e}")
        self.mpv_process_handle = None

    def is_playing(self):
        return False
    
    def is_loading(self):
        return False