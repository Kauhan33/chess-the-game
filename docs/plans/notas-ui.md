# Notas da interface: justificativa gráfica

Material de apoio para o documento de entrega. Tudo aqui descreve o que está no código
(`xadrez/ui/theme.py`, `xadrez/ui/hud.py`) e nos prints de `docs/img/`.

## Conceito

**Mesa de torneio sob a luz de um abajur.** O tabuleiro e as peças já tinham essa cara: nogueira
escura, casas cor de madeira, marfim e ébano. O HUD não é um painel colado por cima. Ele é o
resto da mesa, com os objetos que existem em uma partida de torneio de verdade:

- **Placa de jogador** para cada lado, com nome, cor, relógio, capturas e pontos.
- **Planilha de anotação** de papel pautado entre as duas placas, com os lances em SAN.
- **Filete de latão** separando o painel do tabuleiro, o mesmo que o tabuleiro tem em volta das casas.

O elemento que fica na memória é um só: **a luz do abajur acompanha quem joga**. A placa de quem
tem a vez acende, com fundo claro e brilho quente em volta. A outra fica na sombra. A troca é um
fade de 0,28 s, que acontece junto com o relógio, assim que o lance é feito.

## Paleta

Todas as cores são quentes e saem do mesmo mundo. O latão é a única cor de destaque do HUD.

| Papel | Nome no código | Hex |
|---|---|---|
| Madeira mais funda, sombra do filete | `WALNUT_SHADOW` | `#17100B` |
| Nogueira, fundo de placa e de painel | `WALNUT` | `#2A1B12` |
| Face de botão | `WALNUT_RAISED` | `#422C1C` |
| Borda de placa na sombra | `WALNUT_EDGE` | `#6C4E2E` |
| Latão escuro, borda de placa acesa | `BRASS_DARK` | `#8F6D33` |
| Latão, filete e bordas em foco | `BRASS` | `#C8A15A` |
| Latão claro, títulos e anel de foco | `BRASS_BRIGHT` | `#EBCB8B` |
| Marfim, texto principal sobre madeira (é a cor das peças) | `IVORY` | `#F0E4C8` |
| Papel da planilha | `PAPER` | `#E9DCBE` |
| Pauta da planilha | `PAPER_RULE` | `#C7B694` |
| Margem da planilha | `PAPER_MARGIN` | `#BA705C` |
| Tinta, texto sobre o que está claro | `INK` | `#24170E` |
| Tinta suave, texto secundário sobre claro | `INK_SOFT` | `#543A1E` |
| Texto secundário sobre madeira | `TEXT_MUTED` | `#C9B89A` |
| Alerta sobre escuro (tempo baixo) | `ALERT_ON_DARK` | `#FF8A70` |
| Alerta sobre claro (tempo baixo) | `ALERT_ON_LIGHT` | `#8C180E` |
| Placa de alerta (xeque) | `ALERT_PLATE` | `#96241A` |
| Luz do abajur em volta da placa da vez | `LAMP_GLOW` | `#FFBA68` |
| Placa acesa, do topo à base | `PLATE_LIT` | `#F7E0AA` a `#DEB66E` |
| Placa na sombra, do topo à base | `PLATE_SHADE` | `#322116` a `#22160F` |

### Matriz de cores do tabuleiro

O tema entra em `ColorMatrix(palette=...)`. Os tons foram deslocados para o quente, para
parecerem iluminados pelo mesmo abajur.

| Estado | Hex | Forma que acompanha a cor (RNF04) |
|---|---|---|
| `LAST_MOVE` último lance | `#C6AC54` | nenhuma: é só contexto |
| `PATH` caminho | `#5CAC6C` | ponto |
| `CAPTURE` captura | `#D84E3C` | anel |
| `THREAT` ameaça | `#EC8A2C` | triângulo, e a peça ganha tint pulsante |
| `CHECK` xeque | `#E02C2C` | rei com tint vermelho; atacantes com cantos |
| `SELECTED` seleção | `#F4CE60` | cantos, e a peça é levantada |
| `CURSOR` cursor | `#68AADE` | cantos |

O azul do cursor é a única cor fria da tela, de propósito: em um tabuleiro todo quente, é o que
se acha mais rápido. A casa selecionada não vira azul com o mouse em cima, porque ela é a que o
jogador precisa reconhecer.

### Contraste real

Razão de contraste WCAG, calculada com os valores do código. Os pares principais também estão no
teste `tests/ui/test_ui_tema.py`, que exige pelo menos 4,5:1.

| Par | Razão |
|---|---|
| Relógio em tinta sobre a placa acesa (ponto mais escuro do degradê) | 9,2:1 |
| Relógio em texto secundário sobre a placa na sombra (ponto mais claro do degradê) | 7,9:1 |
| Tempo baixo sobre a placa acesa | 4,9:1 |
| Tempo baixo sobre a placa na sombra | 6,7:1 |
| Tinta sobre o papel da planilha | 12,8:1 |
| Tinta suave sobre o papel | 7,7:1 |
| Marfim sobre botão | 10,3:1 |
| Texto secundário sobre nogueira | 8,5:1 |
| Marfim sobre a placa de alerta | 6,5:1 |

## Tipografia

Somente fontes do sistema, sem nada baixado. Cada papel tem uma lista de alternativas, e no fim
de todas está a fonte padrão do pygame. O jogo abre e desenha acentos mesmo sem nenhuma delas
(há teste disso).

| Papel | Windows | Alternativas | Onde aparece |
|---|---|---|---|
| Serifa de título, em negrito | Palatino Linotype | Book Antiqua, Palatino, P052, URW Palladio, Georgia, DejaVu Serif, Liberation Serif, Times New Roman | título, nomes, lances, faixa de avisos, resultado |
| Sem serifa de rótulo | Franklin Gothic Medium | Helvetica Neue, Avenir Next, Noto Sans, DejaVu Sans, Liberation Sans, Tahoma, Verdana | rótulos, botões, teclas, ajuda |
| Números do relógio | Franklin Gothic Medium | as mesmas, em negrito | relógio e pontos da série |
| Monoespaçada | Consolas | Menlo, DejaVu Sans Mono, Liberation Mono, Lucida Console, Courier New | painéis F3 e F4 |

- **Palatino** vem da caligrafia e tem algarismos alinhados, o que serve à planilha. Tem o tom
  de um documento de torneio. Georgia, a escolha mais óbvia em serifa, tem algarismos que sobem e
  descem da linha: ficou como alternativa, nunca para o relógio.
- **Franklin Gothic** é pesada e clara em tamanho grande. É a fonte do relógio porque ele precisa
  ser lido de longe.
- **O relógio não treme.** `Theme.tabular` desenha cada dígito em uma célula da largura do dígito
  mais largo. Isso funciona com qualquer fonte da lista, inclusive com as que não têm números de
  largura igual.
- Escala: 60 px no relógio, 48 no título do menu, 84 no resultado, 24 nos nomes, de 13 a 17 nos
  rótulos, sempre em 1280x720. Tudo escala com a janela, de 0,6 a 2 vezes.
- Nenhum glifo de xadrez em Unicode: os ícones são a própria malha 3D (`render_icon`), e as teclas
  e os avisos são desenhados como polígonos. Assim não há quadradinho de glifo ausente em nenhuma
  máquina. Nomes digitados recusam caracteres que a fonte não desenha.

## Forma

**Cantos cortados** em toda placa e botão. São as mesmas diagonais das faces low-poly das peças e
não existe outro raio de canto na interface. O papel da planilha é a exceção: é papel, tem canto
reto e uma sombra curta, porque está em cima da mesa.

O chão do painel é a própria função de fundo do renderizador (`render_backdrop`), escurecida. O
veio da madeira do painel e o da mesa são o mesmo.

## Ergonomia para dois jogadores em uma tela

- **Saber de quem é a vez, de longe.** Placa clara contra placa escura é uma inversão total de
  fundo e texto. Não é preciso ler nada para ver. Três sinais confirmam: a etiqueta "Joga agora"
  na placa, a faixa no alto do tabuleiro ("Vez de Jogador 1, Brancas") e a câmera, que gira para o
  lado de quem joga.
- **Saber quanto tempo resta, de longe.** O relógio é o maior elemento do painel. Abaixo de 30 s
  ele muda de cor. No modo sem limite, mostra o tempo decorrido, com a etiqueta "decorrido".
- **Cada jogador tem o seu canto.** As Pretas ficam sempre em cima e as Brancas sempre embaixo,
  com a planilha no meio, mesmo com a câmera girando. Se as placas trocassem de lugar a cada
  turno, o olho teria de procurá-las de novo a cada lance.
- **Avisos no lugar da vez.** A recusa de jogada aparece na mesma faixa em que se lê de quem é a
  vez, em uma placa clara com triângulo, e a peça recusada treme. O xeque usa a placa vermelha.
  Nenhum aviso depende só da cor.
- **Ação nas mãos.** Mouse e teclado fazem tudo o que o outro faz. As setas seguem o que se vê:
  com a câmera do lado das Pretas, "para cima" anda para a fileira menor.
- **Pausa de verdade.** O véu escurece a mesa inteira, o relógio para, e só a sobreposição responde.
- **Empate na mesma tela.** Quem propõe abre o pedido. A pergunta vem com o nome do outro jogador,
  que responde ali mesmo.

## Fim de jogo

O resultado é escrito como em uma planilha de torneio: `1 - 0`, `0 - 1` ou `½ - ½`. O painel da
partida vira o painel do resultado, no mesmo lugar, e o tabuleiro não se mexe na troca de tela: a
posição final continua à vista, girando devagar, com o rei tombado. Depois de mate, a casa do rei
e a peça que deu o mate ficam marcadas.

A luz do abajur fica com quem venceu: a placa do resultado acende. No empate ela não fica com
ninguém: a placa fica na sombra, e os fogos são poucos e em tons neutros.

## Versão 1.1: telas novas, com o mesmo conceito

Nada de tela de formulário solta: login, menu e sala são a mesma mesa, com o tabuleiro girando à
esquerda e o painel de nogueira à direita. `Tableau` é um só no jogo inteiro, então trocar de tela não
faz a mesa pular nem refaz o fundo.

- **Controle segmentado (`SegmentedControl`):** adversário, modo, nível e cor mostram todas as opções e
  acendem a escolhida com a placa de latão. O seletor com setas ficou para o tempo e a câmera, em que
  a lista não cabe na largura.
- **Abas (`TabBar`):** só o texto, em serifa, com o filete de latão embaixo da aberta. Assim as abas
  ficam acima dos campos na hierarquia, sem virar mais uma fileira de botões.
- **A folha da partida:** abrir uma partida no histórico põe uma folha de papel sobre a mesa, escrita à
  tinta, com a mesma cor e a mesma sombra da planilha do HUD. A lista continua no painel, e a roda
  rola o que estiver sob o mouse.
- **Resultado no histórico:** a etiqueta segue a linguagem da mesa. Vitória é a placa acesa, derrota é
  a placa vermelha e empate fica na sombra. A palavra está sempre escrita: nunca só a cor (RNF04).
- **O código da sala é o único elemento grande da tela:** é o que se dita para o outro jogador.
- **Senha:** o campo desenha pontos como círculos, sem passar pela fonte. Assim a senha nunca entra no
  cache de texto do tema, e não há glifo ausente em nenhuma máquina.

### Modo Partida

Treinamento é a versão 1.0, sem nenhuma diferença. No modo Partida ficam só a peça selecionada, o cursor
e o último lance: dizem o que aconteceu, não o que fazer. O modo não calcula ameaças nem xeque por turno.
A planilha omite `+` e `#` até a partida acabar, e aí mostra a notação completa. Lance ilegal, peça
do adversário e casa vazia recebem o mesmo "Lance inválido.", sem tremor nem anel, que seria mais um
marcador. Selecionar uma peça sem jogada não avisa nada. O fim diz o motivo normalmente: depois do mate, o
rei tomba e a casa dele é marcada, porque a partida já acabou e isso não é mais dica. O painel F4 lê a
mesma matriz de cores, então também não revela nada.

### Contra a CPU e em rede

A placa de quem joga acende igual. Na vez da CPU, a etiqueta diz "Pensando", com três pontos que acendem em
sequência, desenhados a cada quadro: custam três círculos e mostram que ela não travou. A faixa no alto
diz quem está pensando. Clicar na vez dela dá um aviso curto e não muda nada.

O giro por turno só existe em 2 jogadores. Contra a CPU e em rede, a câmera fica do lado de quem está
na tela, e "Virar" (tecla F) dá meia volta quando a pessoa quiser olhar do outro lado. O menu começa em
Easy: quem nunca jogou contra a CPU começa pelo nível mais fácil.

### Regra do tempo esgotado em rede

Os dois lados precisam chegar ao mesmo resultado, e um relógio visto de longe pode estar errado: a jogada
do outro pode estar a caminho. Por isso:

1. **Só quem esgota o próprio relógio decide.** Ele perde na hora, pela regra do motor, e avisa o outro lado
   com `send_resign`.
2. **Quem recebe esse aviso, com o relógio do outro em até 2 s (`DECLARED_FLAG_WINDOW_SECONDS`), registra tempo
   esgotado**, pela mesma regra do motor, inclusive o empate quando quem fica só tem o rei. Com mais tempo
   sobrando no relógio, foi desistência comum.
3. **O relógio do outro lado, visto daqui, para em zero sem decidir nada.** Uma jogada que chegue nessa hora
   ainda vale.
4. **Se passarem 5 s (`REMOTE_FLAG_GRACE_SECONDS`) com esse relógio em zero, sem jogada nem aviso, o outro lado
   sumiu:** a partida acaba por abandono, e a sala é fechada.

O `clock_ms` que chega pela rede não entra em nenhuma decisão, porque pode ser falso. Limite conhecido da
regra 2: desistir de propósito nos últimos 2 s, com o adversário só com o rei, vira empate de um lado e
vitória do outro. É o único caso em que os dois discordam, e só no placar da série daquela sala.

### Arrastar a peça

Apertar em peça própria seleciona. Passando de 6 pixels, a peça vai para um plano um pouco acima do tabuleiro
e segue o mouse por `Camera.pick_plane`. Só a matriz de modelo muda, sem chamada nova no renderizador.
Enquanto ela está no ar, fica de fora do `pick`: o que importa é o que há embaixo dela. Soltar em destino válido
joga, soltar na própria casa mantém a seleção, soltar fora do tabuleiro só devolve, e o resto vai para o motor
julgar, com a mesma mensagem do clique. Para o clique e o arrasto conviverem, clicar de novo na peça selecionada
agora desmarca ao soltar o botão, não ao apertar.

### Clique duplo entre telas

O 2º clique de um clique duplo não pode acertar o que apareceu no lugar. A `GameScene` já cuidava disso
com as sobreposições, e agora o `App` cuida na troca de tela: por 0,25 s, o clique no mesmo lugar do clique que
trocou a tela (até 3 pixels de distância) é descartado. O menu novo pôs "Iniciar partida" embaixo de "Voltar ao
menu" da tela de fim, e `tests/ataque` pegou.

### Área de transferência

`pygame.scrap` no Windows usa o texto ANSI do sistema. Conferido em janela real, lendo de volta com outro programa:
UTF-8 chega como `JoÃ£o`, e o tipo `text/plain;charset=utf-8` chega como caracteres chineses. Por isso, no
Windows, o texto vai em `mbcs`, com `\r\n`. Sem janela, ou se a cópia falhar, a resposta é um aviso, nunca exceção.

## Modo didático (F4)

Feito para a defesa oral. Mostra ao vivo a matriz de visão, os estados da matriz de cores em
números, com a legenda, e o raio do mouse (pixel, origem, direção e casa atingida). O tabuleiro
encolhe para dar lugar ao painel, em vez de ficar coberto: é a transformação de viewport em ação,
e o clique continua certo. Em janela estreita, o painel fica por cima.

## Desempenho do HUD

`font.render` é caro, então o texto fica em cache (`Theme.text`), com limite de 1600 entradas. As
placas são compostas em superfícies prontas e só são refeitas quando o conteúdo muda: a placa de
quem joga, uma vez por segundo; a de quem espera, praticamente nunca. A planilha, só quando há
lance novo. A cada quadro, o HUD custa apenas alguns blits.

Medições feitas nesta máquina, reproduzíveis com as ferramentas citadas.

`tools/benchmark_ui.py`, partida de 17 lances jogada por eventos, `App.step` completo com HUD, sem
janela e sem `display.flip`:

| Cenário, em 1280x720 | Média | p95 | p99 | Máximo |
|---|---|---|---|---|
| Partida inteira com câmera parada | 1,96 ms | 3,21 ms | 4,71 ms | 5,44 ms |
| Partida inteira com giro por turno | 4,08 ms | 7,00 ms | 10,06 ms | 14,08 ms |
| Câmera em giro contínuo (pior caso) | 6,77 ms | 7,14 ms | 9,43 ms | 14,81 ms |
| Tela de vitória com fogos | 6,58 ms | 6,93 ms | 9,61 ms | 9,90 ms |

Em 1920x1080, a partida com câmera parada ficou em 3,98 ms de média e 8,09 ms de p99. Com giro por
turno, 6,77 ms de média e 13,58 ms de p99, com 32 de 3438 quadros acima de 16,67 ms.

### Versão 1.1, com a CPU pensando (RNF09)

`tools/demo_automatica.py --cpu hardcore`, janela real em 1280x720, com `display.flip`. A busca roda em uma thread,
com `sys.setswitchinterval(0.0002)`, e dorme 1 ms a cada consulta enquanto há animação ou câmera em movimento.

| Cenário, em janela real | Quadros | FPS médio | Intervalo médio | p99 | Máximo |
|---|---|---|---|---|---|
| CPU Hardcore pensando, câmera parada | 1204 | 60,0 | 16,66 ms | 18,24 ms | 28,30 ms |
| Mesma partida, com "Virar" no meio do pensamento: quadros de câmera parada | 948 | 59,2 | 16,88 ms | 29,89 ms | 37,48 ms |
| Mesma partida: quadros de câmera girando | 238 | 59,5 | 16,80 ms | 24,30 ms | 27,42 ms |
| Partida de 4 lances, 2 jogadores, sem CPU | 1289 | 60,0 | 16,66 ms | 20,87 ms | 40,27 ms |

Quando a câmera para de girar, a camada do tabuleiro e os sprites são refeitos em alguns quadros: é daí que vem o p99
maior na segunda linha.

`tools/benchmark_ui.py --seconds 8`, sem janela e sem `display.flip`, depois do HUD com os botões novos, em 1280x720:

| Cenário | Média | p95 | p99 | Máximo |
|---|---|---|---|---|
| Partida inteira com câmera parada | 2,10 ms | 3,48 ms | 4,99 ms | 6,81 ms |
| Partida inteira com giro por turno | 4,26 ms | 7,32 ms | 10,86 ms | 15,40 ms |
| Câmera em giro contínuo (pior caso) | 6,92 ms | 7,34 ms | 10,51 ms | 10,91 ms |
| Tela de vitória com fogos | 6,76 ms | 7,25 ms | 10,14 ms | 10,95 ms |
| CPU Hardcore pensando, câmera parada | 2,69 ms | 3,22 ms | 3,76 ms | 11,04 ms |

As tabelas de antes, acima, são da versão 1.0 e ficam como registro.

**Medição antiga, anterior ao `FramePacer`.** `tools/demo_automatica.py`, janela real em 1280x720, com `display.flip`: 59,1 FPS de média em 1287
quadros, 16,93 ms de intervalo médio entre quadros e 4,90 ms de trabalho médio por quadro. Dois
quadros passaram de 25 ms. A medição sem janela aponta como causa as duas trocas de tela, cerca de
190 ms cada uma, porque o fundo de madeira é gerado de novo quando o tamanho do tabuleiro muda.
Essa rodada foi feita antes do último ajuste da tela de fim. Depois dele, a troca da partida para
o fim caiu para 15 ms (medido sem janela), porque o tabuleiro não muda mais de tamanho. A troca do
menu para a partida continua em cerca de 195 ms. A demonstração não foi repetida depois do ajuste.
