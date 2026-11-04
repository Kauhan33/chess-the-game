# Relatório de QA: Chess - The Game

Ataque feito sobre a cópia congelada do commit `c5c150b`. Nenhum arquivo do jogo foi alterado. Tudo o que está aqui
foi reproduzido em execução real neste Windows 11, com Python 3.12.10, pygame 2.6.1, SDL 2.28.4 e numpy 2.5.3, com o
driver de vídeo `dummy`. O que não pude verificar está na seção 6.

## 0. Situação depois das correções

Todos os 19 defeitos abaixo foram corrigidos no commit `86de291`. Os testes que provavam cada defeito deixaram de ter a marca
`xfail` e passam a fazer parte da suíte normal. O relatório abaixo é o registro do que foi encontrado na versão auditada e
descreve essa versão, não a atual. As sugestões da seção 3 aplicadas nesse commit: o relógio de quem vai jogar só corre depois
do pouso da peça, o giro por turno sobrevive à revanche, o menu ganhou o botão Sair, F11 liga a tela cheia e `xadrez/__main__.py`
ganhou a proteção de importação. As demais continuam como sugestão.

Dois achados surgiram depois, ao trazer estes testes para o projeto com a documentação pronta: o PlantUML gravava o código-fonte
do diagrama nos metadados dos PNG (resolvido com `-nometadata`) e `tools/gerar_pdf.py` tinha caminho fixo de sistema (resolvido
lendo `ProgramFiles` do ambiente).

## 1. Resumo

| Severidade | Quantos | IDs |
|---|---|---|
| Bloqueante | 1 | QA-01 |
| Alta | 2 | QA-02, QA-03 |
| Média | 3 | QA-04, QA-05, QA-06 |
| Baixa | 13 | QA-07 a QA-19 |

- **O motor de regras resistiu a tudo o que foi jogado contra ele.** Nenhum defeito em jogada legal, xeque, mate, empate
  ou SAN. Os dois achados do motor (QA-14 e QA-15) só aparecem chamando a API com valores que a interface não produz.
- **Nenhuma queda no macaco.** Foram 136 mil quadros sem exceção. A única queda alcançável por um jogador é a do QA-01.
- **O ponto fraco é o clique.** Os testes atuais não veem esse problema porque `click_point` procura, entre cinco
  alturas, um pixel em que o clique acerte. Um jogador clica onde vê a peça, e aí os QA-02 e QA-03 aparecem.

Correção sugerida, nesta ordem: QA-01 (cai o jogo), QA-03 e QA-02 (a mesma correção resolve os dois, e o primeiro lance
de uma partida é atingido), QA-05, QA-04, QA-06.

## 2. Defeitos

Cada defeito aberto tem um teste com `xfail(strict=True)`. Quando o defeito for corrigido, o teste passa, o `strict`
acusa falha e é só retirar a marca.

### QA-01. Bloqueante. Caractere de largura zero no nome derruba o jogo

- **Onde:** `xadrez/ui/theme.py:209` (`font.render`), `xadrez/ui/theme.py:253` (`has_glyph`), `xadrez/ui/widgets.py:140` (filtro).
- **Reprodução mínima:** no menu, com o campo vazio, um único evento `TEXTINPUT` com `U+FE0F`.
  O painel de emojis do Windows (`Win+.`) insere esse caractere depois de muitos emojis. Com `U+1F336 U+FE0F`
  (pimenta), `U+1F5A5 U+FE0F` (monitor) ou `U+1F321 U+FE0F` (termômetro), o emoji é recusado, o seletor `U+FE0F` entra
  e o campo fica só com ele.
- **Esperado:** caractere recusado, e o menu segue.
- **Obtido:** `pygame.error: Text has zero width` em `TextInput._draw_content`, e o jogo fecha.
- **Alcance:** varredura de todo o Unicode com a fonte desta máquina. São 22 caracteres: `U+034F`, `U+17B4`, `U+17B5`,
  `U+180B` a `U+180D` e `U+FE00` a `U+FE0F`. Com outra letra antes (`A` + `U+FE0F`) não cai.
- **Correção:** em `Theme.text`, trocar o conteúdo por `" "` também quando `font.size(content)[0] == 0`. Em
  `TextInput.handle_text`, recusar caractere de largura zero.
- **Teste:** `test_ataque_nome_de_largura_zero_nao_derruba_o_menu`.

### QA-02. Alta. Clicar na cabeça de uma peça alta faz uma jogada que ninguém pediu

- **Onde:** `xadrez/ui/game_scene.py:259-263` (`pick_at`).
- **Causa:** com uma peça selecionada, se o chão sob o raio for um destino válido, ele vence a peça que o jogador está
  vendo. A cabeça de uma peça alta cobre a casa de trás na tela.
- **Reprodução 1 (clique duplo no rei):** depois de `1.e4 e5`, dois cliques no mesmo pixel da cabeça do rei em e1.
  O primeiro seleciona. O segundo joga `Ke2`, e o roque se perde.
- **Reprodução 2 (trocar a seleção):** na mesma posição, selecionar o cavalo g1 e clicar na cabeça do rei. A jogada `Ne2`
  é feita, em vez de a seleção passar para o rei.
- **Esperado:** clicar na peça selecionada desmarca, e clicar em outra peça própria troca a seleção.
- **Obtido, por altura do clique no eixo da peça:**

| Peça | Casa livre atrás | A partir de que altura o 2º clique joga | Jogada feita |
|---|---|---|---|
| Rei e1 | e2 | 70% | `Ke2` |
| Dama d1 | d2 | 85% | `Qd2` |
| Torre a1 | a2 | 95% | `Ra2` |
| Bispo c1 | d2 | não acontece até 95% | nenhuma |

- **Correção:** com o clique por silhueta do QA-03, a preferência pelo chão pode sair. Se ficar, peça própria sob o
  raio vence o chão.
- **Testes:** `test_ataque_clicar_de_novo_na_peca_alta_desmarca`, `test_ataque_clicar_em_outra_peca_propria_troca_a_selecao`.

### QA-03. Alta. O cilindro de clique cobre peças visíveis: o peão e2 quase não é clicável

- **Onde:** `xadrez/graphics/camera.py:28` (`_PIECE_PICK_RADIUS = 0.36`), `camera.py:205-246`.
- **Resposta à pergunta do brief:** sim, incomoda na prática, e é pior do que clique no chão. O cilindro tem raio 0,36
  em toda a altura, inclusive na cruz fina do rei. Ele toma o clique de uma peça que aparece inteira atrás dele.
- **Reprodução mínima:** na posição inicial, clicar no corpo do peão e2 (de 25% a 72% da altura dele).
- **Esperado:** seleciona e2.
- **Obtido:** seleciona o rei e1, com o aviso "Essa peça não tem jogada válida agora." É o primeiro clique de `1.e4`.
- **Medição, pixel a pixel, em 1280x720.** Cada peça foi desenhada com um código de cor na ordem do pintor, para saber o
  que o jogador vê em cada pixel:

| Peça na posição inicial, câmera das Brancas | Pixels em que aparece | Acionam outra casa |
|---|---|---|
| e2 | 1899 | 78% |
| d2 | 2075 | 42% |
| c2 e f2 | cerca de 2370 | 37% |
| c8 e f8 | cerca de 1880 | 34% a 35% |
| Tabuleiro inteiro | 83787 | 13,3% |

  Pelo lado das Pretas é igual: e7 chega a 79%. Além disso, 8,9% dos pixels de chão visível acionam uma peça (amostra de
  1 pixel a cada 2), e 11,5% em um meio-jogo. No zoom mínimo (distância 32), nenhuma das cinco alturas que `click_point`
  tenta acerta o e2.
- **Por que os testes não pegam:** `autoplay.click_point` tenta alturas até `pick_at` responder a casa certa.
- **Correção:** trocar o cilindro pela silhueta. A opção mais simples é testar o pixel contra as faces projetadas da
  malha, da peça mais próxima para a mais distante, só quando o mouse ou a câmera mudam. Outra é um raio por faixa de
  altura, tirado do perfil de cada peça.
- **Testes:** `test_ataque_primeiro_lance_clicando_no_corpo_do_peao_e2`, `test_ataque_pixel_que_mostra_uma_peca_aciona_essa_peca`,
  `test_ataque_pixel_que_mostra_o_chao_aciona_a_casa`.

### QA-04. Média. Clique duplo em "Propor empate" aceita o empate sozinho

- **Onde:** `xadrez/ui/game_scene.py:507-516`, posições em `xadrez/ui/overlays.py:105-118`.
- **Reprodução em 1280x720:** pausar e dar dois cliques em "Propor empate" na parte de cima do botão (y entre 379 e 395).
- **Esperado:** o pedido fica aberto, esperando o outro jogador.
- **Obtido:** o 2º clique cai em "Aceitar empate" (y de 352 a 395), e a partida acaba em empate por acordo. Com y de 405
  a 422, o 2º clique cai em "Recusar". Só a faixa de 396 a 404, o vão entre os botões, não faz nada.
- **Mesma causa:** "Reiniciar partida" com y de 365 a 369 reinicia direto (reproduzido). "Retomar" deixa o 2º clique cair
  no tabuleiro: com peça selecionada, a seleção se perde e aparece um aviso (reproduzido). Se o pixel for um destino
  válido, seria jogada; nas três seleções que testei, o pixel não caiu em destino, então esse último caso não foi observado.
  "Desistir" e "Voltar ao menu" resistiram.
- **Correção:** ignorar cliques nos primeiros 250 ms de uma sobreposição recém-aberta. Isso cobre todos os casos.
- **Teste:** `test_ataque_clique_duplo_em_propor_empate_nao_aceita_sozinho`.

### QA-05. Média. R durante o voo do mate pula a tela de vitória

- **Onde:** `xadrez/ui/game_scene.py:488-492`. `confirm_restart` só olha `_ending_left`, que ainda é `None` enquanto a peça voa.
- **Reprodução:** jogar até o mate do pastor, clicar em h5 e f7 e, nos 0,38 s do voo, apertar R e confirmar.
- **Esperado:** nada a reiniciar, e a partida segue para a vitória. É o que `open_pause` faz.
- **Obtido:** a pergunta "Reiniciar a partida?" abre com a partida já encerrada. Ao confirmar, o tabuleiro volta ao início,
  o vencedor fica com o ponto e a tela de vitória nunca aparece.
- **Correção:** `if self._ending_left is not None or self.engine.result is not None: return`.
- **Teste:** `test_ataque_reiniciar_no_voo_do_mate_nao_pula_a_vitoria`.

### QA-06. Média. `has_glyph` não detecta glifo ausente, e a documentação afirma o contrário

- **Onde:** `xadrez/ui/theme.py:253-256`. A afirmação falsa está na docstring e em `docs/plans/notas-ui.md:108`.
- **Causa:** `font.metrics` devolve as medidas do glifo de substituição, e não `None`, para qualquer caractere abaixo de
  `U+10000`. Só os acima disso são recusados, como o `U+1F600`.
- **Reprodução:** digitar `U+D55C U+AE00` (coreano), `U+4E2D U+6587` (chinês) ou árabe no campo de nome.
- **Esperado:** caractere recusado, como a docstring promete.
- **Obtido:** o nome entra e aparece na partida como uma fila do mesmo ornamento. Dos 55.508 caracteres imprimíveis do plano
  básico, todos são aceitos, e 54.375 saem iguais ao glifo de substituição da Palatino Linotype.
- **Correção:** comparar o desenho do caractere com o de um caractere que a fonte não tem, com cache por caractere.
- **Teste:** `test_ataque_campo_recusa_caractere_que_a_fonte_nao_desenha`.

### Defeitos de severidade baixa

Reproduzidos, mas pouco prováveis em uma banca ou só alcançáveis pela API.

| ID | Onde | Reprodução mínima | Esperado | Obtido | Correção |
|---|---|---|---|---|---|
| QA-07 | `game_over_scene.py:76` | Dois Enter ou dois cliques em Revanche no mesmo quadro | Cores trocadas uma vez | `rematch` roda duas vezes e as cores não trocam. Em quadros seguidos, resiste | Sair se `next_scene` já existir |
| QA-08 | `app.py:114` | Clique em Iniciar e `VIDEORESIZE` no mesmo quadro | Cena nova no tamanho novo | `app.size` 800x600 com o painel em x = 960, fora da janela, até o próximo redimensionamento | `self.scene.resize(self.size)` ao trocar de cena |
| QA-09 | `overlays.py:54`, `menu_scene.py:112` | No menu, F1, depois H (`KEYDOWN` + `TEXTINPUT`) | Ajuda fecha | Ajuda fecha e o campo recebe "h" | Tirar H das teclas de fechar no menu, ou ignorar o texto da mesma tecla |
| QA-10 | `hud.py:165-180` | "Sem limite" com 1 h de jogo: relógio `1:02:05` | Relógio e etiqueta sem se tocar | O relógio invade "Joga agora". Com 10 h, cobre também "decorrido" | Reduzir a fonte do relógio acima de 1 h |
| QA-11 | `hud.py:319` | FEN com as Pretas primeiro, e um lance | Lance na coluna Pretas | Lance na coluna Brancas. Só alcançável por FEN: o menu não tem FEN | Deslocar uma coluna, guardando quem começou |
| QA-12 | `app.py:80` | `App.step(float("nan"))` | Quadro tratado como dt 0 | `ValueError` na partida e `TypeError` no menu. `min`/`max` deixam NaN passar. O `FramePacer` não gera NaN | `if not dt > 0: dt = 0.0` |
| QA-13 | `board_view.py:236` | `MOUSEWHEEL` com y = -1000000 | Zoom no limite | `OverflowError` em `0.92**n`. Com +-500 resiste. Nenhum mouse real gera isso | Limitar os passos antes da potência |
| QA-14 | `clock.py:60-61` | `GameEngine().tick(math.inf)` | Sem limite nunca esgota | Partida encerrada por tempo. O `App` limita o dt, então só pela API | Recusar dt não finito |
| QA-15 | `engine.py:54-55` | FEN já encerrada e `restart()` | Sem pontos novos | Soma 0,5 a cada chamada. Só por FEN | Não pontuar partida sem lances |
| QA-16 | `board_view.py:216` | Zoom, V e jogada que pousa antes de 0,6 s | Zoom volta a 16,5 | `face` cancela a volta e o zoom fica em 15,94 | Manter inclinação e zoom da volta ao girar |
| QA-17 | `game_scene.py:546-551` | T na queda do rei | Aviso de vitória fica | "Xeque-mate! Ana venceu." vira "Giro por turno ligado." e a câmera gira para o lado do perdedor | Ignorar T com `_ending_left` ativo |
| QA-18 | `widgets.py:64-77`, `game_scene.py:196` | Apertar um botão do HUD, abrir a ajuda por tecla e soltar | Botão solto | `is_pressed` e `is_hovered` ficam presos e o botão aparece aceso. Depois, soltar sobre ele sem ter apertado abre a pausa | Limpar os estados em `_push_modal` |
| QA-19 | `game_scene.py:502`, `:511` | Nome com 16 "W", confirmação de empate ou de desistência | Título diz a ação | "WWWWWWWWWWWWWWWW pr..." corta justamente a ação | Título fixo, com o nome na linha de baixo |

## 3. Sugestões, que não são defeitos

**Interface e regras do jogo**

- `App.run` não tem proteção contra exceção. Com ela, um defeito como o QA-01 não fecharia a janela na frente da banca.
- O relógio de quem vai jogar corre 0,383 s por lance durante o voo, com o tabuleiro bloqueado (medido). Em uma blitz de
  40 lances são cerca de 15 s. Dá para começar a contar no pouso ou liberar o clique no voo.
- T durante a partida não sobrevive à revanche: desligado na partida, volta ligado, porque `MatchOptions` guarda a opção do
  menu. Vale decidir qual é o comportamento certo.
- No zoom máximo (distância 9), os quatro cantos do tabuleiro saem da tela: a1 fica em (-220, 752) e h8 em (904, -71). V
  resolve, mas um limite de zoom menos fechado evita o susto.
- O menu não tem "Sair", e Esc não faz nada nele. A saída é só pelo X da janela. Também não há tela cheia, que ajudaria no projetor.
- Dois jogadores com o mesmo nome são aceitos: "Ana propõe empate" e "Ana, você aceita?".

**Código**

- Sem uso em produção: `theme.WARNING_ICON`, `theme.WALNUT` (só testes), `mesh.extrude` (só testes), `Vector2D.reflect`,
  `Vector3D.reflect`, `Vector3D.rotated`, `Vector3D.lerp`.
- `Overlay.update` é um gancho vazio, sem ninguém que o sobrescreva, e `GameScene.update` percorre as sobreposições para chamá-lo.
- `Hud.layout` devolve um valor que ninguém usa. `drawing.py:107` tem `radius // 1`, e `max(stem, 1)` repete o que `stem` já garante.
- Constantes repetidas: `_CONFIRM_KEYS` em `game_scene.py` e `widgets.py`, `_FILE_NAMES` de `debug_panels.py`, igual a
  `FILE_NAMES` do motor, e `_GLOW_MARGIN` e `_GLOW_PEAK_ALPHA` em `hud.py` e `game_over_scene.py`.
- `xadrez/__main__.py` roda `App().run()` sem `if __name__ == "__main__"`: importar o módulo abre o jogo.

**Docstrings que não contam tudo**

- `game_over_scene.py:1-5` diz que o tabuleiro não muda de tamanho na troca de tela. Com F4 aberto, muda: o viewport vai de
  (326, 0, 634, 720) para (0, 0, 960, 720).
- `overlays.py:44` diz que Esc cancela a seleção. Sem seleção, ele abre a pausa.
- O desenho de `pick_at` em `docs/plans/2026-11-03-xadrez-design.md` defende a preferência pelo chão, que é a causa do QA-02.

**Projeto**

- O comando do `CLAUDE.md` (`python -m pytest`) inclui os testes lentos. Só os meus somam cerca de 25 min. Para o dia a dia,
  use `-m "not slow"`, como a CI já faz.
- A tabela de CT em `docs/plans/2026-11-03-xadrez-design.md` precisa ganhar CT-50 a CT-67 (seção 5).
- `.github/workflows/testes.yml` pode declarar `permissions: contents: read`.

## 4. O que resistiu

**Regras, com um gerador de lances e um detector de ataque independentes, escritos por mim, sem usar o motor.**

Rodadas em `test_ataque_regras.py` (CT-50), com semente fixa. A versão curta roda na suíte normal e a longa leva a marca `slow`. O resultado real está na seção 7.4 do plano de testes.

A cada posição foram conferidos: um rei por cor, nenhum peão na 1ª ou 8ª, conjunto de lances legais igual ao do modelo,
rei de quem não joga fora de xeque, FEN de ida e volta, `apply` e `undo` restaurando o tabuleiro inteiro para todas as
jogadas, direitos de roque que nunca voltam, relógio de meio-lance, `threatened_pieces` contra força bruta, SAN apontando
uma única jogada legal, sufixo `+`/`#` correto e resultado de fim de jogo igual à dedução independente.

Bordas que passaram: promoção com captura, xeque e mate no mesmo lance; promoção com peça inválida; peão cravado; en passant
que expõe o rei na fileira e na diagonal; en passant como única defesa; en passant que não resolve o xeque; janela do en
passant; roque com torre capturada e outra torre na casa original; torre que sai e volta; casas atacadas no caminho e na
chegada; mate, afogamento e repetição no lance dos 50; captura e peão no lance 100; FEN que já nasce encerrada; repetição
com direito de roque perdido; en passant legal e ilegal na repetição; material insuficiente por captura, por en passant e
por promoção subpotente, inclusive bispos de mesma cor e de cores diferentes; tempo contra rei só; tempo exato; dt 0,
negativo e NaN no motor; desistir na pausa; pontos que não contam duas vezes; `restart` no meio; revanche sete vezes; FEN
com as Pretas primeiro no motor; 13 formatos de entrada absurda em `play`; 29 FEN malformadas.

**Interface, por eventos reais no `App.step`.**

- **Macaco:** 136 mil quadros sem exceção nem quebra de invariante: 75 mil em 15 sementes, 40 mil em 10 sementes com fins de
  partida forçados e mais de 1.400 redimensionamentos, e 21 mil nas primeiras rodadas. Cliques em tudo, botão direito
  arrastando, roda, todas as teclas pedidas, texto com acentos, controle, emoji e colagem de 5.000 caracteres, janelas de
  1x1, 50x2000, 3000x200 e 2x900, dt 0, negativo e 1e9. Invariantes: histórico legal refeito em tabuleiro próprio; tabuleiro
  e relógio parados com sobreposição que congela; pausa do motor igual à da tela; seleção coerente; uma cena ativa; caches e
  partículas no limite.
- **Roteiros:** tempo acabando com o diálogo de promoção aberto; lance e tempo no mesmo quadro (vale o lance); clique depois
  do tempo (não joga); pausa durante o voo; redimensionar durante voo e giro; atalhos durante a queda do rei; T, V e arraste
  durante o giro; reiniciar durante a captura, sem peça fantasma; Esc em cada estado; ajuda durante o voo do mate; zoom nos
  dois extremos; F4 e F3 em oito tamanhos de janela, até 1x1; menu, partida, fim, revanche, fim, menu e partida, com nomes e
  opções certos; 16 "W" ou "Ç" e nome só de espaços; desistir com as Pretas em cima da hora; revanche e menu com clique
  duplo em quadros seguidos.
- **Vazamento:** teste CT-64, em `test_ataque_interface.py`. O resultado real está na seção 7.4 do plano de testes.
- **Telas:** olhei 25 imagens: menu, partida, xeque, pausa, pedido de empate, ajuda, modo didático, promoção e vitória, com
  nomes de 16 "W" e "Ç", em 400x300, 640x360, 800x500, 1280x720 e 1920x1080, mais capturas cheias e planilha com 30 linhas. Fora
  os achados QA-10, QA-11 e QA-19, nada cortado ou sobreposto. `tools/capturar_telas.py` regerou 11 das 12 imagens de `docs/img`
  idênticas pixel a pixel. A `tela_desempenho`, medida em tempo real, difere em 268 pixels, só no painel de FPS.

**Código e enunciado.**

- `Vector2D` tem uso real: interpolação do voo e direção da queda em `animation.py`, marcadores em `renderer.py`, contorno do
  cavalo em `models.py`. `Vector3D` é usado na câmera, no raio de clique e na luz.
- Enunciado, seções 1 e 2, Grupo 09, conferido no jogo:

| Exigência | Situação | Onde |
|---|---|---|
| 2 jogadores em turnos bem definidos | Atende | placa acesa, "Joga agora", faixa de vez, câmera |
| Tabuleiro 8x8, movimento estrito, xeque e xeque-mate | Atende | `xadrez/core`, testes CT-50 a CT-56 |
| Modelos low-poly | Atende | `graphics/models.py` |
| Matriz de cores de caminhos válidos | Atende | `color_matrix.py`, estados PATH e CAPTURE |
| Feedback visual de peça sob ameaça | Atende, para as peças de quem joga | triângulo, tint e estado THREAT |
| Coordenadas de tela e mundo, matrizes, vetores | Atende | `camera.py`, `matrix.py`, `vector.py` |
| Colisão 2D/3D | Atende | caminho das peças, raio contra cilindro, piso das partículas |
| Polígonos, malhas, cores, luz, partículas | Atende | `renderer.py`, `lighting.py`, `particles.py` |
| Framerate controlado | Atende | `frame_pacer.py` |
| Menu com identificação e modo | Atende | nomes, tempo, câmera, controles |
| HUD com pontuação, vez, cronômetro e área jogável | Atende | `hud.py` |
| Fim de jogo com revanche e menu | Atende | `game_over_scene.py` |

Nenhuma lacuna de jogo que custe ponto. As seções 3 e 4 (UML, Kanban, PDF, README) são da frente de documentação e não estão
na cópia congelada. O `README.md` já existe na raiz do projeto original, mas não li o conteúdo.

**Segurança e privacidade.**

- Sem rede, sem `eval`, `exec`, `subprocess` ou `pickle`, e nenhuma escrita em disco dentro de `xadrez/`. Só escrevem
  `tools/capturar_telas.py` e `--ct-report`, onde se pede.
- Varredura dos 11 termos do brief, sem diferenciar maiúsculas: nenhuma ocorrência em arquivos de texto, em binários e PNG,
  nas mensagens e na autoria dos commits, nem em todos os objetos do git. Os PNG não têm pedaços de metadados.
- Autoria de todos os commits: `Kauhan33`, com e-mail noreply. O teste não lista os termos, para não publicá-los.

**Compatibilidade.**

- Os 88 módulos, contando os testes novos, passam em `ast.parse(feature_version=(3, 10))`, sem biblioteca padrão nova nem API do 3.11 em diante.
- O único trecho específico de Windows é o `windll` de `app.py`, protegido por `sys.platform` e `try`. Não há caminho fixo.
- `xadrez.core` roda sozinho no Python 3.13.15 sem pygame nem numpy: perft 4 da posição inicial deu 197281, e perft 3 da
  Kiwipete deu 97862, os valores de referência.

## 5. Testes novos

Em `tests/ataque/`, determinísticos, com semente fixa e sem tempo real.

| CT | Foco | Arquivo |
|---|---|---|
| CT-50 | Partidas aleatórias contra gerador e detector independentes | `test_ataque_regras.py` |
| CT-51 | Bordas de promoção, en passant e roque | `test_ataque_regras.py` |
| CT-52 | Precedência entre fins de jogo no mesmo lance | `test_ataque_regras.py` |
| CT-53 | Tripla repetição, roque perdido e en passant | `test_ataque_regras.py` |
| CT-54 | Material insuficiente por captura e promoção subpotente | `test_ataque_regras.py` |
| CT-55 | Relógio, desistência, série, revanche, FEN com Pretas primeiro | `test_ataque_regras.py` |
| CT-56 | Entradas absurdas e FEN malformadas | `test_ataque_regras.py` |
| CT-57 | Macaco com invariantes | `test_ataque_macaco.py` |
| CT-58 | Corridas entre relógio, voo, pausa, promoção e fim | `test_ataque_interface.py` |
| CT-59 | Clique: o que se vê é o que se aciona | `test_ataque_interface.py` |
| CT-60 | Clique duplo e eventos no mesmo quadro | `test_ataque_interface.py` |
| CT-61 | Nomes: caracteres perigosos, largura e ajuda | `test_ataque_interface.py` |
| CT-62 | Janelas e números extremos | `test_ataque_interface.py` |
| CT-63 | Fim de jogo, revanche, menu e HUD | `test_ataque_interface.py` |
| CT-64 | Vazamento | `test_ataque_interface.py` |
| CT-65 | Sem rede, sem execução dinâmica, sem escrita | `test_ataque_seguranca.py` |
| CT-66 | PNG, autoria, e-mails e caminhos pessoais | `test_ataque_seguranca.py` |
| CT-67 | Python 3.10 e portabilidade | `test_ataque_seguranca.py` |

Conferi com `--runxfail` que cada teste `xfail` falha pelo motivo do achado, e não por erro do próprio teste. O macaco não recebe
NaN, roda gigante nem caracteres de largura zero, porque cairia no QA-01, QA-12 ou QA-13 antes de atacar o resto. Depois de
corrigir esses três, vale acrescentá-los às listas `TEXTS` e `DTS`.

O resultado real da suíte inteira está na seção 7.2 do plano de testes.

## 6. O que não foi verificado

- **Janela real.** Tudo rodou com o driver `dummy`. Não verifiquei redimensionar arrastando a borda, DPI, foco, FPS real nem
  projetor com resolução menor que 1280x720.
- **Caminho real do emoji e do IME.** O QA-01 e o QA-09 foram reproduzidos com os eventos que o SDL entrega. Não abri o
  painel `Win+.` em janela de verdade.
- **Outras versões de Python com pygame.** Não há Python 3.10 nesta máquina, e o 3.13 e o 3.12 globais não têm pygame. A suíte só
  rodou no 3.12 do `.venv`. Do 3.13, só o núcleo, por script, sem pytest.
- **Linux e macOS.** Só revisão de código. A CI em `.github/workflows/testes.yml` nunca rodou nesta cópia.
- **Versões mínimas** de `requirements.txt` (`pygame 2.5`, `numpy 1.24`).
- **Fontes.** Os números do QA-01 e do QA-06 são da Palatino Linotype desta máquina. Em outra fonte, a lista pode mudar.
- **Documentos criados depois do congelamento** em `docs/` e `README.md` do projeto original: a varredura de dados pessoais não os
  cobriu, porque estão fora da cópia. Vale repetir nessa pasta antes de publicar.
