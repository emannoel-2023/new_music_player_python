import threading
import queue
import time

class TestThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.q = queue.Queue()
        self.running = True
        self.daemon = True

    def run(self):
        print("TestThread: Iniciada.")
        while self.running:
            try:
                item = self.q.get(timeout=0.1)
                print(f"TestThread: Recebeu item: {item}")
                if item == "STOP":
                    self.running = False
                self.q.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                print(f"TestThread: Erro inesperado: {e}")
        print("TestThread: Finalizada.")

if __name__ == "__main__":
    t = TestThread()
    t.start()

    time.sleep(1) # Dá um tempo para a thread iniciar

    print("Main: Enviando 'Hello'")
    t.q.put("Hello")
    time.sleep(0.5)

    print("Main: Enviando 'World'")
    t.q.put("World")
    time.sleep(0.5)

    print("Main: Enviando 'PAUSE_COMMAND'")
    # Simule a situação que causa o travamento
    t.q.put("PAUSE_COMMAND") # Esta é a linha crítica
    time.sleep(0.5)

    print("Main: Enviando 'STOP'")
    t.q.put("STOP")
    time.sleep(0.5)

    t.join(timeout=2)
    if t.is_alive():
        print("Main: Thread de teste ainda ativa. Pode ter travado.")
    print("Main: Script principal finalizado.")