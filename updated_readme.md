# SoundWave Player

Player de música para terminal em Python, com interface dinâmica, espectro visual, controle por comandos, playlist, histórico, monitoramento de CPU/RAM e integração com rádio online.

## Requisitos

- Python 3.7+

## Instalação

```bash
pip install -r requirements.txt
Uso
Execute o player com:

Bash

python main.py
Comandos disponíveis
play ou p: tocar/pausar música 
pause: pausar música 
stop: parar música 
prox ou next: próxima música 
ant ou prev: música anterior 
+ ou =: aumentar volume 
- ou vol-: diminuir volume 
vol <valor>: definir volume (0.0 a 1.0) 
dir: carregar diretório de músicas (cole o caminho) 
radio: abrir aplicativo de rádio integrado 
sair: fechar player 
h ou H: Mostrar histórico 
l ou L: Listar playlists salvas 
c ou C: Criar nova playlist 
a ou A: Adicionar música à playlist 
d ou D: Remover música da playlist 
f ou F: Favoritar/Desfavoritar música 

s ou S: Saltar para uma música específica na playlist 
o ou O: Ordenar a playlist atual 
b ou B: Buscar músicas na biblioteca 
t ou T: Filtrar músicas por categoria (artista, álbum, gênero) 
e ou E: Controlar a equalização de áudio (grave, médio, agudo) 

x ou X: Mostrar estatísticas de reprodução e biblioteca 
Enter: Tocar a música selecionada na playlist 
↑↓←→: Navegar pelas opções e playlist 
Funcionalidades
🎵 Player de Música
Reprodução de arquivos de áudio locais 
Controle de volume e navegação 

Espectro visual em tempo real 
Suporte a múltiplos formatos de áudio (mp3, wav, flac, ogg) 
Equalizador de áudio (grave, médio, agudo) 


📻 Integração com Rádio
Acesso ao aplicativo de rádio terminal integrado 

Pausa automática da música ao abrir o rádio 
Retomada automática ao fechar o rádio 
Interface seamless entre os dois modos 
📊 Monitoramento
Monitoramento de CPU e RAM do processo 


Exibição de informações do sistema em tempo real 

📝 Gerenciamento
Sistema de playlists e favoritos 

Histórico de músicas reproduzidas 
Persistência de dados entre sessões 
Biblioteca de músicas com busca e filtragem por metadados (artista, álbum, gênero, título) 


Ordenação de playlists por diversos critérios 

Estrutura do projeto
soundwave/
├── data/
│   ├── estado_player.json # Estado do player e playlists salvas [cite: 7]
│   ├── favoritos.json     # Lista de favoritos [cite: 7]
│   └── historico.json     # Histórico de reprodução [cite: 278]
├── radio_terminal/ [cite: 374]
│   ├── radio.py           # Aplicativo de rádio integrado [cite: 284]
│   └── ...                # Outros arquivos do rádio (e.g., radios.txt) [cite: 330]
├── src/ [cite: 374]
│   ├── audio.py           # Player de áudio e espectro [cite: 33]
│   ├── biblioteca.py      # Gerenciamento da biblioteca musical [cite: 21, 28]
│   ├── comandos.py        # Interpretação e execução de comandos [cite: 14]
│   ├── config_manager.py  # Gerenciamento de configurações [cite: 12, 13]
│   ├── historico.py       # Histórico de músicas tocadas [cite: 10]
│   ├── playlist.py        # Gerenciamento de playlists e favoritos [cite: 2, 3]
│   ├── recursos.py        # Monitoramento CPU/RAM do processo (deprecated, use ui_utils) [cite: 2]
│   ├── utils.py           # Funções auxiliares (formatar_tempo) [cite: 1, 100]
│   └── ui/ [cite: 374]
│       ├── ui_components.py # Componentes visuais da UI [cite: 72]
│       ├── ui_core.py       # Lógica principal da UI e interação [cite: 121]
│       ├── ui_state.py      # Carregamento/salvamento de estado da UI [cite: 277]
│       └── ui_utils.py      # Funções utilitárias da UI (inicia cores, uso_recursos) [cite: 282, 283]
├── testes/ [cite: 374]
│   ├── test_audio.py
│   ├── test_biblioteca.py
│   └── test_playlist.py
├── main.py                # Arquivo principal para iniciar o player [cite: 1]
├── requirements.txt       # Dependências do projeto [cite: 373]
└── README.md              # Este arquivo
Integração com Rádio
O SoundWave Player inclui integração com um aplicativo de rádio terminal. Quando o comando radio é executado:

A música atual é pausada automaticamente (se estiver tocando) 
O aplicativo de rádio é aberto em uma nova janela 

Ao fechar o rádio, a interface do player é restaurada 
A música é retomada automaticamente (se estava tocando antes) 
Testes
Para rodar os testes:

Bash

python -m unittest discover testes
Dependências
O projeto utiliza as seguintes bibliotecas externas:

pygame: Para reprodução de áudio 
numpy: Para processamento de espectro 
psutil: Para monitoramento do sistema (CPU/RAM) 
windows-curses: Para compatibilidade do curses no Windows 
pyfiglet: Para texto ASCII art (título) 
requests: Para requisições HTTP (rádio online) 
pydub: Para manipulação de segmentos de áudio (espectro, equalização) 

mutagen: Para extração de metadados de arquivos de áudio (duração, artista, título, etc.) 


Desenvolvido para estudo e uso pessoal.


---

### `requirements.txt` (File Content)

pygame
numpy
psutil
windows-curses
pyfiglet
requests
pydub
mutagen