# historico.py
import json
import os
from collections import Counter
from constants import PASTA_DADOS # Importa PASTA_DADOS centralizada

HISTORICO_ARQUIVO = os.path.join(PASTA_DADOS, 'historico.json')

class Historico:
    def __init__(self):
        self.pilha = []
        self.carregar()

    def adicionar(self, caminho_musica):
        # Apenas adicione a música ao histórico. Permite duplicatas para contagem.
        self.pilha.append(caminho_musica)

        # Manter um tamanho razoável para o histórico (ex: últimas 100 músicas)
        # Se você quer contar TODAS as reproduções ao longo do tempo,
        # você pode precisar de um histórico maior ou um mecanismo de armazenamento diferente.
        # Para um histórico recente e contagem de reproduções dentro desse limite:
        if len(self.pilha) > 100:
            self.pilha.pop(0) # Remove o mais antigo

        self.salvar()

    def estatisticas(self, top_n=10):
        # O Counter agora contará todas as ocorrências na pilha, incluindo duplicatas
        return Counter(self.pilha).most_common(top_n)

    def salvar(self):
        try:
            os.makedirs(PASTA_DADOS, exist_ok=True)
            with open(HISTORICO_ARQUIVO, 'w', encoding='utf-8') as f:
                json.dump(self.pilha, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # Você pode querer logar este erro em um arquivo, se quiser manter rastreamento
            pass # Silencia o erro para o usuário final

    def carregar(self):
        try:
            if os.path.exists(HISTORICO_ARQUIVO):
                with open(HISTORICO_ARQUIVO, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                self.pilha = dados if isinstance(dados, list) else []
            else:
                self.pilha = []
        except Exception as e:
            # Você pode querer logar este erro em um arquivo, se quiser manter rastreamento
            self.pilha = [] # Garante que a pilha esteja vazia em caso de erro no carregamento