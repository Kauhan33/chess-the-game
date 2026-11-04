# 2. Protótipos de tela e UI/UX

## 2.1 Wireframes e telas reais

Os wireframes são esboços de baixa fidelidade, em tons de cinza, gerados por `tools/gerar_wireframes.py`. Eles mostram a organização de cada tela. Os prints ao lado são do jogo real, gerados por `tools/capturar_telas.py`, que chega a cada tela por eventos de mouse e teclado.

| Wireframe | Print real |
|---|---|
| ![Wireframe do menu inicial](img/wireframes/wireframe_menu.png) | ![Menu inicial do jogo](img/tela_menu.png) |
| ![Wireframe da partida](img/wireframes/wireframe_partida.png) | ![Partida em andamento](img/tela_partida.png) |
| ![Wireframe do fim de jogo](img/wireframes/wireframe_fim_de_jogo.png) | ![Tela de vitória](img/tela_vitoria.png) |

**Menu inicial.** Identifica os jogadores e escolhe o modo: tempo por jogador e comportamento da câmera. Os controles principais ficam à vista antes da partida começar.

**Tela principal da partida.** O tabuleiro é a área jogável. O painel da direita traz o HUD: placa de cada jogador com nome, pontuação e cronômetro, as peças capturadas e a planilha de lances. O indicador de vez aparece de três formas: a placa acesa, a etiqueta "Joga agora" e a faixa no alto do tabuleiro.

**Fim de jogo.** O painel da partida vira o resultado, no mesmo lugar. O tabuleiro continua à vista, com a posição final e os fogos. Os botões oferecem revanche ou volta ao menu.

## 2.2 Outros estados da interface

| | |
|---|---|
| ![Caminhos válidos pela matriz de cores](img/tela_caminhos.png) | ![Peças sob ameaça](img/tela_ameaca.png) |
| ![Rei em xeque](img/tela_xeque.png) | ![Partida pausada](img/tela_pausa.png) |
| ![Diálogo de promoção](img/tela_promocao.png) | ![Partida empatada](img/tela_empate.png) |
| ![Modo didático, tecla F4](img/tela_didatico.png) | ![Painel de desempenho, tecla F3](img/tela_desempenho.png) |
| ![Ajuda de controles](img/tela_ajuda.png) | |

## 2.3 Justificativa gráfica

### Conceito

A interface imita uma mesa de torneio sob a luz de um abajur. O painel lateral é o resto da mesa e traz objetos de uma partida de verdade: uma placa para cada jogador, uma planilha de anotação em papel pautado e um filete de latão entre o painel e o tabuleiro.

A ideia central é que a luz do abajur acompanha quem joga. A placa da vez acende, com fundo claro e brilho quente. A outra fica na sombra. A troca leva 0,28 s e acontece junto com o relógio, assim que o lance é feito.

### Paleta

Todas as cores são quentes e vêm do mesmo mundo. O latão é a única cor de destaque do HUD.

| Papel | Nome no código | Cor |
|---|---|---|
| Madeira mais funda | `WALNUT_SHADOW` | `#17100B` |
| Nogueira, fundo de placa e painel | `WALNUT` | `#2A1B12` |
| Face de botão | `WALNUT_RAISED` | `#422C1C` |
| Borda de placa na sombra | `WALNUT_EDGE` | `#6C4E2E` |
| Latão escuro, borda de placa acesa | `BRASS_DARK` | `#8F6D33` |
| Latão, filete e bordas em foco | `BRASS` | `#C8A15A` |
| Latão claro, títulos e anel de foco | `BRASS_BRIGHT` | `#EBCB8B` |
| Marfim, texto principal e cor das peças | `IVORY` | `#F0E4C8` |
| Papel da planilha | `PAPER` | `#E9DCBE` |
| Tinta, texto sobre fundo claro | `INK` | `#24170E` |
| Texto secundário sobre madeira | `TEXT_MUTED` | `#C9B89A` |
| Alerta de tempo baixo sobre fundo escuro | `ALERT_ON_DARK` | `#FF8A70` |
| Alerta de tempo baixo sobre fundo claro | `ALERT_ON_LIGHT` | `#8C180E` |
| Placa de xeque | `ALERT_PLATE` | `#96241A` |
| Luz do abajur em volta da placa da vez | `LAMP_GLOW` | `#FFBA68` |

### Matriz de cores do tabuleiro

Cada estado de casa tem uma cor, e a maioria também tem uma forma. Assim, a informação não depende só de enxergar a diferença entre as cores (RNF04).

| Estado | Cor | Forma que acompanha a cor |
|---|---|---|
| `LAST_MOVE` último lance | `#C6AC54` | Nenhuma: é só contexto |
| `PATH` caminho | `#5CAC6C` | Ponto |
| `CAPTURE` captura | `#D84E3C` | Anel |
| `THREAT` ameaça | `#EC8A2C` | Triângulo, e a peça ganha tint pulsante |
| `CHECK` xeque | `#E02C2C` | Rei com tint vermelho e atacantes com cantos |
| `SELECTED` seleção | `#F4CE60` | Cantos, e a peça é levantada |
| `CURSOR` cursor | `#68AADE` | Cantos |

O azul do cursor é a única cor fria da tela. Em um tabuleiro todo quente, é o que se acha mais rápido.

### Contraste

As razões abaixo foram calculadas com a fórmula WCAG, a partir das cores do código. O teste `test_contraste_dos_textos_passa_de_4_5_para_1`, em `tests/ui/test_ui_tema.py`, exige pelo menos 4,5:1 nos pares principais.

| Par | Razão |
|---|---|
| Relógio em tinta sobre a placa acesa | 9,2:1 |
| Relógio em texto secundário sobre a placa na sombra | 7,9:1 |
| Tempo baixo sobre a placa acesa | 4,9:1 |
| Tempo baixo sobre a placa na sombra | 6,7:1 |
| Tinta sobre o papel da planilha | 12,8:1 |
| Marfim sobre botão | 10,3:1 |
| Texto secundário sobre nogueira | 8,5:1 |
| Marfim sobre a placa de alerta | 6,5:1 |

### Tipografia

O jogo só usa fontes do sistema, sem nada baixado. Cada papel tem uma lista de alternativas, e no fim dela está a fonte padrão do pygame. Há teste que abre o jogo inteiro sem nenhuma fonte do sistema.

| Papel | Windows | Onde aparece |
|---|---|---|
| Serifa de título, em negrito | Palatino Linotype | Título, nomes, lances, avisos e resultado |
| Sem serifa de rótulo | Franklin Gothic Medium | Rótulos, botões, teclas e ajuda |
| Números do relógio | Franklin Gothic Medium, em negrito | Relógio e pontos da série |
| Monoespaçada | Consolas | Painéis F3 e F4 |

- A Palatino tem algarismos alinhados, o que serve à planilha, e tom de documento de torneio.
- A Franklin Gothic é pesada e clara em tamanho grande. O relógio usa essa fonte porque precisa ser lido de longe.
- O relógio não treme. `Theme.tabular` desenha cada dígito em uma célula da largura do dígito mais largo.
- Os tamanhos escalam com a janela, de 0,6 a 2 vezes. Em 1280x720, o relógio tem 60 px, e os rótulos, de 13 a 17 px.
- Nenhum glifo de xadrez em Unicode é usado. Os ícones são a própria malha 3D, então não há quadradinho de glifo ausente em nenhuma máquina.

### Forma

Toda placa e todo botão têm cantos cortados, as mesmas diagonais das faces low-poly das peças. O papel da planilha é a exceção: tem canto reto e sombra curta, porque é papel em cima da mesa.

## 2.4 Ergonomia para 2 jogadores

- **Saber de quem é a vez, de longe.** Placa clara contra placa escura é uma inversão total de fundo e texto. Três sinais confirmam: a etiqueta "Joga agora", a faixa "Vez de Jogador 1, Brancas" e a câmera, que gira para o lado de quem joga.
- **Saber quanto tempo resta, de longe.** O relógio é o maior elemento do painel. Abaixo de 30 s, ele muda de cor. No modo sem limite, mostra o tempo decorrido.
- **Cada jogador tem o seu canto.** As pretas ficam sempre em cima e as brancas sempre embaixo, com a planilha no meio, mesmo com a câmera girando.
- **Avisos no lugar da vez.** A recusa de jogada aparece na mesma faixa em que se lê de quem é a vez, em uma placa clara com triângulo, e a peça recusada treme. O xeque usa a placa vermelha.
- **Mouse e teclado.** A partida pode ser jogada inteira por qualquer um dos dois. As setas seguem o que se vê: com a câmera do lado das pretas, "para cima" anda para a fileira menor.
- **Pausa de verdade.** O véu escurece a mesa inteira, o relógio para, e só a sobreposição responde.
- **Empate na mesma tela.** Quem propõe abre o pedido. A pergunta traz o nome do outro jogador, que responde ali mesmo.

## 2.5 Controles

| Entrada | Ação |
|---|---|
| Clique esquerdo | Seleciona a peça e joga |
| Botão direito, arrastando | Gira a câmera |
| Roda do mouse | Aproxima e afasta a câmera |
| Setas | Movem o cursor, conforme a visão |
| Enter ou Espaço | Confirma, como o clique |
| Esc | Cancela a seleção. Sem seleção, abre a pausa |
| P | Pausa a partida |
| R | Reinicia, depois de confirmar |
| T | Liga ou desliga o giro por turno |
| V | Volta à vista padrão |
| H ou F1 | Mostra a ajuda |
| F3 | Mostra FPS e polígonos |
| F4 | Modo didático: matrizes ao vivo |
| F11 | Liga ou desliga a tela cheia |
