# SoundWave Player

Player de música para terminal em Python, com interface dinâmica, espectro visual, controle por comandos, playlist, histórico, monitoramento de CPU/RAM e integração com rádio online.

## Requisitos

- Python 3.7+

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

Execute o player com:

```bash
python main.py
```

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
- `radio`: abrir aplicativo de rádio integrado
- `sair`: fechar player

## Funcionalidades

### 🎵 Player de Música
- Reprodução de arquivos de áudio locais
- Controle de volume e navegação
- Espectro visual em tempo real
- Suporte a múltiplos formatos de áudio

### 📻 Integração com Rádio
- Acesso ao aplicativo de rádio terminal integrado
- Pausa automática da música ao abrir o rádio
- Retomada automática ao fechar o rádio
- Interface seamless entre os dois modos

### 📊 Monitoramento
- Monitoramento de CPU e RAM do processo
- Exibição de informações do sistema em tempo real

### 📝 Gerenciamento
- Sistema de playlists e favoritos
- Histórico de músicas reproduzidas
- Persistência de dados entre sessões

## Estrutura do projeto

```
src/
├── audio.py              # Player de áudio e espectro
├── biblioteca.py         # Gerenciamento da biblioteca musical
├── playlist.py          # Gerenciamento de playlists e favoritos
├── historico.py         # Histórico de músicas tocadas
├── recursos.py          # Monitoramento CPU/RAM do processo
├── comandos.py          # Interpretação e execução de comandos
├── ui.py                # Interface terminal dinâmica
└── utils.py             # Funções auxiliares

radio_terminal/
├── radio.py             # Aplicativo de rádio integrado
└── ...                  # Outros arquivos do rádio

data/
├── estado_playlist.json # Estado da playlist
├── favoritos.json       # Lista de favoritos
└── historico.json       # Histórico de reprodução

testes/
└── ...                  # Testes unitários

main.py                  # Arquivo principal
requirements.txt         # Dependências do projeto
```

## Integração com Rádio

O SoundWave Player inclui integração com um aplicativo de rádio terminal. Quando o comando `radio` é executado:

1. A música atual é pausada automaticamente (se estiver tocando)
2. O aplicativo de rádio é aberto em uma nova janela
3. Ao fechar o rádio, a interface do player é restaurada
4. A música é retomada automaticamente (se estava tocando antes)

## Testes

Para rodar os testes:

```bash
python -m unittest discover testes
```

## Dependências

O projeto utiliza as seguintes bibliotecas externas:
- `requests`: Para requisições HTTP
- `psutil`: Para monitoramento do sistema
- `pyfiglet`: Para texto ASCII art
- `windows-curses`: Para compatibilidade do curses no Windows
- `pygame`: Para reprodução de áudio
- `numpy`: Para processamento de espectro
- `pyaudio`: Para captura de áudio

---

Desenvolvido para estudo e uso pessoal.