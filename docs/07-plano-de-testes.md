# 7. Plano de testes

As seções marcadas como geradas saem de `tools/relatorio_testes.py`. O "Resultado Obtido" nunca é digitado: vem do relatório que o pytest grava durante a execução.

## 7.1 Estratégia

| Nível | O que cobre | Onde está | Como roda |
|---|---|---|---|
| Motor | Regras, turnos, pontuação, relógio, notação | `tests/core/` | Python puro, sem janela |
| Referência externa | Contagem perft contra valores publicados | `tests/core/test_core_perft.py` | Os mais demorados levam a marca `slow` |
| Gráficos | Matrizes, câmera, malhas, partículas, animação e pixels desenhados | `tests/graphics/` | SDL sem janela, lendo a superfície |
| Interface | Partidas e telas por eventos reais de mouse e teclado | `tests/ui/` | SDL sem janela, com `Autoplayer` |
| Arquitetura | Regra de dependência entre camadas | `tests/test_arquitetura.py` | Lê os imports com `ast` |
| Ataque (QA) | Macaco, roteiros maliciosos, invariantes independentes, vazamento e privacidade | `tests/ataque/` | SDL sem janela, com semente fixa. Os longos levam a marca `slow` |
| Desempenho | FPS real e custo do quadro | `tools/demo_automatica.py`, `tools/benchmark_ui.py` | Medição manual, fora do pytest |

O perft é a prova mais forte das regras. Ele conta as posições alcançáveis em N meios-lances e compara com totais publicados. Um único erro em roque, en passant, promoção ou cravada muda a contagem.

Cada teste ligado a um caso formal leva `@pytest.mark.ct("CT-xx")`. Um caso pode ter vários testes, e ele só passa se todos passarem.

## 7.2 Ambiente e execução

<!-- GERADO:execucao -->
- **Data e hora da execução:** 2026-11-04 06:22:06
- **Commit testado:** `c5c150b`. As medições de FPS são do commit `c5c150b`.
- **Ambiente:** Python 3.12.10, Windows 11, pytest 9.2.0, pygame 2.6.1, numpy 2.5.3
- **Modo:** completo, com os testes `slow`
- **Total:** 916 testes: 916 passaram, 0 falharam, 0 foram pulados. Destes, 488 estão vinculados a 38 casos de teste.
<!-- FIM:execucao -->

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
| **CT-31** Câmera: ida e volta mundo, tela e casa em vários ângulos (RF16, UC02, UC06) | As 64 casas, 6 valores de yaw, 3 de pitch e vários viewports. | Projetar o centro da casa para pixel e voltar com `pick_square`. Testar também cliques fora do tabuleiro e na cabeça de uma peça. | A volta dá a mesma casa em toda combinação. Clique fora devolve `None`. Clique na cabeça escolhe a peça. Com duas peças sob o raio, vence a da frente. | Conforme o esperado (PASSOU: 81 de 81 testes) |
| **CT-32** Matriz de cores: estado vira cor, com prioridade (RF09, UC06) | Matriz 8x8 vazia e cada `CellState` em uma casa, em instantes diferentes. | Chamar `set` e `rgb(time)` e comparar as cores. | a1 é escura. Cada estado muda só a sua casa. Prioridade menor não sobrescreve e `NONE` limpa. Casa inválida é ignorada. Só ameaça e xeque pulsam, como função pura do tempo. | Conforme o esperado (PASSOU: 20 de 20 testes) |
| **CT-33** Partículas: gravidade, reflexão no piso e tempo de vida (RF15, UC02) | Partícula única com posição, velocidade e restituição conhecidas, e emissão acima da capacidade. | Chamar `update(dt)` e comparar velocidade, posição, cor e contagem de vivas. | A gravidade acelera para baixo e o arrasto reduz a velocidade. No piso, v' = v - (1 + e)(v.n)n, e nada atravessa. A partícula morre ao fim da vida. A capacidade nunca é ultrapassada. Mesma semente, mesma simulação. | Conforme o esperado (PASSOU: 12 de 12 testes) |
| **CT-34** Malhas: normais para fora e faces válidas (RF15, UC02) | As 6 peças de `build_piece_meshes` e os construtores `lathe`, `box`, `extrude` e `merge`. | Verificar índices, volume, normais, arestas e altura. | Faces válidas e volume positivo. Malhas fechadas, sem aresta solta. Normais para fora. No máximo 160 faces por peça. Peças apoiadas na mesa e dentro da casa. | Conforme o esperado (PASSOU: 40 de 40 testes) |
| **CT-35** Animação: interpolação e easing (RF15, UC02) | As 4 curvas de easing, `Tween` e as animações de voo, captura, promoção e queda do rei. | Avançar com `update(dt)` e ler `value` e `model_matrix`. | Toda curva vai de 0 a 1. A peça viaja em arco e pousa exatamente no alvo. A capturada encolhe girando. A promovida passa um pouco do tamanho. O rei tomba sem tirar a borda da base do lugar. | Conforme o esperado (PASSOU: 20 de 20 testes) |
| **CT-36** Render: corte de faces traseiras e ordem de pintura (RF15, UC02) | Cenas de teste em superfície sem janela, com a câmera parada e em movimento. | Desenhar com `Renderer3D` e ler os pixels da superfície. | Faces de costas e atrás do plano near saem. O objeto da frente cobre o de trás em qualquer ordem de envio. Sombras sobrepostas não escurecem em dobro. Partícula só soma luz. Peça em escala zero não quebra. | Conforme o esperado (PASSOU: 44 de 44 testes) |

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
<!-- FIM:casos -->

## 7.5 Cobertura

Medida com `pytest-cov`, com ramos, na mesma execução dos casos acima. A meta do RNF06 é de pelo menos 90% em `xadrez/core`.

<!-- GERADO:cobertura -->
| Camada | Linhas cobertas | Ramos cobertos | Cobertura |
|---|---|---|---|
| `xadrez/core` | 844 de 844 | 212 de 212 | 100,00% |
| `xadrez/graphics` | 1626 de 1631 | 241 de 248 | 99,36% |
| `xadrez/ui` | 2541 de 2556 | 470 de 490 | 98,85% |
| **Total** | 5014 de 5034 | 923 de 950 | **99,21%** |
<!-- FIM:cobertura -->

## 7.6 Validação dos requisitos não funcionais

<!-- GERADO:rnf -->
| Requisito | Critério de aceite | Evidência real | Situação |
|---|---|---|---|
| **RNF01** Desempenho: 60 FPS travados em 1280x720 | Média de 60 FPS em 1280x720, em janela real, com intervalo entre quadros perto de 16,67 ms. | `tools/demo_automatica.py`, janela real em 1280x720, com `display.flip`: 60,0 FPS médios em 1289 quadros, intervalo médio de 16,66 ms, p95 de 17,22 ms, p99 de 20,01 ms, máximo de 40,29 ms. 2 quadros passaram de 25 ms (0,16%). Testes `test_media_fica_em_60_fps_mesmo_com_sono_atrasado`: 1 de 1 passaram. | Atendido nesta máquina |
| **RNF02** Portabilidade: Python 3.10+ em Windows, Linux e macOS | Suíte passa em Python 3.10+ no Windows, no Linux e no macOS. | Executado: Python 3.12.10 em Windows 11. Python 3.10, Linux e macOS não foram executados localmente. O CI em .github/workflows/testes.yml cobre essas combinações, mas só roda quando o repositório for publicado. Testes `test_source_parses_as_python_310`: 10 de 10 passaram. | Parcial: pendente do CI |
| **RNF03** Responsividade: resposta visual à entrada em até 1 quadro | A casa sob o mouse e a seleção mudam no mesmo quadro do evento. | Testes `test_hover_marca_o_cursor_no_mesmo_quadro`, `test_clique_seleciona_e_preenche_a_matriz_de_cores`: 2 de 2 passaram. | Atendido |
| **RNF04** Estética e acessibilidade: paleta coerente e estados por cor e por forma | Textos com contraste de pelo menos 4,5:1. Caminho, captura e ameaça têm forma além de cor. | Testes `test_contraste_dos_textos_passa_de_4_5_para_1`, `test_caminho_e_captura_tem_forma_alem_de_cor`, `test_pecas_ameacadas_aparecem_na_matriz_com_forma_e_tint`: 16 de 16 passaram. | Atendido |
| **RNF05** Arquitetura em camadas, com motor testável sem interface | `core` não importa pygame, numpy nem `graphics`; `graphics` não importa `core`. | Testes `test_camada_nao_importa_o_que_nao_deve`: 2 de 2 passaram. | Atendido |
| **RNF06** Qualidade: cobertura de pelo menos 90% em `core` | Cobertura de pelo menos 90% em `xadrez/core`, com ramos. | Cobertura medida de 100,00% em `xadrez/core` (844 linhas e 212 ramos). | Atendido |
| **RNF07** Robustez: entrada inválida e redimensionamento nunca derrubam o jogo | Entrada inválida vira erro tratado. Nenhum tamanho de janela derruba o jogo. | Testes `test_invalid_origin_never_raises_and_changes_nothing`, `test_invalid_target_never_raises_and_changes_nothing`, `test_tamanho_extremo_na_partida_nao_derruba`, `test_redimensionar_mantem_o_clique_correto`: 43 de 43 passaram. | Atendido |
<!-- FIM:rnf -->

<!-- GERADO:maquina -->
<!-- FIM:maquina -->

Custo do quadro sem janela e sem a espera do `display.flip`:

<!-- GERADO:benchmark -->
`tools/benchmark_ui.py`, commit `c5c150b`, 1280x720. App.step completo com HUD, sem display.flip.

| Cenário | Quadros | Média | p95 | p99 | Máximo | Acima de 16,67 ms |
|---|---|---|---|---|---|---|
| Partida inteira com câmera parada | 1902 | 1,99 ms | 3,28 ms | 4,70 ms | 5,44 ms | 0 |
| Partida inteira com giro por turno | 3438 | 4,22 ms | 7,17 ms | 10,67 ms | 15,12 ms | 0 |
| Câmera em giro contínuo (pior caso) | 600 | 7,04 ms | 7,94 ms | 10,72 ms | 12,08 ms | 0 |
| Tela de vitória com fogos | 600 | 6,84 ms | 7,46 ms | 10,08 ms | 11,21 ms | 0 |
<!-- FIM:benchmark -->

## 7.7 O que não foi testado

- **Python 3.10, Linux e macOS:** não foram executados localmente. O CI em `.github/workflows/testes.yml` cobre essas combinações, mas só roda quando o repositório for publicado.
- **Máquinas mais fracas:** o FPS foi medido em uma única máquina.
- **Testes com usuários:** não há registro de teste organizado com pessoas de fora do grupo. Clareza e conforto são decisões de projeto, sem medição.
- **Interface em janela real:** os testes de interface rodam com o SDL sem janela. Em janela real, roda a demonstração automática, que joga uma partida e mede os quadros, mas não confere as regras.

## 7.8 Testes por ataque (QA)

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

Todos foram corrigidos, e os testes que provavam cada um continuam na suíte, nos casos CT-50 a CT-67. A lição para o projeto: os testes anteriores procuravam um pixel em que o clique desse certo, por isso não viam QA-02 e QA-03. O teste CT-59 compara, pixel a pixel, a peça pintada com a casa que o clique aciona.

