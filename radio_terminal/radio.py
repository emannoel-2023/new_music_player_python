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
        if new_text is not None and new_text != self.text:
            self.text = new_text
            self.position = 0
            self.last_update = time.time()
            self.paused_since = 0

        current_time = time.time()
        if len(self.text) > self.width:
            if self.paused_since > 0:
                if current_time - self.paused_since > self.pause_at_end:
                    self.paused_since = 0
                else:
                    return
            if current_time - self.last_update > self.scroll_speed:
                self.position = (self.position + 1) % len(self.text)
                if self.position == 0:
                    self.paused_since = current_time
                self.last_update = current_time

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
        pass
    return None

class MPVIPCClient(Thread):
    def __init__(self, socket_path, on_metadata_update):
        super().__init__(daemon=True)
        self.socket_path = socket_path
        self.on_metadata_update = on_metadata_update
        self.sock = None
        self.running = True
        self._lock = Lock()
        self._request_id = 0
        self._responses = {}
        self._connect()

    def _connect(self):
        if sys.platform == 'win32':
            self.sock = None
        else:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            connected = False
            for _ in range(20):
                try:
                    self.sock.connect(self.socket_path)
                    connected = True
                    break
                except FileNotFoundError:
                    time.sleep(0.1)
            if not connected:
                self.sock = None

    def run(self):
        if sys.platform == 'win32':
            import win32file, pywintypes
            while self.running:
                try:
                    self.sock = win32file.CreateFile(
                        self.socket_path,
                        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                        0, None,
                        win32file.OPEN_EXISTING,
                        0, None
                    )
                    break
                except pywintypes.error:
                    time.sleep(0.1)
            if not self.sock:
                return
            while self.running:
                try:
                    res, data = win32file.ReadFile(self.sock, 4096)
                    if res == 0:
                        self._handle_data(data)
                except Exception:
                    time.sleep(0.1)
        else:
            buff = b""
            while self.running and self.sock:
                try:
                    data = self.sock.recv(4096)
                    if not data:
                        break
                    buff += data
                    while b'\n' in buff:
                        line, buff = buff.split(b'\n', 1)
                        self._handle_data(line)
                except Exception:
                    time.sleep(0.1)

    def _handle_data(self, data):
        try:
            msg = json.loads(data.decode('utf-8'))
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
                with self._lock:
                    self._responses[msg['request_id']] = msg
        except Exception:
            pass
    def send_command(self, command, args=None):
        with self._lock:
            self._request_id += 1
            req_id = self._request_id
            msg = {'command': [command] + (args if args else []), 'request_id': req_id}
            try:
                data = (json.dumps(msg) + '\n').encode('utf-8')
                if sys.platform == 'win32':
                    import win32file
                    win32file.WriteFile(self.sock, data)
                else:
                    self.sock.sendall(data)
            except Exception:
                pass
            return req_id

    def observe_property(self, prop):
        self.send_command('observe_property', [1, prop])

    def close(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass

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
        self.bad_urls = self.load_markers('\\radio_terminal\\bad_urls.pkl', set())
        self.good_urls = self.load_markers('\\radio_terminal\\good_urls.pkl', set())
        self.load_radios()
        self.network_monitor = NetworkMonitor()
        self.status_lock = Lock()
        self.stop_event = Event()
        self.scrolling_title = ScrollingText(width=60)
        self.need_redraw = True
        self.last_draw = 0
        self.draw_interval = 1.0 / 30
        self.volume = 50
        self.radio_names_cache = {}
        self.col_page = 0
        self.items_per_col = 10

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
            return "N/A"

    def adjust_volume(self, delta):
        new_volume = max(0, min(100, self.volume + delta))
        if new_volume != self.volume:
            self.volume = new_volume
            self.need_redraw = True
            if self.ipc_client:
                self.ipc_client.send_command('set_property', ['volume', self.volume])

    def stop_playback(self):
        if self.mpv_process:
            try:
                self.mpv_process.terminate()
                self.mpv_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.mpv_process.kill()
            except Exception:
                pass
            self.mpv_process = None
        if self.ipc_client:
            try:
                self.ipc_client.close()
            except Exception:
                pass
            self.ipc_client = None
        with self.status_lock:
            self.current_status["title"] = "Stopped"
            self.need_redraw = True

    def on_metadata_update(self, title):
        with self.status_lock:
            self.current_status["title"] = self.sanitize_title(title)
            self.need_redraw = True

    def start_mpv(self, url):
        if self.ipc_socket_path:
            try:
                if sys.platform != 'win32' and os.path.exists(self.ipc_socket_path):
                    os.unlink(self.ipc_socket_path)
            except Exception:
                pass
        if sys.platform == 'win32':
            self.ipc_socket_path = r'\\.\pipe\mpvpipe'
        else:
            self.ipc_socket_path = os.path.join(tempfile.gettempdir(), f"mpv-socket-{os.getpid()}")
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
        self.stop_playback()
        self.mpv_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.ipc_client = MPVIPCClient(self.ipc_socket_path, self.on_metadata_update)
        self.ipc_client.start()
        time.sleep(0.5)
        self.ipc_client.observe_property('metadata')
        self.ipc_client.observe_property('icy-metadata')
        self.ipc_client.observe_property('media-title')

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
            with open(filename, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return default

    def save_markers(self):
        with open('bad_urls.pkl', 'wb') as f:
            pickle.dump(self.bad_urls, f)
        with open('good_urls.pkl', 'wb') as f:
            pickle.dump(self.good_urls, f)

    def load_radios(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        radios_file = os.path.join(script_dir, 'radios.txt')
        try:
            with open(radios_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '|' in line:
                        url, country = line.strip().split('|', 1)
                        self.radios.append({"url": url.strip(), "country": country.strip()})
        except FileNotFoundError:
            self.radios = []

    def get_radio_display_name(self, radio):
        url = radio['url']
        if url in self.radio_names_cache:
            return self.radio_names_cache[url]
        name = get_radio_name_from_api(url)
        if not name:
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
            except curses.error:
                pass

    def format_network_usage(self):
        usage = self.network_monitor.get_current_usage()
        return f"↓{usage['bytes_recv']:.1f}KB/s ↑{usage['bytes_sent']:.1f}KB/s"

    def draw_radio_art(self, window, start_y, start_x):
        for i, line in enumerate(self.RADIO_ART):
            try:
                window.addstr(start_y + i, start_x, line)
            except curses.error:
                pass

    def start_monitoring(self):
        def network_monitor_task():
            while not self.stop_event.is_set():
                try:
                    self.network_monitor.update()
                    time.sleep(1)
                except Exception:
                    pass
        Thread(target=network_monitor_task, daemon=True).start()

    def draw_interface(self, stdscr, max_columns=2):
        curses.use_default_colors()
        if hasattr(curses, 'set_escdelay'):
            curses.set_escdelay(25)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_BLUE, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        stdscr.keypad(1)
        self.start_monitoring()
        stdscr.nodelay(1)
        curses.curs_set(0)
        stdscr.keypad(1)
        stdscr.timeout(50)
        while not self.stop_event.is_set():
            current_time = time.time()
            if current_time - self.last_draw < self.draw_interval and not self.need_redraw:
                key = stdscr.getch()
                if key != -1:
                    self.handle_input(key)
                continue
            try:
                height, width = stdscr.getmaxyx()
                if self.need_redraw:
                    stdscr.erase()
                self.draw_commands(stdscr, 0)
                net_usage = self.format_network_usage()
                status = f"Net: {net_usage} | Volume: {self.volume}%"
                try:
                    stdscr.addstr(2, 1, status[:width-2], curses.color_pair(4))
                except curses.error:
                    pass
                art_start_y = 4
                art_width = max(len(line) for line in self.RADIO_ART)
                art_start_x = max((width - art_width) // 2, 0)
                self.draw_radio_art(stdscr, art_start_y, art_start_x)
                list_start_y = art_start_y + len(self.RADIO_ART) + 2

                # --- LIMITE DE 2 COLUNAS ---
                col_width = max(30, width // 2)
                num_cols = 2
                visible_cols = 2
                # ---------------------------
                total_items = len(self.radios)
                self.items_per_col = max(1, (height - list_start_y - 3))
                max_rows = self.items_per_col
                max_cols = (total_items + max_rows - 1) // max_rows

                if self.selected_col < self.col_page:
                    self.col_page = self.selected_col
                elif self.selected_col >= self.col_page + visible_cols:
                    self.col_page = self.selected_col - visible_cols + 1

                for col in range(self.col_page, self.col_page + visible_cols):
                    for row in range(max_rows):
                        idx = col * max_rows + row
                        if idx >= total_items:
                            break
                        radio = self.radios[idx]
                        if idx in self.bad_urls:
                            color = curses.color_pair(1)
                        elif idx == self.current_radio_index:
                            color = curses.color_pair(2)
                        elif idx in self.good_urls:
                            color = curses.color_pair(3)
                        else:
                            color = curses.color_pair(0)
                        attr = color
                        if col == self.selected_col and row == self.selected_row:
                            attr |= curses.A_REVERSE
                        with self.status_lock:
                            playing_index = self.current_radio_index
                            playing_title = self.current_status.get('title', 'N/A')
                            if idx == playing_index and playing_title not in ("N/A", "Conectando...", "Stopped"):
                                display_name = playing_title
                            else:
                                display_name = self.get_radio_display_name(radio)
                        radio_text = f"{idx+1}. {radio['country']} - {display_name}"
                        if len(radio_text) > col_width - 2:
                            radio_text = radio_text[:col_width - 5] + "..."
                        try:
                            stdscr.addstr(list_start_y + row, (col - self.col_page) * col_width + 1, radio_text.ljust(col_width - 1), attr)
                        except curses.error:
                            pass

                with self.status_lock:
                    current_title = self.current_status.get('title', 'N/A')
                    self.scrolling_title.update(current_title)
                    display_text = self.scrolling_title.get_display_text()
                try:
                    stdscr.addstr(height-1, 1, f"Tocando: {display_text}", curses.color_pair(4))
                except curses.error:
                    pass

                stdscr.refresh()
                self.last_draw = current_time
                self.need_redraw = False
                key = stdscr.getch()
                if key != -1:
                    if key in (ord('b'), ord('B')):
                        self.stop()
                        return
                    self.handle_input(key)
            except curses.error:
                pass

    def handle_input(self, key):
        total_items = len(self.radios)
        max_rows = self.items_per_col
        max_cols = (total_items + max_rows - 1) // max_rows
        if key in (ord('q'), ord('Q')):
            self.stop()
            return
        if key == curses.KEY_RIGHT:
            if self.selected_col + 1 < max_cols:
                self.selected_col += 1
                max_row_in_col = min(max_rows, total_items - self.selected_col * max_rows) - 1
                if self.selected_row > max_row_in_col:
                    self.selected_row = max_row_in_col
                self.need_redraw = True
        elif key == curses.KEY_LEFT:
            if self.selected_col > 0:
                self.selected_col -= 1
                max_row_in_col = min(max_rows, total_items - self.selected_col * max_rows) - 1
                if self.selected_row > max_row_in_col:
                    self.selected_row = max_row_in_col
                self.need_redraw = True
        elif key == curses.KEY_DOWN:
            max_row_in_col = min(max_rows, total_items - self.selected_col * max_rows) - 1
            if self.selected_row < max_row_in_col:
                self.selected_row += 1
            else:
                if self.selected_col + 1 < max_cols:
                    self.selected_col += 1
                    self.selected_row = 0
            self.need_redraw = True
        elif key == curses.KEY_UP:
            if self.selected_row > 0:
                self.selected_row -= 1
            else:
                if self.selected_col > 0:
                    self.selected_col -= 1
                    max_row_in_col = min(max_rows, total_items - self.selected_col * max_rows) - 1
                    self.selected_row = max_row_in_col
            self.need_redraw = True
        elif key in (10, 13, curses.KEY_ENTER):
            self.play_selected_radio()
            self.need_redraw = True
        elif key == ord('+'):
            self.adjust_volume(5)
        elif key == ord('-'):
            self.adjust_volume(-5)
        elif key in (ord('r'), ord('R')):
            idx = self.selected_col * self.items_per_col + self.selected_row
            if idx < len(self.radios):
                self.bad_urls.add(idx)
                if idx in self.good_urls:
                    self.good_urls.remove(idx)
                self.need_redraw = True
        elif key in (ord('g'), ord('G')):
            idx = self.selected_col * self.items_per_col + self.selected_row
            if idx < len(self.radios):
                self.good_urls.add(idx)
                if idx in self.bad_urls:
                    self.bad_urls.remove(idx)
                self.need_redraw = True
        elif key in (ord('c'), ord('C')):
            idx = self.selected_col * self.items_per_col + self.selected_row
            if idx < len(self.radios):
                if idx in self.bad_urls:
                    self.bad_urls.remove(idx)
                if idx in self.good_urls:
                    self.good_urls.remove(idx)
                self.need_redraw = True

    def stop(self):
        try:
            self.stop_playback()
        except Exception:
            pass
        self.stop_event.set()

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
        raise

if __name__ == '__main__':
    import traceback
    try:
        curses.wrapper(main)
    except Exception:
        traceback.print_exc()
        input("Pressione Enter para sair...")
