import json
import os

CONFIG_FILE = os.path.expanduser('~/.musga_config.json')

class ConfigManager:
    def __init__(self):
        self.config = {}
        self.carregar()

    def carregar(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def salvar(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def set(self, chave, valor):
        self.config[chave] = valor
        self.salvar()

    def get(self, chave, padrao=None):
        return self.config.get(chave, padrao)
