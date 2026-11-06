# 8. Matriz de rastreabilidade

Arquivo gerado por `tools/relatorio_testes.py`. Não edite à mão: os vínculos ficam em `docs/testes/casos.json`, e a situação vem da execução real.

Execução de 2026-11-06 11:33:20, commit `846bba7`.

## 8.1 Requisito, caso de uso e caso de teste

| RF | Requisito | Casos de uso | Casos de teste | Situação |
|---|---|---|---|---|
| **RF01** | Identificar os 2 jogadores e escolher modo (tempo e câmera) no menu | UC01 | CT-40, CT-61 | PASSOU |
| **RF02** | Montar o tabuleiro 8x8 na posição oficial | UC01 | CT-01 | PASSOU |
| **RF03** | Alternar turnos, começando pelas brancas, e recusar jogada fora do turno | UC02 | CT-02, CT-03, CT-43 | PASSOU |
| **RF04** | Validar o movimento estrito das 6 peças, com colisão de caminho e captura | UC02 | CT-04, CT-05, CT-06, CT-07, CT-08, CT-17, CT-50, CT-56 | PASSOU |
| **RF05** | Aceitar as jogadas especiais: roque, en passant e promoção | UC02, UC05 | CT-09, CT-10, CT-11, CT-17, CT-48, CT-50, CT-51, CT-58, CT-126 | PASSOU |
| **RF06** | Validar xeque: nenhuma jogada pode deixar o próprio rei em xeque | UC02, UC07 | CT-12, CT-17, CT-50, CT-51 | PASSOU |
| **RF07** | Detectar fim de jogo: xeque-mate, afogamento, empates, tempo e desistência | UC07, UC08 | CT-13, CT-14, CT-15, CT-16, CT-46, CT-52, CT-53, CT-54, CT-55, CT-58 | PASSOU |
| **RF08** | Permitir selecionar e mover por mouse e por teclado | UC02, UC06 | CT-41, CT-42, CT-59 | PASSOU |
| **RF09** | Indicar caminhos válidos por matriz de cores (seleção, movimento, captura, último lance) | UC06 | CT-32, CT-41, CT-104 | PASSOU |
| **RF10** | Dar feedback visual de peças sob ameaça e de rei em xeque | UC06, UC07 | CT-19, CT-44, CT-104 | PASSOU |
| **RF11** | Exibir HUD com jogadores, vez, cronômetro, pontuação, capturas e lances | UC02 | CT-08, CT-16, CT-18, CT-55, CT-63, CT-132, CT-133 | PASSOU |
| **RF12** | Pausar e retomar, congelando o relógio e a entrada | UC03 | CT-20, CT-45, CT-55, CT-58, CT-60 | PASSOU |
| **RF13** | Reiniciar, pedir revanche e voltar ao menu, mantendo o placar da série | UC04, UC09 | CT-18, CT-21, CT-47, CT-55, CT-63 | PASSOU |
| **RF14** | Exibir tela de fim de jogo com vencedor, motivo e animação de vitória | UC07, UC09 | CT-46, CT-63, CT-133 | PASSOU |
| **RF15** | Animar movimentos e capturas com transformações e partículas | UC02 | CT-30, CT-33, CT-34, CT-35, CT-36 | PASSOU |
| **RF16** | Girar, orbitar e aproximar a câmera, com clique correto em qualquer ângulo | UC02, UC06 | CT-30, CT-31, CT-49, CT-59, CT-62 | PASSOU |
| **RF17** | Oferecer os modos Treinamento e Partida | UC01, UC06 | CT-90, CT-100, CT-101, CT-102, CT-103, CT-104, CT-135 | PASSOU |
| **RF18** | Jogar contra a CPU nos níveis Easy, Medium, Hard e Hardcore, escolhendo a cor | UC10 | CT-70, CT-71, CT-72, CT-73, CT-74, CT-75, CT-91, CT-92, CT-105, CT-106, CT-107, CT-108, CT-109, CT-135 | PASSOU |
| **RF19** | Jogar em rede local por sala com código de 7 letras | UC11, UC12 | CT-85, CT-86, CT-87, CT-88, CT-95, CT-110, CT-111, CT-112, CT-113, CT-114, CT-115, CT-116, CT-117, CT-135 | PASSOU |
| **RF20** | Entrar com conta e senha, criar conta ou jogar como convidado | UC13 | CT-80, CT-83, CT-93, CT-118, CT-120, CT-123, CT-135 | PASSOU |
| **RF21** | Guardar as últimas 50 partidas da conta, com estatísticas, PGN e FEN final | UC14 | CT-76, CT-82, CT-83, CT-94, CT-121, CT-122, CT-123, CT-134, CT-135 | PASSOU |
| **RF22** | Copiar o PGN da partida | UC15 | CT-76, CT-98, CT-103, CT-128, CT-135 | PASSOU |
| **RF23** | Arrastar a peça para jogar e virar o tabuleiro | UC02, UC06 | CT-96, CT-97, CT-124, CT-125, CT-126, CT-127, CT-135 | PASSOU |
| **RF24** | Oferecer os tempos Blitz 3+2, Rápida 10+0 e Clássica 15+10 | UC01 | CT-77, CT-135 | PASSOU |

## 8.2 Caso de uso, requisito e caso de teste

| Caso de uso | Requisitos | Casos de teste | Situação |
|---|---|---|---|
| **UC01** Iniciar Partida | RF01, RF02, RF17, RF24 | CT-01, CT-40, CT-46, CT-61, CT-66, CT-67, CT-77, CT-90, CT-129, CT-131, CT-135 | PASSOU |
| **UC02** Executar Jogada | RF03, RF04, RF05, RF06, RF08, RF11, RF15, RF16, RF23 | CT-02, CT-03, CT-04, CT-05, CT-06, CT-07, CT-08, CT-09, CT-10, CT-11, CT-12, CT-17, CT-30, CT-31, CT-33, CT-34, CT-35, CT-36, CT-41, CT-42, CT-43, CT-46, CT-49, CT-50, CT-51, CT-56, CT-57, CT-58, CT-59, CT-62, CT-65, CT-96, CT-97, CT-101, CT-124, CT-125, CT-126, CT-127, CT-130, CT-132, CT-133, CT-135 | PASSOU |
| **UC03** Pausar Jogo | RF12 | CT-20, CT-45, CT-55, CT-57, CT-58, CT-60 | PASSOU |
| **UC04** Reiniciar Partida | RF13 | CT-21, CT-63 | PASSOU |
| **UC05** Promover Peão | RF05 | CT-11, CT-48, CT-51, CT-58, CT-126 | PASSOU |
| **UC06** Consultar Caminhos e Ameaças | RF08, RF09, RF10, RF16, RF17, RF23 | CT-19, CT-31, CT-32, CT-41, CT-44, CT-59, CT-90, CT-97, CT-100, CT-102, CT-103, CT-104, CT-127 | PASSOU |
| **UC07** Verificar Xeque e Fim de Jogo | RF06, RF07, RF10, RF14 | CT-12, CT-13, CT-14, CT-15, CT-16, CT-18, CT-44, CT-46, CT-50, CT-52, CT-53, CT-54 | PASSOU |
| **UC08** Encerrar Partida | RF07 | CT-15, CT-55, CT-60 | PASSOU |
| **UC09** Pedir Revanche ou Voltar ao Menu | RF13, RF14 | CT-18, CT-21, CT-47, CT-55, CT-60, CT-63, CT-64, CT-129, CT-132, CT-133 | PASSOU |
| **UC10** Jogar contra a CPU | RF18 | CT-70, CT-71, CT-72, CT-73, CT-74, CT-75, CT-91, CT-92, CT-102, CT-105, CT-106, CT-107, CT-108, CT-109, CT-130, CT-135 | PASSOU |
| **UC11** Criar Sala em Rede | RF19 | CT-85, CT-86, CT-87, CT-88, CT-95, CT-102, CT-110, CT-111, CT-112, CT-113, CT-114, CT-115, CT-116, CT-117, CT-129, CT-130, CT-131, CT-135 | PASSOU |
| **UC12** Entrar em Sala | RF19 | CT-85, CT-86, CT-87, CT-88, CT-95, CT-110, CT-111, CT-112, CT-113, CT-114, CT-115, CT-116, CT-117, CT-135 | PASSOU |
| **UC13** Entrar na Conta | RF20 | CT-80, CT-81, CT-83, CT-93, CT-118, CT-119, CT-120, CT-123, CT-129, CT-130, CT-131, CT-135 | PASSOU |
| **UC14** Consultar Histórico | RF21 | CT-76, CT-82, CT-83, CT-94, CT-121, CT-122, CT-123, CT-130, CT-131, CT-134, CT-135 | PASSOU |
| **UC15** Copiar PGN | RF22 | CT-76, CT-98, CT-103, CT-128, CT-135 | PASSOU |

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
| **CT-65** Rede só em net, escrita só em data, sem execução dinâmica | RNF05, RNF07 | UC02 | PASSOU |
| **CT-66** PNG, autoria, e-mails e caminhos pessoais | RNF05 | UC01 | PASSOU |
| **CT-67** Python 3.10 e portabilidade | RNF02 | UC01 | PASSOU |
| **CT-70** CPU sempre devolve jogada legal, sem alterar o tabuleiro | RF18 | UC10 | PASSOU |
| **CT-71** CPU acha mate em 1 em todos os níveis | RF18 | UC10 | PASSOU |
| **CT-72** CPU acha mate em 2 nos níveis Hard e Hardcore | RF18 | UC10 | PASSOU |
| **CT-73** CPU não entrega a dama de graça a partir do Medium | RF18 | UC10 | PASSOU |
| **CT-74** A força cresce com o nível, em partidas entre os níveis | RF18 | UC10 | PASSOU |
| **CT-75** Cancelamento e limite de tempo da busca são respeitados | RF18, RNF09 | UC10 | PASSOU |
| **CT-76** PGN válido, com resultado e cabeçalhos | RF21, RF22 | UC14, UC15 | PASSOU |
| **CT-77** Tempos com incremento | RF24 | UC01 | PASSOU |
| **CT-80** Conta: criar, entrar, recusar senha errada e nome repetido | RF20 | UC13 | PASSOU |
| **CT-81** Senha nunca aparece no arquivo | RNF08 | UC13 | PASSOU |
| **CT-82** Histórico: mantém 50, ordem e estatísticas | RF21 | UC14 | PASSOU |
| **CT-83** Arquivo corrompido não derruba o jogo | RF20, RF21 | UC13, UC14 | PASSOU |
| **CT-85** Código de sala: ida e volta, e recusa de código inválido | RF19 | UC11, UC12 | PASSOU |
| **CT-86** Partida inteira entre duas sessões por socket | RF19 | UC11, UC12 | PASSOU |
| **CT-87** Queda de conexão vira evento, sem travar | RF19 | UC11, UC12 | PASSOU |
| **CT-88** Mensagens inválidas e maliciosas são recusadas | RF19, RNF08 | UC11, UC12 | PASSOU |
| **CT-90** Modo Partida esconde caminhos, ameaças e xeque; Treinamento mostra | RF17 | UC01, UC06 | PASSOU |
| **CT-91** Partida contra a CPU até o fim, por eventos | RF18 | UC10 | PASSOU |
| **CT-92** CPU pensando não bloqueia a entrada nem o desenho | RF18, RNF09 | UC10 | PASSOU |
| **CT-93** Login, criação de conta e convidado | RF20 | UC13 | PASSOU |
| **CT-94** Partida encerrada entra no histórico da conta | RF21 | UC14 | PASSOU |
| **CT-95** Duas instâncias do jogo em rede, por eventos | RF19 | UC11, UC12 | PASSOU |
| **CT-96** Arrastar a peça para jogar | RF23 | UC02 | PASSOU |
| **CT-97** Virar o tabuleiro mantém o clique correto | RF23 | UC02, UC06 | PASSOU |
| **CT-98** Copiar PGN | RF22 | UC15 | PASSOU |
| **CT-100** Modo Partida: tela igual com e sem xeque | RF17 | UC06 | PASSOU |
| **CT-101** Modo Partida: recusa igual em todo motivo | RF17 | UC02 | PASSOU |
| **CT-102** Modo Partida: só indicadores neutros em cada quadro | RF17 | UC06, UC10, UC11 | PASSOU |
| **CT-103** Modo Partida: planilha e cópia sem as marcas de xeque | RF17, RF22 | UC06, UC15 | PASSOU |
| **CT-104** Treinamento continua igual à versão 1.0 | RF17, RF09, RF10 | UC06 | PASSOU |
| **CT-105** Cada saída com a CPU pensando cancela a busca | RF18, RNF09 | UC10 | PASSOU |
| **CT-106** Jogada atrasada da CPU não entra em outra partida | RF18 | UC10 | PASSOU |
| **CT-107** A CPU faz lances especiais, dá mate e abre de brancas | RF18 | UC10 | PASSOU |
| **CT-108** Orçamento da CPU cabe no relógio | RF18 | UC10 | PASSOU |
| **CT-109** Entrada na vez da CPU e falhas da busca | RF18, RNF07 | UC10 | PASSOU |
| **CT-110** Rede: o que chega pelo socket | RF19, RNF08 | UC11, UC12 | PASSOU |
| **CT-111** Rede: nome hostil passa pela tela sem derrubar | RF19, RNF08 | UC11, UC12 | PASSOU |
| **CT-112** Rede: queda em cada estado | RF19, RNF07 | UC11, UC12 | PASSOU |
| **CT-113** Rede: mesmo FEN e mesmo resultado em cada fim | RF19 | UC11, UC12 | PASSOU |
| **CT-114** Rede: quem criou a sala decide o tempo | RF19 | UC11, UC12 | PASSOU |
| **CT-115** Rede: revanche e proposta de empate | RF19 | UC11, UC12 | PASSOU |
| **CT-116** Rede: entrada na sala | RF19 | UC11, UC12 | PASSOU |
| **CT-117** Rede: thread e socket não sobram | RF19, RNF07 | UC11, UC12 | PASSOU |
| **CT-118** Login e conta por teclado e mouse | RF20 | UC13 | PASSOU |
| **CT-119** A senha não fica em widget nem em cache | RNF08 | UC13 | PASSOU |
| **CT-120** Arquivo de contas ruim vira aviso | RF20, RNF07 | UC13 | PASSOU |
| **CT-121** Histórico editado à mão não derruba a aba | RF21, RNF07 | UC14 | PASSOU |
| **CT-122** Registro correto em cada fim de partida | RF21 | UC14 | PASSOU |
| **CT-123** Contas separadas, convidado e 51ª partida | RF20, RF21 | UC13, UC14 | PASSOU |
| **CT-124** Arrastar: soltar fora e interromper | RF23, RNF07 | UC02 | PASSOU |
| **CT-125** Arrastar: na vez errada, em voo e no fim | RF23 | UC02 | PASSOU |
| **CT-126** Arrastar até a promoção e misturar com clique | RF23, RF05 | UC02, UC05 | PASSOU |
| **CT-127** Virar durante o giro e a animação | RF23 | UC02, UC06 | PASSOU |
| **CT-128** Copiar PGN: casos difíceis | RF22 | UC15 | PASSOU |
| **CT-129** O 2º clique de um clique duplo não aciona a tela nova | RNF07 | UC01, UC09, UC11, UC13 | PASSOU |
| **CT-130** Macaco da versão 1.1 | RNF07 | UC02, UC10, UC11, UC13, UC14 | PASSOU |
| **CT-131** Telas: nada fora da janela nem por cima de nada | RNF07 | UC01, UC11, UC13, UC14 | PASSOU |
| **CT-132** HUD, sobreposições e tela de fim em cada janela | RF11, RNF07 | UC02, UC09 | PASSOU |
| **CT-133** Nome longo não corta o que explica a ação | RF11, RF14 | UC02, UC09 | PASSOU |
| **CT-134** O motivo gravado respeita quem lê | RF21 | UC14 | PASSOU |
| **CT-135** Os documentos falam da versão que roda | RF17, RF18, RF19, RF20, RF21, RF22, RF23, RF24 | UC01, UC02, UC10, UC11, UC12, UC13, UC14, UC15 | PASSOU |

## 8.4 Requisito não funcional e como é verificado

| RNF | Requisito | Casos de teste | Verificação | Situação |
|---|---|---|---|---|
| **RNF01** | Desempenho: 60 FPS travados em 1280x720 | CT-64 | FPS em janela real e testes nomeados na seção 7.6 | PASSOU |
| **RNF02** | Portabilidade: Python 3.10+ em Windows, Linux e macOS | CT-67 | CI e testes nomeados na seção 7.6 | PASSOU |
| **RNF03** | Responsividade: resposta visual à entrada em até 1 quadro | Nenhum caso próprio | testes nomeados na seção 7.6 | Ver a seção 7.6 |
| **RNF04** | Estética e acessibilidade: paleta coerente e estados por cor e por forma | Nenhum caso próprio | testes nomeados na seção 7.6 | Ver a seção 7.6 |
| **RNF05** | Arquitetura em camadas, com motor testável sem interface | CT-65, CT-66 | testes nomeados na seção 7.6 | PASSOU |
| **RNF06** | Qualidade: cobertura de pelo menos 90% em `core` | Nenhum caso próprio | Cobertura medida | Ver a seção 7.6 |
| **RNF07** | Robustez: entrada inválida e redimensionamento nunca derrubam o jogo | CT-49, CT-56, CT-57, CT-60, CT-61, CT-62, CT-64, CT-65, CT-109, CT-112, CT-117, CT-120, CT-121, CT-124, CT-129, CT-130, CT-131, CT-132 | testes nomeados na seção 7.6 | PASSOU |
| **RNF08** | Segurança: senha nunca gravada em claro; entrada da rede tratada como não confiável | CT-81, CT-88, CT-110, CT-111, CT-119 | testes nomeados na seção 7.6 | PASSOU |
| **RNF09** | A CPU pensando não pode derrubar os 60 FPS | CT-75, CT-92, CT-105 | FPS em janela real e testes nomeados na seção 7.6 | PASSOU |

## 8.5 Requisito e diagrama

Os nomes são as fontes em `docs/uml/`. As figuras estão nos capítulos 3 e 4.

| Item | Diagramas |
|---|---|
| **RF01** Identificar os 2 jogadores e escolher modo (tempo e câmera) no menu | casos_de_uso, classes_ui_telas, estados_cenas |
| **RF02** Montar o tabuleiro 8x8 na posição oficial | classes_core_tabuleiro |
| **RF03** Alternar turnos, começando pelas brancas, e recusar jogada fora do turno | classes_core_motor, seq_movimento |
| **RF04** Validar o movimento estrito das 6 peças, com colisão de caminho e captura | classes_core_pecas, seq_movimento |
| **RF05** Aceitar as jogadas especiais: roque, en passant e promoção | classes_core_pecas, classes_ui_controles, seq_movimento |
| **RF06** Validar xeque: nenhuma jogada pode deixar o próprio rei em xeque | classes_core_tabuleiro, seq_movimento |
| **RF07** Detectar fim de jogo: xeque-mate, afogamento, empates, tempo e desistência | classes_core_motor, seq_fim_verificacao, estados_partida |
| **RF08** Permitir selecionar e mover por mouse e por teclado | classes_ui_controles, seq_clique, seq_movimento |
| **RF09** Indicar caminhos válidos por matriz de cores (seleção, movimento, captura, último lance) | classes_graphics_pipeline, classes_ui_partida |
| **RF10** Dar feedback visual de peças sob ameaça e de rei em xeque | classes_graphics_pipeline, classes_ui_partida |
| **RF11** Exibir HUD com jogadores, vez, cronômetro, pontuação, capturas e lances | classes_ui_partida |
| **RF12** Pausar e retomar, congelando o relógio e a entrada | classes_ui_controles, estados_partida |
| **RF13** Reiniciar, pedir revanche e voltar ao menu, mantendo o placar da série | classes_ui_cenas, estados_cenas |
| **RF14** Exibir tela de fim de jogo com vencedor, motivo e animação de vitória | seq_fim_vitoria, estados_cenas |
| **RF15** Animar movimentos e capturas com transformações e partículas | classes_graphics_movimento, classes_graphics_pipeline |
| **RF16** Girar, orbitar e aproximar a câmera, com clique correto em qualquer ângulo | classes_graphics_pipeline, seq_clique |
| **RF17** Oferecer os modos Treinamento e Partida | casos_de_uso, classes_ui_cenas, classes_ui_telas |
| **RF18** Jogar contra a CPU nos níveis Easy, Medium, Hard e Hardcore, escolhendo a cor | casos_de_uso, classes_core_ia, classes_ui_cpu_rede, seq_cpu |
| **RF19** Jogar em rede local por sala com código de 7 letras | casos_de_uso, classes_net, classes_ui_cpu_rede, seq_rede, seq_rede_fim, estados_sessao |
| **RF20** Entrar com conta e senha, criar conta ou jogar como convidado | casos_de_uso, classes_data, classes_ui_telas |
| **RF21** Guardar as últimas 50 partidas da conta, com estatísticas, PGN e FEN final | casos_de_uso, classes_data, classes_ui_telas |
| **RF22** Copiar o PGN da partida | casos_de_uso, classes_core_motor, classes_ui_cenas |
| **RF23** Arrastar a peça para jogar e virar o tabuleiro | classes_ui_partida, classes_ui_cenas |
| **RF24** Oferecer os tempos Blitz 3+2, Rápida 10+0 e Clássica 15+10 | classes_core_motor |
| **RNF01** Desempenho: 60 FPS travados em 1280x720 | classes_ui_cenas |
| **RNF02** Portabilidade: Python 3.10+ em Windows, Linux e macOS | classes_visao_geral |
| **RNF03** Responsividade: resposta visual à entrada em até 1 quadro | seq_clique |
| **RNF04** Estética e acessibilidade: paleta coerente e estados por cor e por forma | classes_ui_partida |
| **RNF05** Arquitetura em camadas, com motor testável sem interface | classes_visao_geral |
| **RNF06** Qualidade: cobertura de pelo menos 90% em `core` | classes_core_motor |
| **RNF07** Robustez: entrada inválida e redimensionamento nunca derrubam o jogo | seq_movimento, classes_ui_controles |
| **RNF08** Segurança: senha nunca gravada em claro; entrada da rede tratada como não confiável | classes_data, classes_net, seq_rede_fim |
| **RNF09** A CPU pensando não pode derrubar os 60 FPS | classes_ui_cpu_rede, seq_cpu |
