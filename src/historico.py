class Historico:
    def __init__(self):
        self.pilha = []

    def adicionar(self, musica):
        self.pilha.append(musica)

    def anterior(self):
        if len(self.pilha) > 1:
            self.pilha.pop()
            return self.pilha[-1]
        return None

    def atual(self):
        if self.pilha:
            return self.pilha[-1]
        return None

    def limpar(self):
        self.pilha = []
