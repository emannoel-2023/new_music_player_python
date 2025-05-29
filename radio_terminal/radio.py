import os
import sys
import json
import socket
import tempfile
import threading
import subprocess
import time
import locale
import curses
from urllib.parse import urlparse, quote
import requests
import psutil
import pickle
from collections import deque
from datetime import datetime
from threading import Thread, Lock, Event
import atexit
import logging
import queue

# Importações específicas para Windows, se estiver no Windows
if sys.platform == 'win32':
    try:
        import win32file
        import pywintypes
        import win32pipe # Importação adicionada
    except ImportError:
        logging.error("pywin32 library not found. Please install it (pip install pywin32) for Windows IPC functionality.")
        win32file = None
        pywintypes = None
        win32pipe = None

# Configuração básica de logging
logging.basicConfig(filename='radio_debug.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class NetworkMonitor:
    def __init__(self):
        self.lock = Lock()
        self.history = deque(maxlen=60)
        self.last_io = psutil.net_io_counters()
        self.last_time = time.time()

    def update(self):
        with self.lock:
            current_io = psutil.net_io_counters()
            current_time = time.time()
            time_delta = current_time - self.last_time
            if time_delta > 0:
                bytes_recv = (current_io.bytes_recv - self.last_io.bytes_recv) / time_delta
                bytes_sent = (current_io.bytes_sent - self.last_io.bytes_sent) / time_delta
                self.history.append({
                    'time': datetime.now(),
                    'bytes_recv': bytes_recv / 1024,
                    'bytes_sent': bytes_sent / 1024
                })
            self.last_io = current_io
            self.last_time = current_time

    def get_current_usage(self):
        with self.lock:
            if not self.history:
                return {'bytes_recv': 0, 'bytes_sent': 0}
            return self.history[-1]

class ScrollingText:
    def __init__(self, text="", width=60, scroll_speed=0.3):
        self.text = text
        self.width = width
        self.scroll_speed = scroll_speed
        self.position = 0
        self.last_update = time.time()
        self.pause_at_end = 1.0
        self.paused_since = 0

    def update(self, new_text=None):
        original_text_changed = False
        if new_text is not None and new_text != self.text:
            self.text = new_text
            self.position = 0
            self.last_update = time.time()
            self.paused_since = 0
            original_text_changed = True

        current_time = time.time()
        
        if len(self.text) > self.width:
            if self.paused_since > 0:
                if current_time - self.paused_since > self.pause_at_end:
                    self.paused_since = 0
                else:
                    return original_text_changed
            
            if current_time - self.last_update > self.scroll_speed:
                self.position = (self.position + 1) % len(self.text)
                if self.position == 0:
                    self.paused_since = current_time
                self.last_update = current_time
                return True
        
        return original_text_changed

    def get_display_text(self):
        if len(self.text) <= self.width:
            return self.text.ljust(self.width)
        padded_text = self.text + " • " + self.text
        return padded_text[self.position:self.position + self.width]

def get_radio_name_from_url(url):
    try:
        netloc = urlparse(url).netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        netloc = netloc.split(':')[0]
        return netloc
    except Exception:
        logging.exception("Error getting radio name from URL")
        return "Unknown Radio"

def get_radio_name_from_api(url):
    try:
        api_url = f"https://api.radio-browser.info/json/stations/byurl/{quote(url, safe='')}"
        resp = requests.get(api_url, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if data and "name" in data[0]:
                return data[0]["name"]
    except Exception:
        logging.exception("Error getting radio name from API")
    return None

class MPVIPCClient(Thread):
    def __init__(self, socket_path, on_metadata_update):
        super().__init__(daemon=True)
        self.socket_path = socket_path
        self.on_metadata_update = on_metadata_update
        self.sock = None
        self.running = True
        self._response_lock = Lock()
        self._request_id = 0
        self._responses = {}
        self._buffer = b""
        self._command_queue = queue.Queue()
        self._connect_event = Event()

    def _connect(self):
        if sys.platform == 'win32':
            if win32file is None or pywintypes is None:
                logging.error("win32file or pywintypes not available. Cannot connect to Win32 pipe.")
                return False
            try:
                self.sock = win32file.CreateFile(
                    self.socket_path,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0, None,
                    win32file.OPEN_EXISTING,
                    0, None
                )
                logging.info(f"Connected to Win32 IPC pipe: {self.socket_path}")
                self._connect_event.set()
                return True
            except Exception as e:
                logging.warning(f"Failed to connect to Win32 IPC pipe initially: {e}")
                self.sock = None
                return False
        else:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                self.sock.connect(self.socket_path)
                self.sock.setblocking(False)
                logging.info(f"Connected to Unix IPC socket: {self.socket_path}")
                self._connect_event.set()
                return True
            except Exception as e:
                logging.warning(f"Failed to connect to Unix IPC socket: {e}")
                self.sock = None
                return False

    def run(self):
        while self.running and not self._connect_event.is_set():
            if not self._connect():
                time.sleep(0.2)
        
        if not self.sock:
            logging.error("MPVIPCClient failed to establish connection.")
            self.running = False
            return

        while self.running and self.sock:
            try:
                if sys.platform == 'win32':
                    # Usar PeekNamedPipe para verificar se há dados antes de tentar ReadFile
                    if win32pipe is None: # Verificação para evitar erro se win32pipe não foi importado
                        logging.error("win32pipe not available. Cannot use PeekNamedPipe.")
                        self.running = False
                        break
                    
                    bytes_available = win32pipe.PeekNamedPipe(self.sock, 0)[1] # bytes_read_from_current_message
                    
                    if bytes_available > 0:
                        res, data = win32file.ReadFile(self.sock, 4096)
                        if res == 0 and data:
                            self._buffer += data
                            self._process_buffer()
                        elif res != 0:
                            logging.warning(f"Win32 ReadFile returned non-zero result: {res}")
                            time.sleep(0.005)
                        else:
                            time.sleep(0.005)
                    else:
                        time.sleep(0.005) # Nenhum dado disponível, durma um pouco para não busy-wait

                else: # Unix
                    data = self.sock.recv(4096)
                    if not data:
                        logging.warning("MPV IPC socket disconnected (no data).")
                        break
                    self._buffer += data
                    self._process_buffer()

                # Processar comandos da fila de escrita (do mesmo thread)
                while not self._command_queue.empty():
                    cmd_data = self._command_queue.get_nowait()
                    if sys.platform == 'win32':
                        win32file.WriteFile(self.sock, cmd_data)
                        logging.debug(f"IPC Client (Win): Wrote command from queue.")
                    else:
                        self.sock.sendall(cmd_data)
                        logging.debug(f"IPC Client (Unix): Wrote command from queue.")
                    self._command_queue.task_done()
                
            except BlockingIOError:
                time.sleep(0.005)
            except Exception as e:
                if sys.platform == 'win32' and isinstance(e, pywintypes.error) and e.winerror == 109:
                    logging.warning("MPV IPC pipe broken, attempting to reconnect...")
                    self.close_socket_handle()
                    self._connect_event.clear()
                    if not self._connect():
                        self.running = False
                elif sys.platform != 'win32' and isinstance(e, BrokenPipeError):
                    logging.warning("MPV IPC socket broken, attempting to reconnect...")
                    self.close_socket_handle()
                    self._connect_event.clear()
                    if not self._connect():
                        self.running = False
                else:
                    logging.exception(f"Error in MPVIPCClient run loop: {e}")
                    self.running = False

        logging.info("MPVIPCClient run loop finished.")
        self.running = False
        self.close_socket_handle()

    def _process_buffer(self):
        while b'\n' in self._buffer:
            line, self._buffer = self._buffer.split(b'\n', 1)
            self._handle_json_line(line)

    def _handle_json_line(self, line):
        try:
            msg = json.loads(line.decode('utf-8'))
            if 'event' in msg and msg['event'] == 'property-change':
                if msg.get('name') in ['metadata', 'icy-metadata', 'media-title']:
                    metadata = msg.get('data')
                    title = None
                    if isinstance(metadata, dict):
                        title = metadata.get('icy-title') or metadata.get('title') or metadata.get('media-title')
                    elif isinstance(metadata, str):
                        title = metadata
                    if title:
                        self.on_metadata_update(title)
            elif 'request_id' in msg:
                with self._response_lock:
                    self._responses[msg['request_id']] = msg
        except json.JSONDecodeError:
            logging.warning(f"Could not decode JSON from IPC: {line.decode('utf-8', errors='ignore')}")
        except Exception:
            logging.exception(f"Error handling parsed IPC JSON: {line.decode('utf-8', errors='ignore')}")

    def send_command(self, command, args=None):
        with self._response_lock:
            self._request_id += 1
            req_id = self._request_id
            msg = {'command': [command] + (args if args else []), 'request_id': req_id}
            data = (json.dumps(msg) + '\n').encode('utf-8')
            logging.debug(f"Enqueuing IPC command: {msg['command'][0]} (ID: {req_id})")
            self._command_queue.put(data)
            return req_id

    def observe_property(self, prop):
        self.send_command('observe_property', [1, prop])

    def wait_for_connection(self, timeout=5):
        return self._connect_event.wait(timeout)

    def close_socket_handle(self):
        if sys.platform == 'win32':
            if win32file and self.sock:
                try:
                    win32file.CloseHandle(self.sock)
                    logging.info("Closed Win32 IPC pipe handle.")
                except Exception as e:
                    logging.error(f"Error closing Win32 file handle: {e}")
                self.sock = None
        else:
            if self.sock:
                try:
                    self.sock.close()
                    logging.info("Closed Unix IPC socket.")
                except Exception as e:
                    logging.error(f"Error closing Unix socket: {e}")
                self.sock = None

    def close(self):
        self.running = False
        self.close_socket_handle()
        logging.info("MPVIPCClient stopping gracefully...")

class RadioPlayer:
    RADIO_ART = [
        "                 !",
        "                 |",
        "                 |   ~/",
        "                 |   _|~",
        "   .============.|  (_|  |~/",
        " .-;____________;|.     _|~",
        " | [_________I__] |    (_|",
        " | \"\"\" (_) (_)    |",
        " | .=====..=====. |",
        " | |:::::||:::::| |",
        " | '=====''=====' |",
        " '----------------'"
    ]

    def __init__(self):
        locale.setlocale(locale.LC_ALL, '')
        self.radios = []
        self.selected_row = 0
        self.selected_col = 0
        self.mpv_process = None
        self.ipc_client = None
        self.ipc_socket_path = None
        self.current_radio_index = None
        self.current_status = {"title": "N/A", "status": "Stopped"}
        self.bad_urls = self.load_markers('bad_urls.pkl', set())
        self.good_urls = self.load_markers('good_urls.pkl', set())
        self.load_radios()
        self.network_monitor = NetworkMonitor()
        self.status_lock = Lock()
        self.stop_event = Event()
        self.scrolling_title = ScrollingText(width=60)
        self.need_redraw = True
        self.last_draw = 0
        self.draw_interval = 1.0 / 15
        self.volume = 50
        self.radio_names_cache = {}
        self.col_page = 0
        self.items_per_col = 10

        # Adicionado para monitoramento de CPU/RAM
        self.process = psutil.Process(os.getpid())
        self.cpu_usage = 0.0
        self.ram_usage = 0.0 # Em MB

        atexit.register(self.stop_playback)

    def sanitize_title(self, title):
        if not title:
            return "N/A"
        try:
            if isinstance(title, bytes):
                title = title.decode('utf-8', errors='ignore')
            title = ''.join(char for char in title if ord(char) >= 32 or char in '\n\t')
            if title.strip() == 'Radio Stream':
                return "N/A"
            max_length = 60
            if len(title) > max_length:
                title = title[:max_length] + "..."
            return title.strip() if title.strip() else "N/A"
        except Exception:
            logging.exception("Error sanitizing title")
            return "N/A"

    def adjust_volume(self, delta):
        new_volume = max(0, min(100, self.volume + delta))
        if new_volume != self.volume:
            self.volume = new_volume
            self.need_redraw = True
            if self.ipc_client and self.ipc_client.running:
                try:
                    logging.debug(f"Requesting volume adjustment to: {self.volume}")
                    self.ipc_client.send_command('set_property', ['volume', self.volume])
                except Exception as e:
                    logging.error(f"Failed to enqueue volume command: {e}")

    def stop_playback(self):
        logging.info("Stopping playback...")
        if self.ipc_client:
            if self.mpv_process and self.mpv_process.poll() is None:
                try:
                    self.ipc_client.send_command('quit')
                    logging.info("Sent 'quit' command to MPV via IPC.")
                    time.sleep(0.1)
                except Exception as e:
                    logging.error(f"Failed to send 'quit' command to MPV: {e}")

            self.ipc_client.close()
            self.ipc_client.join(timeout=1.0)
            if self.ipc_client.is_alive():
                logging.warning("IPC Client thread did not terminate gracefully.")

        if self.mpv_process:
            try:
                self.mpv_process.terminate()
                self.mpv_process.wait(timeout=1)
                if self.mpv_process.poll() is None:
                    logging.warning("MPV process did not terminate gracefully, killing it.")
                    self.mpv_process.kill()
            except subprocess.TimeoutExpired:
                logging.warning("MPV process termination timed out, killing it.")
                self.mpv_process.kill()
            except Exception as e:
                logging.exception(f"Error terminating MPV process: {e}")
            finally:
                self.mpv_process = None
                logging.info("MPV process stopped.")

        if self.ipc_client:
            self.ipc_client.close_socket_handle()
            self.ipc_client = None

        if self.ipc_socket_path and os.path.exists(self.ipc_socket_path):
            try:
                if sys.platform != 'win32':
                    os.unlink(self.ipc_socket_path)
                    logging.info(f"Cleaned up IPC socket file: {self.ipc_socket_path}")
            except Exception as e:
                logging.error(f"Error cleaning up IPC socket file {self.ipc_socket_path}: {e}")

        with self.status_lock:
            self.current_status["title"] = "Stopped"
            self.current_radio_index = None
            self.need_redraw = True
        logging.info("Playback fully stopped.")

    def on_metadata_update(self, title):
        with self.status_lock:
            sanitized = self.sanitize_title(title)
            if self.current_status["title"] != sanitized:
                self.current_status["title"] = sanitized
                self.need_redraw = True
                logging.debug(f"Metadata updated: {sanitized}")

    def start_mpv(self, url):
        self.stop_playback()

        if sys.platform == 'win32':
            self.ipc_socket_path = r'\\.\pipe\mpvpipe-' + str(os.getpid())
        else:
            self.ipc_socket_path = os.path.join(tempfile.gettempdir(), f"mpv-socket-{os.getpid()}")
            try:
                if os.path.exists(self.ipc_socket_path):
                    os.unlink(self.ipc_socket_path)
                    logging.info(f"Unlinked old Unix IPC socket: {self.ipc_socket_path}")
            except Exception as e:
                logging.error(f"Could not unlink old IPC socket: {e}")

        cmd = [
            'mpv',
            '--no-video',
            '--input-ipc-server=' + self.ipc_socket_path,
            '--cache=yes',
            '--cache-secs=10',
            '--network-timeout=10',
            '--force-media-title=Radio Stream',
            f'--volume={self.volume}',
            '--idle=no',
            '--quiet',
            url
        ]
        logging.info(f"Starting MPV with command: {' '.join(cmd)}")
        self.mpv_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info(f"MPV process started with PID: {self.mpv_process.pid}")

        self.ipc_client = MPVIPCClient(self.ipc_socket_path, self.on_metadata_update)
        self.ipc_client.start()

        if not self.ipc_client.wait_for_connection(timeout=5):
            logging.error("IPC client failed to connect to MPV within timeout.")
            with self.status_lock:
                self.current_status["title"] = "Erro de conexão IPC!"
                self.need_redraw = True
            self.stop_playback()
            return

        if self.ipc_client and self.ipc_client.running:
            self.ipc_client.send_command('enable_event', ['property-change'])
            self.ipc_client.observe_property('metadata')
            self.ipc_client.observe_property('icy-metadata')
            self.ipc_client.observe_property('media-title')
            logging.info("MPV IPC: Enabled property observation.")
        else:
            logging.error("IPC client not running, cannot send enable_event.")
            with self.status_lock:
                self.current_status["title"] = "Erro de conexão!"
                self.need_redraw = True

    def play_selected_radio(self):
        idx = self.selected_col * self.items_per_col + self.selected_row
        if idx >= len(self.radios):
            return
        self.current_radio_index = idx
        radio = self.radios[idx]
        with self.status_lock:
            self.current_status["title"] = "Conectando..."
            self.need_redraw = True
        self.start_mpv(radio["url"])

    def load_markers(self, filename, default):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, filename)
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            logging.info(f"Marker file not found: {filename}")
            return default
        except Exception as e:
            logging.exception(f"Error loading markers from {filename}: {e}")
            return default

    def save_markers(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            bad_path = os.path.join(script_dir, 'bad_urls.pkl')
            good_path = os.path.join(script_dir, 'good_urls.pkl')
            with open(bad_path, 'wb') as f:
                pickle.dump(self.bad_urls, f)
            with open(good_path, 'wb') as f:
                pickle.dump(self.good_urls, f)
            logging.info("Markers saved successfully.")
        except Exception as e:
            logging.exception(f"Error saving markers: {e}")

    def load_radios(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        radios_file = os.path.join(script_dir, 'radios.txt')
        try:
            with open(radios_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '|' in line:
                        url, country = line.strip().split('|', 1)
                        self.radios.append({"url": url.strip(), "country": country.strip()})
            logging.info(f"Loaded {len(self.radios)} radios.")
        except FileNotFoundError:
            logging.error(f"radios.txt not found at {radios_file}. Please create it.")
            self.radios = []
        except Exception as e:
            logging.exception(f"Error loading radios from {radios_file}: {e}")
            self.radios = []

    def get_radio_display_name(self, radio):
        url = radio['url']
        if url in self.radio_names_cache:
            return self.radio_names_cache[url]

        name = get_radio_name_from_url(url)

        self.radio_names_cache[url] = name
        return name

    def draw_commands(self, window, y):
        commands = [
            "Navegar: ↑↓ ←→ | Tocar: Enter | Vol: +/- | Marcar: R=Ruim G=Boa C=Limpar | Q=Quit | B=Voltar"
        ]
        for i, cmd in enumerate(commands):
            try:
                window.addstr(y + i, 1, cmd, curses.A_BOLD)
            except curses.error as e:
                logging.exception(f"Curses addstr error in draw_commands: {e}")
                pass

    def format_network_usage(self):
        usage = self.network_monitor.get_current_usage()
        return f"↓{usage['bytes_recv']:.1f}KB/s ↑{usage['bytes_sent']:.1f}KB/s"

    def update_resource_usage(self):
        try:
            self.cpu_usage = self.process.cpu_percent(interval=None) # Non-blocking
            self.ram_usage = self.process.memory_info().rss / (1024 * 1024) # RSS memory in MB
            self.need_redraw = True
        except psutil.NoSuchProcess:
            logging.warning("Process not found for resource monitoring.")
            self.cpu_usage = 0.0
            self.ram_usage = 0.0
        except Exception as e:
            logging.exception(f"Error updating resource usage: {e}")
            self.cpu_usage = 0.0
            self.ram_usage = 0.0

    def format_resource_usage(self):
        return f"CPU: {self.cpu_usage:.1f}% RAM: {self.ram_usage:.1f}MB"

    def draw_radio_art(self, window, start_y, start_x):
        for i, line in enumerate(self.RADIO_ART):
            try:
                window.addstr(start_y + i, start_x, line)
            except curses.error as e:
                logging.exception(f"Curses addstr error in draw_radio_art: {e}")
                pass

    def start_monitoring(self):
        def network_monitor_task():
            while not self.stop_event.is_set():
                try:
                    self.network_monitor.update()
                    self.update_resource_usage() # Atualiza CPU/RAM no mesmo loop
                    self.need_redraw = True
                    time.sleep(1)
                except Exception as e:
                    logging.exception(f"Error in monitor task: {e}")
        Thread(target=network_monitor_task, daemon=True).start()

    def draw_interface(self, stdscr):
        curses.use_default_colors()
        if hasattr(curses, 'set_escdelay'):
            curses.set_escdelay(25)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, -1)     # Bad URL
        curses.init_pair(2, curses.COLOR_GREEN, -1)   # Currently Playing
        curses.init_pair(3, curses.COLOR_BLUE, -1)    # Good URL
        curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Status/Info
        stdscr.keypad(1)
        self.start_monitoring()
        stdscr.nodelay(1)
        curses.curs_set(0)
        stdscr.timeout(int(self.draw_interval * 1000))

        logging.info("Starting draw interface loop.")
        while not self.stop_event.is_set():
            key = stdscr.getch()

            if key != -1:
                if key in (ord('b'), ord('B')):
                    self.stop()
                    return
                self.handle_input(key)
            
            # Atualizar scrolling text para exibição do título da rádio
            old_scrolling_display = self.scrolling_title.get_display_text()
            with self.status_lock:
                current_title = self.current_status.get('title', 'N/A')
            scrolling_text_updated = self.scrolling_title.update(current_title)
            new_scrolling_display = self.scrolling_title.get_display_text()

            if scrolling_text_updated or new_scrolling_display != old_scrolling_display:
                self.need_redraw = True

            current_time = time.time()
            if self.need_redraw or (current_time - self.last_draw >= self.draw_interval):
                start_draw_time = time.perf_counter()
                try:
                    height, width = stdscr.getmaxyx()
                    stdscr.erase()

                    self.draw_commands(stdscr, 0)
                    
                    net_usage = self.format_network_usage()
                    resource_usage = self.format_resource_usage() # Novo!
                    status_str = f"Net: {net_usage} | Vol: {self.volume}% | {resource_usage}" # Atualizado
                    try:
                        stdscr.addstr(2, 1, status_str[:width-2].ljust(width-2), curses.color_pair(4))
                    except curses.error as e:
                        logging.exception(f"Curses addstr error for status: {e}")
                        pass

                    art_start_y = 4
                    art_width = max(len(line) for line in self.RADIO_ART)
                    art_start_x = max((width - art_width) // 2, 0)
                    self.draw_radio_art(stdscr, art_start_y, art_start_x)
                    list_start_y = art_start_y + len(self.RADIO_ART) + 2

                    col_width = max(30, (width // 2) - 2)
                    visible_cols = 2

                    self.items_per_col = max(1, (height - list_start_y - 3 - 1))
                    total_items = len(self.radios)
                    max_rows = self.items_per_col
                    max_cols = (total_items + max_rows - 1) // max_rows

                    if self.selected_col < self.col_page:
                        self.col_page = self.selected_col
                    elif self.selected_col >= self.col_page + visible_cols:
                        self.col_page = self.selected_col - visible_cols + 1

                    for col_idx in range(self.col_page, min(self.col_page + visible_cols, max_cols)):
                        for row in range(max_rows):
                            idx = col_idx * max_rows + row
                            if idx >= total_items:
                                break
                            radio = self.radios[idx]
                            
                            color = curses.color_pair(0)
                            if idx in self.bad_urls:
                                color = curses.color_pair(1)
                            elif idx == self.current_radio_index:
                                color = curses.color_pair(2)
                            elif idx in self.good_urls:
                                color = curses.color_pair(3)
                            
                            attr = color
                            if col_idx == self.selected_col and row == self.selected_row:
                                attr |= curses.A_REVERSE

                            # Exibir o nome da rádio atualmente tocando, ou o nome da lista
                            with self.status_lock:
                                playing_index = self.current_radio_index
                                playing_title = self.current_status.get('title', 'N/A')
                                if idx == playing_index and playing_title not in ("N/A", "Conectando...", "Stopped", "Erro de conexão!", "Erro de conexão IPC!"):
                                    display_name = playing_title
                                else:
                                    display_name = self.get_radio_display_name(radio)

                            radio_text = f"{idx+1}. {radio['country']} - {display_name}"
                            if len(radio_text) > col_width - 2:
                                radio_text = radio_text[:col_width - 5] + "..."

                            try:
                                stdscr.addstr(list_start_y + row, (col_idx - self.col_page) * col_width + 1, radio_text.ljust(col_width - 1), attr)
                            except curses.error as e:
                                logging.exception(f"Curses addstr error for radio item {idx}: {e}")
                                pass

                    status_line_y = height - 1
                    try:
                        stdscr.addstr(status_line_y, 1, f"Tocando: {new_scrolling_display}".ljust(width-2), curses.color_pair(4))
                    except curses.error as e:
                        logging.exception(f"Curses addstr error for 'Tocando' line: {e}")
                        pass

                    stdscr.refresh()
                    self.last_draw = current_time
                    self.need_redraw = False
                    end_draw_time = time.perf_counter()
                    logging.debug(f"Draw cycle time: {end_draw_time - start_draw_time:.4f}s")
                
                except curses.error as e:
                    logging.exception(f"Curses error in draw_interface loop: {e}")
                    self.stop_event.set()
                except Exception as e:
                    logging.exception(f"Unexpected error in draw_interface loop: {e}")
                    self.stop_event.set()

    def handle_input(self, key):
        total_items = len(self.radios)
        max_rows = self.items_per_col
        max_cols = (total_items + max_rows - 1) // max_rows

        handled = False
        if key in (ord('q'), ord('Q')):
            self.stop()
            handled = True
        elif key == curses.KEY_RIGHT:
            if self.selected_col + 1 < max_cols:
                self.selected_col += 1
                max_row_in_col = min(max_rows, total_items - self.selected_col * max_rows) - 1
                if self.selected_row > max_row_in_col:
                    self.selected_row = max_row_in_col
                handled = True
        elif key == curses.KEY_LEFT:
            if self.selected_col > 0:
                self.selected_col -= 1
                max_row_in_col = min(max_rows, total_items - self.selected_col * max_rows) - 1
                if self.selected_row > max_row_in_col:
                    self.selected_row = max_row_in_col
            handled = True
        elif key == curses.KEY_DOWN:
            max_row_in_col = min(max_rows, total_items - self.selected_col * max_rows) - 1
            if self.selected_row < max_row_in_col:
                self.selected_row += 1
            else:
                if self.selected_col + 1 < max_cols:
                    self.selected_col += 1
                    self.selected_row = 0
            handled = True
        elif key == curses.KEY_UP:
            if self.selected_row > 0:
                self.selected_row -= 1
            else:
                if self.selected_col > 0:
                    self.selected_col -= 1
                    max_row_in_col = min(max_rows, total_items - self.selected_col * max_rows) - 1
                    self.selected_row = max_row_in_col
            handled = True
        elif key in (10, 13, curses.KEY_ENTER):
            self.play_selected_radio()
            handled = True
        elif key in (ord('='), ord('+'), ):
            self.adjust_volume(5)
            handled = True
        elif key == ord('-'):
            self.adjust_volume(-5)
            handled = True
        elif key in (ord('r'), ord('R')):
            idx = self.selected_col * self.items_per_col + self.selected_row
            if idx < len(self.radios):
                self.bad_urls.add(idx)
                if idx in self.good_urls:
                    self.good_urls.remove(idx)
                handled = True
        elif key in (ord('g'), ord('G')):
            idx = self.selected_col * self.items_per_col + self.selected_row
            if idx < len(self.radios):
                self.good_urls.add(idx)
                if idx in self.bad_urls:
                    self.bad_urls.remove(idx)
                handled = True
        elif key in (ord('c'), ord('C')):
            idx = self.selected_col * self.items_per_col + self.selected_row
            if idx < len(self.radios):
                if idx in self.bad_urls:
                    self.bad_urls.remove(idx)
                if idx in self.good_urls:
                    self.good_urls.remove(idx)
                handled = True

        if handled:
            self.need_redraw = True

    def stop(self):
        logging.info("Stop event received. Initiating shutdown.")
        self.stop_event.set()
        self.save_markers()
        self.stop_playback()

# Ponto de entrada principal para curses
def main(stdscr):
    player = RadioPlayer()
    try:
        player.draw_interface(stdscr)
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, "Erro inesperado:")
        stdscr.addstr(1, 0, str(e))
        stdscr.addstr(3, 0, "Pressione qualquer tecla para sair...")
        stdscr.refresh()
        stdscr.getch()
        logging.exception("Unhandled exception in main Curses loop.")
        raise
    finally:
        player.stop()
        logging.info("Application main loop finished.")

if __name__ == '__main__':
    import traceback
    try:
        curses.wrapper(main)
    except Exception:
        traceback.print_exc()
        input("Pressione Enter para sair...")
    logging.info("Application exited.")