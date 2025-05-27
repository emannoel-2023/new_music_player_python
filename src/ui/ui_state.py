import json
import os

class UIState:
    """
    Gerencia o carregamento e salvamento de dados de estado da interface,
    como histórico de reprodução e músicas favoritas.
    """
    def __init__(self, data_folder):
        self.data_folder = data_folder
        self.historico_arquivo = os.path.join(self.data_folder, 'historico.json')
        self.favoritos_arquivo = os.path.join(self.data_folder, 'favoritos.json')
        
    def carregar_historico(self):
        """Carrega o histórico de músicas de um arquivo JSON."""
        try:
            if os.path.exists(self.historico_arquivo):
                with open(self.historico_arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                return dados if isinstance(dados, list) else []
            else:
                return []
        except Exception as e:
            # Em um aplicativo real, isso seria logado.
            # print(f"Erro ao carregar histórico: {e}")
            return []

    def salvar_historico(self, historico_pilha):
        """Salva o histórico de músicas em um arquivo JSON."""
        try:
            os.makedirs(self.data_folder, exist_ok=True)
            with open(self.historico_arquivo, 'w', encoding='utf-8') as f:
                json.dump(historico_pilha, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # print(f"Erro ao salvar histórico: {e}")
            pass

    def carregar_favoritos(self):
        """Carrega a lista de músicas favoritas de um arquivo JSON."""
        try:
            if os.path.exists(self.favoritos_arquivo):
                with open(self.favoritos_arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                return set(dados) if isinstance(dados, list) else set()
            else:
                return set()
        except Exception as e:
            # print(f"Erro ao carregar favoritos: {e}")
            return set()

    def salvar_favoritos(self, favoritos_set):
        """Salva a lista de músicas favoritas em um arquivo JSON."""
        try:
            os.makedirs(self.data_folder, exist_ok=True)
            with open(self.favoritos_arquivo, 'w', encoding='utf-8') as f:
                json.dump(list(favoritos_set), f, ensure_ascii=False, indent=2)
        except Exception as e:
            # print(f"Erro ao salvar favoritos: {e}")
            pass