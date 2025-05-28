# historico.py
import json
import os
from constants import PASTA_DADOS # Importa PASTA_DADOS centralizada

HISTORICO_ARQUIVO = os.path.join(PASTA_DADOS, 'historico.json')

class Historico:
    def __init__(self):
        self.pilha = []
        self.carregar()

    def adicionar(self, caminho_musica):
        # Adiciona a música ao histórico e salva
        # Remover duplicatas para evitar histórico muito grande e repetir músicas
        if caminho_musica in self.pilha:
            self.pilha.remove(caminho_musica) # Move para o final se já existe
        self.pilha.append(caminho_musica)

        # Manter um tamanho razoável para o histórico (ex: últimas 100 músicas)
        if len(self.pilha) > 100:
            self.pilha.pop(0) # Remove o mais antigo

        self.salvar()

    def estatisticas(self, top_n=10):
        from collections import Counter
        return Counter(self.pilha).most_common(top_n)

    def salvar(self):
        try:
            os.makedirs(PASTA_DADOS, exist_ok=True)
            with open(HISTORICO_ARQUIVO, 'w', encoding='utf-8') as f:
                json.dump(self.pilha, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar histórico: {str(e)}")

    def carregar(self):
        try:
            if os.path.exists(HISTORICO_ARQUIVO):
                with open(HISTORICO_ARQUIVO, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                self.pilha = dados if isinstance(dados, list) else []
            else:
                self.pilha = []
        except Exception as e:
            print(f"Erro ao carregar histórico: {str(e)}")
            self.pilha = []