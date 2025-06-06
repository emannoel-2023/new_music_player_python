# SoundWave Player: Música no Terminal para Todos

## Introdução

No mundo digital de hoje, onde interfaces gráficas complexas e softwares que demandam muitos recursos são a norma, o SoundWave Player surge como uma alternativa propositalmente minimalista e eficiente. Desenvolvido em Python, este projeto visa oferecer uma experiência musical completa diretamente no terminal, priorizando a leveza, a acessibilidade e o controle direto. Este artigo detalha as motivações por trás das escolhas de design e as funcionalidades implementadas, explicando o "porquê" de cada decisão.

## O Porquê do Terminal: Acessibilidade e Eficiência

A escolha de desenvolver o SoundWave Player para o terminal não foi arbitrária; ela reflete uma filosofia de design focada na **eficiência e na acessibilidade**.

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

## Escolhas de Arquitetura e Implementação

O SoundWave Player é construído sobre uma arquitetura modular, onde cada componente tem uma responsabilidade bem definida. Isso facilita a manutenção, a adição de novas funcionalidades e a compreensão do código.

### 1. Reprodução de Áudio (`audio.py`)

* **`pygame.mixer`**: A escolha de `pygame.mixer` para a reprodução de áudio se deve à sua simplicidade e eficiência para tocar arquivos de música. Embora `pygame` seja conhecido por desenvolvimento de jogos, seu módulo de mixer é leve e performático para áudio, suportando diversos formatos como MP3, WAV, FLAC e OGG.
* **Espectro Visual (`numpy`, `pydub`)**: A geração do espectro visual é uma funcionalidade que enriquece a experiência no terminal.
    * `pydub` é utilizada para carregar segmentos de áudio e extrair os dados de amostra brutos, que são então processados.
    * `numpy`é fundamental para realizar a Transformada Rápida de Fourier (FFT), convertendo os dados de tempo para o domínio da frequência, permitindo a visualização das barras do espectro. A suavização das barras e a normalização do espectro dinâmico garantem uma visualização fluida e adaptável.
* **Mutagen**: A biblioteca `mutagen` é empregada para extrair metadados como duração, artista, álbum, gênero e título dos arquivos de áudio. Isso garante que o player possa exibir informações detalhadas sobre a música atual e organizar a biblioteca.

### 2. Interface de Usuário (`src/ui/`)

A pasta `src/ui` contém a lógica para a interface de usuário baseada em `curses`.

* **`ui_core.py`**: É o coração da interface. Ele orquestra a interação entre o player de áudio, o gerenciador de playlists, o histórico e os componentes visuais. O uso do padrão Observer para a comunicação entre o `AudioPlayer` e a `UIPlayer` (através do método `atualizar`) permite que a UI reaja a eventos do player, como mudança de volume ou fim de música, de forma desacoplada.
* **`ui_components.py`**: Este módulo é responsável por desenhar os elementos individuais da interface, como bordas, título (`pyfiglet` ), espectro, barra de volume, status da música e o menu inferior. A separação dos componentes de desenho torna o código mais limpo e reutilizável.
* **`ui_utils.py`**: Contém funções auxiliares como a inicialização das cores `curses` e o formato de tempo. A função `uso_recursos`  (que utiliza `psutil` ) foi realocada para cá para centralizar as utilidades de UI.
* **`ui_state.py`**: Gerencia a persistência de dados específicos da interface, como o histórico de reprodução e a lista de favoritos. Ele utiliza `json` para salvar e carregar esses dados em arquivos na pasta `data/`.

### 3. Gerenciamento de Conteúdo

* **`playlist.py`**: Permite criar, adicionar, remover e ordenar playlists. Ele também é responsável por carregar o estado das playlists e favoritos de um arquivo `json`.
* **`historico.py`**: Mantém um registro das músicas reproduzidas, oferecendo funcionalidades como `adicionar`, `anterior` e `estatisticas` (para as músicas mais tocadas). A persistência é gerenciada por `ui_state.py`.
* **`biblioteca.py`**: Gerencia a coleção de músicas do usuário, permitindo carregar diretórios, listar músicas por artista, álbum ou gênero, e realizar buscas. A implementação de uma árvore binária de busca (`ArvoreMusicas`) para títulos  demonstra uma preocupação com a eficiência na busca em grandes coleções.
* **`config_manager.py`**: Responsável por salvar e carregar configurações do usuário, como o volume e as preferências de equalização, garantindo que as configurações sejam mantidas entre as sessões.

### 4. Integração com Rádio (`radio_terminal/`)

A inclusão de um módulo de rádio separado (`radio.py`) é um "bônus" que amplia a funcionalidade do player.

* **Execução Separada**: O rádio é executado como um subprocesso em uma nova janela de terminal. Isso permite que o player principal pause a música atual, entregue o controle ao rádio e, ao final, retome a reprodução automaticamente, proporcionando uma transição suave.
* **`MPVIPCClient`**: Esta classe permite a comunicação com o MPV (um player de mídia leve e de código aberto) via IPC (Inter-Process Communication). Isso é crucial para o rádio poder controlar o MPV e obter metadados das estações, como o título da música sendo transmitida.
* **Monitoramento de Rede**: O `NetworkMonitor`  dentro do módulo de rádio demonstra uma preocupação com a experiência do usuário, exibindo o uso de rede em tempo real para streams de rádio.

## Conclusão

O SoundWave Player é mais do que apenas um tocador de música no terminal; é um projeto que abraça a filosofia de "fazer mais com menos". Suas escolhas de design, desde a interface de texto até a modularidade do código e a integração com ferramentas eficientes como `pygame.mixer` e `mpv`, visam proporcionar uma experiência musical acessível e robusta, especialmente para aqueles com recursos de hardware limitados. Ele prova que não é preciso uma interface complexa para desfrutar plenamente da sua biblioteca musical e do mundo do rádio online.

# SoundWave Player: Música no Terminal para Todos

## Introdução

No mundo digital de hoje, onde interfaces gráficas complexas e softwares que demandam muitos recursos são a norma, o SoundWave Player surge como uma alternativa propositalmente minimalista e eficiente. Desenvolvido em Python, este projeto visa oferecer uma experiência musical completa diretamente no terminal, priorizando a leveza, a acessibilidade e o controle direto. Este artigo detalha as motivações por trás das escolhas de design e as funcionalidades implementadas, explicando o "porquê" de cada decisão.

## O Porquê do Terminal: Acessibilidade e Eficiência

A escolha de desenvolver o SoundWave Player para o terminal não foi arbitrária; ela reflete uma filosofia de design focada na **eficiência e na acessibilidade**.

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

## Escolhas de Arquitetura e Implementação

O SoundWave Player é construído sobre uma arquitetura modular, onde cada componente tem uma responsabilidade bem definida. Isso facilita a manutenção, a adição de novas funcionalidades e a compreensão do código.

### 1. Reprodução de Áudio (`audio.py`)

* **`pygame.mixer`**: A escolha de `pygame.mixer` para a reprodução de áudio se deve à sua simplicidade e eficiência para tocar arquivos de música. Embora `pygame` seja conhecido por desenvolvimento de jogos, seu módulo de mixer é leve e performático para áudio, suportando diversos formatos como MP3, WAV, FLAC e OGG.
* **Espectro Visual (`numpy`, `pydub`)**: A geração do espectro visual é uma funcionalidade que enriquece a experiência no terminal.
    * `pydub` é utilizada para carregar segmentos de áudio e extrair os dados de amostra brutos, que são então processados.
    * `numpy` é fundamental para realizar a Transformada Rápida de Fourier (FFT), convertendo os dados de tempo para o domínio da frequência, permitindo a visualização das barras do espectro. A suavização das barras e a normalização do espectro dinâmico garantem uma visualização fluida e adaptável.
* **Mutagen**: A biblioteca `mutagen` é empregada para extrair metadados como duração, artista, álbum, gênero e título dos arquivos de áudio. Isso garante que o player possa exibir informações detalhadas sobre a música atual e organizar a biblioteca.

### 2. Interface de Usuário (`src/ui/`)

A pasta `src/ui` contém a lógica para a interface de usuário baseada em `curses`.

* **`ui_core.py`**: É o coração da interface. Ele orquestra a interação entre o player de áudio, o gerenciador de playlists, o histórico e os componentes visuais. O uso do padrão Observer para a comunicação entre o `AudioPlayer` e a `UIPlayer` (através do método `atualizar`) permite que a UI reaja a eventos do player, como mudança de volume ou fim de música, de forma desacoplada.
* **`ui_components.py`**: Este módulo é responsável por desenhar os elementos individuais da interface, como bordas, título (`pyfiglet`), espectro, barra de volume, status da música e o menu inferior. A separação dos componentes de desenho torna o código mais limpo e reutilizável.
* **`ui_utils.py`**: Contém funções auxiliares como a inicialização das cores `curses` e o formato de tempo. A função `uso_recursos` (que utiliza `psutil`) foi realocada para cá para centralizar as utilidades de UI.
* **Persistência de Dados (Centralizada)**: Anteriormente gerenciada por `ui_state.py`, a persistência de dados como histórico de reprodução e favoritos agora é tratada diretamente pelos módulos `historico.py` e `playlist.py`, utilizando a pasta `data/` na raiz do projeto.

### 3. Gerenciamento de Conteúdo

* **`playlist.py`**: Permite criar, adicionar, remover e ordenar playlists. Ele também é responsável por carregar e salvar o estado das playlists e a lista de favoritos em um arquivo `json` na pasta `data/` do projeto.
* **`historico.py`**: Mantém um registro das músicas reproduzidas, oferecendo funcionalidades como `adicionar`, `anterior` e `estatisticas` (para as músicas mais tocadas). A persistência é gerenciada diretamente pelo próprio módulo, salvando em um arquivo `json` na pasta `data/`.
* **`biblioteca.py`**: Gerencia a coleção de músicas do usuário, permitindo carregar diretórios, listar músicas por artista, álbum ou gênero, e realizar buscas. A implementação de uma árvore binária de busca (`ArvoreMusicas`) para títulos demonstra uma preocupação com a eficiência na busca em grandes coleções.
* **`config_manager.py`**: Responsável por salvar e carregar configurações do usuário, como o volume e as preferências de equalização, garantindo que as configurações sejam mantidas entre as sessões. Este módulo persiste suas configurações em um arquivo oculto no diretório do usuário (`~/.musga_config.json`), não na pasta `data/` do projeto.

### 4. Integração com Rádio (`radio_terminal/`)

A inclusão de um módulo de rádio separado (`radio.py`) é um "bônus" que amplia a funcionalidade do player.

* **Execução Separada**: O rádio é executado como um subprocesso em uma nova janela de terminal. Isso permite que o player principal pause a música atual, entregue o controle ao rádio e, ao final, retome a reprodução automaticamente, proporcionando uma transição suave.
* **`MPVIPCClient`**: Esta classe permite a comunicação com o MPV (um player de mídia leve e de código aberto) via IPC (Inter-Process Communication). Isso é crucial para o rádio poder controlar o MPV e obter metadados das estações, como o título da música sendo transmitida.
* **Monitoramento de Rede**: O `NetworkMonitor` dentro do módulo de rádio demonstra uma preocupação com a experiência do usuário, exibindo o uso de rede em tempo real para streams de rádio.

### 5. Constantes Globais (`constants.py`)

* **`constants.py`**: Este novo arquivo, localizado na raiz do projeto, serve como um ponto centralizado para definir caminhos importantes, como `PASTA_DADOS`. Isso evita duplicações de código e garante que todos os módulos acessem o mesmo local para persistência de dados.

## Conclusão

O SoundWave Player é mais do que apenas um tocador de música no terminal; é um projeto que abraça a filosofia de "fazer mais com menos". Suas escolhas de design, desde a interface de texto até a modularidade do código e a integração com ferramentas eficientes como `pygame.mixer` e `mpv`, visam proporcionar uma experiência musical acessível e robusta, especialmente para aqueles com recursos de hardware limitados. Ele prova que não é preciso uma interface complexa para desfrutar plenamente da sua biblioteca musical e do mundo do rádio online.

# SoundWave Player

Player de música para terminal em Python, com interface dinâmica, espectro visual, controle por comandos, playlist, histórico, monitoramento de CPU/RAM e integração com rádio online.

## Requisitos

-   Python 3.7+

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
Suporte a múltiplos formatos de áudio (mp3, wav, flac, ogg, m4a)
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

Sistema de playlists e favoritos (agora persistidos diretamente por playlist.py)
Histórico de músicas reproduzidas (agora persistido diretamente por historico.py)
Persistência de dados entre sessões
Biblioteca de músicas com busca e filtragem por metadados (artista, álbum, gênero, título)
Ordenação de playlists por diversos critérios
Estrutura do Projeto

soundwave/
│
├── constants.py           # Define PASTA_DADOS e outras constantes globais
├── data/                  # AGORA APENAS AQUI: Armazena estado_player.json, favoritos.json, historico.json
│   ├── estado_player.json # Estado do player e playlists salvas
│   ├── favoritos.json     # Lista de favoritos
│   └── historico.json     # Histórico de reprodução
├── radio_terminal(bonus)/
│   ├── radio.py           # Aplicativo de rádio integrado
│   └── ...                # Outros arquivos do rádio (e.g., radios.txt)
├── src/
│   ├── __pycache__/
│   ├── ui/
│   │   ├── __pycache__/
│   │   ├── __init__.py
│   │   ├── ui_components.py # Componentes visuais da UI
│   │   ├── ui_core.py       # Lógica principal da UI e interação
│   │   └── ui_utils.py      # Funções utilitárias da UI (inicia cores, uso_recursos)
│   ├── __init__.py
│   ├── audio.py           # Player de áudio e espectro
│   ├── biblioteca.py      # Gerenciamento da biblioteca musical
│   ├── comandos.py        # Interpretação e execução de comandos
│  	├── config_manager.py  # Gerenciamento de configurações
│  	├── historico.py       # Histórico de músicas tocadas (agora com persistência própria)
│  	├── playlist.py        # Gerenciamento de playlists e favoritos (agora com persistência própria)
│  	├── recursos.py        # Monitoramento CPU/RAM do processo (deprecated, use ui_utils ou psutil diretamente)
│  	└── utils.py           # Funções auxiliares (como formatar_tempo)
├── testes/
│   ├── test_audio.py
│   ├── test_biblioteca.py
│   └── test_playlist.py
├── main.py                # Arquivo principal para iniciar o player
├── requirements.txt       # Dependências do projeto
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
