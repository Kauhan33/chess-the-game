# 10. Roteiro da apresentação

O enunciado dá de 12 a 15 minutos por grupo: 10 minutos de apresentação e demonstração, mais 5 de arguição. Todos os integrantes precisam falar, e o jogo precisa rodar na hora, com uma partida curta entre os dois jogadores e as telas de vitória ou derrota.

## 10.1 Divisão da fala

O grupo tem 3 integrantes. Os tempos somam 9 min 15 s, com a partida ao vivo incluída. A folga de 45 s é para não estourar os 10 minutos.

| Quem | Slide | O que dizer | Tempo |
|---|---|---|---|
| Integrante 1 | Capa | Grupo, trabalho e nome do jogo | 15 s |
| Integrante 1 | Escopo | 2 jogadores, CPU e rede local, com regras oficiais completas | 20 s |
| Integrante 1 | Modos | Treinamento mostra tudo. Partida mostra só o que aconteceu, como em um torneio | 20 s |
| Integrante 1 | Regras | Roque, en passant, promoção e empates. Perft prova que estão certas | 25 s |
| Integrante 1 | Arquitetura | Cinco camadas: `core`, `data`, `net`, `graphics` e `ui`. Um teste barra a dependência errada | 30 s |
| Integrante 1 | Casos de uso | UC01 a UC15, e como UC10, UC11 e UC12 reaproveitam a mesma jogada | 20 s |
| Integrante 1 | Classes | As seis classes do enunciado, e `GameScene` ligando tudo | 20 s |
| Integrante 2 | Pipeline | Modelo, mundo, visão, recorte, NDC e tela. Divisão por w | 40 s |
| Integrante 2 | Malhas | Revolução, faces low-poly, normais e Lambert | 20 s |
| Integrante 2 | Clique | O raio pela inversa de P·V, a silhueta, e o arrasto no mesmo raio | 30 s |
| Integrante 2 | Matriz de cores | Estado por casa, cor e forma. No modo Partida, a mesma matriz com menos coisa | 25 s |
| Integrante 2 | Partículas | Gravidade, reflexão no piso e restituição | 20 s |
| Integrante 2 | Framerate | `FramePacer`: prazos em segundos, e o que muda com a CPU pensando | 15 s |
| Integrante 3 | CPU | Negamax com alfa-beta e quiescência, em uma thread, sobre uma cópia. Hardcore 24 a 0 Hard | 30 s |
| Integrante 3 | Rede | Sala com código, quem cria é a autoridade, entrada não confiável e senha com PBKDF2 | 25 s |
| Integrante 3 | Testes | Resultado real gerado pela suíte, QA por ataque, e o que ainda não foi verificado | 20 s |
| Integrante 3 | Demonstração | Integrante 3 narra, e os Integrantes 1 e 2 jogam | 2 min 50 s |
| Integrante 3 | Fim | Agradecimento e abertura para perguntas | 10 s |

| Quem | Total |
|---|---|
| Integrante 1 | 2 min 30 s |
| Integrante 2 | 2 min 30 s |
| Integrante 3 | 4 min 15 s |
| **Total** | **9 min 15 s** |

O código que aparece no slide de rede é o do print, `GEJXWVH`. O print foi feito em `127.0.0.1`, e é esse o endereço que o código guarda. Na máquina da apresentação, o código será outro, porque depende do IP dela.

## 10.2 Antes de a banca começar

1. Abra o jogo pelo `ChessTheGame.exe` e confirme que ele chega à tela de entrada. Se a máquina tiver Python, teste também `python main.py`.
2. Conecte o projetor e aperte F11 para a tela cheia.
3. Na tela de entrada, use "Jogar como convidado": nenhum dado de conta aparece na projeção.
4. Deixe o menu aberto em "2 jogadores" e "Treinamento", com os nomes já digitados e o tempo em "Blitz 5".
5. Deixe `tools/demo_automatica.py` à mão, se a máquina tiver Python: é o plano B, porque joga sozinho.
6. Deixe o PDF unificado aberto em outra janela, para mostrar um diagrama se perguntarem.

**Para a rede, ainda antes de a banca chegar:**

7. Ligue os dois computadores na mesma rede e crie uma sala em um deles. Se o firewall perguntar, é a porta 50507 de quem criou a sala que precisa ser liberada.
8. Entre com o código pelo outro computador, jogue um lance de cada lado e saia. Isso nunca foi feito em dois computadores antes do ensaio do grupo, e é o único jeito de saber se a rede do local deixa.
9. Deixe o segundo computador em "Rede local", com "Entrar com código" à vista.
10. Se a conexão não sair nesse teste, decida ali mesmo: a demonstração usa o plano B da seção 10.4.

## 10.3 Demonstração, em 2 min 50 s

Os Integrantes 1 e 2 jogam, e o Integrante 3 narra. A planilha do jogo usa a notação internacional: Q é dama, N é cavalo, B é bispo.

### Partida entre 2 jogadores, em Treinamento: cerca de 1 min 20 s

| Lance | Quem clica | O que narrar |
|---|---|---|
| Menu | Qualquer um | Adversário "2 jogadores", modo "Treinamento" e "Blitz 5". Iniciar partida. |
| 1. e4 | Brancas | Selecionar o peão mostra os caminhos em verde, com ponto. A peça voa em arco. |
| 1... e5 | Pretas | A câmera girou para o lado de quem joga. Só a matriz V mudou. |
| 2. Bc4 | Brancas | Antes de jogar, clique em uma peça preta: aparece "Essa peça é do adversário." e ela treme. |
| 2... Nc6 | Pretas | Lance normal, sem parar a narração. |
| 3. Qh5 | Brancas | O peão preto em f7 fica destacado como ameaça, em laranja e pulsando. |
| 3... Nf6 | Pretas | Aperte F4: a matriz de visão e a matriz de estados aparecem em números. Feche o F4. |
| 4. Qxf7# | Brancas | Faíscas quicando no piso, rei tombando e fogos. |
| Fim | Qualquer um | Tela de vitória com placar. "Revanche com cores trocadas" mantém o placar da série. |

### Modo Partida: cerca de 30 s

Volte ao menu pela pausa, escolha "Partida" e inicie.

| Ação | O que narrar |
|---|---|
| Selecionar o peão e2 | Mesma seleção de antes: só os cantos na casa dele. Nenhum caminho, nenhuma captura. |
| Clicar em e5 | A casa não é um destino válido. A recusa é "Lance inválido.", sem tremor e sem dizer o motivo. |
| Jogar `1. e4` | O último lance fica marcado. É tudo o que esta tela conta. |

### CPU Hardcore: cerca de 30 s

Volte ao menu, escolha "Contra a CPU" e "Hardcore" e inicie.

| Ação | O que narrar |
|---|---|
| F3, antes do primeiro lance | O painel mostra os quadros por segundo. |
| Jogar `1. e4` | A placa acende com "Pensando". A busca roda em outra thread, sobre uma cópia do tabuleiro, por cerca de 4 s. |
| Orbitar com o botão direito enquanto ela pensa | A tela continua respondendo, e o painel fica perto de 60. O número medido em janela real foi de 59,5 a 59,7 FPS. |

### Sala em rede: cerca de 30 s, se houver rede no local

| Ação | Quem | O que narrar |
|---|---|---|
| "Rede local", "Criar sala" | Integrante 1, no projetor | O código tem 7 caracteres: é o IP da máquina, em base 31, sem os que se confundem. O modo e o tempo escolhidos aqui valem para os dois. |
| Digitar o código e "Entrar na sala" | Integrante 2, no outro computador | Entrada conferida. A partida abre nos dois lados. |
| `1. e4` e `1... e5` | Os dois | Quem criou a sala valida os lances e decide o fim. O outro joga sem esperar. |
| Desistir de um dos lados | Integrante 2 | Quem entrou faz um pedido. A sala decide, e os dois terminam com o mesmo resultado. |

## 10.4 Planos B

**Plano B da rede:** mostre a tela da sala com o código e explique, sem jogar. Use estes pontos, nesta ordem:

1. "Este é o código: o IP da máquina em 7 caracteres, com conferência." Aponte para o código na tela.
2. "A rede do local não deixa os dois computadores se verem, e o jogo não usa servidor."
3. "Testamos a partida inteira em dois processos em `127.0.0.1`, e a sala pelo IP real em um computador só. Entre dois computadores, [diga o que o ensaio do grupo mostrou]."
4. Se ainda houver tempo, mostre a partida em rede e o cartão de empate, nos prints do capítulo 2.

Nunca diga que funcionou entre dois computadores sem ter visto funcionar. Hoje, isso está em "Não verificado" no capítulo 7.

**Plano B geral:** se o jogo não abrir por `python main.py`, abra o `ChessTheGame.exe`. Se a partida não puder ser jogada, rode `python tools/demo_automatica.py`, que joga sozinho até a vitória, ou `python tools/demo_automatica.py --cpu hardcore`, contra a CPU.

**Se o tempo apertar:** corte primeiro a sala em rede, e explique por um único print. Depois, corte a CPU. A partida entre os dois jogadores com a tela de vitória é a parte que o enunciado exige.

## 10.5 Perguntas prováveis

Cada integrante responde pela parte que apresentou. As fórmulas completas estão no capítulo 6, e as respostas mais longas sobre CPU e rede estão na seção 11.7.

| Pergunta | Resposta curta | Onde está |
|---|---|---|
| Por que não usaram OpenGL? | Para escrever e poder explicar cada etapa do pipeline, e para não depender do driver da máquina da banca. O custo é desempenho, resolvido com malhas low-poly e cache. | `xadrez/graphics/renderer.py` |
| O que é a coordenada homogênea? | É a quarta coordenada. Com ela, a translação vira multiplicação de matriz, e todas as transformações podem ser combinadas em uma só. | `xadrez/graphics/matrix.py` |
| Por que dividir por w? | É a divisão perspectiva: o que está longe tem w maior, e por isso fica menor na tela. | `Camera.project` |
| Qual o limite da ordem do pintor? | Ela erra quando objetos se atravessam, porque não há z-buffer. Aqui, as peças não se atravessam, então a ordem por distância basta. | `_object_paint_ranks` em `xadrez/graphics/renderer.py` |
| Como o clique acha a peça? | O pixel vira um raio pela inversa de P·V. Um cilindro descarta as peças longe do raio, e o pixel é testado contra as faces projetadas, da peça mais próxima para a mais distante. | `Camera.pick_piece` |
| Como vocês validam o xeque? | Aplica a jogada, confere se o próprio rei ficou atacado e desfaz. Se ficou, a jogada é recusada. | `leaves_king_in_check` em `xadrez/core/rules.py` |
| Por que T(p) · R · T(-p) no rei tombando? | A rotação é sempre em torno da origem. Para girar em torno da borda da base, leva-se o ponto até a origem, gira e devolve. | `KingFallAnimation` em `xadrez/graphics/animation.py` |
| Como garantem 60 FPS? | O `FramePacer` encadeia prazos em segundos, porque `Clock.tick(60)` trabalha em milissegundos inteiros. Com a câmera parada, peças e tabuleiro viram camadas em cache. | `xadrez/ui/frame_pacer.py` |
| Como sabem que as regras estão certas? | Perft: a contagem de posições confere com os valores publicados, inclusive com mais de 4 milhões de posições na Kiwipete. | `tests/core/test_core_perft.py` |
| Algum bug que os testes não pegaram? | Sim. O clique no peão e2 selecionava o rei, e os testes não viam porque procuravam um pixel em que o clique desse certo. A auditoria mediu pixel a pixel, e hoje isso é o caso CT-59. | `docs/testes/relatorio-qa.md` |
| O que é a poda alfa-beta? | Se um lance já garante algo melhor do que o adversário deixaria acontecer em outra linha, o resto daquela linha pode ser ignorado. A nota final não muda, e o trabalho cai muito. | `_Search._search_moves` em `xadrez/core/ai.py` |
| Para que serve a quiescência? | Sem ela, a busca pararia no meio de uma troca e acharia que ganhou uma peça que será recapturada. Ela continua só pelas capturas até a posição acalmar. | `_Search._quiesce` |
| Por que thread e não processo? | Com o intervalo de troca em 0,2 ms, a tela fica em 58,7 FPS, igual a um processo, e não precisa de `multiprocessing` no executável. Com o intervalo padrão, eram 9,5 FPS. | `xadrez/ui/cpu_player.py` |
| Cada jogador escolhe o modo em rede? | Não. Quem cria a sala escolhe, e a mensagem `start` leva o modo. Assim os dois jogam a mesma partida. | `_begin_game` em `xadrez/net/session.py` |
| Por que quem cria a sala decide tudo? | Dois relógios nunca batem. Quando cada lado decidia pelo próprio, os dois podiam se dar a vitória: o QA provou isso (QA11-09). | `xadrez/ui/net_link.py` |
| E se o outro lado trapacear? | Cada mensagem é conferida no esquema, e cada lance, no motor. Lance ilegal encerra a sala. O limite é a sala alterada, que pode mentir sobre tempo e desistência. | `xadrez/net/protocol.py` |
| Como a senha é guardada? | Não é. Fica o resultado de PBKDF2-HMAC-SHA256, com 600 mil iterações e sal próprio. Leva 0,17 s, de propósito. | `xadrez/data/accounts.py` |
| Funciona entre dois computadores? | Responda com o que o ensaio mostrou. O que está provado na documentação é 2 processos em `127.0.0.1` e a sala pelo IP real em um computador só. | Seção 7.9 |
