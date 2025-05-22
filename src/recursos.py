import psutil
import os

def uso_recursos():
    p = psutil.Process(os.getpid())
    cpu = p.cpu_percent(interval=0.1)
    ram = p.memory_info().rss / (1024 * 1024)  # MB
    return cpu, ram
