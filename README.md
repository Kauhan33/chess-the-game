# Chess - The Game

Xadrez 3D low-poly em Python, para 2 jogadores na mesma tela, contra a CPU ou em rede local. Regras oficiais completas e pipeline gráfico próprio, escrito sobre pygame e numpy: matrizes, malhas, iluminação, sombras, partículas e clique por raio estão todos no código, sem motor pronto.

Projeto da atividade A3 de Computação Gráfica e Realidade Virtual, Grupo 09.

![Partida em andamento](docs/img/tela_partida.png)

## O que o jogo tem

- Roque, en passant, promoção, xeque, xeque-mate, afogamento e empates.
- Relógio sem limite, Blitz 3+2, Blitz 5, Rápida 10+0, Clássica 30 e Clássica 15+10, e placar da série entre partidas.
- Caminhos válidos por matriz de cores. Peças sob ameaça e rei em xeque ganham cor e forma.
- Câmera que orbita e aproxima, com clique correto em qualquer ângulo.
- Partida inteira por mouse ou por teclado.
- Modo didático (F4), que mostra as matrizes e o raio do mouse ao vivo.

### Novo na versão 1.1

- **Modos Treinamento e Partida.** As regras são as mesmas. O modo Partida esconde as dicas.
- **CPU** nos níveis Easy, Medium, Hard e Hardcore, com a cor escolhida por quem joga.
- **Rede local**, sem servidor: um cria a sala e o outro digita um código de 7 caracteres.
- **Contas** com senha, guardadas neste computador, e botão de convidado.
- **Histórico** das últimas 50 partidas da conta, com estatísticas, PGN e posição final.
- **Copiar o PGN** da partida.
- **Arrastar a peça**, além de clicar, e **virar o tabuleiro**.

## Como jogar cada modo

Ao abrir, entre em uma conta ou escolha "Jogar como convidado". O convidado joga tudo, mas as partidas dele não ficam guardadas.

No menu, "Adversário" escolhe com quem jogar, e "Modo" escolhe o que a tela mostra:

| Modo | O que aparece | Lance ilegal |
|---|---|---|
| Treinamento (padrão) | Peça selecionada, caminhos, capturas, ameaças, xeque e último lance | Recusado, com o motivo, e a casa treme |
| Partida | Só a peça selecionada, o cursor e o último lance. A planilha omite `+` e `#` até o fim | Recusado, sempre com "Lance inválido." |

| Adversário | Como jogar |
|---|---|
| 2 jogadores | Digite os nomes, escolha o tempo e a câmera, e aperte "Iniciar partida". Cada um joga na sua vez, na mesma tela. |
| Contra a CPU | Escolha o nível, a sua cor e o tempo. A placa dela mostra "Pensando" enquanto ela busca o lance. O Hardcore pensa cerca de 4 s por lance. |
| Rede local | Um aperta "Criar sala" e passa o código. O outro aperta "Entrar com código" e digita. Veja a seção abaixo. |

### Rede local e firewall

Os dois computadores precisam estar na mesma rede. Não há servidor: o código da sala é o endereço IP de quem criou, escrito em 7 caracteres, e a conexão é direta, em TCP, na porta 50507.

- Quem cria a sala escolhe o modo e o tempo, que valem para os dois, joga de brancas na primeira partida e decide o resultado.
- Se o outro computador não conseguir entrar, o motivo mais provável é o firewall de quem criou a sala. No Windows, permita o jogo quando ele perguntar, ou libere a porta TCP 50507 na rede privada.
- Redes de escola, empresa e hotel podem impedir que dois computadores se vejam, mesmo no mesmo Wi-Fi.
- O tráfego é JSON sem cifra, e a sala não tem senha. É para jogar com quem está ao lado, em uma rede em que você confia.

**Não verificado até aqui:** conexão entre dois computadores diferentes, passagem pelo firewall e rede em janela real. A sala foi testada em `127.0.0.1` e pelo IP real da rede local, em um único computador. Detalhes na seção 7.9 da documentação.

### Onde ficam os dados

Contas e histórico ficam só neste computador, em arquivos JSON. A senha nunca é gravada, só o resultado de PBKDF2-HMAC-SHA256 com 600 mil iterações e sal próprio.

| Sistema | Pasta |
|---|---|
| Windows | `%APPDATA%\ChessTheGame` |
| macOS | `~/Library/Application Support/ChessTheGame` |
| Linux | `~/.local/share/chess-the-game` |

Cada conta guarda as últimas 50 partidas. Arquivo corrompido é guardado com outro nome, e o jogo segue com a lista vazia. A variável de ambiente `CHESS_THE_GAME_DATA` troca a pasta, e é o que os testes usam. Nada disso vai para o repositório.

## Instalação

Precisa de Python 3.10 ou mais novo. As dependências são `pygame` e `numpy`.

Baixe o código:

```
git clone https://github.com/Kauhan33/chess-the-game.git
cd chess-the-game
```

No Windows:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

No Linux e no macOS:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

O CI em `.github/workflows/testes.yml` roda os testes em Python 3.10 e 3.12, no Windows, no Linux e no macOS, sem janela. Na versão 1.1.1, todas as combinações passaram, sem os testes `slow`. O jogo só foi aberto em janela real e medido em Python 3.12 no Windows 11. O capítulo 7 traz os detalhes.

### Executável, sem instalar Python (Windows)

No Windows, o jeito mais simples é baixar o `ChessTheGame.exe` na [página de releases](https://github.com/Kauhan33/chess-the-game/releases/latest): um arquivo único, que abre o jogo sem precisar de Python. Para gerar esse arquivo a partir do código, com `tools/gerar_executavel.py`:

```
pip install pyinstaller pillow
python tools/gerar_executavel.py
```

## Controles

| Entrada | Ação |
|---|---|
| Clique esquerdo | Seleciona a peça e joga |
| Clique esquerdo, arrastando | Leva a peça até o destino e joga ao soltar |
| Botão direito, arrastando | Gira a câmera |
| Roda do mouse | Aproxima e afasta a câmera. No histórico, rola o que está sob o mouse |
| Setas | Movem o cursor, conforme a visão |
| Enter ou Espaço | Confirma, como o clique |
| Esc | Cancela a seleção. Sem seleção, abre a pausa |
| P | Pausa a partida. Em rede, abre as opções, sem parar o relógio |
| R | Reinicia, depois de confirmar. Não vale em rede |
| T | Liga ou desliga o giro por turno. Só em 2 jogadores |
| V | Volta à vista padrão |
| F | Vira o tabuleiro |
| C | Copia o PGN da partida |
| A | Aceita a proposta de empate recebida em rede |
| H ou F1 | Mostra a ajuda |
| F3 | Mostra FPS e polígonos |
| F4 | Modo didático |
| F11 | Liga ou desliga a tela cheia |

## Testes

```
pip install -r requirements-dev.txt
python -m pytest                  # todos, inclusive o perft profundo e o macaco longo, que demoram
python -m pytest -m "not slow"    # sem os testes demorados
```

Os testes rodam sem abrir janela, com os dados em pasta temporária e a rede só em `127.0.0.1`. O resultado da última execução, com a cobertura, está em `docs/07-plano-de-testes.md`.

Para ver o jogo em janela real e medir o FPS:

```
python tools/demo_automatica.py
python tools/demo_automatica.py --cpu hardcore
```

## Estrutura

```
main.py          inicia o jogo
xadrez/
  core/          regras do jogo e CPU. Python puro, sem pygame e sem numpy
  data/          contas e histórico em disco. Python puro
  net/           sala em rede local. Python puro
  graphics/      computação gráfica. numpy e pygame, sem conhecer as regras
  ui/            cenas, HUD e entrada. Liga tudo
tests/           testes de core, data, net, graphics, ui, da regra de camadas e de ataque
tools/           benchmarks, demonstração, geração de prints, documentação e executável
docs/            documentação, diagramas UML e imagens
```

A regra de dependência é `ui -> core, data, net, graphics` e `net -> core`. `core` e `graphics` nunca se importam, `data` e `net` também não, e `tests/test_arquitetura.py` garante isso.

## Documentação

| Capítulo | Conteúdo |
|---|---|
| [1. Visão e requisitos](docs/01-visao-e-requisitos.md) | Escopo, regras, modos, público-alvo, RF e RNF |
| [2. Protótipos de tela](docs/02-prototipos-ui-ux.md) | Wireframes, prints e justificativa de cada tela |
| [3. Casos de uso](docs/03-casos-de-uso.md) | Diagrama e especificação dos fluxos |
| [4. Modelagem UML](docs/04-modelagem-uml.md) | Diagramas de classes, sequência e estados |
| [5. Arquitetura](docs/05-arquitetura.md) | Camadas, decisões, modelo de ameaça e limites conhecidos |
| [6. Computação gráfica](docs/06-computacao-grafica.md) | Cada conceito: fórmula, código e como mostrar no jogo |
| [7. Plano de testes](docs/07-plano-de-testes.md) | Casos de teste, resultados reais, cobertura e RNF |
| [8. Matriz de rastreabilidade](docs/08-matriz-rastreabilidade.md) | RF, RNF, UC, CT e diagramas cruzados |
| [9. Kanban](docs/09-kanban.md) | Tarefas e evolução real pelo git |
| [10. Roteiro da apresentação](docs/10-roteiro-apresentacao.md) | Divisão da fala, demonstração, planos B e perguntas prováveis |
| [11. Guia de estudo](docs/11-guia-de-estudo.md) | O que cada integrante precisa ler e explicar, com experimentos testados e perguntas da banca |

### Gerar a documentação de novo

```
python tools/gerar_documentacao.py
```

Refaz, em ordem, os prints, os wireframes, os diagramas, os testes, a matriz e os PDFs. Tudo o que é resultado sai da execução real. Precisa de:

- Java e `tools/.cache/plantuml.jar`, para os diagramas ([PlantUML](https://github.com/plantuml/plantuml/releases));
- Chrome ou Edge, para os PDFs.

Os PDFs ficam em `entrega/`, que não vai para o repositório. A capa com os dados do grupo é lida de `entrega/dados_capa.json`. Sem esse arquivo, sai uma capa genérica.
