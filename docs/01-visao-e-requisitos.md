# 1. Visão e requisitos

## 1.1 Escopo

Chess - The Game é um xadrez 3D low-poly para 2 jogadores, em turnos alternados, na mesma tela, contra a CPU ou em rede local. É o trabalho do Grupo 09 na atividade A3 de Computação Gráfica e Realidade Virtual. Foi escrito em Python, com um pipeline gráfico próprio sobre pygame e numpy.

Este documento descreve a versão 1.1. A versão 1.0 era só a partida na mesma tela. A 1.1 acrescentou os modos Treinamento e Partida, a CPU em 4 níveis, a sala em rede local, contas com histórico, a cópia do PGN, o arrasto da peça, a virada do tabuleiro e 2 tempos com incremento. A partida de 2 jogadores continua como era, e é o padrão do menu.

O enunciado pede para o grupo um "Xadrez Simplificado": tabuleiro 8x8, movimento estrito das peças, validação de xeque e xeque-mate, modelos geométricos ou low-poly, indicação de caminhos válidos por matriz de cores e feedback visual de peças sob ameaça. O grupo decidiu ir além e implementar as regras oficiais completas, porque a rubrica cobra regras oficiais e porque a contagem perft dá uma forma objetiva de provar que elas estão certas.

**Dentro do escopo:**

- regras oficiais, incluindo roque, en passant, promoção, afogamento e empates;
- partida para 2 pessoas no mesmo computador, por mouse ou teclado;
- modos Treinamento, com todas as dicas, e Partida, sem nenhuma;
- partida contra a CPU, nos níveis Easy, Medium, Hard e Hardcore, com a cor escolhida pelo jogador;
- partida em rede local, sem servidor, entrando na sala por um código de 7 caracteres;
- contas com senha, guardadas neste computador, e botão de convidado;
- histórico das últimas 50 partidas da conta, com estatísticas, PGN e posição final;
- cópia do PGN da partida para a área de transferência;
- relógio com 6 opções de tempo, 2 delas com incremento;
- placar de material na partida e placar da série entre partidas;
- câmera orbital com clique correto em qualquer ângulo, e virada do tabuleiro;
- arrasto da peça, além do clique;
- animações, partículas, iluminação e sombras feitas no próprio pipeline.

**Fora do escopo:**

- jogo pela internet, com servidor ou lista de salas (a rede é só local, e a sessão recusa endereço fora dela);
- tráfego cifrado e sala com senha (o código da sala é o IP escrito de outra forma, e não é segredo);
- contas fora deste computador e recuperação de senha;
- salvar uma partida em andamento e continuar depois (o histórico só guarda partidas encerradas, e o motor lê FEN, mas a interface não oferece isso);
- importar PGN (o jogo só exporta);
- som (o jogo não tem áudio);
- desfazer lance a pedido do jogador (`Board.undo` existe para o motor testar jogadas, e `GameEngine.take_back_last_move` só serve ao lance que cruzou com o fim da partida em rede).

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

**Xeque.** Nenhuma jogada pode deixar o próprio rei atacado. Em Treinamento, uma jogada assim é recusada com a mensagem "Essa jogada deixa o seu rei em xeque.". No modo Partida, com "Lance inválido.".

**Modos.** As regras são as mesmas nos dois. O que muda é o que a tela conta.

| O que a tela mostra | Treinamento | Partida |
|---|---|---|
| Peça selecionada, cursor e último lance | Sim | Sim |
| Caminhos válidos e capturas | Sim | Não |
| Peças sob ameaça | Sim | Não |
| Rei em xeque, atacantes e aviso "Xeque!" | Sim | Não |
| Motivo da recusa de um lance | A mensagem do motor, e a casa treme | Sempre "Lance inválido.", sem tremor |
| Aviso de peça sem jogada | Sim | Não |
| `+` e `#` na planilha com a partida correndo | Sim | Não |
| `+` e `#` em "Copiar PGN" com a partida correndo | Sim | Não |
| Notação completa depois do fim | Sim | Sim |

Treinamento é o padrão. Em rede, o modo é um só para os dois: quem cria a sala escolhe, e quem entra segue. O PGN gravado no histórico guarda sempre a notação completa.

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
| Acordo | Empate, com a resposta do outro jogador na mesma tela. Em rede, a resposta vem pelo cartão de proposta. Contra a CPU, não há acordo |
| Abandono | Em rede, quem sai da sala ou fecha a janela perde. Quem saiu lê "Abandonou a partida", e quem ficou lê "Adversário desconectou" |

**Pontuação.** Há dois placares. O de material soma os pontos das peças capturadas na partida. O da série soma 1 por vitória e 0,5 por empate, passa de uma partida para a outra na revanche e recomeça quando se volta ao menu.

**Tempo.** As opções são "Sem limite", "Blitz 3+2", "Blitz 5", "Rápida 10+0", "Clássica 30" e "Clássica 15+10". O primeiro número são os minutos por jogador, e o segundo, os segundos de incremento, somados ao relógio de quem acabou de jogar. Sem limite, o relógio mostra o tempo decorrido. Em rede, o tempo é o que a sala escolheu, e só ela decide o tempo esgotado.

## 1.3 Público-alvo

- **Jogadores:** quem já conhece o movimento das peças, sozinho contra a CPU, com outra pessoa no mesmo computador ou em dois computadores na mesma rede. O modo Treinamento mostra os caminhos válidos, mas o jogo não ensina as regras.
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
| RF17 | Oferecer os modos Treinamento e Partida | No modo Partida ficam só peça selecionada, cursor e último lance, e a recusa é sempre "Lance inválido.". A tela sai igual, pixel a pixel, com e sem xeque. Treinamento é igual à versão 1.0. | CT-90, CT-100 a CT-104, CT-135 |
| RF18 | Jogar contra a CPU nos níveis Easy, Medium, Hard e Hardcore, escolhendo a cor | A jogada é sempre legal e o tabuleiro da partida não muda. A CPU acha mate em 1 a partir do Medium e mate em 2 a partir do Hard, e a força cresce com o nível. A partida vai do menu à tela de fim. | CT-70 a CT-75, CT-91, CT-92, CT-105 a CT-109, CT-135 |
| RF19 | Jogar em rede local por sala com código de 7 letras | Um cria a sala e o outro digita o código. Os dois terminam com o mesmo FEN e o mesmo resultado, e quem criou a sala decide o fim. Queda de conexão e mensagem inválida viram aviso, sem travar. | CT-85 a CT-88, CT-95, CT-110 a CT-117, CT-135 |
| RF20 | Entrar com conta e senha, criar conta ou jogar como convidado | Nome de 3 a 16 caracteres, sem diferenciar maiúsculas, e senha de pelo menos 8. Senha errada e conta inexistente recebem a mesma mensagem. O convidado joga sem conta e não grava nada. | CT-80, CT-83, CT-93, CT-118, CT-120, CT-123, CT-135 |
| RF21 | Guardar as últimas 50 partidas da conta, com estatísticas, PGN e FEN final | A partida encerrada entra uma vez, a 51ª empurra a mais antiga, e a aba "Meu histórico" mostra lista, estatísticas, lances e posição final. Arquivo ruim não derruba o jogo. | CT-76, CT-82, CT-83, CT-94, CT-121 a CT-123, CT-134, CT-135 |
| RF22 | Copiar o PGN da partida | Botão ou tecla C copia um PGN válido, com cabeçalhos e resultado. No modo Partida, com a partida correndo, sai sem `+` e `#`. Falha na área de transferência vira aviso. | CT-76, CT-98, CT-103, CT-128, CT-135 |
| RF23 | Arrastar a peça para jogar e virar o tabuleiro | Passando de 6 pixels, a peça segue o mouse. Soltar em destino válido joga, e o resto devolve ou vai para o motor julgar. A tecla F vira o tabuleiro, e o clique continua certo. | CT-96, CT-97, CT-124 a CT-127, CT-135 |
| RF24 | Oferecer os tempos Blitz 3+2, Rápida 10+0 e Clássica 15+10 | O menu oferece os tempos, e o incremento entra só para quem jogou. Os presets antigos não mudam. | CT-77, CT-135 |

## 1.6 Requisitos não funcionais

O resultado medido de cada um está na seção 7.6.

| ID | Requisito | Critério de aceite | Como verificar |
|---|---|---|---|
| RNF01 | Desempenho: 60 FPS travados em 1280x720 | Média de 60 FPS em janela real, com intervalo perto de 16,67 ms. | `python tools/demo_automatica.py` e tecla F3 no jogo |
| RNF02 | Portabilidade: Python 3.10+ em Windows, Linux e macOS | A suíte passa nas 3 plataformas, em Python 3.10 e 3.12. | `.github/workflows/testes.yml`, a cada envio ao GitHub |
| RNF03 | Responsividade: resposta visual à entrada em até 1 quadro | A casa sob o mouse e a seleção mudam no mesmo quadro do evento. | Testes em `tests/ui/test_ui_selecao.py` |
| RNF04 | Estética e acessibilidade: paleta coerente e estados por cor e por forma | Texto com contraste de pelo menos 4,5:1. Caminho, captura e ameaça têm forma além de cor. | Testes em `tests/ui/test_ui_tema.py` e prints do capítulo 2 |
| RNF05 | Arquitetura em camadas, com motor testável sem interface | `core`, `data` e `net` não importam pygame nem numpy. `graphics` não importa `core`. `data` e `net` não se importam. | `tests/test_arquitetura.py` |
| RNF06 | Qualidade: cobertura de pelo menos 90% em `core` | Cobertura de linhas e ramos medida na execução dos testes. | `python tools/relatorio_testes.py` |
| RNF07 | Robustez: entrada inválida e redimensionamento nunca derrubam o jogo | Entrada inválida vira erro tratado. Nenhum tamanho de janela derruba o jogo, nem 1x1. | CT-49 e testes de tamanho extremo |
| RNF08 | Segurança: senha nunca gravada em claro; entrada da rede tratada como não confiável | O arquivo de contas só tem nome, sal, iterações e hash (PBKDF2-HMAC-SHA256, 600 mil iterações). Tudo o que chega da rede é JSON conferido, e mensagem inválida encerra a conexão. | CT-81, CT-88, CT-110, CT-111 e CT-119 |
| RNF09 | A CPU pensando não pode derrubar os 60 FPS | Com a CPU Hardcore pensando, a média fica perto de 60 FPS em 1280x720, em janela real, e a entrada responde no mesmo quadro. | `python tools/demo_automatica.py --cpu hardcore`, CT-75, CT-92 e CT-105 |
