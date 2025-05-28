import json
import os

class UIState:
    def __init__(self, data_folder):
        self.data_folder = data_folder
        self.historico_arquivo = os.path.join(self.data_folder, 'historico.json')
        self.favoritos_arquivo = os.path.join(self.data_folder, 'favoritos.json')
        
    def carregar_historico(self):
        try:
            if os.path.exists(self.historico_arquivo):
                with open(self.historico_arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                return dados if isinstance(dados, list) else []
            else:
                return []
        except Exception as e:
            return []

    def salvar_historico(self, historico_pilha):
        try:
            os.makedirs(self.data_folder, exist_ok=True)
            with open(self.historico_arquivo, 'w', encoding='utf-8') as f:
                json.dump(historico_pilha, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def carregar_favoritos(self):
        try:
            if os.path.exists(self.favoritos_arquivo):
                with open(self.favoritos_arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                return set(dados) if isinstance(dados, list) else set()
            else:
                return set()
        except Exception as e:
            return set()

    def salvar_favoritos(self, favoritos_set):
        try:
            os.makedirs(self.data_folder, exist_ok=True)
            with open(self.favoritos_arquivo, 'w', encoding='utf-8') as f:
                json.dump(list(favoritos_set), f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass