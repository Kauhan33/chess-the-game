# 11. Guia de estudo para a banca

A rubrica avalia o domínio do código pelos integrantes. Na arguição, cada um precisa explicar a sua parte sem ler. Este guia diz o que ler, em que ordem, e traz experimentos para ver cada conceito acontecer. O tempo de estudo sugerido é de cerca de 1 hora por pessoa, mais o ensaio.

## 11.1 Mapa do código

| Camada | Linhas | O que tem |
|---|---|---|
| `xadrez/core/` | cerca de 1400 | As regras. Python puro. |
| `xadrez/graphics/` | cerca de 2750 | Matrizes, câmera, malhas, luz, partículas, animação e desenho. |
| `xadrez/ui/` | cerca de 3650 | Telas, HUD, entrada, relógio de quadros. |

Ninguém precisa decorar tudo. Basta saber o caminho de uma jogada e de um vértice, e onde cada coisa está. `xadrez/graphics/renderer.py` é o maior arquivo: leia o começo e `flush`, sem tentar acompanhar cada cache.

## 11.2 Trilha do Integrante 1: regras, arquitetura e UML

Leia nesta ordem:

1. `xadrez/core/types.py` e `xadrez/core/move.py`: casas, cores, peças e jogadas.
2. `xadrez/core/pieces.py`: `SlidingPiece.attacks`, o laço da colisão de caminho. Depois `Pawn`, a peça mais trabalhosa.
3. `xadrez/core/board.py`: `apply` e `undo`.
4. `xadrez/core/rules.py`: `legal_moves` e `leaves_king_in_check`, o coração da validação de xeque.
5. `xadrez/core/engine.py`: `play`, do começo ao fim, e `_detect_board_result`.
6. `tests/core/test_core_perft.py`.
7. Capítulos 3, 4 e 5 da documentação.

Precisa explicar sem ler:

- O que acontece, passo a passo, quando alguém joga um lance, até o motor responder.
- Por que uma peça não atravessa a outra, apontando a linha.
- Como o motor descobre que uma jogada deixaria o próprio rei em xeque.
- O que é perft e por que ele é uma prova forte.
- Por que `core` não importa pygame, e que teste garante isso.
- A diferença entre herança e composição, com exemplos do diagrama.

## 11.3 Trilha do Integrante 2: computação gráfica

Leia nesta ordem, com o capítulo 6 aberto ao lado:

1. `xadrez/graphics/matrix.py`: `translation`, `rotation_y`, `compose`, `look_at`, `perspective` e `planar_shadow`.
2. `xadrez/graphics/camera.py`: `project`, `screen_ray` e `pick_piece`.
3. `xadrez/graphics/mesh.py` e `xadrez/graphics/models.py`: `lathe` e os perfis das peças.
4. `xadrez/graphics/lighting.py`: `shade`, com a fórmula de Lambert.
5. `xadrez/graphics/color_matrix.py`: `ColorMatrix.rgb`.
6. `xadrez/graphics/particles.py`: `update` e `_bounce_on_floor`.
7. `xadrez/graphics/animation.py`: `PieceAnimation` e `KingFallAnimation`.

Precisa explicar sem ler:

- O caminho de um vértice até o pixel, nomeando cada matriz.
- Para que serve a coordenada homogênea, e por que se divide por w.
- Por que a ordem das matrizes importa, usando o rei que tomba como exemplo.
- Como o clique vira uma casa, e por que só o cilindro não bastava.
- A fórmula de Lambert, e por que as faces têm uma cor só.
- A reflexão da partícula no piso, e o que é a restituição.
- A ordem do pintor, e quando ela erraria.

## 11.4 Trilha do Integrante 3: interface, framerate e qualidade

Leia nesta ordem:

1. `xadrez/ui/app.py`: `step` e `run_frame`, o laço do jogo.
2. `xadrez/ui/frame_pacer.py`: o arquivo inteiro. É curto.
3. `xadrez/ui/game_scene.py`: `handle_event`, `_activate_square` e `_advance_world`.
4. `xadrez/ui/board_view.py`: `start_move` e `pick`.
5. `xadrez/ui/autoplay.py`: como os testes jogam por eventos reais.
6. `tests/ui/test_ui_partida_completa.py`.
7. Capítulo 7 da documentação e `docs/testes/relatorio-qa.md`.

Precisa explicar sem ler:

- O que acontece em um quadro, do evento ao desenho.
- Por que `Clock.tick(60)` dava 59,1 FPS, e como o `FramePacer` resolve.
- Por que a animação dura o mesmo tempo mesmo com outro FPS.
- Como um teste joga uma partida inteira sem janela.
- Por que o "Resultado Obtido" não é digitado à mão.
- Dois defeitos que a auditoria achou e como foram corrigidos, e o defeito das sombras que só o CI do macOS revelou.

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

Para ver a matriz de visão mudar sem alterar nada: abra o jogo, aperte F4 e arraste na horizontal com o botão direito. Só a 1ª e a 3ª colunas das três primeiras linhas mudam. A coluna do meio e a translação ficam iguais, porque a câmera gira em torno do eixo y, sem mudar a distância. Saber explicar isso é um ótimo sinal de que a matriz está entendida.

## 11.6 Ensaio

1. **Troca de papéis:** cada integrante explica, em 2 minutos, a parte de outro. Quem conseguir explicar a parte dos outros responde bem a qualquer pergunta.
2. **Passagem com relógio:** apresente tudo uma vez cronometrando. A meta é ficar abaixo de 10 minutos, com a partida ao vivo incluída.
3. **Arguição simulada:** um integrante faz as perguntas da seção 10.4, e quem responde não pode olhar o código, só mostrar no jogo.
4. **Ensaio de falha:** feche o jogo no meio da apresentação e reabra pelo `.exe`, para treinar o plano B.
