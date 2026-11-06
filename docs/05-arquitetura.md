# 5. Arquitetura

## 5.1 Camadas

```
xadrez/
├── core/       regras do jogo e CPU. Python puro: sem pygame, sem numpy.
├── data/       contas e histórico em disco. Python puro.
├── net/        sala em rede local por socket. Python puro.
├── graphics/   computação gráfica. numpy + pygame. Não conhece as regras.
└── ui/         cenas, HUD e entrada. Liga tudo.
```

| Camada | Responsabilidade | Arquivos principais |
|---|---|---|
| `xadrez/core` | Posição, peças, legalidade, fim de jogo, relógio, pontuação, PGN e CPU | `engine.py`, `board.py`, `pieces.py`, `rules.py`, `notation.py`, `pgn.py`, `clock.py`, `player.py`, `move.py`, `types.py`, `ai.py`, `search_board.py`, `evaluation.py` |
| `xadrez/data` | Contas com senha e histórico de partidas, em JSON na pasta do usuário | `paths.py`, `storage.py`, `accounts.py`, `history.py` |
| `xadrez/net` | Sala em rede local: código, mensagens, conexão e sessão | `room_code.py`, `events.py`, `protocol.py`, `connection.py`, `session.py` |
| `xadrez/graphics` | Vetores, matrizes, câmera, malhas, luz, sombra, partículas, animação e desenho | `vector.py`, `matrix.py`, `camera.py`, `mesh.py`, `models.py`, `lighting.py`, `color_matrix.py`, `animation.py`, `particles.py`, `renderer.py`, `board_model.py`, `backdrop.py` |
| `xadrez/ui` | Janela, laço principal, telas, HUD, entrada e tradução entre as outras camadas | `app.py`, `frame_pacer.py`, `scene.py`, `arena_scene.py`, `login_scene.py`, `menu_scene.py`, `lobby_scene.py`, `history_panel.py`, `game_scene.py`, `game_over_scene.py`, `board_view.py`, `hud.py`, `overlays.py`, `widgets.py`, `debug_panels.py`, `theme.py`, `drawing.py`, `match.py`, `match_record.py`, `cpu_player.py`, `net_link.py`, `clipboard.py`, `autoplay.py` |

## 5.2 Regra de dependência

```
ui  ->  core, data, net, graphics
net ->  core
data   não importa nenhuma outra camada
core   não importa nenhuma outra camada
graphics não importa nenhuma outra camada
```

A regra permite que `data` importe `core`, mas hoje ela não precisa: `MatchRecord` guarda só texto e números. `tests/test_arquitetura.py` lê os imports de cada arquivo e falha se a regra for quebrada: `core`, `data` e `net` não importam pygame nem numpy, `graphics` não importa `core`, e `data` e `net` não se importam. Outro teste, `tests/ataque/test_ataque_seguranca.py`, confere que só `net` importa `socket` e `selectors`, que só `data` grava em disco e que threads só existem em `net` e na `ui`.

Como `graphics` não conhece o motor, a `ui` traduz os tipos: a casa vira `(file, rank)` e o tipo de peça vira texto, como `"pawn"`. Essa tradução acontece em `BoardView`. Do mesmo jeito, `data` não conhece a partida: `match_record.py`, na `ui`, traduz o motor para um `MatchRecord`.

Consequências práticas:

- os testes do motor, dos dados e da rede rodam sem abrir janela e sem pygame;
- o perft testa as regras em milhões de posições, sem nenhum custo de desenho;
- o pipeline gráfico pode ser testado com cenas artificiais, sem uma partida de verdade;
- a sala em rede pode ser testada por socket em `127.0.0.1`, sem interface, com um atacante escrevendo bytes crus.

## 5.3 Fluxo de um quadro

`App.step(dt)` faz um quadro completo:

1. entrega os eventos à cena atual;
2. confere se o tamanho da janela mudou;
3. chama `scene.update(dt)`, com o `dt` limitado a 0,1 s;
4. faz a troca de cena, se a cena pediu;
5. chama `scene.draw(screen)`.

`App.run_frame` acrescenta a espera do `FramePacer` e o `display.flip`. Separar os dois permite que testes e ferramentas rodem `step` com tempo fixo, sem janela e sem relógio real.

Na versão 1.1, duas threads podem rodar ao lado do quadro: a da busca da CPU e a da sessão de rede. Nenhuma delas toca no motor da partida nem em pygame. A da CPU recebe uma cópia do tabuleiro e devolve um `Move`. A da rede só fala por duas filas `deque`, e `GameScene` lê os eventos com `poll`, a cada quadro. Por isso, tudo o que muda a partida continua acontecendo na thread principal, dentro de `update`.

## 5.4 Decisões e motivos: versão 1.0

| Decisão | Motivo | O que se abriu mão |
|---|---|---|
| Pipeline próprio em numpy + pygame, em vez de OpenGL ou um motor pronto | Matrizes, malhas, luz e clique por raio ficam explícitos e explicáveis na banca. Não depende de driver de GPU. | Desempenho de GPU. O desenho roda na CPU, e foi preciso otimizar com caches. |
| Motor sem interface | Testável sem janela. O perft prova as regras. A interface nunca decide regra, então a mensagem de recusa vem sempre do motor. | A `ui` precisa traduzir os tipos para `graphics`. |
| Regras oficiais completas, em vez do xadrez simplificado | A rubrica cobra regras oficiais, e o perft dá validação objetiva. | Mais código e mais casos de teste. |
| `play` devolve `MoveOutcome`, sem exceção para entrada inválida | Jogada inválida é um caminho normal do jogo. A interface só lê o resultado (RNF07). | Quem chama precisa olhar o campo `ok`. |
| Legalidade por aplicar e desfazer | Olhar o rei depois de aplicar a jogada é a resposta certa em todos os casos, inclusive en passant. Um filtro só pula o teste quando a peça não está alinhada com o rei. | Custo de `apply` e `undo` nas peças alinhadas. |
| Toda face como quadrilátero | A forma fixa `(M, 4)` permite processar a cena inteira em arrays, sem laço por face no Python. Triângulo repete o último índice. | Um pouco de memória nos triângulos. |
| Dois modos de desenho | Câmera em movimento redesenha polígonos. Câmera parada usa camada e sprites prontos, com bordas melhores por superamostragem. | Mais código no renderizador. |
| Algoritmo do pintor, sem z-buffer | Em software, um z-buffer por pixel em Python custaria caro. Ordenar por objeto e depois por face resolve o caso das peças. | Só funciona porque os objetos da cena são separados. |
| Sombra planar por matriz | Uma matriz achata a peça no plano do tabuleiro. É simples e dá para explicar em uma frase. | A sombra só cai no tabuleiro, não em outras peças. |
| Só fontes do sistema e nada baixado | O jogo roda em qualquer máquina sem arquivos extras. | A aparência varia um pouco conforme as fontes instaladas. |
| Clique pela silhueta da malha, em vez de volume simples | Um cilindro por peça cobria a peça de trás: o peão e2 quase não era clicável (achado QA-03). Testar as faces projetadas, da peça mais próxima para a mais distante, aciona o que o jogador vê. | Projetar as malhas candidatas custa mais, então um cilindro envolvente descarta antes as que estão longe do raio. |
| `FramePacer` próprio, em vez de `Clock.tick` | `tick(60)` trabalha em milissegundos inteiros, e o sono do sistema acorda atrasado. Medido em janela real, isso dava 59,1 FPS. Com prazos em segundos, deu 60,0. | Uma pequena espera ativa antes de cada prazo. |
| `preload` antes da primeira partida | Desenha uma partida invisível, para os fundos ficarem prontos. A troca do menu para a partida caiu para 26 ms. | Um pouco mais de tempo ao abrir o jogo. |

## 5.5 Decisões e motivos: versão 1.1

| Decisão | Motivo | O que se abriu mão | Alternativa recusada |
|---|---|---|---|
| CPU em uma thread, com `sys.setswitchinterval(0.0002)` durante a busca | O medido com a cena de `tools/benchmark.py`: thread no intervalo padrão de 5 ms deixa a tela em 9,5 FPS. Com 0,2 ms, 58,7 FPS, contra 58,9 sem CPU. O intervalo volta ao original no fim de toda busca, inclusive com exceção. | Menos nós por segundo que um processo. | Processo separado: deu os mesmos 58,7 FPS, com mais nós por segundo, mas exige `multiprocessing` e a chamada freeze_support no executável, um risco a mais na demonstração. |
| `should_stop` dorme 1 ms com câmera ou peça em movimento | Com a câmera girando, o quadro precisa do interpretador mais do que a busca. A consulta é a cada 64 nós. | A busca anda mais devagar nesses quadros. | Pausar a busca: ela perderia o tempo do relógio. |
| `board.copy()` na thread principal, antes de iniciar a busca | `legal_moves_from` faz `apply` e `undo` temporários no tabuleiro real, então a busca não pode ler o mesmo objeto. | Uma cópia por lance. | Travas: complicariam o motor por causa de um uso só. |
| Tabuleiro compacto de inteiros, só para a busca (`SearchBoard`) | Em Python puro, criar objetos por posição custaria caro demais. Aqui, casa, peça e jogada são inteiros, e a jogada cabe em 15 bits. Os mesmos perft do motor provam as regras, e `choose_move` só devolve o que `rules.legal_moves` aceita. | Duas implementações das regras, a legível e a rápida. | Buscar sobre `Board`: fácil de ler, lento demais para qualquer profundidade útil. |
| Busca de um jeito só, com a tabela `_LEVELS` separando os níveis | Profundidade, ruído, margem, nós e tempo mudam, e o código não. De Easy a Hard, o resultado se repete com a mesma semente, porque o limite é em nós, não em tempo. | | Um código por nível. |
| Quem cria a sala é a autoridade do resultado (protocolo v2) | Os dois lados precisam chegar ao mesmo FEN e ao mesmo resultado, e dois relógios separados nunca batem: `dt` limitado a 0,1 s e janela arrastada defasam um deles. Com um lado só decidindo, nunca há dois vencedores nem motivos diferentes. | Uma cópia alterada do jogo na sala pode mentir, e uma sala travada atrasa os dois relógios. | Consenso entre os dois lados: era a versão anterior, e o QA provou dois vencedores (QA11-09) e lance cruzado com FEN diferente (QA11-08). |
| Quem entrou joga sem esperar, e o lance volta se cruzou com o fim | A resposta na tela fica imediata, sem esperar a rede. `take_back_last_move` desfaz o lance, com a captura e o ponto. | Quem saiu com um lance da sala a caminho fica com um lance a menos no histórico. | Esperar a sala confirmar cada lance: atraso visível a cada jogada. |
| JSON por linha, com validação em cada campo | `pickle` executa código ao ler, e a rede não é confiável. JSON é só dado, e o esquema confere tipos, campos e faixas. | Texto é maior que binário, mas é pouco: linha de no máximo 4096 bytes. | `pickle` e formatos binários próprios. |
| Sem servidor | Cada um roda o jogo e pronto: nada para hospedar, nada para manter no ar na banca. O código de sala é o próprio IP. | Só funciona na mesma rede, e depende do firewall de quem cria a sala. | Servidor central: fora do escopo do trabalho, e a demonstração dependeria dele. |
| Código de 7 caracteres em base 31 | É o IP vezes 6, mais uma conferência. Sem 0, O, 1, I e L, sobram 31 símbolos, e 31^7 cabe 6,4 vezes em 2^32. A conferência pega cerca de 5 em cada 6 erros de digitação. | Não é segredo: é o IP escrito de outra forma. | Mostrar o IP: mais difícil de ditar e sem nenhuma conferência. |
| Contas locais com PBKDF2-HMAC-SHA256, 600 mil iterações | A OWASP recomenda esse mínimo. Medido em 0,17 s por verificação: forte, sem travar a tela. Sal próprio de 16 bytes por conta, e comparação em tempo constante com `hmac.compare_digest`. | O jogo espera 0,17 s ao entrar. | SHA-256 simples: rápido demais para quem tenta adivinhar. bcrypt e Argon2 exigiriam dependência nova, e `hashlib` já resolve. |
| JSON com escrita atômica em disco | `mkstemp` na mesma pasta, `fsync` e `os.replace`: quem lê vê o arquivo antigo ou o novo, nunca metade. | Grava o arquivo inteiro a cada partida. | SQLite: mais do que 50 registros por conta precisam. |
| Arquivo ruim é posto de lado, e o jogo segue | Histórico nunca impede de jogar. Arquivo corrompido vira cópia com outro nome e a lista começa vazia. Erro de leitura é outra coisa: levanta `DataError`, para a próxima gravação não apagar dados que só estão inacessíveis agora. | | Avisar e parar. |
| `App()` sem contas nem rede, e `App(require_login=True)` no jogo | Testes e ferramentas não tocam a pasta de dados nem abrem porta, nem por um clique do macaco. Os testes de rede passam `App(network=...)`, em `127.0.0.1`. | Dois caminhos de abertura para manter. | Variável global de "modo teste". |
| `CHESS_THE_GAME_DATA` substitui a pasta de dados | Os testes usam sempre uma pasta temporária. | | |

### Onde ficam os dados

| Sistema | Pasta |
|---|---|
| Windows | `%APPDATA%\ChessTheGame` |
| macOS | `~/Library/Application Support/ChessTheGame` |
| Linux | `~/.local/share/chess-the-game` |

`accounts.json` guarda as contas, e cada conta tem um arquivo `history-` seguido de 32 caracteres do hash do nome. Nada disso vai para o repositório.

### A busca em uma tabela

| Técnica | Em uma frase | Onde está |
|---|---|---|
| Negamax | A nota de um lance para mim é o negativo da nota para o adversário, então um único código serve aos dois lados. | `_Search._negamax` |
| Poda alfa-beta | `alpha` é o que já tenho garantido e `beta` é o que o adversário permite. Passou de `beta`, o resto dos lances pode ser ignorado. | `_Search._search_moves` |
| Janela mínima | Só o primeiro lance recebe a janela inteira. Os outros só precisam provar que não superam `alpha`, e são buscados de novo se surpreenderem. | `_Search._score_child` |
| Ordenação MVV-LVA | A poda só corta muito se os melhores lances vierem primeiro: lance da tabela, capturas (maior vítima com o menor atacante), promoções, depois "killers" e história. | `_Search._ordered`, `_capture_priority` |
| Quiescência | Na profundidade limite, continua só pelas capturas. Sem isso, a busca pararia no meio de uma troca. | `_Search._quiesce` |
| Tabela de transposição | A mesma posição aparece por caminhos diferentes, e a nota só é calculada uma vez. Vive só durante a chamada. | `_Search.table`, com chave de Zobrist em `SearchBoard` |
| Aprofundamento iterativo | Busca 1, 2, 3... lances. Cada volta ordena a seguinte, e sempre há resposta pronta quando o tempo acaba. | `_Search.run` |
| Técnicas seletivas, só no Hardcore | Estende a busca em xeque, reduz lances tardios e corta pela avaliação estática. | `_Search._negamax`, `_Search._late_move_reduction` |
| Avaliação | Material, tabelas de posição misturadas por fase, par de bispos e estrutura de peões. | `evaluate`, em `xadrez/core/evaluation.py` |

| Nível | Profundidade | Ruído na nota | Margem de sorteio | Limite | Quiescência |
|---|---|---|---|---|---|
| Easy | 1 meio-lance | ±300 (centésimos de peão) | | Sem limite | Não, mas vê o mate em 1 |
| Medium | 2 | ±40 | | 30 mil nós | Sim |
| Hard | 3 | | 10 | 90 mil nós | Sim |
| Hardcore | Aprofundamento até o tempo acabar | | 20, só até o lance 8 | 4 s | Sim, com as técnicas seletivas |

Até o Easy dá mate em 1 quando pode: a nota de mate vale cerca de 100 mil, muito acima do ruído. Ela nem recebe ruído, para a CPU não sortear entre mate em 1 e mate em 2, que diferem por poucos pontos. No meio-jogo, o Hardcore chega à profundidade 8 a 9.

## 5.6 Modelo de ameaça

O jogo não tem servidor, então o que pode dar errado está na rede local e no disco deste computador.

| Quem ou o quê | O que pode tentar | O que o jogo faz | O que fica de fora |
|---|---|---|---|
| Estranho na mesma rede, antes de entrar | Bytes aleatórios, linha sem fim, enxurrada, conexões mudas | Só cai a conexão dele. No máximo 8 conexões à espera, 5 s para o `hello` e linha de 4096 bytes | Sala não tem senha: quem chegar primeiro na porta entra |
| Adversário com o jogo alterado, dentro da sala | Lance ilegal, formato errado, relógio falso, nome hostil, enxurrada de propostas | Cada mensagem é conferida no esquema, e cada lance, no motor. `clock_ms` não decide nada. Mensagem inválida encerra a conexão, e 2000 mensagens por segundo também. Vale uma proposta por lance | |
| Sala alterada, para quem entrou | `result` falso, `start` fora de hora | `result` que não bate com o próprio tabuleiro encerra a sala. `start` sem revanche pedida também | Pode mentir sobre o tempo e sobre desistência, porque o outro lado não mede os relógios |
| Código digitado errado | Apontar para fora da rede | A sessão recusa endereço global, tanto ao conectar quanto ao aceitar | |
| Alguém com o arquivo de contas | Ler a senha | Só há sal, iterações e hash. Quebrar exige força bruta, a 0,17 s por tentativa nesta máquina | Senha fraca continua fraca |
| Alguém tentando descobrir contas | Testar nomes pelo login | Mensagem única e o mesmo custo de hash para conta inexistente | |
| Arquivo editado à mão | Tipos errados, texto e números gigantes, controle | Tudo é entrada não confiável: tipos conferidos, textos cortados e números no teto. O arquivo ruim é posto de lado | |
| Nome de conta malicioso | `../../x`, `CON` | O nome do arquivo é um hash: nada digitado chega ao caminho | |

O tráfego da rede é JSON em claro, sem cifra: quem está na mesma rede pode ler os lances. Para uma partida entre amigos, é o que se quer. Não é um canal para nada secreto, e nada secreto passa por ele: a senha nunca sai do computador.

## 5.7 Limites conhecidos

Inerentes às decisões acima, e não defeitos a corrigir:

- **Cliente alterado.** Uma cópia alterada do jogo que entrou na sala pode mentir sobre o que diz, mas a sala confere tudo o que chega dela. Já uma sala alterada pode mentir sobre o resultado, dentro do que o tabuleiro de quem entrou consegue conferir.
- **Sala travada.** Quem mede os relógios é a sala. Um quadro travado por muito tempo lá atrasa os dois relógios, porque o `dt` é limitado a 0,1 s.
- **Saída com lance a caminho.** Se quem entrou sair com um lance da sala a caminho, o histórico dele fica com um lance a menos, porque não há mais a quem perguntar. O vencedor é o mesmo.
- **Sufixo no nome.** Dois jogadores com o mesmo nome: as pretas viram "Jogador 1 (2)". O sufixo fica em `Player.name`, então aparece também no PGN e no histórico. É o desvio registrado no achado QA11-12.
- **Modo por jogador.** Em rede, cada um escolhe o próprio modo, e o protocolo não avisa o outro. Quem joga em Partida pode enfrentar alguém com todas as dicas, sem saber. Mudar isso é decisão do aluno.
- **Formulários em 640x360.** Não cabem na janela, mas o jogo não cai. A partir de 640x480 está tudo certo (achado QA11-17, aceito).

Ainda não verificado, nesta versão:

- **Duas máquinas e firewall.** A sala foi testada em `127.0.0.1` pelas suítes, e também pelo IP real da rede local, com `0.0.0.0` e a porta 50507, em um único computador, por um script avulso, com sessões e sem janela. Conexão entre dois computadores diferentes e passagem pelo firewall nunca foram verificadas.
- **Rede em janela real.** Os testes de rede por tela rodam com o SDL sem janela.
- **Versão 1.1 em Linux, macOS e Python 3.10.** O CI só roda no envio ao GitHub, e esta versão ainda não foi enviada.

## 5.8 Convenções

- **Casa:** `file` 0 a 7 são as colunas a a h, e `rank` 0 a 7 são as fileiras 1 a 8. A casa é escura quando `(file + rank) % 2 == 0`.
- **Mundo:** y para cima, tabuleiro no plano y = 0, cada casa mede 1 unidade. O centro da casa é `x = file - 3.5` e `z = 3.5 - rank`. As brancas ficam em z positivo.
- **Câmera:** `yaw = 0` olha pelo lado das brancas, e `yaw = pi`, pelo das pretas.
- **Matrizes:** numpy `(4, 4)`, com vetor coluna: `p' = M @ p`.
- **Idioma:** identificadores em inglês, alinhados aos nomes do enunciado. Comentários, telas e documentos em português.

## 5.9 Testes como parte da arquitetura

Cada teste ligado a um caso formal leva `@pytest.mark.ct("CT-xx")`. A opção `--ct-report`, definida em `tests/conftest.py`, grava o resultado real em JSON. `tools/relatorio_testes.py` junta esse resultado às especificações e gera o capítulo 7 e o capítulo 8. Assim, "Resultado Obtido" nunca é digitado à mão.

`Autoplayer`, em `xadrez/ui/autoplay.py`, joga por eventos reais de mouse e teclado. É usado pelos testes de interface, pela captura de telas, pelo benchmark e pela demonstração automática.
