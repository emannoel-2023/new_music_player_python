# SoundWave Player

Player de música para terminal em Python, com interface dinâmica, espectro visual, controle por comandos, playlist, histórico e monitoramento de CPU/RAM do processo.

## Requisitos

- Python 3.7+
- pygame
- numpy
- psutil

## Instalação

pip install -r requirements.txt

## Uso

Execute o player com:

python main.py

### Comandos disponíveis

- `play` ou `p`: tocar/pausar música
- `pause`: pausar música
- `stop`: parar música
- `prox` ou `next`: próxima música
- `ant` ou `prev`: música anterior
- `+` ou `=`: aumentar volume
- `-` ou `vol-`: diminuir volume
- `vol <valor>`: definir volume (0.0 a 1.0)
- `dir`: carregar diretório de músicas (cole o caminho)
- `sair`: fechar player

## Estrutura do projeto

- `audio.py`: player de áudio e espectro
- `biblioteca.py`: gerenciamento da biblioteca musical
- `playlist.py`: gerenciamento de playlists e favoritos
- `historico.py`: histórico de músicas tocadas
- `recursos.py`: monitoramento CPU/RAM do processo
- `comandos.py`: interpretação e execução de comandos
- `ui.py`: interface terminal dinâmica
- `utils.py`: funções auxiliares
- `testes/`: testes unitários

## Testes

Para rodar os testes:
python -m unittest discover testes



---

Desenvolvido para estudo e uso pessoal.
