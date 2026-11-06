# QA da versão 1.1: auditoria de ataque

## Situação

Situação em 2026-11-06, depois deste relatório. As seções abaixo são o texto original da auditoria, com o estado da cópia congelada: o que elas dizem como "obtido" não vale mais para os achados corrigidos.

| Achado | Severidade | Situação | Commit |
|---|---|---|---|
| QA11-01 | Média | Corrigido: duração e lances param em um teto ao carregar o histórico | `eaf8f25` |
| QA11-02 | Média | Corrigido: com a troca de tela já pedida, o resto do quadro não chega à cena | `eaf8f25` |
| QA11-03 | Média | Corrigido: ao criar conta, Enter em "Senha" vai para "Repita a senha" | `eaf8f25` |
| QA11-04 | Baixa | Corrigido: o foco fica nas abas, e não em "Sair da conta" | `eaf8f25` |
| QA11-05 | Baixa | Corrigido: o orçamento da busca nunca passa da metade do que resta | `eaf8f25` |
| QA11-06 | Baixa | Corrigido: a frase de vitória só sai se a saída do outro decidiu a partida | `eaf8f25` |
| QA11-07 | Baixa | Corrigido: a sala decide, e vale a primeira desistência que ela viu | `eaf8f25` |
| QA11-08 | Baixa | Corrigido: `result` diz em que lance a partida parou, e o lance cruzado é desfeito | `eaf8f25` |
| QA11-09 | Média | Corrigido: protocolo v2, com quem criou a sala como autoridade | `eaf8f25` |
| QA11-10 | Baixa | Corrigido: fechar a janela em rede grava a derrota antes de a conexão fechar | `eaf8f25` |
| QA11-11 | Baixa | Corrigido: virar durante o giro conta a partir do destino do giro | `eaf8f25` |
| QA11-12 | Baixa | Corrigido, com o desvio descrito abaixo | `eaf8f25` |
| QA11-13 | Baixa | Corrigido: texto da sala com `text_fit`, e o botão diz "Aceitar: o adversário pediu revanche" | `eaf8f25` |
| QA11-14 | Média | Corrigido: no modo Partida, com a partida correndo, a cópia sai sem `+` e `#` | `eaf8f25` |
| QA11-15 | Baixa | Corrigido: quem abandona lê "Abandonou a partida" | `eaf8f25` |
| QA11-16 | Baixa | Corrigido: o texto é cortado no limite do campo ao carregar | `eaf8f25` |
| QA11-17 | Baixa | **Aceito:** em 640x360 os formulários não cabem, e o jogo não cai. A partir de 640x480 está tudo certo. Os 4 testes seguem em `xfail`, com o motivo escrito | sem correção |
| QA11-18 | Média | **Resolvido por este trabalho:** requisitos, plano de testes, matriz e README cobrem a versão 1.1, e os testes de CT-135 passam sem `xfail` | ver o histórico do git depois de `eaf8f25` |
| QA11-19 | Baixa | Corrigido: o motivo da sala encerrada segue até a tela de fim | `eaf8f25` |
| QA11-20 | Baixa | Corrigido: uma proposta por lance, e a proposta repetida é ignorada | `eaf8f25` |

**Desvio do QA11-12.** A correção sugerida trocava o nome de quem entra só na sala. O que foi feito: quando os dois nomes são iguais, as pretas viram "Jogador 1 (2)", em `distinct_player_names`, com a conta feita nos dois computadores a partir da mesma mensagem. O sufixo fica em `Player.name`, então aparece também no PGN e no histórico, e vale também em 2 jogadores locais.

**Sugestões não aplicadas.**

| Sugestão | Situação |
|---|---|
| 1. Modo por jogador em rede | Não aplicada. É decisão do aluno: hoje cada um escolhe o próprio modo, e o outro não sabe. |
| 2. Sala sem segredo | Não aplicada. O código é o IP escrito de outra forma, e quem chegar primeiro à porta entra. |
| 3. Fugir da derrota contra a CPU | Não aplicada. "Voltar ao menu" e fechar a janela não gravam nada contra a CPU. |
| 5. Hard responde mais rápido que Easy | Não aplicada. `_MINIMUM_THINK_SECONDS` segue só em Easy e Medium. |
| 6. Soltar fora do tabuleiro e fora da janela | Não aplicada. Soltar fora do tabuleiro desmarca, e soltar fora da janela mantém a seleção. |

As sugestões 4, 7 e 8 foram aplicadas no mesmo commit `eaf8f25`: a ajuda só lista o que vale, o erro de pasta não mostra o caminho, e a limpeza foi feita.

**O que mudou no "Não verificado" abaixo.**

- **60 FPS reais (RNF09):** agora medido em janela real, com `tools/demo_automatica.py`, no commit `eaf8f25`: 60,0 FPS em 2 jogadores, 59,7 na partida contra a CPU Hardcore, 59,5 com a CPU pensando e a câmera parada e 59,7 com a CPU pensando e animação.
- **Dois processos:** teste em 127.0.0.1 com mesmo FEN, histórico, resultado e placar.
- **Sala pelo IP real:** verificada em um só computador em 2026-11-06, no commit `eaf8f25`, com `0.0.0.0`, a porta 50507 e o código gerado com o IP da rede local, por um script avulso, com sessões e sem janela. Início da partida, um lance de cada lado, `result` e saída funcionaram.
- **Macaco longo, no estado final:** 16 aprovados, em 12 min 41 s.

**Segue não verificado:** conexão entre dois computadores, passagem pelo firewall, rede em janela real e versão 1.1 em Linux, em macOS e em Python 3.10, porque o CI só roda no envio ao GitHub.

## Relatório original da auditoria

Cópia congelada no commit `0671f69`, com SDL sem janela, dados em pasta temporária e rede só em `127.0.0.1`. O jogo não foi alterado: só entraram os testes `tests/ataque/test_ataque_v11_*.py` e este relatório.

Cada achado foi reproduzido antes de entrar aqui e tem um teste com `xfail(strict=True)`. Quando o defeito for corrigido, o teste passa a dar XPASS, a suíte acusa, e basta tirar a marca.

## Resumo

| Severidade | Quantos | Achados |
|---|---|---|
| Bloqueante | 0 | |
| Alta | 0 | |
| Média | 6 | QA11-01, 02, 03, 09, 14, 18 |
| Baixa | 14 | QA11-04, 05, 06, 07, 08, 10, 11, 12, 13, 15, 16, 17, 19, 20 |

**O pedido central resistiu na tela:** o modo Partida não entrega o xeque por nenhum pixel. O único vazamento é fora da tela (QA11-14).

Os três que eu corrigiria antes da banca, pelo risco de aparecerem ao vivo: QA11-03 (criar conta com Enter dá erro), QA11-12 (dois convidados com o mesmo nome) e QA11-18 (matriz de rastreabilidade sem a versão 1.1).

## Defeitos

### Média

#### QA11-01: inteiro gigante em `seconds` derruba o jogo ao abrir "Meu histórico"
- **Onde:** `xadrez/data/history.py:55` aceita, `xadrez/ui/match.py:87` quebra.
- **Reprodução:** no arquivo de histórico, troque `"seconds"` por um inteiro de 401 dígitos (`10**400`). Abra a aba "Meu histórico".
- **Esperado:** o registro é posto de lado, ou a duração aparece limitada, como nos outros campos adulterados.
- **Obtido:** `OverflowError: int too large to convert to float` em `format_clock`, dentro do `draw`. O jogo fecha, e fecha de novo a cada vez que a aba abre, porque o arquivo não é posto de lado.
- **Correção:** em `MatchRecord.__post_init__`, exigir `seconds < 1e12` (e o mesmo para `moves`). Em `format_clock`, proteger a conversão.
- **Teste:** `test_duracao_com_inteiro_gigante_nao_derruba_a_aba`. Precisa de edição à mão: por isso é média, apesar de derrubar o jogo.

#### QA11-02: dois Enter no mesmo quadro no menu abrem duas sessões, e a primeira segura a porta
- **Onde:** `xadrez/ui/menu_scene.py:123` (`start_match`) e `:150` (`_open_lobby`). A tela de fim já tem a proteção (`game_over_scene.py:89`), o menu não.
- **Reprodução:** foco em "Criar sala", dois `K_RETURN` no mesmo `App.step`.
- **Esperado:** uma sala.
- **Obtido:** duas `LobbyScene`, cada uma com a sua `HostSession`. A primeira fica sem dono, com a thread viva e a porta presa. Na porta fixa, a tela mostra "Não foi possível abrir a porta". Conferi: nem "Abrir a sala de novo" nem voltar ao menu e criar outra resolvem, só fechar o jogo. Em "Iniciar partida" contra a CPU de brancas, a primeira partida deixa uma busca pensando sem dono, até acabar sozinha.
- **Correção:** `if self.next_scene is not None: return` no começo de `start_match` e de `_open_lobby`.
- **Testes:** `test_enter_repetido_em_criar_sala_abre_uma_sessao_so`, `test_enter_repetido_em_criar_sala_nao_prende_a_porta`, `test_enter_repetido_no_menu_abre_uma_partida_so`. Exige um quadro longo ou dois toques em 16 ms: pouco provável, mas o efeito só sai fechando o jogo.

#### QA11-03: criar conta só pelo teclado dá erro e apaga a senha
- **Onde:** `xadrez/ui/login_scene.py:34`. O campo "Senha" tem `on_submit=self.submit` também no modo de criar.
- **Reprodução:** "Criar conta", usuário, Enter, senha, Enter.
- **Esperado:** o foco vai para "Repita a senha".
- **Obtido:** o formulário envia, mostra "As duas senhas não são iguais. Digite de novo." e apaga a senha. O foco volta para "Senha", e o próximo Enter repete o erro. Só sai com Tab ou com o mouse.
- **Correção:** no modo de criar, Enter em "Senha" avança. Em `_apply_mode`, ajustar `password_input.advances_on_enter` e tirar o `on_submit` enquanto `is_creating`.
- **Teste:** `test_criar_conta_so_pelo_teclado_com_enter_entre_os_campos`.

#### QA11-09: em rede, o relógio de lá não fecha a conta
Três sintomas da mesma causa: cada lado só decide pelo próprio relógio, sem conferir com o outro.
- **Onde:** `xadrez/ui/net_link.py:118` (zera a espera a cada lance), `:190` (`_tick_remote_clock`), `:134` (janela de 2 s). A defasagem vem de `xadrez/ui/app.py:50`, que limita o `dt` a 0,1 s: janela arrastada ou quadro lento atrasam só aquele relógio.
- **Reprodução 1:** uma cópia alterada do jogo não se declara sem tempo e joga a cada 4 s. **Obtido:** a partida segue para sempre com o relógio dela em zero. **Esperado:** a folga de 5 s não renova.
- **Reprodução 2:** relógios 5 s defasados, com o de lá em zero. **Obtido:** quem esperou declara abandono e manda `bye`. O outro recebe `PeerLeft` e também declara abandono. **Os dois lados se dão a vitória.**
- **Reprodução 3:** quem esgota o relógio avisa, e o outro ainda vê 3 s. **Obtido:** um lado grava "Tempo esgotado" e o outro "Desistência".
- **Correção:** mensagem própria de tempo esgotado no protocolo, em vez de `send_resign`, e um `bye` de abandono que diga quem perdeu. Para a reprodução 1, acumular `_flag_wait` em vez de zerar.
- **Testes:** `test_quem_ignora_o_proprio_relogio_nao_joga_para_sempre`, `test_relogios_defasados_nao_podem_dar_dois_vencedores`, `test_relogios_defasados_nao_podem_dar_motivos_diferentes`. `notas-ui.md` documenta só o caso de desistir de propósito nos últimos 2 s.

#### QA11-14: "Copiar PGN" no meio da partida entrega o xeque no modo Partida
- **Onde:** `xadrez/ui/game_scene.py:819`.
- **Reprodução:** modo Partida, `1. e4 f6 2. d4 a6 3. Qh5+`, tecla C, colar em qualquer lugar.
- **Esperado:** nada que a tela escondeu.
- **Obtido:** o texto traz `Qh5+`. É o único caminho que encontrei para descobrir o xeque sem calcular. A seção 10 diz que o PGN guarda a notação completa, mas fala do que fica gravado, não de uma cópia no meio do jogo.
- **Correção:** com `hides_hints` e sem resultado, tirar as marcas do texto copiado, ou recusar a cópia até o fim.
- **Teste:** `test_copiar_pgn_no_meio_da_partida_nao_entrega_o_xeque`.

#### QA11-18: documentos da entrega param no RF16
- **Onde:** `docs/01-visao-e-requisitos.md`, `docs/07-plano-de-testes.md`, `docs/08-matriz-rastreabilidade.md`, `README.md`.
- **Reprodução:** procurar `RF17` a `RF24` nesses arquivos, e "CPU", "rede" e "conta" no README.
- **Esperado:** a mesma versão que roda.
- **Obtido:** nada disso aparece. RF17 a RF24 só estão em `docs/plans/2026-11-03-xadrez-design.md`. A banca que abrir a matriz vê um jogo sem CPU, sem rede e sem contas.
- **Correção:** levar RF17 a RF24, RNF08, RNF09, UC10 a UC15 e CT-70 a CT-135 para os três documentos, e citar a versão 1.1 no README.
- **Testes:** `test_documentos_da_entrega_cobrem_a_versao_1_1`, `test_readme_cita_o_que_a_versao_1_1_trouxe`. Pode já estar no plano do aluno: registro porque nada no repositório diz isso.

### Baixa

#### QA11-04: Esc, Esc no histórico deixa o foco em "Sair da conta"
- **Onde:** `xadrez/ui/menu_scene.py:214`. O foco na lista some, e `FocusGroup.set_widgets` (`widgets.py:383`) cai no primeiro controle.
- **Reprodução:** logado, abrir uma partida no histórico, Esc, Esc, Enter.
- **Esperado:** nada acontece, ou o foco fica nas abas.
- **Obtido:** o Enter desloga.
- **Correção:** em `_refresh_widgets_keeping_focus`, usar `self.tab_bar` quando o focado sair da tela.
- **Teste:** `test_esc_esc_enter_no_historico_nao_sai_da_conta`.

#### QA11-05: orçamento da CPU passa do que resta no relógio
- **Onde:** `xadrez/ui/cpu_player.py:60`.
- **Reprodução:** Blitz 3+2, CPU com 1 s: `search_budget(1.0, 2.0)` dá 1,54 s. O Hardcore usa tudo e perde no tempo.
- **Esperado:** o limite nunca passa do que resta.
- **Obtido:** derrota por tempo, em tempo real. Em jogo normal a CPU não deve chegar nisso: pela conta, não medida em partida, o relógio dela estabiliza em cerca de 12 s em Blitz 3+2. Daí a severidade baixa.
- **Correção:** `min(remaining * 0.5, ...)`.
- **Testes:** `test_orcamento_nunca_passa_do_que_resta`, `test_hardcore_com_pouco_tempo_e_incremento_nao_estoura_o_proprio_relogio`.

#### QA11-06: quem perdeu lê "A vitória é sua"
- **Onde:** `xadrez/ui/net_link.py:159` e `:165`. A frase é montada sem olhar quem venceu.
- **Reprodução:** desistir em rede. O outro fecha o jogo antes de acabar a animação de fim (0,9 s, ou 2,2 s no mate).
- **Esperado:** aviso neutro de que o outro saiu.
- **Obtido:** "O adversário saiu da partida. A vitória é sua." para quem acabou de perder.
- **Correção:** em `_on_peer_left`, só acrescentar a frase quando o `abandon` decidir a partida.
- **Teste:** `test_quem_perdeu_nao_le_que_venceu_quando_o_outro_sai_na_animacao_de_fim`.

#### QA11-07: desistências cruzadas dão dois perdedores
- **Onde:** `xadrez/ui/game_scene.py:732` e `net_link.py:131`.
- **Reprodução:** os dois desistem antes de a mensagem do outro chegar.
- **Esperado:** o mesmo resultado nos dois lados.
- **Obtido:** cada um grava a própria derrota e ignora o aviso do outro.
- **Correção:** ao receber `resign` com a própria desistência já feita, empatar ou fazer valer a de quem criou a sala, com a mesma regra nos dois lados.
- **Teste:** `test_desistencias_cruzadas_nao_podem_dar_dois_perdedores`.

#### QA11-08: lance cruzado com o fim dá FEN diferente
- **Onde:** `xadrez/ui/net_link.py:109`.
- **Reprodução:** brancas propõem empate e jogam. As pretas aceitam antes de receber o lance. Ou: brancas jogam, e as pretas desistem antes de receber.
- **Esperado:** mesmo FEN, como pede CT-95.
- **Obtido:** um lado tem um lance a mais no histórico e no PGN gravado. O resultado é o mesmo.
- **Correção:** levar o número do lance em `draw_answer` e `resign`, e quem tem lance a mais desfaz ou o outro aplica antes de encerrar.
- **Teste:** `test_lance_cruzado_com_o_fim_nao_pode_dar_fen_diferente` (2 casos).

#### QA11-10: fechar a janela em rede não grava a derrota de quem saiu
- **Onde:** `xadrez/ui/game_scene.py:812`. "Sair da sala" grava (`:794`), e `shutdown` não.
- **Reprodução:** logado, em rede, fechar a janela no meio da partida.
- **Esperado:** derrota no histórico, como em "Sair da sala".
- **Obtido:** o outro grava vitória, e quem saiu fica sem registro.
- **Correção:** em `shutdown`, com rede e sem resultado, chamar `engine.abandon` e `_save_result` antes de `leave`.
- **Teste:** `test_fechar_a_janela_em_rede_grava_a_derrota_de_quem_saiu`.

#### QA11-11: Virar durante o giro por turno não vira
- **Onde:** `xadrez/ui/board_view.py:237`. `_flip_yaw` só guarda a última virada, e `face` não o atualiza.
- **Reprodução:** 2 jogadores com giro ligado, jogar, apertar F com a câmera girando.
- **Esperado:** termina do lado oposto ao destino do giro.
- **Obtido:** termina no próprio destino do giro, como se F não tivesse sido apertado.
- **Correção:** guardar o destino em `Camera.orbit_to` e usá-lo em `flip`.
- **Teste:** `test_virar_durante_o_giro_por_turno_vai_para_o_lado_oposto`.

#### QA11-12: dois convidados entram com o mesmo nome
- **Onde:** `xadrez/ui/lobby_scene.py:71` e `:92`, com o padrão de `xadrez/ui/match.py:10`.
- **Reprodução:** duas máquinas como convidado, sem digitar nome.
- **Esperado:** dá para saber quem é quem.
- **Obtido:** "Vez de Jogador 1" nas duas telas e "Jogador 1 venceu" no fim, com o placar da série com dois "Jogador 1". É o cenário mais provável numa demonstração.
- **Correção:** a sala troca o nome de quem entra quando for igual, por exemplo com um "(2)", no `start`.
- **Teste:** `test_dois_convidados_nao_ficam_com_o_mesmo_nome`.

#### QA11-13: nome longo corta o texto da sala e o "aceitar" da revanche
- **Onde:** `xadrez/ui/lobby_scene.py:186` usa `theme.text`, sem caber. `xadrez/ui/game_over_scene.py:176` põe a ação no fim do rótulo.
- **Reprodução:** adversário com 16 "W". Conferido nas capturas em 800x600.
- **Esperado:** texto dentro do painel, e a ação à vista.
- **Obtido:** "WWWWWWWWWWWWWWWW entrou. C" cortado na borda da janela (832 + 571 > 1280 em 1280x720), e o botão "WWWWWWWWWWWWWWWW pedi...", sem dizer que aceita.
- **Correção:** `text_fit` na sala. No botão, "Aceitar revanche" e o nome em uma linha à parte.
- **Testes:** `test_nome_longo_nao_vaza_na_sala_antes_de_a_partida_comecar`, `test_botao_de_aceitar_revanche_mantem_a_acao_a_vista`.

#### QA11-15: quem abandona lê "Adversário desconectou"
- **Onde:** `xadrez/core/types.py:107`, gravado por `xadrez/ui/match_record.py:25`.
- **Reprodução:** "Sair da sala" no meio da partida e abrir o histórico.
- **Esperado:** algo como "Abandonou a partida".
- **Obtido:** a folha diz "Derrota contra Bia" e, logo abaixo, "Adversário desconectou", na conta de quem saiu.
- **Correção:** escolher o texto em `build_record` conforme o vencedor.
- **Teste:** `test_quem_abandona_nao_le_que_o_adversario_desconectou`.

#### QA11-16: nome gigante no arquivo trava a lista do histórico
- **Onde:** `xadrez/ui/theme.py:355` (`_ellipsize` chama `font.size` para cada comprimento) e `xadrez/data/history.py`, que não limita o tamanho.
- **Reprodução:** `opponent` com 20 mil caracteres, aba "Meu histórico".
- **Esperado:** quadro normal.
- **Obtido:** 9,18 s em um quadro, a cada quadro. Pelo código, o custo cresce com o quadrado do tamanho. Só com arquivo editado à mão.
- **Correção:** cortar o texto em `displayable` (100 caracteres) e fazer busca binária em `_ellipsize`.
- **Teste:** `test_nome_gigante_no_historico_nao_trava_a_lista`.

#### QA11-17: em 640x360, os formulários não cabem
- **Onde:** `xadrez/ui/arena_scene.py:159`, porque `_MIN_SPACING` esgota antes de caber.
- **Reprodução:** janela 640x360, criar conta com erro, ou menu em qualquer aba.
- **Esperado:** nada fora da janela nem um botão sobre o outro.
- **Obtido:** "Sair do jogo" sai da janela, e "Iniciar partida" cobre "Ver todos os controles". A partir de 640x480 está tudo certo.
- **Correção:** tamanho mínimo de janela, ou esconder as notas quando faltar altura.
- **Teste:** `test_formularios_na_menor_janela` (4 casos).

#### QA11-19: motivo da sala encerrada some em 0,9 s
- **Onde:** `xadrez/ui/net_link.py:126` e `:201`, e `game_scene.py:266`, que só passa o aviso de gravação para a tela de fim.
- **Reprodução:** o outro lado manda jogada ilegal.
- **Esperado:** a tela de fim explica.
- **Obtido:** "O adversário enviou uma jogada ilegal" dura 0,9 s, e depois só resta "Adversário desconectou".
- **Correção:** passar a mensagem para `GameOverScene.notices`, como já é feito com `_save_warning`.
- **Teste:** `test_motivo_da_sala_encerrada_chega_a_tela_de_fim`.

#### QA11-20: proposta de empate logo depois da recusa abre outra sobreposição
- **Onde:** `xadrez/ui/net_link.py:137`. Só barra a proposta enquanto a anterior está aberta.
- **Reprodução:** o outro lado propõe, você recusa, e ele propõe de novo sem nenhum lance no meio.
- **Esperado:** uma proposta por lance, como na regra do xadrez.
- **Obtido:** a sobreposição reabre na hora, com o seu relógio correndo. Uma cópia alterada do jogo, mandando sem parar, impede o outro de jogar até o tempo dele acabar. Em um jogo normal, é só um incômodo.
- **Correção:** em `_on_draw_offered`, ignorar a proposta até haver um lance novo depois da última recusa, e responder recusando.
- **Teste:** `test_proposta_recusada_nao_reabre_sem_um_lance_no_meio`.

## Sugestões, sem defeito

1. **Modo por jogador em rede.** Cada um escolhe o próprio modo (`test_cada_jogador_escolhe_o_proprio_modo` diz que é decisão), e a mensagem `start` não leva o modo. Quem joga em Partida pode enfrentar alguém com todas as dicas, sem saber. Vale ao menos mostrar o modo do outro.
2. **Sala sem segredo.** O código é só o IP escrito de outra forma, e o `hello` não o leva. Qualquer um na mesma rede que chegue primeiro à porta 50507 entra. Para banca, serve. Para rede de faculdade aberta, um número a mais no `hello` resolveria.
3. **Fugir da derrota contra a CPU.** "Voltar ao menu" e fechar a janela não gravam nada. Em rede, sair conta como derrota. Decisão consciente pelo texto da confirmação, mas as estatísticas ficam otimistas.
4. **Ajuda lista teclas que não valem.** R e T aparecem na ajuda contra a CPU e em rede, onde T não faz nada, e R não faz nada em rede.
5. **Hard responde mais rápido que Easy.** `_MINIMUM_THINK_SECONDS` cobre só Easy e Medium (0,5 s). O Hard respondeu em 0,18 a 0,23 s nas posições medidas. O comentário no código diz que jogada instantânea parece defeito.
6. **Soltar fora do tabuleiro desmarca, soltar fora da janela mantém a seleção.** Os testes atuais aceitam os dois, mas o jogador não tem como prever.
7. **Texto de erro com o caminho da pasta** (`storage.py`) mostra o nome do usuário do Windows na tela, se aparecer durante a apresentação.
8. **Limpeza:** `WARNING_ICON` (`theme.py:46`) não é usado por ninguém. `pyproject.toml:4` e `xadrez/__init__.py:1` ainda dizem "para 2 jogadores". O topo de `net/session.py` diz que nada ali bloqueia quem chama, mas `close()` espera a thread por até 2 s (na prática, um ciclo de 20 ms).

Na leitura do código não achei condição de corrida entre a thread e a tela: a busca trabalha em uma cópia do tabuleiro, a sessão só fala por duas filas `deque`, e a jogada só é lida com a thread já encerrada.

## O que resistiu

**Modo Partida, o pedido central.**
- Pixel a pixel, entre posições em que só o xeque muda (o peão bloqueia ou não): painel lateral idêntico, faixa idêntica e tabuleiro idêntico fora das casas do peão. O controle em Treinamento prova que o teste enxerga a diferença.
- Placas, etiqueta "Joga agora", tints, marcadores, matriz e F4: só seleção, cursor e último lance, em cada quadro, em 2 jogadores, contra a CPU e em rede.
- Recusa: "Lance inválido." em 6 motivos diferentes, sem tremor, e igual no arrasto. Peça cravada e peça livre desenham igual. O peão cravado na sétima não abre a promoção.
- A planilha esconde `+` e `#` até o fim. A revanche continua em Partida. Treinamento continua mostrando tudo.

**CPU.** Pausa, reiniciar, desistir, menu, fechar e tempo esgotado com ela pensando: nada chega depois, e nenhuma thread sobra. Busca cancelada que termina depois não vira lance da partida seguinte. Tempo acabando no quadro em que a busca termina: a jogada não entra. Roque, en passant, promoção e mate dela. CPU de brancas abrindo, inclusive na revanche. Posição sem lance para ela não abre thread. `setswitchinterval` volta em toda saída, inclusive com exceção. Clique, arrasto e teclado na vez dela não mudam nada. Mate em 1 nos 4 níveis, 8 em 8. Hardcore: 4,02 s por lance.

**Rede.**
- Socket cru: jogada ilegal, fora da vez, formato errado, JSON com 3000 `[`, bytes inválidos, `clock_ms` falso, 500 propostas de empate, `start` e `hello` fora de hora. Sala de atacante com início estranho, recusa inválida e silêncio.
- Nomes hostis (16 "W", só acentos combinantes, emoji, árabe, coreano, tentativa de sair do cabeçalho do PGN): não derrubam, e bidi e controle são recusados pelo protocolo.
- Queda na sala, na promoção, em sobreposição aberta, em voo e na tela de fim.
- Revanche e empate cruzados, regra do tempo esgotado de `notas-ui.md`, as 4 regras.
- Código em minúsculas e com espaços, código errado, Enter repetido no campo do código.
- **Porta presa não acontece:** reabre na hora em 127.0.0.1, nas 3 ordens de saída, mesmo com a conexão em TIME_WAIT.
- Nenhum dos 8 caminhos de saída deixa thread nem porta aberta.

**Contas e histórico.** Maiúsculas, acento, formas Unicode, espaços. Senha vazia, longa, com espaços, com acento e emoji. A senha não fica em widget nem em cache de texto em 6 caminhos, e a máscara desenha igual para senhas diferentes. 16 tipos de `accounts.json` corrompido. 31 campos de histórico adulterados, 14 tipos errados, 8 arquivos corrompidos. Pasta inválida e arquivo somente leitura viram aviso. Registro certo em cada fim, cor depois da revanche, duração, modo, 51ª partida, duas contas, convidado sem gravar, "Sair da conta".

**Arrastar, virar e copiar.** Soltar no painel, em botão, fora da janela, sem ter apertado. Tecla, botão direito, janela e F3, F4, F11 com a peça no ar. Na vez errada, em voo, com tempo esgotando e com o outro desistindo. Promoção, clique misturado com arrasto. PGN válido com aspas, barras e colchetes, refeito lance a lance. Área de transferência falhando. Clique duplo em cada tela nova.

**Macaco.** Passou por login, menu, histórico, sala, CPU nos 4 níveis, rede com um robô real em loopback e tela de fim, sem nenhuma falha do jogo. Os números estão na última seção.

**Telas.** Abri com Read as capturas em 800x600, 1024x640 e 1920x1080, com nomes longos: login, menu em cada opção, sala, histórico cheio e aberto, HUD com 3 e 4 fileiras, pausa, ajuda, promoção, fim em CPU e rede. Só achei o que está em QA11-13. Teste de geometria em 7 tamanhos.

**Segurança e privacidade.**
- Rede: só JSON, tipos conferidos, linha limitada, 2000 mensagens/s, 8 conexões à espera, fila de 1024 eventos, só endereços locais.
- Caminho do histórico é hash, então `../..` e `CON` não têm efeito.
- PBKDF2 com 600 mil iterações, sal próprio e comparação em tempo constante. Mensagem única no login, com a mesma demora para conta inexistente.
- **Varredura dos 16 termos pedidos em toda a cópia, nos PNG e no `git log`: nenhum resultado.** Abri também os PNG de `docs/img`: só "Jogador 1" e "Jogador 2", e o código da sala nas imagens é o de `127.0.0.1`. O usuário público do GitHub aparece nas URLs e no autor dos commits, com e-mail `noreply`: não está na lista pedida, então só registro.

**RF17 a RF24:** todos existem e foram exercitados por eventos (`test_cada_requisito_novo_existe_no_jogo` e os demais).

## Não verificado

- **Janela de verdade:** tudo rodou em SDL sem janela. Não vi arrasto com mouse real, F11 real, nem a cópia lida de volta por outro programa.
- **`0.0.0.0`, firewall e duas máquinas:** fora do limite pedido. A porta foi testada em `127.0.0.1`. O comportamento de `SO_EXCLUSIVEADDRUSE` com `0.0.0.0` não foi visto, e é o que a banca vai usar. "Entrar na própria sala" só existe com duas instâncias na mesma máquina, que é como rodam os testes de duas telas. Vale ensaiar isso na máquina da apresentação.
- **Executável:** não há `dist/` na cópia.
- **60 FPS reais (RNF09):** sem `display.flip`, só medi o trabalho do quadro. Média de 3 a 6 ms com Easy, Medium e Hardcore pensando, com p99 de até 36 ms. No Hard, a amostra é curta, com cerca de 10 quadros e média de 15 a 22 ms, incluindo a abertura da partida.
- **Permissão de pasta real:** simulei com caminho embaixo de um arquivo, arquivo no lugar da pasta e arquivo somente leitura. Não mexi em ACL.
- **Linux e macOS.**

## Testes novos e resultado

Arquivos em `tests/ataque/`: `test_ataque_v11_apoio.py` (só fixtures), `_partida`, `_cpu`, `_rede`, `_contas`, `_arrastar`, `_telas`, `_macaco` e `_documentos`. Casos CT-100 a CT-135, descritos no topo de cada arquivo.

São 476 testes novos: 460 na suíte normal (423 passam e 37 ficam em `xfail` estrito) e 16 do macaco longo, com `slow`. Rodei os 37 também com `--runxfail`, para confirmar que cada um falha pelo motivo descrito, e não por outro erro.

**Suíte inteira, sem `slow`, no estado final:** 3406 passaram (os 2983 de antes mais 423 novos), 1 pulado, 36 fora por `slow`, 37 `xfail`, em 11 min 34 s. Nenhuma falha. Dos testes `slow`, só rodei os 16 do macaco novo: os outros 20 do projeto não rodei.

**Macaco.**
- Curto (CT-130, 3 sementes, 5400 quadros): 44,6 s, sem falha.
- Longo, no estado final: **16 sementes de 6000 quadros, 96 mil no total, 16 passaram, em 12 min 56 s.** Foram 2250 lances jogados, 23555 quadros contra a CPU, 9106 em rede com o robô, 14206 no login, 1392 no histórico, 837 na sala e 1921 na tela de fim. Nenhuma exceção do jogo, nenhuma thread sobrando e nenhuma senha em cache.
- Na primeira rodada, a semente 206 caiu no quadro 5644, e o erro era do próprio teste: reiniciar e jogar no mesmo quadro deixava o histórico do mesmo tamanho, e o verificador não percebia a partida nova. Reduzi a isso e corrigi o verificador.
- Efeito colateral a saber: o macaco aperta F11, e o `set_mode` seguinte herda o tamanho da tela cheia. Só afeta quem cria um segundo `App` no mesmo processo, ou seja, os testes. O macaco agora fecha a janela ao terminar.
