# SoundWave Player: Música no Terminal para Todos

Player de música para terminal em Python, com interface dinâmica, espectro visual, controle por comandos, playlist, histórico, monitoramento de CPU/RAM e integração com rádio online e YouTube.

## Introdução

No mundo digital de hoje, onde interfaces gráficas complexas e softwares que demandam muitos recursos são a norma, o SoundWave Player surge como uma alternativa propositalmente minimalista e eficiente. Desenvolvido em Python, este projeto visa oferecer uma experiência musical completa diretamente no terminal, priorizando a leveza, a acessibilidade e o controle direto. Este documento detalha as motivações por trás das escolhas de design, as funcionalidades implementadas e um guia completo para colocar o player em funcionamento.

## O Porquê do Terminal: Acessibilidade e Eficiência

A escolha de desenvolver o SoundWave Player para o terminal não foi arbitrária; ela reflete uma filosofia de design focada na **eficiência, estabilidade e acessibilidade**.

### 1. Desempenho e Requisitos de Hardware Reduzidos

Ambientes gráficos modernos, com suas animações, transições e elementos visuais ricos, consomem uma quantidade significativa de recursos de CPU e RAM. Para usuários com **hardware mais antigo ou limitado**, essa demanda pode resultar em lentidão, travamentos e uma experiência frustrante.

O SoundWave Player, ao operar no terminal, elimina a necessidade de renderizar uma interface gráfica complexa. As bibliotecas como `curses` são otimizadas para manipulação de texto em console, resultando em:

* **Menor consumo de CPU**: A ausência de uma interface gráfica pesada significa que o processador pode se concentrar na reprodução de áudio e nas funcionalidades do player, em vez de gerenciar elementos visuais. O player inclusive monitora e exibe o uso de CPU e RAM em tempo real.
* **Menor consumo de RAM**: A memória é utilizada principalmente para os dados do áudio e as estruturas de dados do programa, não para texturas ou elementos visuais complexos. Isso é crucial para máquinas com pouca RAM.
* **Compatibilidade ampla**: Um aplicativo de terminal tende a ser mais portátil e a funcionar em uma gama maior de sistemas operacionais (Linux, macOS, Windows via `windows-curses`), sem a necessidade de drivers gráficos específicos ou dependências de frameworks GUI.

### 2. Estabilidade e Foco

Ambientes de terminal são inerentemente mais estáveis para certas aplicações, pois há menos camadas de software entre o programa e o sistema operacional. Isso pode se traduzir em:

* **Menos bugs relacionados à GUI**: Elimina uma grande classe de problemas comuns em aplicações de desktop, como falhas de renderização, problemas de escala ou incompatibilidade com diferentes ambientes gráficos.
* **Experiência consistente**: A interface será a mesma em qualquer terminal compatível, garantindo que o usuário tenha sempre a mesma experiência visual e interativa.
* **Foco na funcionalidade**: Ao desviar a atenção do design visual extravagante, o desenvolvimento pode se concentrar puramente na robustez das funcionalidades e na experiência de áudio.

### 3. Aprendizado e Habilidade Técnica

Para desenvolvedores e entusiastas, a criação de uma aplicação de terminal é um excelente exercício de programação de baixo nível e compreensão de como as interfaces de usuário realmente funcionam. Também serve como uma ferramenta "nerd-friendly" que pode ser apreciada por aqueles que preferem interagir com seus sistemas de forma mais direta.

## 🚀 Instalação e Configuração do Ambiente

Para executar o SoundWave Player, é crucial preparar o ambiente com as versões e programas corretos. Siga este guia detalhadamente.

### **Pré-requisitos**
* **Sistema Operacional:** Windows (o guia foi focado nesta plataforma), Linux, macOS
* **Terminal:** PowerShell é recomendado para Windows
* **Git:** Para clonar o projeto
* **Python 3.11:** Versão específica necessária para compatibilidade

---

### **Passo 1: Instalar Python 3.11**

O projeto **exige o Python 3.11** devido a incompatibilidades de uma de suas dependências (`pydub`) com versões mais recentes.

1. Baixe o instalador do Python 3.11.9 aqui: **[Python 3.11.9 para Windows](https://www.python.org/downloads/release/python-3119/)**
2. Execute o instalador. Na primeira tela, **marque a caixa "Add python.exe to PATH"**. Esta etapa é fundamental.
3. Prossiga com a instalação padrão.

### **Passo 2: Instalar FFmpeg e MPV**

Estas ferramentas externas são **obrigatórias** para o funcionamento completo.

1. **FFmpeg:** (Necessário para `pydub` processar áudios)
   - Baixe a versão "release-full" em: [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
   - Extraia para uma pasta permanente (ex: `C:\ffmpeg`)
   - Adicione a subpasta `bin` ao PATH do Windows (ex: `C:\ffmpeg\bin`)

2. **MPV:** (Necessário para a reprodução do YouTube e Rádio)
   - Baixe o MPV em: [https://mpv.io/installation/](https://mpv.io/installation/)
   - Extraia para uma pasta permanente (ex: `C:\mpv`)
   - Adicione esta pasta ao PATH do Windows (ex: `C:\mpv`)

> **Como adicionar ao PATH:** Pressione `Win`, digite "variáveis de ambiente", clique em "Editar as variáveis de ambiente do sistema" -> "Variáveis de Ambiente...", selecione "Path" na lista de baixo e clique em "Editar". Adicione uma nova entrada para cada caminho.

### **Passo 3: Clonar e Preparar o Projeto**

1. Abra um terminal (PowerShell) e clone o repositório
2. Crie o ambiente virtual usando o **Python 3.11**:
```powershell
# Cria o ambiente virtual na pasta .venv
py -3.11 -m venv .venv
```

3. **Habilite a execução de scripts no PowerShell** (só precisa ser feito uma vez):
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Pressione `S` e `Enter` para confirmar.

4. **Ative o ambiente virtual:**
```powershell
.\.venv\Scripts\activate
```
Seu prompt deverá mostrar `(.venv)` no início.

5. **Instale todas as dependências Python:**
```powershell
pip install -r requirements.txt
```

## 🏃 Como Executar

Com o ambiente configurado e ativado (`(.venv)` visível no prompt), inicie o programa:

```bash
python main.py
```

## ⌨️ Comandos e Atalhos

A interface é controlada inteiramente pelo teclado.

| Tecla(s) | Ação |
|----------|------|
| 1 | Abrir um diretório (colar caminho) |
| 2 / Enter | Tocar / Pausar a música selecionada |
| 3 | Música Anterior |
| 4 | Próxima Música |
| ↑ ↓ ← → | Navegar na lista de músicas |
| + / = | Aumentar Volume |
| - | Diminuir Volume |
| i | Abrir o Navegador de Arquivos |
| b | Buscar músicas na biblioteca |
| t | Filtrar biblioteca por categoria |
| s | Saltar para uma música pelo número |
| o | Ordenar a playlist atual |
| l | Listar e carregar playlists salvas |
| c | Criar uma nova playlist |
| a | Adicionar música atual a uma playlist |
| d | Remover música de uma playlist |
| f | Favoritar / Desfavoritar música |
| h | Ver histórico de reprodução |
| e | Abrir controles de Equalização (EQ) |
| x | Mostrar tela de Estatísticas |
| y | Abrir modo de reprodução do YouTube |
| r | Abrir modo Rádio |
| q | Sair do programa |

### Comandos de Texto Tradicionais

Você também pode usar comandos de texto digitando no prompt inferior:

- `play` ou `p`: tocar/pausar música
- `pause`: pausar música
- `stop`: parar música
- `prox` ou `next`: próxima música
- `ant` ou `prev`: música anterior
- `vol <valor>`: definir volume (0.0 a 1.0)
- `dir`: carregar diretório de músicas (cole o caminho)
- `radio`: abrir aplicativo de rádio integrado
- `sair`: fechar player

## 🎵 Funcionalidades

### Player de Música
- Reprodução de arquivos de áudio locais
- Controle de volume e navegação
- Espectro visual em tempo real
- Suporte a múltiplos formatos de áudio (mp3, wav, flac, ogg, m4a)
- Equalizador de áudio (grave, médio, agudo)

### 📻 Integração com Rádio
- Acesso ao aplicativo de rádio terminal integrado
- Pausa automática da música ao abrir o rádio
- Retomada automática ao fechar o rádio
- Interface seamless entre os dois modos

### 🎬 Integração com YouTube
- Reprodução de vídeos do YouTube (apenas áudio)
- Busca e seleção de vídeos
- Controle integrado com a interface principal

### 📊 Monitoramento
- Monitoramento de CPU e RAM do processo
- Exibição de informações do sistema em tempo real

### 📝 Gerenciamento
- Sistema de playlists e favoritos (persistidos diretamente por playlist.py)
- Histórico de músicas reproduzidas (persistido diretamente por historico.py)
- Persistência de dados entre sessões
- Biblioteca de músicas com busca e filtragem por metadados (artista, álbum, gênero, título)
- Ordenação de playlists por diversos critérios

## Escolhas de Arquitetura e Implementação

O SoundWave Player é construído sobre uma arquitetura modular, onde cada componente tem uma responsabilidade bem definida. Isso facilita a manutenção, a adição de novas funcionalidades e a compreensão do código.

### 1. Reprodução de Áudio (`audio.py`)

* **`pygame.mixer`**: A escolha de `pygame.mixer` para a reprodução de áudio se deve à sua simplicidade e eficiência para tocar arquivos de música. Embora `pygame` seja conhecido por desenvolvimento de jogos, seu módulo de mixer é leve e performático para áudio, suportando diversos formatos como MP3, WAV, FLAC e OGG.
* **Espectro Visual (`numpy`, `pydub`)**: A geração do espectro visual é uma funcionalidade que enriquece a experiência no terminal.
    * `pydub` é utilizada para carregar segmentos de áudio e extrair os dados de amostra brutos, que são então processados.
    * `numpy` é fundamental para realizar a Transformada Rápida de Fourier (FFT), convertendo os dados de tempo para o domínio da frequência, permitindo a visualização das barras do espectro. A suavização das barras e a normalização do espectro dinâmico garantem uma visualização fluida e adaptável.
* **`mutagen`**: A biblioteca `mutagen` é empregada para extrair metadados como duração, artista, álbum, gênero e título dos arquivos de áudio. Isso garante que o player possa exibir informações detalhadas sobre a música atual e organizar a biblioteca.
* **Processamento em Thread**: O núcleo de áudio opera em sua própria thread, usando uma fila (`queue`) para receber comandos. Isso garante que a interface do usuário permaneça sempre fluida e responsiva.

### 2. Interface de Usuário (`src/ui/`)

A pasta `src/ui` contém a lógica para a interface de usuário baseada em `curses`.

* **`ui_core.py`**: É o coração da interface. Ele orquestra a interação entre o player de áudio, o gerenciador de playlists, o histórico e os componentes visuais. O uso do padrão Observer para a comunicação entre o `AudioPlayer` e a `UIPlayer` (através do método `atualizar`) permite que a UI reaja a eventos do player, como mudança de volume ou fim de música, de forma desacoplada.
* **`ui_components.py`**: Este módulo é responsável por desenhar os elementos individuais da interface, como bordas, título (`pyfiglet`), espectro, barra de volume, status da música e o menu inferior. A separação dos componentes de desenho torna o código mais limpo e reutilizável.
* **`ui_utils.py`**: Contém funções auxiliares como a inicialização das cores `curses` e o formato de tempo. A função `uso_recursos` (que utiliza `psutil`) foi realocada para cá para centralizar as utilidades de UI.

### 3. Gerenciamento de Conteúdo e Dados

* **`playlist.py`**: Permite criar, adicionar, remover e ordenar playlists. Ele também é responsável por carregar e salvar o estado das playlists e a lista de favoritos em um arquivo `json` na pasta `data/` do projeto.
* **`historico.py`**: Mantém um registro das músicas reproduzidas, oferecendo funcionalidades como `adicionar`, `anterior` e `estatisticas` (para as músicas mais tocadas). A persistência é gerenciada diretamente pelo próprio módulo, salvando em um arquivo `json` na pasta `data/`.
* **`biblioteca.py`**: Gerencia a coleção de músicas do usuário, permitindo carregar diretórios, listar músicas por artista, álbum ou gênero, e realizar buscas. A implementação de uma **Árvore Binária de Busca** (`ArvoreMusicas`) para títulos demonstra uma preocupação com a eficiência na busca em grandes coleções.
* **`config_manager.py`**: Responsável por salvar e carregar configurações do usuário, como o volume e as preferências de equalização. Este módulo persiste suas configurações em um arquivo oculto no diretório home (`~/.musga_config.json`), não na pasta `data/` do projeto, garantindo que as configurações sejam mantidas entre as sessões.
* **`constants.py`**: Este arquivo na raiz do projeto centraliza a definição de caminhos importantes, como `PASTA_DADOS`, evitando duplicações de código e garantindo que todos os módulos acessem o mesmo local para persistência de dados.

### 4. Integração com Ferramentas Externas

* **Rádio e YouTube (`radio_terminal/`, `youtube_integration.py`)**: A inclusão de módulos separados para rádio e YouTube amplia a funcionalidade. Eles são executados como subprocessos, permitindo que o player principal pause a música, entregue o controle e retome a reprodução automaticamente ao final. A comunicação com `mpv` é um exemplo de como orquestrar ferramentas externas poderosas.
* **`MPVIPCClient`**: Esta classe permite a comunicação com o MPV (um player de mídia leve e de código aberto) via IPC (Inter-Process Communication). Isso é crucial para o rádio poder controlar o MPV e obter metadados das estações, como o título da música sendo transmitida.
* **Monitoramento de Rede**: O `NetworkMonitor` dentro do módulo de rádio demonstra uma preocupação com a experiência do usuário, exibindo o uso de rede em tempo real para streams de rádio.

## 📁 Estrutura do Projeto

```
soundwave/
│
├── .venv/                 # Pasta do ambiente virtual Python
├── constants.py           # Define PASTA_DADOS e outras constantes globais
├── data/                  # Armazena estado_player.json, favoritos.json, historico.json
│   ├── estado_player.json # Estado do player e playlists salvas
│   ├── favoritos.json     # Lista de favoritos
│   └── historico.json     # Histórico de reprodução
├── radio_terminal(bonus)/ # Módulo bônus para rádio online
│   ├── radio.py           # Aplicativo de rádio integrado
│   └── ...                # Outros arquivos do rádio (e.g., radios.txt)
├── src/                   # Contém todo o código-fonte principal
│   ├── __pycache__/
│   ├── ui/                # Módulos da interface do usuário (curses)
│   │   ├── __pycache__/
│   │   ├── __init__.py
│   │   ├── ui_components.py # Componentes visuais da UI
│   │   ├── ui_core.py       # Lógica principal da UI e interação
│   │   └── ui_utils.py      # Funções utilitárias da UI (inicia cores, uso_recursos)
│   ├── __init__.py
│   ├── audio.py           # Player de áudio e espectro
│   ├── biblioteca.py      # Gerenciamento da biblioteca musical
│   ├── comandos.py        # Interpretação e execução de comandos
│   ├── config_manager.py  # Gerenciamento de configurações
│   ├── historico.py       # Histórico de músicas tocadas (com persistência própria)
│   ├── playlist.py        # Gerenciamento de playlists e favoritos (com persistência própria)
│   ├── recursos.py        # Monitoramento CPU/RAM do processo (deprecated, use ui_utils)
│   ├── utils.py           # Funções auxiliares (como formatar_tempo)
│   └── youtube_integration.py # Integração com YouTube
├── testes/                # Testes unitários
│   ├── test_audio.py
│   ├── test_biblioteca.py
│   └── test_playlist.py
├── main.py                # Arquivo principal para iniciar o player
├── requirements.txt       # Dependências do projeto
└── README.md              # Este arquivo
```

## Integração com Rádio e YouTube

### Rádio Online
O SoundWave Player inclui integração com um aplicativo de rádio terminal. Quando o comando `radio` ou tecla `r` é executado:

- A música atual é pausada automaticamente (se estiver tocando)
- O aplicativo de rádio é aberto em uma nova janela
- Ao fechar o rádio, a interface do player é restaurada
- A música é retomada automaticamente (se estava tocando antes)

### YouTube
A integração com YouTube permite:

- Buscar e reproduzir vídeos do YouTube (apenas áudio)
- Interface integrada para seleção de vídeos
- Controle seamless entre música local e YouTube

## 🧪 Testes

Para rodar os testes unitários e garantir a integridade dos módulos:

```bash
python -m unittest discover testes
```

## 📦 Dependências

O projeto utiliza as seguintes bibliotecas externas:

### Dependências Principais
- **pygame**: Para reprodução de áudio
- **numpy**: Para processamento de espectro
- **psutil**: Para monitoramento do sistema (CPU/RAM)
- **windows-curses**: Para compatibilidade do curses no Windows
- **pyfiglet**: Para texto ASCII art (título)
- **requests**: Para requisições HTTP (rádio online)
- **pydub**: Para manipulação de segmentos de áudio (espectro, equalização)
- **mutagen**: Para extração de metadados de arquivos de áudio (duração, artista, título, etc.)
- **yt-dlp**: Para obter informações de vídeos do YouTube
- **pywin32**: Para funcionalidades de IPC no Windows

## Conclusão

O SoundWave Player é mais do que apenas um tocador de música no terminal; é um projeto que abraça a filosofia de "fazer mais com menos". 
Suas escolhas de design, desde a interface de texto até a modularidade do código e a integração com ferramentas eficientes como `pygame.mixer` e `mpv`,
visam proporcionar uma experiência musical acessível e robusta, especialmente para aqueles com recursos de hardware limitados. Ele prova que não é preciso
 uma interface complexa para desfrutar plenamente da sua biblioteca musical e do mundo do rádio online e YouTube.