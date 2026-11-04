# 1. Visão e requisitos

## 1.1 Escopo

Chess - The Game é um xadrez 3D low-poly para 2 jogadores locais, em turnos alternados, na mesma tela. É o trabalho do Grupo 09 na atividade A3 de Computação Gráfica e Realidade Virtual. Foi escrito em Python, com um pipeline gráfico próprio sobre pygame e numpy.

O enunciado pede para o grupo um "Xadrez Simplificado": tabuleiro 8x8, movimento estrito das peças, validação de xeque e xeque-mate, modelos geométricos ou low-poly, indicação de caminhos válidos por matriz de cores e feedback visual de peças sob ameaça. O grupo decidiu ir além e implementar as regras oficiais completas, porque a rubrica cobra regras oficiais e porque a contagem perft dá uma forma objetiva de provar que elas estão certas.

**Dentro do escopo:**

- regras oficiais, incluindo roque, en passant, promoção, afogamento e empates;
- partida para 2 pessoas no mesmo computador, por mouse ou teclado;
- relógio com 4 opções de tempo;
- placar de material na partida e placar da série entre partidas;
- câmera orbital com clique correto em qualquer ângulo;
- animações, partículas, iluminação e sombras feitas no próprio pipeline.

**Fora do escopo:**

- oponente controlado pelo computador;
- jogo em rede;
- salvar e carregar partida (o motor lê FEN, mas a interface não oferece isso);
- som (o jogo não tem áudio);
- desfazer lance durante a partida (o `undo` do tabuleiro existe para o motor testar jogadas).

## 1.2 Regras do jogo

**Tabuleiro.** São 8 colunas (a a h) e 8 fileiras (1 a 8). A casa a1 é escura. As brancas começam embaixo e jogam primeiro.

**Movimento das peças.**

| Peça | Movimento | Pontos de material |
|---|---|---|
| Peão | Avança 1 casa, ou 2 saindo da fileira inicial. Captura na diagonal. | 1 |
| Cavalo | Salta em L. Nenhuma peça bloqueia o caminho. | 3 |
| Bispo | Desliza na diagonal até encontrar uma peça. | 3 |
| Torre | Desliza em linha reta até encontrar uma peça. | 5 |
| Dama | Desliza em linha reta e na diagonal. | 9 |
| Rei | Anda 1 casa em qualquer direção. | 0 |

**Jogadas especiais.**

- **Roque:** rei e torre sem ter movido, caminho livre, rei fora de xeque e sem passar nem chegar em casa atacada.
- **En passant:** captura de peão que acabou de avançar 2 casas, válida só no lance imediato.
- **Promoção:** o peão que chega à última fileira vira dama, torre, bispo ou cavalo, à escolha do jogador.

**Xeque.** Nenhuma jogada pode deixar o próprio rei atacado. Uma jogada assim é recusada com a mensagem "Essa jogada deixa o seu rei em xeque.".

**Fim de jogo.**

| Motivo | Resultado |
|---|---|
| Xeque-mate | Vitória de quem deu o mate |
| Afogamento | Empate |
| Material insuficiente | Empate automático |
| Regra dos 50 lances | Empate automático, em 100 meios-lances sem peão movido nem captura |
| Tripla repetição | Empate automático, na 3ª vez da mesma posição |
| Tempo esgotado | Derrota de quem ficou sem tempo. Empate se o adversário só tiver o rei |
| Desistência | Vitória do adversário |
| Acordo | Empate, com a resposta do outro jogador na mesma tela |

**Pontuação.** Há dois placares. O de material soma os pontos das peças capturadas na partida. O da série soma 1 por vitória e 0,5 por empate, passa de uma partida para a outra na revanche e recomeça quando se volta ao menu.

**Tempo.** As opções são sem limite, 5, 10 ou 30 minutos por jogador, sem incremento. Sem limite, o relógio mostra o tempo decorrido.

## 1.3 Público-alvo

- **Jogadores:** duas pessoas que já conhecem o movimento das peças e dividem um computador. O jogo mostra os caminhos válidos, mas não ensina as regras.
- **Banca:** os professores, que precisam ver a partida rodando e os conceitos da disciplina no código. O modo didático (F4) foi feito para isso.
- **Estudantes de computação gráfica:** quem quiser ler um pipeline 3D escrito à mão, sem motor pronto.

Essa definição é uma decisão do grupo. Não houve pesquisa com usuários.

## 1.4 Objetivos didáticos

| Objetivo da disciplina | Onde aparece no projeto |
|---|---|
| Coordenadas de mundo e de tela | Pipeline completo e clique por raio |
| Transformações por matrizes 4x4 | `xadrez/graphics/matrix.py` e animações |
| Vetores | `Vector2D`, `Vector3D`, normais, reflexão |
| Colisão | Caminho das peças, raio contra peça e partícula contra piso |
| Primitivas e malhas | Peças por revolução, caixas e silhueta facetada |
| Cores | Matriz de cores do tabuleiro |
| Iluminação e sombra | Lambert, Blinn-Phong e sombra planar |
| Partículas e animação | `ParticleSystem`, `Tween` e animações de peça |
| Controle de framerate | `FramePacer` e `dt` real |
| Engenharia de software | Camadas, UML, testes e rastreabilidade |

O detalhamento, com fórmulas e como demonstrar cada item, está no capítulo 6.

## 1.5 Requisitos funcionais

A matriz completa com os casos de uso está no capítulo 8.

| ID | Requisito | Critério de aceite | Casos de teste |
|---|---|---|---|
| RF01 | Identificar os 2 jogadores e escolher modo (tempo e câmera) no menu | Com mouse ou só com teclado, digitar os nomes e escolher tempo e câmera. A partida abre com essas escolhas. Nome vazio vira "Jogador 1" ou "Jogador 2". | CT-40 |
| RF02 | Montar o tabuleiro 8x8 na posição oficial | O FEN inicial é `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`. | CT-01 |
| RF03 | Alternar turnos, começando pelas brancas, e recusar jogada fora do turno | Cada lance aceito passa a vez. Peça de quem não joga é recusada com "Essa peça é do adversário." e a posição não muda. | CT-02, CT-03, CT-43 |
| RF04 | Validar o movimento estrito das 6 peças, com colisão de caminho e captura | Cada peça alcança só as casas do seu padrão. Peça deslizante não atravessa outra. Movimento proibido não altera o jogo. Perft confere com os valores publicados. | CT-04 a CT-08, CT-17 |
| RF05 | Aceitar as jogadas especiais: roque, en passant e promoção | Os casos válidos executam, e os inválidos são recusados. A promoção abre um diálogo com as 4 peças. | CT-09 a CT-11, CT-17, CT-48 |
| RF06 | Validar xeque: nenhuma jogada pode deixar o próprio rei em xeque | Jogada que expõe o rei é recusada com a mensagem própria. Em xeque, só valem jogadas que o resolvem. | CT-12, CT-17 |
| RF07 | Detectar fim de jogo: xeque-mate, afogamento, empates, tempo e desistência | Cada condição encerra a partida com o motivo e o vencedor corretos. Depois do fim, nenhum lance é aceito. | CT-13 a CT-16, CT-46 |
| RF08 | Permitir selecionar e mover por mouse e por teclado | Uma partida pode ser jogada só com o mouse ou só com setas e Enter. As setas seguem a visão atual. | CT-41, CT-42 |
| RF09 | Indicar caminhos válidos por matriz de cores | Selecionar uma peça marca seleção, caminho e captura em cores diferentes. O último lance fica marcado. | CT-32, CT-41 |
| RF10 | Dar feedback visual de peças sob ameaça e de rei em xeque | No início do turno, peças atacadas ganham cor, triângulo e tint. Rei em xeque e atacantes ficam marcados, e a faixa avisa. | CT-19, CT-44 |
| RF11 | Exibir HUD com jogadores, vez, cronômetro, pontuação, capturas e lances | O painel mostra tudo isso, e os valores mudam a cada lance. | CT-08, CT-16, CT-18 |
| RF12 | Pausar e retomar, congelando o relógio e a entrada | Com a pausa aberta, o relógio não anda e o tabuleiro não responde. Ao retomar, tudo volta. | CT-20, CT-45 |
| RF13 | Reiniciar, pedir revanche e voltar ao menu, mantendo o placar da série | Reiniciar mantém as cores e o placar. Revanche troca as cores e mantém o placar. Menu começa uma série nova. | CT-18, CT-21, CT-47 |
| RF14 | Exibir tela de fim de jogo com vencedor, motivo e animação de vitória | Do menu à vitória por eventos reais, a tela mostra resultado, vencedor, motivo e placar, com fogos. | CT-46 |
| RF15 | Animar movimentos e capturas com transformações e partículas | A peça voa em arco e pousa no alvo. A capturada encolhe girando. Partículas têm gravidade e vida. | CT-30, CT-33 a CT-36 |
| RF16 | Girar, orbitar e aproximar a câmera, com clique correto em qualquer ângulo | Ida e volta de mundo para tela e casa dá a mesma casa nas 64 casas, em vários ângulos e tamanhos de janela. | CT-30, CT-31, CT-49 |

## 1.6 Requisitos não funcionais

O resultado medido de cada um está na seção 7.6.

| ID | Requisito | Critério de aceite | Como verificar |
|---|---|---|---|
| RNF01 | Desempenho: 60 FPS travados em 1280x720 | Média de 60 FPS em janela real, com intervalo perto de 16,67 ms. | `python tools/demo_automatica.py` e tecla F3 no jogo |
| RNF02 | Portabilidade: Python 3.10+ em Windows, Linux e macOS | A suíte passa nas 3 plataformas, em Python 3.10 e 3.12. | `.github/workflows/testes.yml`, que só roda depois da publicação |
| RNF03 | Responsividade: resposta visual à entrada em até 1 quadro | A casa sob o mouse e a seleção mudam no mesmo quadro do evento. | Testes em `tests/ui/test_ui_selecao.py` |
| RNF04 | Estética e acessibilidade: paleta coerente e estados por cor e por forma | Texto com contraste de pelo menos 4,5:1. Caminho, captura e ameaça têm forma além de cor. | Testes em `tests/ui/test_ui_tema.py` e prints do capítulo 2 |
| RNF05 | Arquitetura em camadas, com motor testável sem interface | `core` não importa pygame, numpy nem `graphics`. `graphics` não importa `core`. | `tests/test_arquitetura.py` |
| RNF06 | Qualidade: cobertura de pelo menos 90% em `core` | Cobertura de linhas e ramos medida na execução dos testes. | `python tools/relatorio_testes.py` |
| RNF07 | Robustez: entrada inválida e redimensionamento nunca derrubam o jogo | Entrada inválida vira erro tratado. Nenhum tamanho de janela derruba o jogo, nem 1x1. | CT-49 e testes de tamanho extremo |
