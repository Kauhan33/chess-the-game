# 7. Plano de testes

As seções marcadas como geradas saem de `tools/relatorio_testes.py`. O "Resultado Obtido" nunca é digitado: vem do relatório que o pytest grava durante a execução.

## 7.1 Estratégia

| Nível | O que cobre | Onde está | Como roda |
|---|---|---|---|
| Motor | Regras, turnos, pontuação, relógio, notação, PGN e CPU | `tests/core/` | Python puro, sem janela |
| Referência externa | Contagem perft contra valores publicados, no motor e no tabuleiro compacto da CPU | `tests/core/test_core_perft.py`, `tests/core/test_core_search_board.py` | Os mais demorados levam a marca `slow` |
| Força da CPU | Partidas de verdade entre os níveis | `tests/core/test_core_ai_strength.py`, `tools/avaliar_cpu.py` | O teste leva a marca `slow`, e a ferramenta é manual |
| Dados | Contas, histórico, escrita atômica e arquivo corrompido | `tests/data/` | Python puro, sempre em pasta temporária, por `CHESS_THE_GAME_DATA` |
| Rede | Código de sala, protocolo, sessões reais e socket cru de atacante | `tests/net/` | Python puro, sempre em `127.0.0.1` |
| Gráficos | Matrizes, câmera, malhas, partículas, animação e pixels desenhados | `tests/graphics/` | SDL sem janela, lendo a superfície |
| Interface | Partidas e telas por eventos reais de mouse e teclado, inclusive contra a CPU e duas instâncias em rede | `tests/ui/` | SDL sem janela, com `Autoplayer` |
| Arquitetura | Regra de dependência entre as 5 camadas | `tests/test_arquitetura.py` | Lê os imports com `ast` |
| Ataque (QA) | Macaco, roteiros maliciosos, invariantes independentes, vazamento e privacidade | `tests/ataque/` | SDL sem janela, com semente fixa. Os longos levam a marca `slow` |
| Desempenho | FPS real, com e sem a CPU pensando, e custo do quadro | `tools/demo_automatica.py`, `tools/benchmark_ui.py` | Medição manual, fora do pytest |

O perft é a prova mais forte das regras. Ele conta as posições alcançáveis em N meios-lances e compara com totais publicados. Um único erro em roque, en passant, promoção ou cravada muda a contagem.

Cada teste ligado a um caso formal leva `@pytest.mark.ct("CT-xx")`. Um caso pode ter vários testes, e ele só passa se todos passarem.

## 7.2 Ambiente e execução

<!-- GERADO:execucao -->
- **Data e hora da execução:** 2026-11-06 06:35:48
- **Commit testado:** `0021280`. As medições de FPS são de `eaf8f25`.
- **Ambiente:** Python 3.12.10, Windows 11, pytest 9.2.0, pygame 2.6.1, numpy 2.5.3
- **Modo:** completo, com os testes `slow`
- **Total:** 3660 testes: 3655 passaram, 0 falharam, 1 foram pulados e 4 ficaram em `xfail`. Destes, 2989 estão vinculados a 117 casos de teste.
<!-- FIM:execucao -->

As verificações de rede fora da suíte e o resultado do CI estão na seção 7.9.

Para repetir:

```
pip install -r requirements-dev.txt
python -m pytest                       # todos os testes
python -m pytest -m "not slow"         # sem o perft profundo
python tools/relatorio_testes.py       # roda tudo e gera os capítulos 7 e 8
```

No Windows, com o ambiente do projeto, troque `python` por `.venv\Scripts\python.exe`.

## 7.3 Focos exigidos pelo enunciado

O enunciado pede no mínimo 6 casos detalhados, validando colisão, alternância de turnos, movimentos proibidos e pontuação. A tabela liga cada foco aos casos que o cobrem.

<!-- GERADO:focos -->
| Foco exigido | Casos | Resultado real |
|---|---|---|
| Colisão | CT-06, CT-07, CT-33 | 23 de 23 testes passaram |
| Alternância de turnos | CT-02, CT-03, CT-43 | 9 de 9 testes passaram |
| Movimentos proibidos | CT-05, CT-12, CT-43 | 27 de 27 testes passaram |
| Pontuação | CT-08, CT-18 | 15 de 15 testes passaram |
<!-- FIM:focos -->

## 7.4 Casos de teste

<!-- GERADO:casos -->
### Motor de regras

| Caso | Entrada | Procedimento | Resultado Esperado | Resultado Obtido |
|---|---|---|---|---|
| **CT-01** Posição inicial oficial (RF02, UC01) | Nenhuma: `GameEngine()` e `Board.initial()`. | Criar o motor e o tabuleiro. Ler o FEN, as peças de cada casa e o estado. | FEN `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`, partida em andamento, sem resultado e sem lances. | Conforme o esperado (PASSOU: 3 de 3 testes) |
| **CT-02** Alternância de turnos, brancas começam (RF03, UC02) | Lances `e2e4` e `e7e5`. | Conferir a vez antes do primeiro lance e depois de cada um. | Brancas começam. Depois de e4, joga o lado preto. Depois de e5, voltam as brancas, o número do lance passa a 2 e o histórico fica `e4`, `e5`. | Conforme o esperado (PASSOU: 1 de 1 teste) |
| **CT-03** Jogada fora do turno é recusada (RF03, UC02) | Posição inicial com `e7e5` na vez das brancas. Depois de `e2e4`, `d2d4` na vez das pretas. | Chamar `play` com a peça de quem não joga e consultar `legal_moves_from` da peça adversária. | Erro `NOT_YOUR_TURN`, posição, vez e histórico inalterados. `legal_moves_from(e7)` vazio na vez das brancas. | Conforme o esperado (PASSOU: 3 de 3 testes) |
| **CT-04** Movimentos válidos de cada peça (RF04, UC02) | FENs com cada peça sozinha em d4, peões em posições variadas e a sequência `e4 d5 exd5 Qxd5 Nc3 Qa5 Bc4 Bg4 Nf3 Nc6 Rb1`. | Comparar as casas de `legal_moves_from` com o padrão de cada peça. Jogar a sequência pelo motor. | Cada peça alcança todas as casas do padrão. O peão anda 1 ou 2 casas saindo da fileira inicial, 1 fora dela, e só captura na diagonal. O histórico fica igual à sequência. | Conforme o esperado (PASSOU: 10 de 10 testes) |
| **CT-05** Movimento proibido é recusado (RF04, UC02) | 11 posições: torre em diagonal, bispo em linha reta, dama em L, cavalo em linha reta, rei andando 2 casas, peão para trás, avanço duplo fora da fileira inicial, diagonal sem captura, captura em frente, rei e torre sobre peça própria. | Chamar `play` e comparar FEN e histórico antes e depois. | Erro `ILLEGAL_MOVE` e estado inalterado nas 11 posições. | Conforme o esperado (PASSOU: 11 de 11 testes) |
| **CT-06** Colisão: peça deslizante é bloqueada por peça no caminho (RF04, UC02) | FENs com torre, bispo e dama e peças no caminho, a dama cercada da posição inicial e peão com peça à frente. | Ler `legal_moves_from` e tentar atravessar a peça com `play`. | A peça para antes da própria e na primeira inimiga, nunca além. A dama inicial não tem jogada. Atravessar dá `ILLEGAL_MOVE`. O avanço duplo do peão é bloqueado por peça em qualquer das duas casas. | Conforme o esperado (PASSOU: 8 de 8 testes) |
| **CT-07** Cavalo salta sem colisão (RF04, UC02) | Posição inicial, cavalo em d4 cercado por peões e cavalo no canto a1. | Ler `legal_moves_from` e jogar `b1c3`. | b1 alcança a3 e c3 por cima dos peões, e o lance é aceito. O cavalo cercado mantém as 8 casas. No canto, restam b3 e c2. | Conforme o esperado (PASSOU: 3 de 3 testes) |
| **CT-08** Captura atualiza a pontuação de material (RF04, RF11, UC02) | Sequência `e2e4 d7d5 e4d5 d8d5 b1c3 d5d2 c1d2`. FENs com torre capturando peão, cavalo, bispo, torre e dama. Captura en passant. | Conferir `captured`, `material_score` e `material_balance` depois de cada captura. | Peão vale 1, cavalo e bispo 3, torre 5, dama 9. Na sequência, brancas 10, pretas 2 e saldo +8. Lance sem captura não muda nada. En passant vale 1. | Conforme o esperado (PASSOU: 10 de 10 testes) |
| **CT-09** Roque válido e roques proibidos (RF05, UC02) | FENs de roque pequeno e grande dos dois lados. Rei ou torre que já moveu, peça no caminho, rei em xeque, casa atacada no trajeto ou na chegada, torre capturada. | Tentar o roque com `play` e, nos válidos, conferir rei, torre, direitos e `undo`. | Roque válido move rei e torre, com SAN `O-O` ou `O-O-O`, e o `undo` restaura tudo. Os proibidos são recusados. Ataque a b1 no roque grande ou à própria torre não impede. | Conforme o esperado (PASSOU: 23 de 23 testes) |
| **CT-10** En passant válido e fora da janela (RF05, UC02) | Peões lado a lado depois de avanço duplo, janela vencida, avanço simples e en passant que expõe o rei na fileira. | Tentar a captura logo depois do avanço duplo e um lance depois. | O peão capturado sai da casa ao lado da origem. A captura só vale no lance imediato e só depois de avanço duplo. A que expõe o rei é recusada, e a que elimina o peão que dá xeque é aceita. | Conforme o esperado (PASSOU: 7 de 7 testes) |
| **CT-11** Promoção exige escolha e troca a peça (RF05, UC02, UC05) | Peão na 7ª fileira (brancas) ou na 2ª (pretas). Escolhas: nenhuma, dama, torre, bispo, cavalo, rei e peão. | Chamar `play` com e sem a peça escolhida. Testar também um peão cravado. | Sem escolha, `PROMOTION_REQUIRED` e nada muda. Com escolha válida, a peça é trocada. Rei ou peão como escolha são recusados. Peão cravado recebe `LEAVES_KING_IN_CHECK` antes de qualquer escolha. | Conforme o esperado (PASSOU: 15 de 15 testes) |
| **CT-12** Peça cravada: jogada que expõe o rei é recusada (RF06, UC02, UC07) | FENs com cavalo, torre, bispo e peão cravados, rei perto de casa atacada, xeque simples e xeque duplo. | Ler as jogadas legais e tentar as ilegais com `play`. | Erro `LEAVES_KING_IN_CHECK`, diferente de `ILLEGAL_MOVE`. A peça cravada só anda na linha da cravada. Em xeque, só valem jogadas que o resolvem. No xeque duplo, só o rei move. | Conforme o esperado (PASSOU: 11 de 11 testes) |
| **CT-13** Xeque-mate encerra a partida (RF07, UC07) | Mate do louco, mate do pastor, mate de corredor, mate sufocado e FEN já em mate. Contraprova: xeque com fuga. | Jogar até o mate e tentar outro lance depois. | Resultado `CHECKMATE` com o vencedor certo e estado `FINISHED`. Depois do mate, nenhum lance é aceito. Xeque com fuga não encerra. | Conforme o esperado (PASSOU: 7 de 7 testes) |
| **CT-14** Afogamento é empate (RF07, UC07) | FENs de afogamento, a partida conhecida mais curta que termina assim e uma posição com xeque. | Jogar o último lance ou carregar o FEN e ler o resultado. | Resultado `STALEMATE` sem vencedor. Sem jogadas, mas em xeque, não é afogamento. | Conforme o esperado (PASSOU: 4 de 4 testes) |
| **CT-15** Empates: material insuficiente, 50 lances, tripla repetição (RF07, UC07, UC08) | FENs de material insuficiente, relógio de meio-lance em 99, sequências de repetição e proposta de empate. | Jogar até a condição e também um lance antes dela. Comparar as chaves de posição. | Empate automático com material insuficiente, nos 100 meios-lances e na 3ª repetição. Mate vence os 50 lances. A repetição distingue vez, roque e en passant legal. `agree_draw` empata por acordo. | Conforme o esperado (PASSOU: 30 de 30 testes) |
| **CT-16** Tempo esgotado encerra a partida (RF07, RF11, UC07) | `TimeControl.BLITZ_5` e `tick` de 300 s. FEN `4k3/8/8/8/8/8/4P3/4K3` nos dois lados. | Avançar o relógio de quem joga e ler o resultado e os pontos. | Quem fica sem tempo perde por `TIMEOUT`. Contra rei sozinho é empate, com 0,5 para cada. Depois do fim, `tick` não faz nada e nenhum lance é aceito. | Conforme o esperado (PASSOU: 6 de 6 testes) |
| **CT-17** Perft: contagem de posições confere com valores de referência (RF04, RF05, RF06, UC02) | 6 posições de referência, entre elas a inicial (20, 400, 8902 e 197281 posições) e Kiwipete (até 4085603 na profundidade 4, teste lento). | Rodar `perft(board, profundidade)` e comparar o total. Conferir o FEN ao final. | Todos os totais iguais aos publicados e tabuleiro restaurado. Um erro em roque, en passant, promoção ou cravada mudaria a contagem. | Conforme o esperado (PASSOU: 24 de 24 testes) |
| **CT-18** Placar da série: vitória vale 1, empate vale 0,5 (RF11, RF13, UC07, UC09) | Partidas terminadas em mate, empate e desistência, e revanche com troca de cores. | Ler `match_points` depois de cada fim e tentar encerrar de novo a mesma partida. | Vitória soma 1, empate soma 0,5 para cada e desistência dá o ponto ao adversário. Os pontos entram uma só vez por partida e acompanham o jogador na troca de cores. | Conforme o esperado (PASSOU: 5 de 5 testes) |
| **CT-19** Cálculo de peças sob ameaça (RF10, UC06) | FENs com peças atacadas, defendidas, ataque bloqueado, rei em xeque e en passant legal e ilegal. | Chamar `threatened_pieces(color)` para as duas cores. | Lista as peças atacadas, mesmo defendidas. O rei não entra. Ataque bloqueado não conta. O peão capturável en passant entra enquanto a janela durar, sem repetir. A consulta não altera o jogo. | Conforme o esperado (PASSOU: 10 de 10 testes) |
| **CT-20** Pausa congela o relógio e recusa jogada (RF12, UC03) | `TimeControl.BLITZ_5`, `tick(10)`, `pause()`, `tick(100)` e uma tentativa de lance. | Conferir estado e relógio durante a pausa e depois de `resume()`. | Estado `PAUSED`, relógio em 290 s, lance recusado com `GAME_NOT_ACTIVE` e jogadas legais vazias. Pausa e retomada não reabrem partida encerrada. | Conforme o esperado (PASSOU: 6 de 6 testes) |
| **CT-21** Reiniciar e revanche (RF13, UC04, UC09) | Partida em andamento e partida terminada. Motor criado com FEN próprio. | Chamar `restart()` e `rematch()` e ler posição, cores, pontos e contagem de repetição. | `restart` volta à posição de partida com as mesmas cores e o mesmo placar. `rematch` inverte as cores e mantém o placar. Partida abandonada não dá pontos. | Conforme o esperado (PASSOU: 7 de 7 testes) |

### Computação gráfica

| Caso | Entrada | Procedimento | Resultado Esperado | Resultado Obtido |
|---|---|---|---|---|
| **CT-30** Matrizes: translação, rotação, escala e composição (RF15, RF16, UC02) | Pontos e vetores conhecidos, ângulos de 90 graus, câmeras, luz e sombra planar. | Aplicar `translation`, `scaling`, `rotation_*`, `compose`, `look_at`, `perspective`, `viewport` e `planar_shadow`. Comparar com o resultado calculado à mão. | Translação não afeta direção (w = 0), rotação preserva distâncias, `compose` aplica o último argumento primeiro, near e far vão às faces do cubo NDC e o y da tela inverte. | Conforme o esperado (PASSOU: 24 de 24 testes) |
| **CT-31** Câmera: ida e volta mundo, tela e casa em vários ângulos (RF16, UC02, UC06) | As 64 casas, 6 valores de yaw, 3 de pitch e vários viewports. | Projetar o centro da casa para pixel e voltar com `pick_square`. Testar também cliques fora do tabuleiro e na cabeça de uma peça. | A volta dá a mesma casa em toda combinação. Clique fora devolve `None`. Clique na cabeça escolhe a peça. Com duas peças sob o raio, vence a da frente. | Conforme o esperado (PASSOU: 84 de 84 testes) |
| **CT-32** Matriz de cores: estado vira cor, com prioridade (RF09, UC06) | Matriz 8x8 vazia e cada `CellState` em uma casa, em instantes diferentes. | Chamar `set` e `rgb(time)` e comparar as cores. | a1 é escura. Cada estado muda só a sua casa. Prioridade menor não sobrescreve e `NONE` limpa. Casa inválida é ignorada. Só ameaça e xeque pulsam, como função pura do tempo. | Conforme o esperado (PASSOU: 20 de 20 testes) |
| **CT-33** Partículas: gravidade, reflexão no piso e tempo de vida (RF15, UC02) | Partícula única com posição, velocidade e restituição conhecidas, e emissão acima da capacidade. | Chamar `update(dt)` e comparar velocidade, posição, cor e contagem de vivas. | A gravidade acelera para baixo e o arrasto reduz a velocidade. No piso, v' = v - (1 + e)(v.n)n, e nada atravessa. A partícula morre ao fim da vida. A capacidade nunca é ultrapassada. Mesma semente, mesma simulação. | Conforme o esperado (PASSOU: 12 de 12 testes) |
| **CT-34** Malhas: normais para fora e faces válidas (RF15, UC02) | As 6 peças de `build_piece_meshes` e os construtores `lathe`, `box`, `extrude` e `merge`. | Verificar índices, volume, normais, arestas e altura. | Faces válidas e volume positivo. Malhas fechadas, sem aresta solta. Normais para fora. No máximo 160 faces por peça. Peças apoiadas na mesa e dentro da casa. | Conforme o esperado (PASSOU: 40 de 40 testes) |
| **CT-35** Animação: interpolação e easing (RF15, UC02) | As 4 curvas de easing, `Tween` e as animações de voo, captura, promoção e queda do rei. | Avançar com `update(dt)` e ler `value` e `model_matrix`. | Toda curva vai de 0 a 1. A peça viaja em arco e pousa exatamente no alvo. A capturada encolhe girando. A promovida passa um pouco do tamanho. O rei tomba sem tirar a borda da base do lugar. | Conforme o esperado (PASSOU: 20 de 20 testes) |
| **CT-36** Render: corte de faces traseiras e ordem de pintura (RF15, UC02) | Cenas de teste em superfície sem janela, com a câmera parada e em movimento. | Desenhar com `Renderer3D` e ler os pixels da superfície. | Faces de costas e atrás do plano near saem. O objeto da frente cobre o de trás em qualquer ordem de envio. Sombras sobrepostas não escurecem em dobro. Partícula só soma luz. Peça em escala zero não quebra. | Conforme o esperado (PASSOU: 45 de 45 testes) |

### Interface

| Caso | Entrada | Procedimento | Resultado Esperado | Resultado Obtido |
|---|---|---|---|---|
| **CT-40** Menu inicia partida com nomes e tempo escolhidos (RF01, UC01) | Eventos reais: nomes `Alfa` e `Bravo` e Blitz pelo mouse. Nomes `Lado Claro` e `Lado Escuro`, Clássica e câmera fixa só pelo teclado. | Preencher o menu por eventos e acionar "Iniciar partida". | Abre `GameScene` com os nomes, o tempo e o modo de câmera escolhidos, nos dois caminhos. | Conforme o esperado (PASSOU: 2 de 2 testes) |
| **CT-41** Clique seleciona e preenche a matriz de cores (RF08, RF09, UC02, UC06) | Posição inicial com clique em e2. Depois de `e2e4 d7d5`, clique em e4. | Clicar por evento de mouse e ler a matriz e os marcadores. | e2 fica `SELECTED`, e3 e e4 ficam `PATH`, e5 fica `NONE`. Caminho tem ponto e captura tem anel. Clicar no alvo joga e marca `LAST_MOVE` nas duas casas. | Conforme o esperado (PASSOU: 3 de 3 testes) |
| **CT-42** Teclado seleciona e executa jogada (RF08, UC02) | Teclas: seta para cima, Enter, duas setas para cima e Espaço. Depois, setas com a câmera do lado das pretas e de lado. | Enviar eventos de teclado e ler o cursor e o histórico. | O cursor nasce em e2, a seleção abre, o cursor chega a e4 e a jogada entra no histórico. As setas seguem o que se vê: do lado das pretas, para cima é fileira menor. | Conforme o esperado (PASSOU: 3 de 3 testes) |
| **CT-43** Clique fora do turno dá aviso e não altera o jogo (RF03, UC02) | Cliques em e7 na vez das brancas, em e5 e e7 com e2 selecionada, em casa vazia e em lance que expõe o rei. | Clicar por evento e ler a faixa de avisos, a seleção, o tremor e o FEN. | A faixa mostra a mensagem do motor (por exemplo, "Essa peça é do adversário."), a casa treme, a seleção limpa e o FEN não muda. | Conforme o esperado (PASSOU: 5 de 5 testes) |
| **CT-44** Ameaça e xeque aparecem na matriz de cores (RF10, UC06, UC07) | Lances `e2e4 e7e5 g1f3 b8c6 f1c4`, com ameaça a e5 e f7. Lances `e2e4 d7d5 f1b5`, com xeque, seguidos de `c7c6`. | Jogar por eventos e ler a matriz, os marcadores, os tints e a faixa. | e5 e f7 ficam `THREAT` com triângulo e tint. O rei em e8 e a peça em b5 ficam `CHECK`, e a faixa começa com "Xeque!". Depois de `c7c6`, os alertas somem. | Conforme o esperado (PASSOU: 3 de 3 testes) |
| **CT-45** Pausa bloqueia a entrada (RF12, UC03) | Tecla P, 90 quadros, clique em e2, setas, T, V e R, clique no botão de giro e Retomar, P ou Esc. | Enviar os eventos com a pausa aberta e depois retomar. | O relógio não anda, nada seleciona, nenhum atalho age e o painel não recebe clique. Ao retomar, relógio e tabuleiro voltam a responder. | Conforme o esperado (PASSOU: 5 de 5 testes) |
| **CT-46** Partida completa por eventos até a tela de vitória (RF07, RF14, UC01, UC02, UC07) | Partida de 33 meios-lances (termina em `Rd8#`, com `O-O-O` no meio) e mate do pastor com câmera fixa. | Do menu à vitória, só por eventos de mouse e teclado. | Abre `GameOverScene` com vitória das brancas por `CHECKMATE`, 33 meios-lances no histórico e 1 ponto na série. Com a câmera fixa, o yaw continua 0. | Conforme o esperado (PASSOU: 2 de 2 testes) |
| **CT-47** Revanche troca cores e mantém o placar; menu volta ao início (RF13, UC09) | Tela de vitória, botões "Revanche com cores trocadas" e "Voltar ao menu". | Clicar, jogar nova partida e ler cores, pontos e motor. | Na revanche, as cores trocam, o placar fica e o histórico zera, com câmera padrão e sem partículas. Pelo menu, começa um motor novo com placar zerado. | Conforme o esperado (PASSOU: 4 de 4 testes) |
| **CT-48** Promoção pelo diálogo (RF05, UC05) | `4k3/1P6/8/8/8/8/8/4K3 w - - 0 1` e a posição equivalente das pretas. Clique, setas com Enter, teclas 1 a 4 e Esc. | Clicar em b7 e b8 e escolher a peça. | O diálogo abre antes de jogar. A peça escolhida entra em b8, nas 4 opções e nos 3 meios de entrada. Esc cancela sem jogar e limpa a seleção. | Conforme o esperado (PASSOU: 9 de 9 testes) |
| **CT-49** Redimensionar a janela mantém o clique correto (RNF07, RF16, UC02) | Janelas de 1024x640, 1920x1080, 800x600 e 1600x700, em sequência e com a pausa aberta. | Redimensionar por evento, clicar em e2 e e4 e nos botões. | O viewport acompanha a janela, os cliques caem nas casas certas e a jogada acontece. Botões e sobreposição seguem no lugar certo. | Conforme o esperado (PASSOU: 7 de 7 testes) |

### Ataques do QA, versão 1.0

| Caso | Entrada | Procedimento | Resultado Esperado | Resultado Obtido |
|---|---|---|---|---|
| **CT-50** Partidas aleatórias contra gerador e detector independentes (RF04, RF05, RF06, UC02, UC07) | Partidas aleatórias com semente fixa, com milhares de lances. | Jogar lances sorteados pelo motor e conferir cada posição com um gerador de lances e um detector de ataque escritos à parte, sem usar o motor. | O conjunto de lances legais é igual ao do modelo independente. Um rei por cor, nenhum peão na 1ª ou 8ª, FEN de ida e volta, undo restaura tudo, roque nunca volta e SAN aponta uma única jogada. | Conforme o esperado (PASSOU: 7 de 7 testes) |
| **CT-51** Bordas de promoção, en passant e roque (RF05, RF06, UC02, UC05) | Promoção com captura, xeque e mate; en passant que expõe o rei; roque com torre capturada e outra na casa original. | Montar cada posição por FEN e tentar a jogada pelo motor. | Cada jogada é aceita ou recusada conforme a regra oficial, com o erro certo. | Conforme o esperado (PASSOU: 23 de 23 testes) |
| **CT-52** Precedência entre fins de jogo no mesmo lance (RF07, UC07) | Mate, afogamento e tripla repetição no lance que completaria os 50 lances. | Jogar o lance decisivo pelo motor. | Vale a regra que encerra primeiro: o mate vence os 50 lances. | Conforme o esperado (PASSOU: 10 de 10 testes) |
| **CT-53** Tripla repetição, roque perdido e en passant (RF07, UC07) | Sequências que repetem a posição com e sem direito de roque, e com en passant legal e ilegal. | Repetir lances e conferir quando o empate é declarado. | Só contam como iguais as posições com a mesma vez, os mesmos direitos de roque e o mesmo en passant legal. | Conforme o esperado (PASSOU: 4 de 4 testes) |
| **CT-54** Material insuficiente por captura e promoção subpotente (RF07, UC07) | Finais com R x R, R+B x R, R+C x R e bispos de mesma cor ou de cores diferentes. | Chegar à posição por captura, en passant ou promoção subpotente. | Empate imediato só quando nenhum dos lados consegue dar mate. | Conforme o esperado (PASSOU: 9 de 9 testes) |
| **CT-55** Relógio, desistência, série, revanche e pretas primeiro (RF07, RF11, RF12, RF13, UC03, UC08, UC09) | Tempo contra rei só, tempo exato, dt zero, negativo, NaN e infinito, desistência na pausa, sete revanches, FEN com as Pretas primeiro. | Chamar o motor em cada situação e conferir resultado e placar. | Tempo esgotado contra rei só é empate. Pontos da série nunca contam duas vezes. dt inválido não altera o relógio. | Conforme o esperado (PASSOU: 14 de 14 testes) |
| **CT-56** Entradas absurdas e FEN malformadas (RF04, RNF07, UC02) | 13 formatos de casa absurdos em play e 29 FEN malformadas. | Chamar play com cada entrada e from_fen com cada FEN. | play devolve erro, sem exceção e sem alterar o estado. FEN inválida levanta ValueError claro. | Conforme o esperado (PASSOU: 44 de 44 testes) |
| **CT-57** Macaco: eventos aleatórios com invariantes (RNF07, UC02, UC03) | Cliques, teclas, roda, texto com emoji e caracteres de controle, janelas de 1x1 a 3000x200, dt inválidos, com semente fixa. | Enviar eventos aleatórios ao App.step, em todas as cenas, e conferir as invariantes a cada quadro. | Nenhuma exceção. Histórico sempre legal, tabuleiro e relógio parados com sobreposição que congela, uma cena ativa. | Conforme o esperado (PASSOU: 2 de 2 testes) |
| **CT-58** Corridas entre relógio, voo, pausa, promoção e fim (RF05, RF07, RF12, UC02, UC03, UC05) | Tempo acabando com a promoção aberta, lance e tempo no mesmo quadro, pausa durante o voo, Esc em cada estado. | Dirigir cada roteiro por eventos reais. | O estado final é coerente, sem peça fantasma, sem lance depois do fim e sem cena presa. | Conforme o esperado (PASSOU: 15 de 15 testes) |
| **CT-59** Clique: o que se vê é o que se aciona (RF08, RF16, UC02, UC06) | Posição inicial, cada pixel do tabuleiro, peão e2 atrás do rei, clique na cabeça de peça alta selecionada. | Comparar, pixel a pixel, a peça pintada com a casa que o clique aciona, e clicar nos casos do relatório de QA. | Menos de 2% de divergência, tanto em pixels de peça quanto em pixels de chão. O 1º lance e2 é clicável, e clicar de novo na peça selecionada desmarca. | Conforme o esperado (PASSOU: 12 de 12 testes) |
| **CT-60** Clique duplo e eventos no mesmo quadro (RF12, RNF07, UC03, UC08, UC09) | Clique duplo em Propor empate, Reiniciar e Retomar. Dois Enter em Revanche no mesmo quadro. Redimensionar ao trocar de cena. | Enviar os dois eventos sem intervalo de tempo real. | O 2º clique não aciona o que apareceu embaixo do mouse. As cores trocam uma vez só. A cena nova já nasce no tamanho certo. | Conforme o esperado (PASSOU: 8 de 8 testes) |
| **CT-61** Nomes: caracteres perigosos, largura e ajuda (RF01, RNF07, UC01) | Seletores de variação (largura zero), emoji, coreano, 16 W, 16 Ç, nome só de espaços, H fechando a ajuda. | Digitar no campo por TEXTINPUT e iniciar a partida. | O jogo não cai. Caractere que a fonte não desenha é recusado. O nome cabe nas placas. A tecla que fecha a ajuda não vira texto. | Conforme o esperado (PASSOU: 34 de 34 testes) |
| **CT-62** Janelas e números extremos (RF16, RNF07, UC02) | F3 e F4 em oito tamanhos até 1x1, dt NaN e infinito, roda de um milhão de passos, jogada no meio da volta à vista padrão. | Aplicar cada entrada no App.step. | Nenhuma exceção, zoom no limite, e a vista padrão termina mesmo com jogada no meio. | Conforme o esperado (PASSOU: 19 de 19 testes) |
| **CT-63** Fim de jogo, revanche, menu e HUD (RF11, RF13, RF14, UC04, UC09) | R no voo do mate, T na queda do rei, relógio com mais de 1 hora, nomes longos nas confirmações, ciclo menu, partida, fim, menu. | Dirigir cada roteiro por eventos e olhar o estado da cena. | A tela de vitória não é pulada, o aviso não é trocado, o relógio não invade a etiqueta, o título não corta a ação, nomes e opções sobrevivem ao ciclo. | Conforme o esperado (PASSOU: 11 de 11 testes) |
| **CT-64** Vazamento de memória (RNF01, RNF07, UC09) | 200 revanches seguidas e 5 minutos simulados de partida. | Medir com tracemalloc e conferir os caches e as partículas. | Memória estável, caches e partículas sempre dentro do limite. | Conforme o esperado (PASSOU: 3 de 3 testes) |
| **CT-65** Rede só em net, escrita só em data, sem execução dinâmica (RNF05, RNF07, UC02) | Todos os módulos do jogo e das ferramentas. | Analisar o código-fonte pela árvore sintática. | Só `xadrez/net` importa socket e selectors, e só `xadrez/data` grava em disco. Threads só em `net` e na `ui`. Nada usa eval, exec, pickle nem subprocess, e só as ferramentas de documentação chamam programas externos. | Conforme o esperado (PASSOU: 204 de 204 testes) |
| **CT-66** PNG, autoria, e-mails e caminhos pessoais (RNF05, UC01) | Imagens de docs/, arquivos versionados e autoria dos commits. | Ler os pedaços dos PNG, procurar e-mails e caminhos pessoais e conferir a autoria. | Os PNG não têm metadados de texto, e não há e-mail nem caminho pessoal no que o git publica. | Conforme o esperado (PASSOU: 64 de 64 testes) |
| **CT-67** Python 3.10 e portabilidade (RNF02, UC01) | Todos os módulos do projeto. | Analisar com ast.parse(feature_version=(3, 10)) e procurar biblioteca padrão nova e caminho fixo de sistema. | Todos os módulos são sintaxe válida de Python 3.10, sem API nova nem caminho fixo. A execução real em 3.10, Linux e macOS fica com o CI. | Conforme o esperado (PASSOU: 370 de 370 testes) |

### Versão 1.1: CPU, PGN e tempos

| Caso | Entrada | Procedimento | Resultado Esperado | Resultado Obtido |
|---|---|---|---|---|
| **CT-70** CPU sempre devolve jogada legal, sem alterar o tabuleiro (RF18, UC10) | 17 posições especiais (promoções, roques, en passant, xeques, cravada), 40 posições de partidas aleatórias e os 4 níveis, com o Hardcore limitado a 0,05 s. Perft do `SearchBoard` nas posições de referência. | Chamar `choose_move` e comparar a jogada com `legal_moves` e o FEN antes e depois. Contar posições no tabuleiro compacto e conferir, lance a lance, contra `rules.py`. | A jogada é sempre legal e o FEN não muda. Promoção já vem com a peça. Sem jogada legal, `ValueError` claro. Os perft do tabuleiro compacto batem com os valores publicados. | Conforme o esperado (PASSOU: 132 de 132 testes) |
| **CT-71** CPU acha mate em 1 em todos os níveis (RF18, UC10) | Posições de mate em 1, como o de corredor e o abafado, e mate no lance que completaria os 50 lances. | Pedir a jogada a cada nível e aplicá-la no tabuleiro. | A jogada dá xeque-mate. O ruído do Easy e do Medium não esconde o mate. O mate no 50º lance vale mais que o empate. | Conforme o esperado (PASSOU: 29 de 29 testes) |
| **CT-72** CPU acha mate em 2 nos níveis Hard e Hardcore (RF18, UC10) | Posições de mate em 2, como a escada de torres, e posições com mate rápido e mate lento. | Pedir a jogada e provar por força bruta que toda resposta permite mate imediato. Ler a nota de `analyze`. | A jogada força o mate. O mate mais rápido é preferido, e a nota mede a distância. Quem está levando mate adia o quanto puder. | Conforme o esperado (PASSOU: 12 de 12 testes) |
| **CT-73** CPU não entrega a dama de graça a partir do Medium (RF18, UC10) | Posições com a dama em jogo e partidas inteiras contra o Easy (estas com a marca `slow`). | Aplicar a jogada e conferir se o adversário pode capturar a dama com peça mais barata ou sem recaptura. | Medium e Hard não deixam a dama de graça quando havia como evitar. | Conforme o esperado (PASSOU: 20 de 20 testes) |
| **CT-74** A força cresce com o nível, em partidas entre os níveis (RF18, UC10) | 12 partidas por par, com as cores alternadas e sementes fixas: Medium contra Easy, Hard contra Medium e Hardcore contra Hard, com o Hardcore limitado a 0,25 s por lance. | Jogar as partidas pelo motor até o fim, ou até 300 meios-lances, e somar os pontos. | O nível mais forte faz pelo menos 75% dos pontos em cada par. Todo lance é aceito pelo motor. | Conforme o esperado (PASSOU: 3 de 3 testes) |
| **CT-75** Cancelamento e limite de tempo da busca são respeitados (RF18, RNF09, UC10) | Meio-jogo e posição tática de referência, `should_stop` em vários momentos e `max_seconds` curto ou negativo. | Cancelar a busca do início, no meio e de outra thread. Medir o tempo com limite de tempo. | A resposta é sempre uma jogada legal, a melhor achada até ali. O limite de tempo nunca passa de `max_seconds` com folga de 0,1 s. `should_stop` é consultado com frequência. | Conforme o esperado (PASSOU: 61 de 61 testes) |
| **CT-76** PGN válido, com resultado e cabeçalhos (RF21, RF22, UC14, UC15) | Partidas com mate, empate e em andamento, FEN próprio, pretas jogando primeiro, nomes com aspas e barras e partidas longas. | Chamar `game_to_pgn` e refazer os lances do texto no motor. | Cabeçalhos obrigatórios e resultado certos. FEN próprio gera `SetUp` e `FEN`. O texto fica em até 80 colunas, e a ida e volta dá a mesma partida. Nome nenhum quebra o cabeçalho. | Conforme o esperado (PASSOU: 19 de 19 testes) |
| **CT-77** Tempos com incremento (RF24, UC01) | `TimeControl.BLITZ_3_2` e `TimeControl.CLASSIC_15_10`, além dos presets antigos. | Conferir os valores e jogar lances com o relógio correndo. | O incremento entra só para quem jogou, e pode manter vivo quem passaria do tempo inicial. Os presets antigos não mudam. | Conforme o esperado (PASSOU: 5 de 5 testes) |

### Versão 1.1: contas e histórico

| Caso | Entrada | Procedimento | Resultado Esperado | Resultado Obtido |
|---|---|---|---|---|
| **CT-80** Conta: criar, entrar, recusar senha errada e nome repetido (RF20, UC13) | Contas em pasta temporária, grafias diferentes do mesmo nome, nomes e senhas inválidos e tipos errados. | Chamar `AccountStore.create` e `AccountStore.authenticate`. | Entra só com a senha certa, com a mesma mensagem para senha errada e conta inexistente, e o mesmo custo de hash nos dois casos. Maiúsculas e formas Unicode são a mesma conta. Tipo errado responde não, sem exceção. | Conforme o esperado (PASSOU: 37 de 37 testes) |
| **CT-81** Senha nunca aparece no arquivo (RNF08, UC13) | Senhas com acento e emoji, gravadas em pasta temporária. | Procurar a senha em todos os bytes do arquivo e ler os campos gravados. | A senha não aparece em nenhuma codificação. O arquivo só guarda nome, sal, iterações e hash, e o sal muda mesmo com a mesma senha. | Conforme o esperado (PASSOU: 5 de 5 testes) |
| **CT-82** Histórico: mantém 50, ordem e estatísticas (RF21, UC14) | Registros de `MatchRecord`, 51 partidas, duas contas e nomes maliciosos como `../../x`. | Chamar `HistoryStore.add`, `HistoryStore.records` e `HistoryStore.stats`. | A mais recente vem primeiro, a 51ª empurra a mais antiga e as estatísticas contam só as guardadas. Cada conta tem o seu arquivo, e nome nenhum sai da pasta de dados. | Conforme o esperado (PASSOU: 43 de 43 testes) |
| **CT-83** Arquivo corrompido não derruba o jogo (RF20, RF21, UC13, UC14) | Arquivos truncados e fora do formato, pasta impossível, falta de permissão simulada e troca atômica bloqueada. Local por sistema e `CHESS_THE_GAME_DATA`. | Abrir os dados em cada situação e conferir o que ficou em disco. | O arquivo ruim é guardado com outro nome, e a lista começa vazia. Falha de gravação vira erro claro, sem deixar temporário e sem apagar o que existe. Abrir o jogo não grava nada. | Conforme o esperado (PASSOU: 52 de 52 testes) |

### Versão 1.1: rede local

| Caso | Entrada | Procedimento | Resultado Esperado | Resultado Obtido |
|---|---|---|---|---|
| **CT-85** Código de sala: ida e volta, e recusa de código inválido (RF19, UC11, UC12) | IPv4 variados, código em minúsculas e com espaços, dígito trocado, vizinhos trocados, códigos e tipos inválidos e endereços fora da rede local. | Chamar `encode_room_code`, `decode_room_code`, `local_ipv4` e `is_lan_address`. | A ida e volta dá o mesmo IP, em 7 caracteres e sem 0, O, 1, I e L. A conferência pega a maioria dos erros de digitação. Erro vem em português. `local_ipv4` não envia pacote. | Conforme o esperado (PASSOU: 61 de 61 testes) |
| **CT-86** Partida inteira entre duas sessões por socket (RF19, UC11, UC12) | `HostSession` e `ClientSession` reais em 127.0.0.1, com partida até o fim, empate, desistência e revanche. | Trocar mensagens por `send_move`, `send_result` e os demais `send`, e ler os eventos em `poll`. | Os dois lados terminam com o mesmo FEN. A jogada ilegal é recusada pelo motor de quem recebe. A revanche troca as cores e só começa com os dois pedidos. `result` só vale vindo da sala. | Conforme o esperado (PASSOU: 26 de 26 testes) |
| **CT-87** Queda de conexão vira evento, sem travar (RF19, UC11, UC12) | Queda brusca dos dois lados, sinal de vida parado, porta ocupada, segundo jogador, versão diferente, sala muda e fechamento em cada fase. | Provocar cada situação e ler `poll`, com tempos curtos em `NetTimings`. | Toda falha vira `PeerLeft` ou `NetworkError`, uma vez só e com mensagem clara. `poll` não bloqueia, `close` não espera o prazo, e a porta fica livre depois. | Conforme o esperado (PASSOU: 57 de 57 testes) |
| **CT-88** Mensagens inválidas e maliciosas são recusadas (RF19, RNF08, UC11, UC12) | Socket cru em 127.0.0.1: bytes aleatórios, linha sem fim, linha de 4097 bytes, tipos errados, enxurrada, conexões mudas e conexão de fora da rede local. | Enviar cada ataque antes e depois de entrar na sala e chamar `encode_message` e `decode_message`. | Antes de entrar, só cai a conexão do atacante. Na partida, a sala encerra com erro. Nada acumula memória além do limite, e o nome do atacante não chega à tela. | Conforme o esperado (PASSOU: 300 de 300 testes) |

### Versão 1.1: interface

| Caso | Entrada | Procedimento | Resultado Esperado | Resultado Obtido |
|---|---|---|---|---|
| **CT-90** Modo Partida esconde caminhos, ameaças e xeque; Treinamento mostra (RF17, UC01, UC06) | As mesmas posições nos dois modos, com peça selecionada, ameaça, xeque, lance ilegal e peça sem jogada. | Jogar por eventos e ler a matriz de cores, os marcadores, a planilha e a faixa de avisos. | No modo Partida ficam só seleção, cursor e último lance, e a recusa é "Lance inválido.". A planilha omite `+` e `#` até o fim. As regras são as mesmas nos dois modos. Treinamento mostra tudo. | Conforme o esperado (PASSOU: 19 de 19 testes) |
| **CT-91** Partida contra a CPU até o fim, por eventos (RF18, UC10) | Do menu à tela de fim em cada nível, com a CPU de brancas e de pretas e sorteio de cor. | Jogar por eventos reais até o fim, com mate dos dois lados, captura, roque e promoção da CPU e revanche. | A tela de fim abre com o resultado certo. A CPU promove sem abrir o diálogo, e suas jogadas animam. A câmera fica do lado do jogador, e a revanche troca as cores. | Conforme o esperado (PASSOU: 18 de 18 testes) |
| **CT-92** CPU pensando não bloqueia a entrada nem o desenho (RF18, RNF09, UC10) | Partida contra o Hardcore, mouse sobre o tabuleiro, câmera em movimento, pausa, reinício, desistência, menu, fechamento e busca com falha. | Dar quadros com a busca correndo e conferir o cursor, a thread, `sys.getswitchinterval` e a cópia do tabuleiro. | O cursor responde no mesmo quadro e o tabuleiro real não muda. O intervalo de troca vale durante a busca e sempre volta. Com a câmera em movimento, a busca dorme. Toda saída cancela sem deixar thread. | Conforme o esperado (PASSOU: 29 de 29 testes) |
| **CT-93** Login, criação de conta e convidado (RF20, UC13) | Eventos reais de teclado e mouse em `App(require_login=True)`, com dados em pasta temporária. | Criar conta, entrar com outra grafia, errar a senha, jogar como convidado e sair da conta. | `main` abre no login e `App()` abre no menu. Senha errada e conta inexistente têm a mesma mensagem. A senha é mascarada e não passa pelo cache de texto. O convidado entra sem conta. | Conforme o esperado (PASSOU: 19 de 19 testes) |
| **CT-94** Partida encerrada entra no histórico da conta (RF21, UC14) | Partidas de conta logada e de convidado, mate, empate, CPU, reinício, abandono e arquivo corrompido. | Terminar a partida por eventos e abrir a aba "Meu histórico": lista, folha, roda, teclado e cópia. | A partida entra uma vez, com a cor, o resultado e o nível certos, mesmo com a peça no ar. Reinício e convidado não gravam. Falha ao gravar vira aviso. Arquivo ruim não derruba a aba. | Conforme o esperado (PASSOU: 27 de 27 testes) |
| **CT-95** Duas instâncias do jogo em rede, por eventos (RF19, UC11, UC12) | Duas instâncias de `App` no mesmo processo, em 127.0.0.1, do menu até a revanche. | Jogar pelos dois lados por eventos, com relógio, empate, desistência, queda e jogada ilegal vinda de fora. | Os dois lados chegam ao mesmo FEN e ao mesmo resultado. A sala mede os relógios e decide. `clock_ms` não decide nada. Jogada ilegal encerra a sala, e não há pausa nem reinício em rede. | Conforme o esperado (PASSOU: 37 de 37 testes) |
| **CT-96** Arrastar a peça para jogar (RF23, UC02) | Arrastos por eventos até destino válido, destino ilegal, fora do tabuleiro, painel, promoção e na vez da CPU. | Apertar, mover e soltar, lendo a matriz de modelo, a seleção e a jogada. | Passando de 6 pixels, a peça sobe e segue o mouse. Soltar em destino válido joga. Na própria casa mantém a seleção, e fora do tabuleiro só devolve. Clique e teclado seguem valendo. | Conforme o esperado (PASSOU: 23 de 23 testes) |
| **CT-97** Virar o tabuleiro mantém o clique correto (RF23, UC02, UC06) | Tecla F e botão "Virar", com a câmera parada, durante o giro e na volta à vista padrão. | Virar, clicar em várias casas e usar as setas. | A câmera termina no lado exato oposto, o clique continua na casa certa e as setas seguem o lado de quem olha. A vista padrão desfaz a virada. | Conforme o esperado (PASSOU: 14 de 14 testes) |
| **CT-98** Copiar PGN (RF22, UC15) | Botão e tecla C na partida e na tela de fim, com `pygame.scrap` substituído por uma imitação e sem janela. | Copiar e ler o texto entregue à área de transferência. | O texto é o PGN da partida. No Windows vai em `mbcs` com quebra de linha do sistema, e nos outros em UTF-8. Falha vira aviso, nunca exceção. | Conforme o esperado (PASSOU: 12 de 12 testes) |

### Ataques do QA, versão 1.1

| Caso | Entrada | Procedimento | Resultado Esperado | Resultado Obtido |
|---|---|---|---|---|
| **CT-100** Modo Partida: tela igual com e sem xeque (RF17, UC06) | Posições em que só o xeque muda, porque o peão bloqueia ou não a coluna, e cavalo cravado e livre. | Comparar a tela pixel a pixel nos dois casos. Repetir em Treinamento, como controle. | Painel e faixa idênticos, e tabuleiro idêntico fora das casas do peão. O controle em Treinamento mostra a diferença, o que prova que o teste enxerga. | Conforme o esperado (PASSOU: 3 de 3 testes) |
| **CT-101** Modo Partida: recusa igual em todo motivo (RF17, UC02) | Lance ilegal por motivos diferentes, peça do adversário, casa vazia, arrasto recusado e peão cravado na sétima. | Tentar cada lance por eventos e ler a faixa, o tremor e os marcadores. | A mensagem é sempre "Lance inválido.", sem tremor nem anel. Peça sem jogada não avisa nada. O peão cravado não abre a promoção. | Conforme o esperado (PASSOU: 11 de 11 testes) |
| **CT-102** Modo Partida: só indicadores neutros em cada quadro (RF17, UC06, UC10, UC11) | Partida com xeques em 2 jogadores, contra a CPU e em rede, com o painel F4 aberto. | Ler em cada quadro os estados da matriz, os tints, as placas e o painel F4. | Só aparecem seleção, cursor e último lance, em todos os quadros. A revanche continua em Partida. | Conforme o esperado (PASSOU: 4 de 4 testes) |
| **CT-103** Modo Partida: planilha e cópia sem as marcas de xeque (RF17, RF22, UC06, UC15) | Partidas com xeque e mate, e jogador com `+` ou `#` no nome. | Ler a planilha e copiar o PGN no meio da partida e depois do fim. | Com a partida correndo, planilha e cópia omitem `+` e `#` dos lances, e o cabeçalho fica como está. Depois do fim, a notação sai completa. | Conforme o esperado (PASSOU: 5 de 5 testes) |
| **CT-104** Treinamento continua igual à versão 1.0 (RF17, RF09, RF10, UC06) | Posições com caminho, captura, ameaça, xeque e peça sem jogada, e dois jogadores com o mesmo nome. | Jogar por eventos em Treinamento, ler a tela e copiar o PGN. | Caminhos, capturas, ameaças, xeque, tremor e motivo da recusa aparecem. A cópia traz `+` e `#`. Nomes iguais ficam diferentes na tela. | Conforme o esperado (PASSOU: 4 de 4 testes) |
| **CT-105** Cada saída com a CPU pensando cancela a busca (RF18, RNF09, UC10) | Pausar, reiniciar, desistir, menu, fechar, redimensionar e virar com a CPU pensando, inclusive mil trocas de partida. | Executar cada saída e conferir thread, lance e `sys.getswitchinterval`. | Nada chega depois da saída, nenhuma thread sobra e o intervalo de troca volta ao original, mesmo com exceção. Redimensionar e virar não cancelam. | Conforme o esperado (PASSOU: 9 de 9 testes) |
| **CT-106** Jogada atrasada da CPU não entra em outra partida (RF18, UC10) | Busca cancelada que ainda termina, tempo acabando no quadro em que a busca termina, rei sozinho e posição sem lance. | Forçar cada corrida com busca substituída ou relógio ajustado. | A jogada de uma busca cancelada nunca chega à partida seguinte. O tempo acabado vale antes do lance. Sem lance, nenhuma thread abre. | Conforme o esperado (PASSOU: 5 de 5 testes) |
| **CT-107** A CPU faz lances especiais, dá mate e abre de brancas (RF18, UC10) | Posições de roque, en passant, promoção e mate para a CPU, e revanche que a põe de brancas. | Jogar por eventos até o lance dela e até a tela de fim. | Os lances valem e animam. O mate grava a derrota de quem está logado. O relógio dela anda enquanto pensa, e o do humano não. | Conforme o esperado (PASSOU: 7 de 7 testes) |
| **CT-108** Orçamento da CPU cabe no relógio (RF18, UC10) | `search_budget` em vários valores de relógio e incremento, e Hardcore com 1 s e 2 s de incremento. | Calcular o orçamento e jogar lances reais em tempo real. | O orçamento nunca passa do que resta no relógio, e a CPU joga antes de o tempo acabar, mesmo com pouco tempo. | Conforme o esperado (PASSOU: 11 de 11 testes) |
| **CT-109** Entrada na vez da CPU e falhas da busca (RF18, RNF07, UC10) | Clique, arrasto e teclado na vez dela, jogada recusada pelo motor, thread que não abre e dois Enter no menu. | Enviar os eventos e simular cada falha. | Nada muda na posição. A falha vira lance simples com aviso, e a partida segue. Dois Enter abrem uma partida só. | Conforme o esperado (PASSOU: 6 de 6 testes) |
| **CT-110** Rede: o que chega pelo socket (RF19, RNF08, UC11, UC12) | Socket cru contra a tela real: jogada ilegal e fora da vez, formato errado, `clock_ms` falso, 500 propostas de empate, `hello` e `start` fora de hora, `result` que não confere. | Enviar cada mensagem com o jogo aberto e ler o motor, os relógios e as sobreposições. | A sala encerra com vitória de quem ficou, nada é aplicado ao tabuleiro e nenhum relógio muda. O `result` que não confere com o tabuleiro encerra a partida. Sala muda não prende quem entrou. | Conforme o esperado (PASSOU: 53 de 53 testes) |
| **CT-111** Rede: nome hostil passa pela tela sem derrubar (RF19, RNF08, UC11, UC12) | Nomes de 16 W, só acentos combinantes, emoji, árabe, coreano e controle. | Fazer o nome chegar pela rede e passar pelo HUD, pela faixa, pelas sobreposições e pela tela de fim. | Nada cai nem vaza da área. Inversão de direção e controle são recusados pelo protocolo. | Conforme o esperado (PASSOU: 15 de 15 testes) |
| **CT-112** Rede: queda em cada estado (RF19, RNF07, UC11, UC12) | Queda na sala, no diálogo de promoção, em sobreposição aberta, com a peça no ar e na tela de fim. | Fechar o outro lado em cada estado e dar quadros. | A partida termina sem cair e a revanche desliga. O motivo chega à tela de fim. Quem perdeu não lê que venceu. | Conforme o esperado (PASSOU: 9 de 9 testes) |
| **CT-113** Rede: mesmo FEN e mesmo resultado em cada fim (RF19, UC11, UC12) | Duas telas reais: mate, empate, desistência, abandono, desistências cruzadas, lance cruzado com o fim e mate cruzado com o tempo. | Jogar pelos dois lados e comparar FEN, histórico, resultado e placar. | Os dois lados terminam iguais, e o lance que cruzou com o fim é desfeito. Único caso sem como igualar: quem saiu com um lance da sala a caminho fica com um lance a menos, com o mesmo vencedor. | Conforme o esperado (PASSOU: 54 de 54 testes) |
| **CT-114** Rede: quem criou a sala decide o tempo (RF19, UC11, UC12) | Relógios esgotados dos dois lados, relógios defasados, cópia que ignora o próprio relógio e revanche com a sala de pretas. | Dar quadros com `dt` diferente em cada lado e ler o resultado. | A sala mede os dois relógios e decide, inclusive jogando de pretas. Nunca há dois vencedores nem motivos diferentes. Jogada depois do fim é ignorada, e quem fica só com o rei empata. | Conforme o esperado (PASSOU: 11 de 11 testes) |
| **CT-115** Rede: revanche e proposta de empate (RF19, UC11, UC12) | Pedidos cruzados, proposta sem resposta, proposta repetida, recusa, lance que recusa e resposta sem proposta. | Enviar por eventos e pelo socket, com as duas telas abertas. | A revanche cruzada começa uma partida só, com as cores trocadas. Vale uma proposta por lance. O cartão fica sobre a planilha, sem parar o relógio, e jogar um lance recusa. | Conforme o esperado (PASSOU: 17 de 17 testes) |
| **CT-116** Rede: entrada na sala (RF19, UC11, UC12) | Código errado, em minúsculas e com espaços, Enter repetido e reabertura logo depois de sair, na mesma porta em 127.0.0.1. | Digitar por eventos e abrir a sala de novo. | Erro vira mensagem, e o campo continua funcionando. Enter repetido abre uma sessão só. A porta reabre na hora, mesmo com a conexão em TIME_WAIT. | Conforme o esperado (PASSOU: 17 de 17 testes) |
| **CT-117** Rede: thread e socket não sobram (RF19, RNF07, UC11, UC12) | 8 caminhos de saída: cancelar, fechar a sala, fechar entrando, sair para o menu, fechar na partida, sair e fechar na tela de fim e jogada de trapaça. | Percorrer cada caminho e listar as threads e a porta. | Nenhuma thread `chess-net` nem porta aberta sobra. | Conforme o esperado (PASSOU: 8 de 8 testes) |
| **CT-118** Login e conta por teclado e mouse (RF20, UC13) | Nome com acento, maiúsculas, espaços e emoji, e senha vazia, longa, com espaços e acentos. | Preencher por eventos, inclusive só com Tab e Enter. | A conta entra por qualquer grafia. Emoji não entra no campo. Enter em "Senha" avança para "Repita a senha" ao criar conta. Erro limpa as senhas, com a mesma mensagem para senha errada e conta inexistente. | Conforme o esperado (PASSOU: 19 de 19 testes) |
| **CT-119** A senha não fica em widget nem em cache (RNF08, UC13) | Seis caminhos depois de digitar a senha, senhas diferentes e arquivo de contas. | Procurar a senha nos campos, no cache de texto do tema e no arquivo. Comparar o desenho da máscara. | A senha não fica em lugar nenhum depois de usada. A máscara desenha só pontos, igual para senhas diferentes do mesmo tamanho. | Conforme o esperado (PASSOU: 8 de 8 testes) |
| **CT-120** Arquivo de contas ruim vira aviso (RF20, RNF07, UC13) | `accounts.json` corrompido de vários jeitos, pasta inválida, arquivo que é uma pasta e arquivo somente leitura. | Abrir o login e criar uma conta em cada caso. | A tela mostra aviso e nunca cai. A conta nova funciona quando dá para gravar. O arquivo ruim fica guardado, e nenhum temporário sobra. | Conforme o esperado (PASSOU: 20 de 20 testes) |
| **CT-121** Histórico editado à mão não derruba a aba (RF21, RNF07, UC14) | Campos adulterados, tipos errados, controle, nome e PGN gigantes e duração de 401 dígitos. | Abrir a aba "Meu histórico" e a folha, e gravar uma partida nova por cima. | A aba abre e desenha, e os textos e números param no limite de cada campo. A partida nova entra, e arquivo sem gravação vira aviso na tela de fim. | Conforme o esperado (PASSOU: 72 de 72 testes) |
| **CT-122** Registro correto em cada fim de partida (RF21, UC14) | Mate, empate, desistência, tempo, revanche, CPU e rede, com abandono e janela fechada. | Terminar por eventos e ler o registro. | Resultado, adversário, cor, duração, modo e motivo certos, uma vez só. Em rede, cada lado grava a sua visão. Fechar a janela grava a derrota de quem saiu. | Conforme o esperado (PASSOU: 10 de 10 testes) |
| **CT-123** Contas separadas, convidado e 51ª partida (RF20, RF21, UC13, UC14) | Duas contas com nomes parecidos, convidado, "Sair da conta", 51 partidas e lista vazia. | Jogar e navegar por eventos, inclusive Esc, Esc e Enter na aba. | Os históricos não se misturam, e o convidado não toca a pasta de dados. A 51ª empurra a mais antiga, e a lista rola até o fim. Esc e Enter não saem da conta. | Conforme o esperado (PASSOU: 6 de 6 testes) |
| **CT-124** Arrastar: soltar fora e interromper (RF23, RNF07, UC02) | Soltar no painel, em botão, fora da janela, sem ter apertado. Tecla, botão direito, janela, F3, F4 e F11 com a peça no ar. | Enviar os eventos no meio do arrasto. | A peça volta, nenhum botão é acionado e nada cai. O botão direito gira a câmera, e o arrasto continua. | Conforme o esperado (PASSOU: 16 de 16 testes) |
| **CT-125** Arrastar: na vez errada, em voo e no fim (RF23, UC02) | Peça do outro, casa vazia, voo, tempo esgotando, e em rede na vez do outro e com ele desistindo. | Apertar e arrastar em cada situação. | O arrasto não começa quando não pode. Com a partida acabando, a peça volta. Em rede, o arrasto solto envia a jogada. | Conforme o esperado (PASSOU: 6 de 6 testes) |
| **CT-126** Arrastar até a promoção e misturar com clique (RF23, RF05, UC02, UC05) | Peão na sétima, cancelamento, tempo esgotando com o diálogo aberto e sequências de clique e arrasto. | Arrastar, escolher ou cancelar, e clicar em seguida. | O diálogo abre, e cancelar não joga. Clicar de novo na selecionada só desmarca ao soltar. Enter com a peça no ar age sobre o cursor e termina o arrasto. | Conforme o esperado (PASSOU: 7 de 7 testes) |
| **CT-127** Virar durante o giro e a animação (RF23, UC02, UC06) | Tecla F durante o giro por turno, o voo, a volta à vista padrão e a animação de fim. | Virar e conferir o yaw final, o clique e as setas. | A câmera termina no lado oposto ao destino do giro, com o clique certo. As setas seguem o lado, e a tela de fim abre normalmente. | Conforme o esperado (PASSOU: 5 de 5 testes) |
| **CT-128** Copiar PGN: casos difíceis (RF22, UC15) | Sem lances, nomes com aspas, barras e colchetes, revanche, área de transferência falhando, durante o voo e na vez da CPU. | Copiar e refazer o texto lance a lance. | O texto é sempre um PGN válido, com os nomes certos depois da revanche. Falha vira aviso. Copiar não toca na busca da CPU. | Conforme o esperado (PASSOU: 15 de 15 testes) |
| **CT-129** O 2º clique de um clique duplo não aciona a tela nova (RNF07, UC01, UC09, UC11, UC13) | Clique duplo em cada troca de tela: menu e partida, login e menu, sala, tela de fim e folha do histórico. | Enviar dois cliques no mesmo ponto, sem tempo real entre eles. | Por 0,25 s, o clique no mesmo lugar (até 3 pixels) é descartado. Nada abre sem querer. | Conforme o esperado (PASSOU: 6 de 6 testes) |
| **CT-130** Macaco da versão 1.1 (RNF07, UC02, UC10, UC11, UC13, UC14) | Eventos com semente fixa por login, menu, histórico, sala, CPU nos 4 níveis, rede com um robô real em 127.0.0.1 e tela de fim. O longo tem 16 sementes de 6000 quadros, com a marca `slow`. | Enviar eventos aleatórios e conferir as invariantes a cada quadro. | Nenhuma exceção do jogo, nenhuma invariante quebrada, nenhuma thread sobrando e nenhuma senha em cache. | Conforme o esperado (PASSOU: 17 de 17 testes) |
| **CT-131** Telas: nada fora da janela nem por cima de nada (RNF07, UC01, UC11, UC13, UC14) | Login, menu em cada opção, histórico cheio e sala, em 7 tamanhos de janela, de 640x360 a 1920x1080, com nomes longos. | Montar cada tela e conferir os retângulos dos controles. | Todos os controles dentro da janela e sem se sobrepor a partir de 640x480. Abaixo disso, o jogo não cai. | Conforme o esperado (PASSOU: 72 de 76 testes; em xfail ou pulados: test_formularios_na_menor_janela[login_criar], test_formularios_na_menor_janela[menu_local], test_formularios_na_menor_janela[menu_cpu], test_formularios_na_menor_janela[menu_rede]). Os 4 em xfail são o QA11-17, aceito: em 640x360 os formulários não cabem, e o jogo não cai. |
| **CT-132** HUD, sobreposições e tela de fim em cada janela (RF11, RNF07, UC02, UC09) | HUD com 3 e 4 fileiras de botões, em rede com 6 botões, sobreposições e tela de fim, nos mesmos tamanhos. | Montar cada tela e conferir os retângulos. | Tudo cabe na janela, sem sobreposição. | Conforme o esperado (PASSOU: 29 de 29 testes) |
| **CT-133** Nome longo não corta o que explica a ação (RF11, RF14, UC02, UC09) | Nomes de 16 caracteres largos na faixa, no botão de aceitar revanche e na tela de fim. | Medir o texto na área de cada um. | O texto cabe, e a ação continua à vista. O painel lateral não passa da metade da janela. | Conforme o esperado (PASSOU: 15 de 15 testes) |
| **CT-134** O motivo gravado respeita quem lê (RF21, UC14) | Abandono em rede, gravado nos dois lados. | Ler o registro de quem saiu e de quem ficou. | Quem saiu lê "Abandonou a partida", e quem ficou lê "Adversário desconectou". | Conforme o esperado (PASSOU: 2 de 2 testes) |
| **CT-135** Os documentos falam da versão que roda (RF17, RF18, RF19, RF20, RF21, RF22, RF23, RF24, UC01, UC02, UC10, UC11, UC12, UC13, UC14, UC15) | O jogo, o design, os capítulos 1, 7 e 8 e o README. | Conferir que cada RF novo existe no código e aparece nos documentos, e que o README cita CPU, rede, conta e histórico. | Cada RF existe no jogo e é citado nos três capítulos e no contrato. | Conforme o esperado (PASSOU: 6 de 6 testes) |
<!-- FIM:casos -->

## 7.5 Cobertura

Medida com `pytest-cov`, com ramos, na mesma execução dos casos acima. A meta do RNF06 é de pelo menos 90% em `xadrez/core`.

<!-- GERADO:cobertura -->
| Camada | Linhas cobertas | Ramos cobertos | Cobertura |
|---|---|---|---|
| `xadrez/core` | 1824 de 1824 | 554 de 554 | 100,00% |
| `xadrez/data` | 295 de 295 | 58 de 58 | 100,00% |
| `xadrez/net` | 739 de 747 | 146 de 150 | 98,66% |
| `xadrez/graphics` | 1627 de 1631 | 240 de 246 | 99,47% |
| `xadrez/ui` | 4594 de 4609 | 937 de 960 | 99,32% |
| **Total** | 9083 de 9110 | 1936 de 1970 | **99,45%** |
<!-- FIM:cobertura -->

## 7.6 Validação dos requisitos não funcionais

<!-- GERADO:rnf -->
| Requisito | Critério de aceite | Evidência real | Situação |
|---|---|---|---|
| **RNF01** Desempenho: 60 FPS travados em 1280x720 | Média de 60 FPS em 1280x720, em janela real, com intervalo entre quadros perto de 16,67 ms. | `tools/demo_automatica.py`, janela real em 1280x720, com `display.flip`: 60,0 FPS médios em 1287 quadros, intervalo médio de 16,66 ms, p95 de 17,22 ms, p99 de 20,51 ms, máximo de 40,55 ms. 2 quadros passaram de 25 ms (0,16%). Por cenário: `tools/demo_automatica.py`, commit `eaf8f25`, janela real em 1280x720: 60,0 FPS em 2 jogadores, 59,7 FPS em partida contra a CPU Hardcore, 59,5 FPS em CPU pensando, câmera parada, 59,7 FPS em CPU pensando, com animação. O cenário de 2 jogadores roda sem argumento, e os da CPU rodam com `--cpu hardcore`. Testes `test_media_fica_em_60_fps_mesmo_com_sono_atrasado`: 1 de 1 passaram. | Atendido nesta máquina |
| **RNF02** Portabilidade: Python 3.10+ em Windows, Linux e macOS | Suíte passa em Python 3.10+ no Windows, no Linux e no macOS. | Executado: Python 3.12.10 em Windows 11. O CI confirmou as 6 combinações no commit d14edf5, o da tag v1.1.0: Python 3.10 e 3.12 em Windows, Linux e macOS, com 3619 testes aprovados em cada uma, sem os testes slow (https://github.com/Kauhan33/chess-the-game/actions/runs/42213421124). O CI roda sem janela real. Testes `test_source_parses_as_python_310`: 14 de 14 passaram. | Atendido nos testes, com janela real só no Windows |
| **RNF03** Responsividade: resposta visual à entrada em até 1 quadro | A casa sob o mouse e a seleção mudam no mesmo quadro do evento. | Testes `test_hover_marca_o_cursor_no_mesmo_quadro`, `test_clique_seleciona_e_preenche_a_matriz_de_cores`: 2 de 2 passaram. | Atendido |
| **RNF04** Estética e acessibilidade: paleta coerente e estados por cor e por forma | Textos com contraste de pelo menos 4,5:1. Caminho, captura e ameaça têm forma além de cor. | Testes `test_contraste_dos_textos_passa_de_4_5_para_1`, `test_caminho_e_captura_tem_forma_alem_de_cor`, `test_pecas_ameacadas_aparecem_na_matriz_com_forma_e_tint`: 16 de 16 passaram. | Atendido |
| **RNF05** Arquitetura em camadas, com motor testável sem interface | `core` não importa pygame, numpy nem `graphics`; `graphics` não importa `core`. | Testes `test_camada_nao_importa_o_que_nao_deve`: 4 de 4 passaram. | Atendido |
| **RNF06** Qualidade: cobertura de pelo menos 90% em `core` | Cobertura de pelo menos 90% em `xadrez/core`, com ramos. | Cobertura medida de 100,00% em `xadrez/core` (1824 linhas e 554 ramos). | Atendido |
| **RNF07** Robustez: entrada inválida e redimensionamento nunca derrubam o jogo | Entrada inválida vira erro tratado. Nenhum tamanho de janela derruba o jogo. | Testes `test_invalid_origin_never_raises_and_changes_nothing`, `test_invalid_target_never_raises_and_changes_nothing`, `test_tamanho_extremo_na_partida_nao_derruba`, `test_redimensionar_mantem_o_clique_correto`: 43 de 43 passaram. | Atendido |
| **RNF08** Segurança: senha nunca gravada em claro; entrada da rede tratada como não confiável | A senha nunca é gravada: o arquivo só tem nome, sal, iterações e hash. Tudo o que chega da rede é conferido, e a mensagem inválida encerra a conexão. | Testes `test_data_senha_nao_aparece_em_nenhum_byte`, `test_senha_nao_fica_em_widget_nem_em_cache`, `test_net_mensagem_invalida_e_recusada_nos_dois_sentidos`, `test_net_ataque_de_dentro_da_partida_encerra_a_sala_com_erro`, `test_jogada_ilegal_encerra_a_sala`: 111 de 111 passaram. | Atendido |
| **RNF09** A CPU pensando não pode derrubar os 60 FPS | Com a CPU pensando, a média fica perto de 60 FPS em 1280x720, em janela real, e a entrada responde no mesmo quadro. | `tools/demo_automatica.py`, commit `eaf8f25`, janela real em 1280x720: 60,0 FPS em 2 jogadores, 59,7 FPS em partida contra a CPU Hardcore, 59,5 FPS em CPU pensando, câmera parada, 59,7 FPS em CPU pensando, com animação. O cenário de 2 jogadores roda sem argumento, e os da CPU rodam com `--cpu hardcore`. Testes `test_cpu_pensando_nao_bloqueia_quadro_nem_entrada`, `test_intervalo_de_troca_vale_durante_a_busca_e_volta_depois`, `test_com_a_camera_em_movimento_a_busca_dorme_a_cada_consulta`: 3 de 3 passaram. | Atendido nesta máquina |
<!-- FIM:rnf -->

<!-- GERADO:maquina -->
O FPS em janela real depende da máquina. Máquina usada: Intel Core i5-13600KF, NVIDIA GeForce RTX 5070, 48 GB de memória, Windows 11 Pro. O pipeline 3D roda na CPU, em numpy e pygame. A GPU não faz as contas de desenho. Na mesma medição, o trabalho médio por quadro foi de 4,99 ms. Sem janela, a troca do menu para a partida levou 20 ms.
<!-- FIM:maquina -->

Custo do quadro sem janela e sem a espera do `display.flip`:

<!-- GERADO:benchmark -->
`tools/benchmark_ui.py`, commit `eaf8f25`, 1280x720. App.step completo com HUD, sem display.flip.

| Cenário | Quadros | Média | p95 | p99 | Máximo | Acima de 16,67 ms |
|---|---|---|---|---|---|---|
| Partida inteira com câmera parada (giro por turno desligado) | 1902 | 2,11 ms | 3,40 ms | 5,01 ms | 6,33 ms | 0 |
| Partida inteira com giro por turno | 3438 | 4,25 ms | 7,26 ms | 10,76 ms | 16,22 ms | 0 |
| Câmera em giro contínuo (pior caso) | 600 | 6,99 ms | 7,40 ms | 10,34 ms | 11,04 ms | 0 |
| Tela de vitória com fogos | 600 | 6,80 ms | 7,23 ms | 10,33 ms | 10,93 ms | 0 |
| CPU Hardcore pensando, câmera parada | 3376 | 2,88 ms | 3,53 ms | 4,19 ms | 5,45 ms | 0 |
<!-- FIM:benchmark -->

## 7.7 O que não foi testado

- **Janela real em Linux e macOS:** nenhuma versão foi aberta assim. O CI roda sem janela. O jogo só foi aberto em janela real, com FPS medido, no Windows.
- **Rede entre duas máquinas e firewall:** não verificado. Ver a seção 7.9.
- **Rede em janela real:** não verificado. Os testes de rede por tela rodam com o SDL sem janela.
- **Máquinas mais fracas:** o FPS foi medido em uma única máquina.
- **Testes com usuários:** não há registro de teste organizado com pessoas de fora do grupo. Clareza e conforto são decisões de projeto, sem medição.
- **Interface em janela real:** os testes de interface rodam com o SDL sem janela. Em janela real, roda a demonstração automática, que joga uma partida e mede os quadros, mas não confere as regras.

## 7.8 Testes por ataque (QA) da versão 1.0

Depois de o jogo ficar pronto, uma auditoria tentou quebrá-lo numa cópia congelada do código, sem poder alterar nada. Ela achou 19 defeitos: 1 bloqueante, 2 altos, 3 médios e 13 baixos. O motor de regras resistiu a tudo, e o ponto fraco era o clique. O relatório completo, com reprodução de cada achado, está em [testes/relatorio-qa.md](testes/relatorio-qa.md).

| ID | Defeito | Severidade |
|---|---|---|
| QA-01 | Caractere de largura zero no nome derrubava o jogo | Bloqueante |
| QA-02 | Clicar na cabeça de uma peça alta fazia uma jogada que ninguém pediu | Alta |
| QA-03 | O cilindro de clique cobria peças visíveis: o peão e2 quase não era clicável | Alta |
| QA-04 | Clique duplo em "Propor empate" aceitava o empate sozinho | Média |
| QA-05 | R durante o voo do mate pulava a tela de vitória | Média |
| QA-06 | Caractere que a fonte não desenha entrava no nome | Média |
| QA-07 a QA-19 | Casos raros, como dois Enter no mesmo quadro, relógio com mais de 1 hora e dt NaN | Baixa |
| CI-01 | No macOS ARM, as sombras praticamente sumiam | Alta |

Todos foram corrigidos, e os testes que provavam cada um continuam na suíte, nos casos CT-50 a CT-67. A lição para o projeto: os testes anteriores procuravam um pixel em que o clique desse certo, por isso não viam QA-02 e QA-03. O teste CT-59 compara, pixel a pixel, a peça pintada com a casa que o clique aciona.

O defeito CI-01 não veio da auditoria: apareceu quando o CI rodou no macOS, porque só ali ele acontece. Sem SSE, o pygame usa o backend `GENERIC` do `smoothscale`, que escreve errado quando o destino é uma subsuperfície. A correção é não passar destino nesses casos, em `xadrez/graphics/renderer.py`. O defeito foi reproduzido no Windows forçando esse backend, e o teste da sombra agora roda nos dois, em qualquer máquina.

## 7.9 Versão 1.1

### O que entrou nos testes

| Faixa | O que cobre | Onde está |
|---|---|---|
| CT-70 a CT-77 | CPU, tabuleiro compacto, PGN e tempos com incremento | `tests/core/` |
| CT-80 a CT-83 | Contas, senha, histórico e arquivo corrompido | `tests/data/` |
| CT-85 a CT-88 | Código de sala, sessões por socket, quedas e mensagens maliciosas | `tests/net/` |
| CT-90 a CT-98 | Modos, CPU por eventos, login, histórico, duas instâncias em rede, arrasto, virada e cópia do PGN | `tests/ui/` |
| CT-100 a CT-135 | Ataques do QA: modo Partida pixel a pixel, CPU, rede, contas, arrasto, macaco, telas e documentos | `tests/ataque/test_ataque_v11_partida.py` e os demais `test_ataque_v11_` da mesma pasta |

A especificação e o resultado de cada caso estão na seção 7.4. Os totais estão na seção 7.2.

Toda pasta de dados de teste é temporária, por `CHESS_THE_GAME_DATA`, e toda rede de teste é `127.0.0.1`. A exceção é a verificação avulsa descrita abaixo, que não faz parte da suíte.

### Rede: o que foi verificado e o que não foi

| Verificação | Como | Resultado | Fora da suíte? |
|---|---|---|---|
| Duas sessões por socket em `127.0.0.1` | CT-86, CT-87 e CT-88 | Ver a seção 7.4 | Não |
| Duas instâncias do jogo no mesmo processo, em `127.0.0.1` | CT-95 e CT-110 a CT-117 | Ver a seção 7.4 | Não |
| Dois processos em `127.0.0.1` | Execução avulsa | Mesmo FEN, mesmo histórico, mesmo resultado e mesmo placar | Sim |
| Sala pelo IP real, em um só computador | Em 2026-11-06, commit `eaf8f25`: `HostSession` em `0.0.0.0`, porta 50507, e `ClientSession` entrando pelo código gerado com o IP da rede local. Script avulso, por sessões e sem janela | Início da partida, um lance de cada lado, `result` e saída funcionaram, sem erro de rede | Sim |

**Não verificado, com todas as letras:**

- conexão entre dois computadores diferentes;
- passagem pelo firewall;
- rede em janela real.

A sala pelo IP real prova que `0.0.0.0` e o código funcionam nesta máquina. Ela não prova que outra máquina chega até aqui, e por isso o roteiro da apresentação tem um plano B para a rede.

### CI da versão 1.1

O primeiro envio falhou nas 6 combinações ([execução](https://github.com/Kauhan33/chess-the-game/actions/runs/42197820704)). Foram dois casos de teste presos a uma suposição, e nenhum defeito do jogo:

- **Arquivo somente leitura (CT-120 e CT-121), no macOS e no Linux.** Os testes supunham o Windows, onde um arquivo somente leitura barra a troca do temporário pelo arquivo. Nos outros sistemas, a troca só depende da permissão da pasta, e a gravação dá certo. Agora o teste bloqueia o que cada sistema confere.
- **Profundidade do Hardcore, no Windows e no Linux.** O teste dava 1 s ao nível e esperava passar da profundidade 3 do Hard. Em máquina lenta e com cobertura, 1 s não bastava. Agora ele usa o mesmo limite de nós nos dois níveis, e o resultado é igual em qualquer máquina.

Corrigidos os dois, as 6 combinações passaram no commit `3cd07ad`, com 3619 testes aprovados em cada uma, sem os `slow` ([execução](https://github.com/Kauhan33/chess-the-game/actions/runs/42202345318)). A execução completa da seção 7.2 é do commit `0021280`. Entre os dois, só esses testes mudaram, e o código do jogo é o mesmo.

A rodada seguinte, só com documentação, falhou em 1 combinação, o macOS com Python 3.12 ([execução](https://github.com/Kauhan33/chess-the-game/actions/runs/42208107479)), em um teste do sinal de vida (CT-87). O teste somava 8 s ao relógio real e conferia o prazo exato. Perto de uma potência de 2, a soma em `float` arredonda, e `(t + 8.0) - t` fica abaixo de 8,0: isso só acontece nos 8 s antes de cada potência de 2, e por isso as outras rodadas passaram. Na partida real, o aviso sai na verificação seguinte, sem efeito perceptível. O teste agora usa um instante fixo.

Com essa correção, as 6 combinações passaram no commit `d14edf5`, o da tag `v1.1.0`, com 3619 testes aprovados em cada uma, sem os `slow` ([execução](https://github.com/Kauhan33/chess-the-game/actions/runs/42213421124)).

### Força da CPU

<!-- GERADO:forca_cpu -->
`tools/avaliar_cpu.py`. Partidas de verdade entre os níveis.

| Par de níveis | Placar | Observação |
|---|---|---|
| Hardcore contra Hard | 24 a 0 | Hardcore com 4 s por lance |
| Hard contra Medium | 18 a 2 |  |
| Medium contra Easy | 20 a 0 |  |

O Easy foi feito para errar: ele deixa a dama pendurada em 184 de 200 sementes.
<!-- FIM:forca_cpu -->

Essa medição é manual, e serve para calibrar os níveis. O que entra na suíte é CT-74, que exige do nível mais forte pelo menos 75% dos pontos, em 12 partidas por par, com o Hardcore limitado a 0,25 s por lance.

### RNF08: segurança

A evidência é a da seção 7.6, com os testes nomeados. O que cada parte prova:

| O que o requisito pede | Como é provado | Casos |
|---|---|---|
| Senha nunca gravada em claro | A senha é procurada em todos os bytes do arquivo, em várias codificações. O arquivo só tem nome, sal, iterações e hash | CT-81, CT-119 |
| Senha não fica em memória de tela | Campo, cache de texto do tema e máscara são conferidos depois de cada uso | CT-93, CT-119 |
| Entrada da rede não é confiável | Socket cru em `127.0.0.1` manda bytes aleatórios, linha sem fim, tipos errados, lance ilegal, `result` falso e enxurrada | CT-88, CT-110, CT-111 |
| Sem execução de código | Só JSON, sem `pickle` nem `eval`, conferido pela árvore sintática de todo o código | CT-65 |
| Arquivo em disco não é confiável | Campos adulterados, tipos errados e números gigantes não derrubam a aba | CT-83, CT-120, CT-121 |

### RNF09: a CPU pensando não derruba os 60 FPS

<!-- GERADO:fps_v11 -->
`tools/demo_automatica.py`, commit `eaf8f25`, janela real em 1280x720, com `display.flip`. O cenário de 2 jogadores roda sem argumento, e os da CPU rodam com `--cpu hardcore`.

| Cenário | Média |
|---|---|
| 2 jogadores | 60,0 FPS |
| Partida contra a CPU Hardcore | 59,7 FPS |
| CPU pensando, câmera parada | 59,5 FPS |
| CPU pensando, com animação | 59,7 FPS |
<!-- FIM:fps_v11 -->

Sem as medidas da seção 6.17, a tela cai para 9,5 FPS na cena de `tools/benchmark.py`, porque a busca segura o interpretador por 5 ms de cada vez. Os testes de CT-92 conferem que o intervalo de troca vale durante a busca e sempre volta, e que a entrada responde no mesmo quadro, mas FPS em si só se mede em janela real, nesta máquina.

O custo do quadro sem janela, da seção 7.6, é da versão 1.0. Com a versão 1.1, esse número foi medido, mas não em um commit registrado: a tabela em `docs/plans/notas-ui.md` fica como registro.

### QA da versão 1.1

Uma auditoria atacou a versão 1.1 em uma cópia congelada do commit `0671f69`, sem poder alterar o jogo. Ela achou 20 defeitos: nenhum bloqueante, nenhum alto, 6 médios e 14 baixos. O pedido central resistiu: o modo Partida não entrega o xeque por nenhum pixel. O relatório completo, com reprodução e situação de cada achado, está em [testes/relatorio-qa-v11.md](testes/relatorio-qa-v11.md).

| Situação | Achados | Onde |
|---|---|---|
| Corrigidos | 18: QA11-01 a QA11-16, QA11-19 e QA11-20 | Commit `eaf8f25`, com os testes de ataque valendo |
| Aceito | QA11-17: em 640x360, os formulários não cabem, e o jogo não cai. A partir de 640x480 está tudo certo | 4 testes em `xfail`, em CT-131 |
| Resolvido na documentação | QA11-18: os documentos paravam no RF16 | Este capítulo, os capítulos 1 e 8 e o README, conferidos por CT-135 |

O achado que mudou o desenho foi o QA11-09: com cada lado decidindo pelo próprio relógio, os dois podiam se dar a vitória. A correção virou o protocolo v2, em que quem cria a sala decide tudo (seção 5.5).

Macaco longo da versão 1.1, no estado final: 16 sementes aprovadas, em 12 min 41 s, passando por login, menu, histórico, sala, CPU nos 4 níveis, rede com um robô real em `127.0.0.1` e tela de fim.

