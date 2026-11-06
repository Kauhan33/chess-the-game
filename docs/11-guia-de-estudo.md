# 11. Guia de estudo para a banca

A rubrica avalia o domínio do código pelos integrantes. Na arguição, cada um precisa explicar a sua parte sem ler. Este guia diz o que ler, em que ordem, e traz experimentos para ver cada conceito acontecer, além das perguntas prováveis sobre CPU, senha, protocolo e autoridade. O tempo de estudo sugerido é de cerca de 2 horas por pessoa, mais o ensaio.

## 11.1 Mapa do código

| Camada | Linhas | O que tem |
|---|---|---|
| `xadrez/core/` | cerca de 2950 | As regras e a CPU. Python puro. |
| `xadrez/data/` | cerca de 450 | Contas com senha e histórico em JSON. Python puro. |
| `xadrez/net/` | cerca de 1170 | Sala em rede local. Python puro. |
| `xadrez/graphics/` | cerca de 2750 | Matrizes, câmera, malhas, luz, partículas, animação e desenho. |
| `xadrez/ui/` | cerca de 6340 | Telas, HUD, entrada, relógio de quadros, CPU em thread e rede na partida. |

Ninguém precisa decorar tudo. Basta saber o caminho de uma jogada e de um vértice, e onde cada coisa está. `xadrez/graphics/renderer.py` é o maior arquivo: leia o começo e `flush`, sem tentar acompanhar cada cache. Em `xadrez/core/search_board.py`, basta ler o topo: a banca não vai pedir a geração de lances com inteiros.

## 11.2 Trilha do Integrante 1: regras, modos, arquitetura e UML

Leia nesta ordem:

1. `xadrez/core/types.py` e `xadrez/core/move.py`: casas, cores, peças e jogadas.
2. `xadrez/core/pieces.py`: `SlidingPiece.attacks`, o laço da colisão de caminho. Depois `Pawn`, a peça mais trabalhosa.
3. `xadrez/core/board.py`: `apply` e `undo`.
4. `xadrez/core/rules.py`: `legal_moves` e `leaves_king_in_check`, o coração da validação de xeque.
5. `xadrez/core/engine.py`: `play`, do começo ao fim, e `_detect_board_result`.
6. `tests/core/test_core_perft.py`.
7. `xadrez/ui/match.py`: `GameMode`. Depois, em `xadrez/ui/game_scene.py`: `hides_hints`, `_compute_alerts`, `_paint_selection` e `_refuse`.
8. `tests/test_arquitetura.py`.
9. Capítulos 3, 4 e 5 da documentação.

Precisa explicar sem ler:

- O que acontece, passo a passo, quando alguém joga um lance, até o motor responder.
- Por que uma peça não atravessa a outra, apontando a linha.
- Como o motor descobre que uma jogada deixaria o próprio rei em xeque.
- O que é perft e por que ele é uma prova forte.
- As cinco camadas, quem pode importar quem, e que teste garante isso.
- O que o modo Partida esconde, e por que a recusa não diz o motivo.
- A diferença entre herança e composição, com exemplos do diagrama.
- Como UC10, UC11 e UC12 se ligam a UC01 e UC02.

## 11.3 Trilha do Integrante 2: computação gráfica

Leia nesta ordem, com o capítulo 6 aberto ao lado:

1. `xadrez/graphics/matrix.py`: `translation`, `rotation_y`, `compose`, `look_at`, `perspective` e `planar_shadow`.
2. `xadrez/graphics/camera.py`: `project`, `screen_ray`, `pick_plane` e `pick_piece`.
3. `xadrez/graphics/mesh.py` e `xadrez/graphics/models.py`: `lathe` e os perfis das peças.
4. `xadrez/graphics/lighting.py`: `shade`, com a fórmula de Lambert.
5. `xadrez/graphics/color_matrix.py`: `ColorMatrix.rgb`.
6. `xadrez/graphics/particles.py`: `update` e `_bounce_on_floor`.
7. `xadrez/graphics/animation.py`: `PieceAnimation` e `KingFallAnimation`.
8. `xadrez/ui/board_view.py`: `drag_to`, `flip` e `pick`.
9. `xadrez/ui/frame_pacer.py`: o arquivo inteiro. É curto.
10. `xadrez/ui/arena_scene.py`: `Tableau`.

Precisa explicar sem ler:

- O caminho de um vértice até o pixel, nomeando cada matriz.
- Para que serve a coordenada homogênea, e por que se divide por w.
- Por que a ordem das matrizes importa, usando o rei que tomba como exemplo.
- Como o clique vira uma casa, e por que só o cilindro não bastava.
- Como o arrasto usa o mesmo raio, em um plano acima do tabuleiro, e por que a peça no ar fica de fora de `pick`.
- Por que virar o tabuleiro não estraga o clique.
- A fórmula de Lambert, e por que as faces têm uma cor só.
- A reflexão da partícula no piso, e o que é a restituição.
- A ordem do pintor, e quando ela erraria.
- Por que `Clock.tick(60)` dava 59,1 FPS, e como o `FramePacer` resolve.

## 11.4 Trilha do Integrante 3: CPU, rede, dados e qualidade

Leia nesta ordem:

1. `xadrez/core/ai.py`: o topo do arquivo, `_LEVELS`, `_negamax`, `_search_moves`, `_quiesce`, `run` e `_pick_root_move`.
2. `xadrez/ui/cpu_player.py`: o arquivo inteiro. É curto, e é onde ficam a thread e o intervalo de troca.
3. `xadrez/data/accounts.py`: `create`, `authenticate` e `_hash_password`. Depois, `write_json_atomic` em `xadrez/data/storage.py`.
4. `xadrez/net/room_code.py`, `xadrez/net/protocol.py` e `xadrez/net/session.py`: `encode_room_code`, `decode_message`, `_handle_hello` e `_handle_peer_line`.
5. `xadrez/ui/net_link.py`: o topo do arquivo, `_on_move`, `_on_decision`, `tick` e `publish_result`. É onde está a autoridade.
6. `xadrez/ui/app.py`: `step` e `run_frame`, o laço do jogo.
7. `xadrez/ui/autoplay.py`: como os testes jogam por eventos reais.
8. Capítulo 7 da documentação, `docs/testes/relatorio-qa.md` e `docs/testes/relatorio-qa-v11.md`.

Precisa explicar sem ler:

- O que acontece em um quadro, do evento ao desenho, com a CPU pensando ao lado.
- As perguntas da seção 11.7.
- Como um teste joga uma partida inteira sem janela, e como dois jogos conversam em `127.0.0.1` dentro de um teste.
- Por que o "Resultado Obtido" não é digitado à mão.
- Dois defeitos que a auditoria achou e como foram corrigidos, e o defeito das sombras que só o CI do macOS revelou.
- O que ainda não foi verificado, sem hesitar.

## 11.5 Experimentos

O melhor jeito de entender é quebrar de propósito. Cada um leva cerca de 5 minutos. Todos foram testados em uma cópia do projeto, e o resultado abaixo é o que aconteceu de verdade.

Para cada um: mude a linha, rode o jogo ou o teste indicado, olhe o que aconteceu e **desfaça** com o comando abaixo. Nunca faça commit de um experimento.

```
git checkout -- <arquivo>
```

| # | Onde | Mude | Rode | O que acontece | Conceito |
|---|---|---|---|---|---|
| E1 | `SlidingPiece.attacks` em `xadrez/core/pieces.py` | Apague o `if` com o `break` | `pytest tests/core/test_core_piece_moves.py` | Muitos testes falham: a torre atravessa tudo. | Colisão de caminho |
| E2 | `_REPETITIONS_FOR_DRAW` em `xadrez/core/engine.py` | De 3 para 2 | `pytest tests/core/test_core_draws.py` | 5 testes falham: empata na segunda repetição. | Regra de empate |
| E3 | `leaves_king_in_check` em `xadrez/core/rules.py` | Primeira linha: `return False` | `pytest tests/core/test_core_check.py` | Muitos testes falham: peça cravada volta a andar. O perft também acusa. | Validação de xeque |
| G1 | `restitution` em `xadrez/graphics/particles.py` | De 0.45 para 0.95 | O jogo, fazendo uma captura | Nenhum teste falha. As faíscas quicam muito mais. | Reflexão de vetor |
| G2 | `LAMP_DIRECTION` em `xadrez/graphics/lighting.py` | `(-0.42, -1.0, 0.30)` | O jogo | As sombras e a luz trocam de lado. O teste da sombra falha. | Lambert e sombra planar |
| G3 | `fov_y` em `Camera.__init__`, em `xadrez/graphics/camera.py` | De 30 para 60 graus | O jogo | A perspectiva muda, e **nenhum teste falha**: o clique continua certo, porque usa a inversa da mesma matriz. | Projeção e clique |
| U1 | `_DOUBLE_CLICK_SECONDS` em `xadrez/ui/game_scene.py` | De 0.25 para 0.0 | `pytest tests/ui/test_ui_janela_e_saida.py` | Um teste falha: o 2º clique do clique duplo atinge o tabuleiro. | Fluxo de exceção |
| U2 | `FPS` em `xadrez/ui/app.py` | De 60 para 30 | O jogo, com F3 | Mostra cerca de 30 FPS, e a peça leva o mesmo tempo para voar, porque tudo usa `dt`. | Controle de framerate |
| A1 | `_Search._search_moves` em `xadrez/core/ai.py` | Apague o `if score >= beta:` inteiro, até o `break` | O trecho de medição abaixo | O Hard bate no limite de 90048 nós sem terminar a profundidade 3 e escolhe outro lance (`e1g1`, em vez de `c3c4`). A resposta muda porque ele não teve como buscar tudo. | Poda alfa-beta |
| A2 | `Difficulty.HARD` em `_LEVELS` | Acrescente `uses_quiescence=False` | `pytest tests/core/test_core_ai.py -m "not slow"` | 2 testes falham, um sobre a variedade do Hard e outro sobre aceitar o empate quando está perdendo. A nota agora para no meio das trocas. | Quiescência |
| A3 | `_pick_root_move` em `xadrez/core/ai.py` | Some o ruído também na nota de mate | `pytest tests/core/test_core_ai.py -m "not slow"` | **Nenhum teste falha.** A nota de mate vale cerca de 100 mil, e o ruído máximo é 300. O que a regra evita é sortear entre mate em 1 e mate em 2. | Ruído e mate |
| T1 | `_SearchJob._should_stop` em `xadrez/ui/cpu_player.py` | Tire o `time.sleep` | `pytest tests/ui/test_ui_cpu.py -k dorme` | Um teste falha: com a câmera em movimento, a busca devia dormir a cada consulta. | Thread e quadro |
| T2 | `SEARCH_SWITCH_INTERVAL` em `xadrez/ui/cpu_player.py` | De 0.0002 para 0.005 | `python tools/demo_automatica.py --cpu hardcore --lances 2` | **`test_intervalo_da_busca_fica_bem_abaixo_do_padrao_de_5_ms` falha.** Rodando sem janela, com a CPU pensando e a câmera parada, a média cai de 59,7 para 38,8 FPS, com um quadro de 825 ms. FPS só se mede rodando. | Intervalo de troca |
| D1 | `_PBKDF2_ITERATIONS` em `xadrez/data/accounts.py` | De 600_000 para 1_000 | `pytest tests/data/test_data_accounts.py` | Um teste falha: o que confere as iterações gravadas. O resto passa, e o login fica barato para quem tenta adivinhar. Sem a mudança, cada verificação leva cerca de 0,18 s. | Custo do hash |
| D2 | `_serialize` em `xadrez/data/accounts.py` | Acrescente um campo `senha` ao que é gravado | `pytest tests/data/test_data_accounts.py` | Um teste falha: o arquivo só pode ter nome, sal, iterações e hash. | Senha nunca gravada |
| R1 | `NetMatch._agrees_with_board` em `xadrez/ui/net_link.py` | Primeira linha: `return True` | `pytest tests/ataque/test_ataque_v11_rede.py -k resultado` | 3 testes falham: o resultado que não confere passa a valer. | Conferir a autoridade |
| R2 | `NetMatch._on_decision` em `xadrez/ui/net_link.py` | Troque as duas linhas do lance que cruzou por `pass` | `pytest tests/ataque/test_ataque_v11_rede.py -k cruzad` | 6 testes falham: o lance que cruzou com o fim continua no tabuleiro de quem entrou. | Lance cruzado |
| R3 | `NetMatch.tick` em `xadrez/ui/net_link.py` | Apague o bloco `if not self.is_authority` | `pytest tests/ataque/test_ataque_v11_rede.py -k "relogio or convidado"` | 3 testes falham: quem entrou decide pelo próprio relógio, e os relógios defasados voltam a dar dois vencedores. | Quem mede o relógio |
| M1 | `GameScene.__init__` em `xadrez/ui/game_scene.py` | `self.hides_hints = False` | `pytest tests/ui/test_ui_modos.py` | 14 testes falham: as dicas voltam, e a recusa volta a explicar o motivo. | Modo Partida |

Trecho de medição de A1. Sem a mudança, o Hard resolve esse meio-jogo em 16474 nós, na profundidade 3, em cerca de 0,10 s:

```
python -c "import random; from xadrez.core import Board, Difficulty, analyze; r = analyze(Board.from_fen('r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P1B2/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 9'), Difficulty.HARD, random.Random(1)); print(r.move.uci, r.score, r.nodes, r.depth, r.seconds)"
```

Para ver a matriz de visão mudar sem alterar nada: abra o jogo, aperte F4 e arraste na horizontal com o botão direito. Só a 1ª e a 3ª colunas das três primeiras linhas mudam. A coluna do meio e a translação ficam iguais, porque a câmera gira em torno do eixo y, sem mudar a distância. Saber explicar isso é um ótimo sinal de que a matriz está entendida.

## 11.6 Ensaio

1. **Troca de papéis:** cada integrante explica, em 2 minutos, a parte de outro. Quem conseguir explicar a parte dos outros responde bem a qualquer pergunta.
2. **Passagem com relógio:** apresente tudo uma vez cronometrando. A meta é ficar abaixo de 10 minutos, com a partida ao vivo incluída. O roteiro soma 9 min 15 s.
3. **Arguição simulada:** um integrante faz as perguntas da seção 10.5 e da seção 11.7, e quem responde não pode olhar o código, só mostrar no jogo.
4. **Ensaio de falha:** feche o jogo no meio da apresentação e reabra pelo `.exe`, para treinar o plano B.
5. **Ensaio de rede, no próprio local:** crie a sala em um computador e entre pelo outro, com os dois na rede que a banca vai usar. É o único jeito de saber se a demonstração de rede vai sair, e o resultado do ensaio é o que o Integrante 3 pode afirmar. Anote o que aconteceu, inclusive se o firewall pediu permissão.

## 11.7 Perguntas da banca: CPU, senha, protocolo e autoridade

Cada resposta foi conferida no código, no arquivo citado. Todos precisam saber as respostas curtas. O Integrante 3 precisa saber mostrar a linha.

### CPU

**O que é negamax?** É o minimax escrito de um jeito só. A nota de um lance para mim é o negativo da nota para o adversário, então o mesmo código serve aos dois lados: `score = -self._negamax(...)`. Está em `_Search._negamax`, em `xadrez/core/ai.py`.

**O que é a poda alfa-beta?** `alpha` é o que eu já tenho garantido nesta linha. `beta` é o que o adversário deixa eu ter. Em `_search_moves`, quando um lance chega a `beta`, o laço para com `break`: o adversário nunca deixaria chegar aqui, então os lances restantes não mudam nada. Exemplo: já achei um lance que me garante +1. No lance seguinte, a primeira resposta do adversário já me deixa em -3. Não preciso ver as outras respostas: esse lance não será escolhido. A resposta é a mesma de sem poda. O que muda é o trabalho (experimento A1).

**Por que a ordem dos lances importa?** A poda só corta quando um lance bom vem cedo. Por isso `_ordered` põe primeiro o lance da tabela de transposição, depois as capturas pela regra MVV-LVA (maior vítima com o menor atacante, em `_capture_priority`) e as promoções, depois os "killers" e a história, que são lances que já causaram corte em posições parecidas.

**O que é a janela mínima?** Em `_score_child`, só o primeiro lance recebe a janela inteira. Os demais recebem `(-alpha - 1, -alpha)`, que só pergunta se o lance supera `alpha`. É bem mais barato, e, se ele surpreender, é buscado de novo por inteiro.

**O que é a quiescência?** Ao chegar na profundidade limite, a busca não para: continua só pelas capturas, em `_quiesce`, até a posição acalmar. Sem isso, ela pararia no meio de uma troca e acharia que ganhou uma peça que será recapturada no lance seguinte. Esse é o "efeito de horizonte". O "stand pat" diz que ninguém é obrigado a capturar, então a nota atual já é um piso. Em xeque, examina todas as saídas. Termina sempre, porque as capturas se esgotam, e o `_MAX_PLY` segura a sequência de xeques estendidos.

**O que é a tabela de transposição?** A mesma posição aparece por caminhos diferentes. A tabela guarda, pela chave de Zobrist da posição, a profundidade, a nota, o tipo da nota (exata, limite inferior ou superior) e o melhor lance. Vive só durante a chamada, e por isso `choose_move` não tem estado. A chave é o XOR de um número aleatório por peça em cada casa, então mover uma peça custa só dois XOR, em `SearchBoard`.

**Por que aprofundamento iterativo, em vez de ir direto à profundidade 8?** Porque o tempo é limitado e sempre há uma resposta pronta. E a volta anterior ordena a seguinte, o que faz a poda cortar mais: buscar 1, 2, 3 até 8 sai mais barato que parece. Se o tempo acabar no meio, `_adopt_partial_iteration` só aceita a volta incompleta se um lance superou o melhor da anterior, porque aquele foi pesquisado primeiro.

**O que muda entre os níveis?** Só a tabela `_LEVELS`: profundidade, ruído, margem, limite de nós e tempo. O Easy busca 1 meio-lance, sem quiescência, com ruído de ±300 centésimos de peão. O Medium, 2, com ruído de ±40 e 30 mil nós. O Hard, 3, com margem 10 e 90 mil nós. O Hardcore aprofunda por cerca de 4 s, com as técnicas seletivas, e chega à profundidade 8 a 9 no meio-jogo.

**Então o Easy erra de propósito?** Sim, e por isso ele deixa a dama pendurada em 184 de 200 sementes. Mas ele dá mate em 1 quando pode: a nota de mate vale cerca de 100 mil, muito acima do ruído. Em `_pick_root_move`, ela nem recebe ruído, para a CPU não sortear entre mate em 1 e mate em 2, que diferem por poucos pontos.

**O nível fica mais forte mesmo?** Medido em partidas de verdade, com `tools/avaliar_cpu.py`: Hardcore 24 a 0 Hard, com 4 s por lance, Hard 18 a 2 Medium e Medium 20 a 0 Easy. O teste CT-74 exige pelo menos 75% dos pontos do nível mais forte.

**Por que outro tabuleiro para a busca?** `Board` é legível, com objetos para peças, casas e jogadas. Uma busca em Python puro não pode criar um objeto por posição. `SearchBoard` guarda tudo em inteiros, e a jogada cabe em 15 bits: origem, alvo e marca. A corretude é provada pelos mesmos perft do motor, em `tests/core/test_core_search_board.py`, e por partidas aleatórias comparadas lance a lance com `rules.py`. Na raiz, a busca só recebe lances que `legal_moves` aceitou.

**Por que thread e não processo?** Medido na cena de `tools/benchmark.py`: a thread com o intervalo padrão de 5 ms deixa a tela em 9,5 FPS. Com `sys.setswitchinterval(0.0002)` durante a busca, 58,7 FPS, contra 58,9 sem CPU. Um processo daria os mesmos 58,7 FPS, com mais nós por segundo, mas exigiria `multiprocessing` e a chamada freeze_support no executável, um risco a mais na demonstração. A thread venceu pela simplicidade, sem perder quadros.

**Se o Python só roda uma thread por vez, como a tela não trava?** O interpretador alterna as threads. Com o intervalo em 0,2 ms, a thread do quadro espera bem menos por sua vez. Com a câmera ou uma peça em movimento, a busca também dorme 1 ms a cada 64 nós, em `_should_stop`, porque nesses quadros a tela precisa mais do interpretador. Em janela real: 59,5 FPS com a CPU pensando e a câmera parada, e 59,7 com animação.

**A busca pode estragar a partida?** Não. `CpuPlayer.start` copia o tabuleiro na thread principal, antes de iniciar a thread, porque `legal_moves_from` faz `apply` e `undo` temporários no tabuleiro real. A jogada volta para a thread principal por `poll` e ainda passa por `GameEngine.play`. Cada busca é um `_SearchJob` próprio: a jogada de uma busca cancelada nunca chega a ninguém.

### Senha

**O que é PBKDF2?** É uma função para derivar chave a partir de senha: repete um HMAC muitas vezes, de propósito. Aqui, PBKDF2-HMAC-SHA256 com 600 mil iterações, em `_hash_password`, em `xadrez/data/accounts.py`. A OWASP recomenda esse mínimo.

**Por que deixar lento de propósito?** Quem entra certo só espera uma vez, medido em 0,17 s. Quem tenta adivinhar precisa esperar a cada tentativa. Um SHA-256 simples seria rápido demais para quem ataca.

**Para que serve o sal?** São 16 bytes aleatórios por conta, de `secrets.token_bytes`. Duas contas com a mesma senha ficam com hashes diferentes, e uma tabela pronta de senhas não serve. O sal não é segredo: fica no arquivo, junto com o hash.

**Por que não criptografar a senha?** Criptografia se desfaz com uma chave, e essa chave teria de estar neste computador. O hash não se desfaz: para conferir, calcula-se de novo e compara-se.

**O que há no arquivo?** Nome, sal, iterações e hash, em `accounts.json`. O CT-81 procura a senha em todos os bytes. As iterações ficam gravadas por conta para poder subir o padrão sem invalidar quem já existe.

**Por que `hmac.compare_digest`?** Comparar byte a byte para no primeiro diferente, e o tempo poderia vazar informação. Essa função leva sempre o mesmo tempo.

**O que acontece com conta inexistente?** A mesma mensagem, "Usuário ou senha incorretos.", e o mesmo custo: `authenticate` calcula o hash com um sal de enfeite. Responder mais rápido revelaria quais nomes existem.

**E na memória da tela?** O campo desenha pontos, sem passar pelo cache de texto do tema, e é limpo logo depois do envio. O CT-119 confere isso.

### Protocolo

**Como funciona o código da sala?** O IP vira um número de 32 bits, é multiplicado por 6, soma-se uma conferência de 0 a 5 e o resultado é escrito em base 31. Por exemplo, `192.168.0.10` vira `QVEFASM`. O alfabeto não tem 0, O, 1, I e L, que se confundem ao ditar, e por isso são 31 símbolos. Como 31^7 cabe 6,4 vezes em 2^32, sobram exatamente 6 valores para a conferência, que pega cerca de 5 em cada 6 erros. Está em `xadrez/net/room_code.py`.

**O código é uma senha?** Não. É o IP escrito de outra forma. Quem estiver na mesma rede e chegar primeiro à porta 50507 entra. Para uma partida entre colegas, serve. Foi uma sugestão do QA não aplicada.

**Por que TCP?** Lance de xadrez não pode se perder nem chegar fora de ordem, e o TCP garante as duas coisas. A rede local não tem o problema de latência que justificaria UDP.

**Como o fluxo de bytes vira mensagem?** O TCP não tem mensagens, só bytes. Cada mensagem é um JSON em uma linha, e `LineSplitter` separa as linhas. Nenhuma pode passar de 4096 bytes: uma linha sem fim é descartada sem acumular memória.

**Quais são as mensagens?** Na entrada, `hello` (versão e nome), `start` (nomes, cor, minutos, incremento e modo) e `refused` (`version` ou `room_full`). Na partida, `move` (uci e `clock_ms`), `resign`, `draw_offer`, `draw_answer`, `rematch`, `ping` e `bye`, e `result` (vencedor, motivo e `plies`), que só sai da sala.

**O que `decode_message` confere?** Que é JSON, que é um objeto, que o tipo existe, que os campos são exatamente os esperados e que cada valor tem o tipo e a faixa certos. Booleano não passa como número, nome com controle ou inversão de direção não passa, e vencedor que não combina com o motivo não passa. Qualquer erro levanta `ProtocolError`, e a conexão é encerrada: não se tenta entender.

**Por que JSON e não `pickle`?** Ler `pickle` de quem não se confia executa código. JSON é só dado.

**E se mandarem lixo antes de entrar?** Só cai a conexão de quem mandou: um estranho não pode fechar a sala. Há no máximo 8 conexões à espera, com 5 s para mandar o `hello`.

**Como a tela não trava esperando a rede?** Uma thread por sessão cuida dos sockets, com `selectors`, e fala com a interface por duas filas `deque`. A cena chama `poll` a cada quadro, sem esperar nada. Só `close` espera, e pouco.

**Como sabem que o outro sumiu?** Sinal de vida a cada 2 s, e 8 s sem uma linha válida viram `PeerLeft`. Pingar um byte por vez não segura a sala, porque só linha completa conta.

**Só funciona na rede local?** Sim, de propósito. `is_lan_address` recusa endereço global, tanto ao conectar quanto ao aceitar conexão, e o jogo não consulta DNS.

**Funciona entre dois computadores?** Resposta honesta: a partida inteira foi testada em dois processos em `127.0.0.1`, e a sala foi testada pelo IP real, com `0.0.0.0` e a porta 50507, em um computador só. A conexão entre dois computadores e a passagem pelo firewall não estão verificadas na documentação. Diga o que o ensaio do grupo mostrou, e nada além disso.

### Autoridade

**Cada um escolhe o modo?** Não: o modo é um só por sala. Quem cria escolhe, e `start` leva o valor. Em `_start_game`, na `LobbyScene`, quem entra troca o modo do menu pelo da sala, e a faixa avisa se eram diferentes. Se a sala mudar o modo na revanche, a conexão é encerrada, em `_start_network_rematch`. Por que mudar: com um modo por jogador, quem estava em Partida enfrentaria, sem saber, alguém com todas as dicas. É o protocolo 3: versões diferentes não jogam entre si, e `refused` com `version` explica isso na tela.

**Por que um lado manda em tudo?** Os dois lados precisam chegar ao mesmo resultado, e dois relógios separados nunca batem: o `dt` de cada quadro é limitado a 0,1 s, então uma janela arrastada atrasa só aquele relógio. Na primeira versão, cada lado decidia pelo próprio relógio, e o QA provou que os dois podiam se dar a vitória (QA11-09). Com uma autoridade só, isso não acontece.

**O que a sala faz?** Em `xadrez/ui/net_link.py`: valida cada lance no próprio motor, em `_on_move`; mede os dois relógios, em `tick`; decide o fim; e manda `result`, em `publish_result`. Ela é a autoridade também jogando de pretas, na revanche.

**O que quem entrou faz?** Joga sem esperar, porque ninguém quer atraso a cada lance. Mas nada ali é definitivo antes da palavra da sala: o relógio só serve para mostrar, desistir e aceitar empate são pedidos, e a partida só é gravada depois do `result`. Em `_begin_turn`, o fim visto no próprio tabuleiro espera `_is_result_final`.

**O que é o `plies` do `result`?** É em que meio-lance a partida parou. Quem entrou compara com o próprio histórico em `_on_decision`. Se tem um a mais, e foi dele, esse lance cruzou com o fim: a sala nem o viu. Então `take_back_last_move` o desfaz, inclusive a captura e o ponto na série. Qualquer outra diferença encerra a sala.

**Dá um exemplo de lance cruzado.** Quem entrou joga um lance no mesmo instante em que o relógio dele zera na sala. Os dois se cruzam na rede. A sala ignora o lance, porque a partida já acabou, e manda `result` com o número de lances de antes. Quem entrou recebe, vê um lance a mais e volta atrás. Os dois terminam com o mesmo FEN.

**Quem entrou confere a sala?** Sim, dentro do que dá para conferir. Em `_agrees_with_board`: se o próprio tabuleiro já terminou, tem de bater. Se não terminou, o motivo não pode ser um que o tabuleiro desmentiria, como um mate que não existe. Falhou, encerra com "A sala enviou um resultado que não confere, e a partida foi encerrada.".

**Então a sala pode trapacear?** Pode, nesse limite: como só ela mede o tempo, uma cópia alterada pode dizer que o outro perdeu no relógio. É inerente a ter uma autoridade, e está registrado na seção 5.7. O outro limite: uma sala travada atrasa os dois relógios.

**E o `clock_ms` que chega no lance?** É só informativo, e não entra em nenhuma decisão, porque pode ser falso. O CT-110 manda um relógio falso e confere que nenhum relógio muda.

**E se a sala sumir?** Vale `PeerLeft`, na hora, ou o sinal de vida, em 8 s. Sem ninguém para decidir, quem entrou fica com o que já sabia: o fim no tabuleiro, o próprio pedido ou o abandono da sala. Com a sala viva e muda depois de um pedido, a espera termina em 5 s.

**E se quem entrou sair?** Sair é abandono, e a sala decide a favor de quem ficou. Se ele saiu com um lance da sala a caminho, o histórico dele fica com um lance a menos, porque não há mais a quem perguntar. O vencedor é o mesmo.

### Testes e CI

**O que é o CI?** É a execução automática dos testes a cada envio ao GitHub, em `.github/workflows/testes.yml`: Python 3.10 e 3.12, no Windows, no Linux e no macOS, sem janela. É o que comprova o RNF02.

**O CI achou algo na versão 1.1?** Sim: dois casos de teste presos a uma suposição, e nenhum defeito do jogo. O de arquivo somente leitura supunha o Windows. No macOS e no Linux, a troca do temporário pelo arquivo só depende da permissão da pasta, e a gravação dá certo. O de profundidade dava 1 s ao Hardcore, o que não bastava em máquina lenta e com cobertura. Agora ele usa limite de nós, e o resultado é igual em qualquer máquina. Depois, uma rodada falhou por acaso no macOS: um teste somava 8 s ao relógio real, e perto de uma potência de 2 o `float` arredonda. Agora ele usa um instante fixo. A seção 7.9 traz as execuções.
