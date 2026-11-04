# 8. Matriz de rastreabilidade

Arquivo gerado por `tools/relatorio_testes.py`. Não edite à mão: os vínculos ficam em `docs/testes/casos.json`, e a situação vem da execução real.

Execução de 2026-11-04 16:21:07, commit `bf74717`.

## 8.1 Requisito, caso de uso e caso de teste

| RF | Requisito | Casos de uso | Casos de teste | Situação |
|---|---|---|---|---|
| **RF01** | Identificar os 2 jogadores e escolher modo (tempo e câmera) no menu | UC01 | CT-40, CT-61 | PASSOU |
| **RF02** | Montar o tabuleiro 8x8 na posição oficial | UC01 | CT-01 | PASSOU |
| **RF03** | Alternar turnos, começando pelas brancas, e recusar jogada fora do turno | UC02 | CT-02, CT-03, CT-43 | PASSOU |
| **RF04** | Validar o movimento estrito das 6 peças, com colisão de caminho e captura | UC02 | CT-04, CT-05, CT-06, CT-07, CT-08, CT-17, CT-50, CT-56 | PASSOU |
| **RF05** | Aceitar as jogadas especiais: roque, en passant e promoção | UC02, UC05 | CT-09, CT-10, CT-11, CT-17, CT-48, CT-50, CT-51, CT-58 | PASSOU |
| **RF06** | Validar xeque: nenhuma jogada pode deixar o próprio rei em xeque | UC02, UC07 | CT-12, CT-17, CT-50, CT-51 | PASSOU |
| **RF07** | Detectar fim de jogo: xeque-mate, afogamento, empates, tempo e desistência | UC07, UC08 | CT-13, CT-14, CT-15, CT-16, CT-46, CT-52, CT-53, CT-54, CT-55, CT-58 | PASSOU |
| **RF08** | Permitir selecionar e mover por mouse e por teclado | UC02, UC06 | CT-41, CT-42, CT-59 | PASSOU |
| **RF09** | Indicar caminhos válidos por matriz de cores (seleção, movimento, captura, último lance) | UC06 | CT-32, CT-41 | PASSOU |
| **RF10** | Dar feedback visual de peças sob ameaça e de rei em xeque | UC06, UC07 | CT-19, CT-44 | PASSOU |
| **RF11** | Exibir HUD com jogadores, vez, cronômetro, pontuação, capturas e lances | UC02 | CT-08, CT-16, CT-18, CT-55, CT-63 | PASSOU |
| **RF12** | Pausar e retomar, congelando o relógio e a entrada | UC03 | CT-20, CT-45, CT-55, CT-58, CT-60 | PASSOU |
| **RF13** | Reiniciar, pedir revanche e voltar ao menu, mantendo o placar da série | UC04, UC09 | CT-18, CT-21, CT-47, CT-55, CT-63 | PASSOU |
| **RF14** | Exibir tela de fim de jogo com vencedor, motivo e animação de vitória | UC07, UC09 | CT-46, CT-63 | PASSOU |
| **RF15** | Animar movimentos e capturas com transformações e partículas | UC02 | CT-30, CT-33, CT-34, CT-35, CT-36 | PASSOU |
| **RF16** | Girar, orbitar e aproximar a câmera, com clique correto em qualquer ângulo | UC02, UC06 | CT-30, CT-31, CT-49, CT-59, CT-62 | PASSOU |

## 8.2 Caso de uso, requisito e caso de teste

| Caso de uso | Requisitos | Casos de teste | Situação |
|---|---|---|---|
| **UC01** Iniciar Partida | RF01, RF02 | CT-01, CT-40, CT-46, CT-61, CT-66, CT-67 | PASSOU |
| **UC02** Executar Jogada | RF03, RF04, RF05, RF06, RF08, RF11, RF15, RF16 | CT-02, CT-03, CT-04, CT-05, CT-06, CT-07, CT-08, CT-09, CT-10, CT-11, CT-12, CT-17, CT-30, CT-31, CT-33, CT-34, CT-35, CT-36, CT-41, CT-42, CT-43, CT-46, CT-49, CT-50, CT-51, CT-56, CT-57, CT-58, CT-59, CT-62, CT-65 | PASSOU |
| **UC03** Pausar Jogo | RF12 | CT-20, CT-45, CT-55, CT-57, CT-58, CT-60 | PASSOU |
| **UC04** Reiniciar Partida | RF13 | CT-21, CT-63 | PASSOU |
| **UC05** Promover Peão | RF05 | CT-11, CT-48, CT-51, CT-58 | PASSOU |
| **UC06** Consultar Caminhos e Ameaças | RF08, RF09, RF10, RF16 | CT-19, CT-31, CT-32, CT-41, CT-44, CT-59 | PASSOU |
| **UC07** Verificar Xeque e Fim de Jogo | RF06, RF07, RF10, RF14 | CT-12, CT-13, CT-14, CT-15, CT-16, CT-18, CT-44, CT-46, CT-50, CT-52, CT-53, CT-54 | PASSOU |
| **UC08** Encerrar Partida | RF07 | CT-15, CT-55, CT-60 | PASSOU |
| **UC09** Pedir Revanche ou Voltar ao Menu | RF13, RF14 | CT-18, CT-21, CT-47, CT-55, CT-60, CT-63, CT-64 | PASSOU |

## 8.3 Caso de teste, requisito e caso de uso

| Caso de teste | Requisitos | Casos de uso | Situação |
|---|---|---|---|
| **CT-01** Posição inicial oficial | RF02 | UC01 | PASSOU |
| **CT-02** Alternância de turnos, brancas começam | RF03 | UC02 | PASSOU |
| **CT-03** Jogada fora do turno é recusada | RF03 | UC02 | PASSOU |
| **CT-04** Movimentos válidos de cada peça | RF04 | UC02 | PASSOU |
| **CT-05** Movimento proibido é recusado | RF04 | UC02 | PASSOU |
| **CT-06** Colisão: peça deslizante é bloqueada por peça no caminho | RF04 | UC02 | PASSOU |
| **CT-07** Cavalo salta sem colisão | RF04 | UC02 | PASSOU |
| **CT-08** Captura atualiza a pontuação de material | RF04, RF11 | UC02 | PASSOU |
| **CT-09** Roque válido e roques proibidos | RF05 | UC02 | PASSOU |
| **CT-10** En passant válido e fora da janela | RF05 | UC02 | PASSOU |
| **CT-11** Promoção exige escolha e troca a peça | RF05 | UC02, UC05 | PASSOU |
| **CT-12** Peça cravada: jogada que expõe o rei é recusada | RF06 | UC02, UC07 | PASSOU |
| **CT-13** Xeque-mate encerra a partida | RF07 | UC07 | PASSOU |
| **CT-14** Afogamento é empate | RF07 | UC07 | PASSOU |
| **CT-15** Empates: material insuficiente, 50 lances, tripla repetição | RF07 | UC07, UC08 | PASSOU |
| **CT-16** Tempo esgotado encerra a partida | RF07, RF11 | UC07 | PASSOU |
| **CT-17** Perft: contagem de posições confere com valores de referência | RF04, RF05, RF06 | UC02 | PASSOU |
| **CT-18** Placar da série: vitória vale 1, empate vale 0,5 | RF11, RF13 | UC07, UC09 | PASSOU |
| **CT-19** Cálculo de peças sob ameaça | RF10 | UC06 | PASSOU |
| **CT-20** Pausa congela o relógio e recusa jogada | RF12 | UC03 | PASSOU |
| **CT-21** Reiniciar e revanche | RF13 | UC04, UC09 | PASSOU |
| **CT-30** Matrizes: translação, rotação, escala e composição | RF15, RF16 | UC02 | PASSOU |
| **CT-31** Câmera: ida e volta mundo, tela e casa em vários ângulos | RF16 | UC02, UC06 | PASSOU |
| **CT-32** Matriz de cores: estado vira cor, com prioridade | RF09 | UC06 | PASSOU |
| **CT-33** Partículas: gravidade, reflexão no piso e tempo de vida | RF15 | UC02 | PASSOU |
| **CT-34** Malhas: normais para fora e faces válidas | RF15 | UC02 | PASSOU |
| **CT-35** Animação: interpolação e easing | RF15 | UC02 | PASSOU |
| **CT-36** Render: corte de faces traseiras e ordem de pintura | RF15 | UC02 | PASSOU |
| **CT-40** Menu inicia partida com nomes e tempo escolhidos | RF01 | UC01 | PASSOU |
| **CT-41** Clique seleciona e preenche a matriz de cores | RF08, RF09 | UC02, UC06 | PASSOU |
| **CT-42** Teclado seleciona e executa jogada | RF08 | UC02 | PASSOU |
| **CT-43** Clique fora do turno dá aviso e não altera o jogo | RF03 | UC02 | PASSOU |
| **CT-44** Ameaça e xeque aparecem na matriz de cores | RF10 | UC06, UC07 | PASSOU |
| **CT-45** Pausa bloqueia a entrada | RF12 | UC03 | PASSOU |
| **CT-46** Partida completa por eventos até a tela de vitória | RF07, RF14 | UC01, UC02, UC07 | PASSOU |
| **CT-47** Revanche troca cores e mantém o placar; menu volta ao início | RF13 | UC09 | PASSOU |
| **CT-48** Promoção pelo diálogo | RF05 | UC05 | PASSOU |
| **CT-49** Redimensionar a janela mantém o clique correto | RNF07, RF16 | UC02 | PASSOU |
| **CT-50** Partidas aleatórias contra gerador e detector independentes | RF04, RF05, RF06 | UC02, UC07 | PASSOU |
| **CT-51** Bordas de promoção, en passant e roque | RF05, RF06 | UC02, UC05 | PASSOU |
| **CT-52** Precedência entre fins de jogo no mesmo lance | RF07 | UC07 | PASSOU |
| **CT-53** Tripla repetição, roque perdido e en passant | RF07 | UC07 | PASSOU |
| **CT-54** Material insuficiente por captura e promoção subpotente | RF07 | UC07 | PASSOU |
| **CT-55** Relógio, desistência, série, revanche e pretas primeiro | RF07, RF11, RF12, RF13 | UC03, UC08, UC09 | PASSOU |
| **CT-56** Entradas absurdas e FEN malformadas | RF04, RNF07 | UC02 | PASSOU |
| **CT-57** Macaco: eventos aleatórios com invariantes | RNF07 | UC02, UC03 | PASSOU |
| **CT-58** Corridas entre relógio, voo, pausa, promoção e fim | RF05, RF07, RF12 | UC02, UC03, UC05 | PASSOU |
| **CT-59** Clique: o que se vê é o que se aciona | RF08, RF16 | UC02, UC06 | PASSOU |
| **CT-60** Clique duplo e eventos no mesmo quadro | RF12, RNF07 | UC03, UC08, UC09 | PASSOU |
| **CT-61** Nomes: caracteres perigosos, largura e ajuda | RF01, RNF07 | UC01 | PASSOU |
| **CT-62** Janelas e números extremos | RF16, RNF07 | UC02 | PASSOU |
| **CT-63** Fim de jogo, revanche, menu e HUD | RF11, RF13, RF14 | UC04, UC09 | PASSOU |
| **CT-64** Vazamento de memória | RNF01, RNF07 | UC09 | PASSOU |
| **CT-65** Sem rede, sem execução dinâmica, sem escrita | RNF05, RNF07 | UC02 | PASSOU |
| **CT-66** PNG, autoria, e-mails e caminhos pessoais | RNF05 | UC01 | PASSOU |
| **CT-67** Python 3.10 e portabilidade | RNF02 | UC01 | PASSOU |
