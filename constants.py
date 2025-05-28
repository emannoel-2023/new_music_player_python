# constants.py (na raiz do projeto)
import os

# Definindo a pasta de dados no nível raiz do projeto
# Isso pressupõe que 'constants.py' está no mesmo nível de 'src' e 'data'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_DADOS = os.path.join(BASE_DIR, 'data')

# Certifica-se de que a pasta de dados existe
os.makedirs(PASTA_DADOS, exist_ok=True)