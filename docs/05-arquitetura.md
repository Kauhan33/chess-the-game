# 5. Arquitetura

## 5.1 Camadas

```
xadrez/
├── core/       regras do jogo. Python puro: sem pygame, sem numpy.
├── graphics/   computação gráfica. numpy + pygame. Não conhece as regras.
└── ui/         cenas, HUD e entrada. Liga core e graphics.
```

| Camada | Responsabilidade | Arquivos principais |
|---|---|---|
| `xadrez/core` | Posição, peças, legalidade, fim de jogo, relógio e pontuação | `engine.py`, `board.py`, `pieces.py`, `rules.py`, `notation.py`, `clock.py`, `player.py`, `move.py`, `types.py` |
| `xadrez/graphics` | Vetores, matrizes, câmera, malhas, luz, sombra, partículas, animação e desenho | `vector.py`, `matrix.py`, `camera.py`, `mesh.py`, `models.py`, `lighting.py`, `color_matrix.py`, `animation.py`, `particles.py`, `renderer.py`, `board_model.py`, `backdrop.py` |
| `xadrez/ui` | Janela, laço principal, telas, HUD, entrada e tradução entre as outras duas | `app.py`, `frame_pacer.py`, `scene.py`, `menu_scene.py`, `game_scene.py`, `game_over_scene.py`, `board_view.py`, `hud.py`, `overlays.py`, `widgets.py`, `debug_panels.py`, `theme.py`, `drawing.py`, `match.py`, `autoplay.py` |

## 5.2 Regra de dependência

`ui` importa `core` e `graphics`. `core` e `graphics` nunca se importam entre si. O teste `tests/test_arquitetura.py` lê os imports de cada arquivo e falha se a regra for quebrada.

Como `graphics` não conhece o motor, a `ui` traduz os tipos: a casa vira `(file, rank)` e o tipo de peça vira texto, como `"pawn"`. Essa tradução acontece em `BoardView`.

Consequências práticas:

- os testes do motor rodam sem abrir janela e sem pygame;
- o perft testa as regras em milhões de posições, sem nenhum custo de desenho;
- o pipeline gráfico pode ser testado com cenas artificiais, sem uma partida de verdade.

## 5.3 Fluxo de um quadro

`App.step(dt)` faz um quadro completo:

1. entrega os eventos à cena atual;
2. confere se o tamanho da janela mudou;
3. chama `scene.update(dt)`, com o `dt` limitado a 0,1 s;
4. faz a troca de cena, se a cena pediu;
5. chama `scene.draw(screen)`.

`App.run_frame` acrescenta a espera do `FramePacer` e o `display.flip`. Separar os dois permite que testes e ferramentas rodem `step` com tempo fixo, sem janela e sem relógio real.

## 5.4 Decisões e motivos

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

## 5.5 Convenções

- **Casa:** `file` 0 a 7 são as colunas a a h, e `rank` 0 a 7 são as fileiras 1 a 8. A casa é escura quando `(file + rank) % 2 == 0`.
- **Mundo:** y para cima, tabuleiro no plano y = 0, cada casa mede 1 unidade. O centro da casa é `x = file - 3.5` e `z = 3.5 - rank`. As brancas ficam em z positivo.
- **Câmera:** `yaw = 0` olha pelo lado das brancas, e `yaw = pi`, pelo das pretas.
- **Matrizes:** numpy `(4, 4)`, com vetor coluna: `p' = M @ p`.
- **Idioma:** identificadores em inglês, alinhados aos nomes do enunciado. Comentários, telas e documentos em português.

## 5.6 Testes como parte da arquitetura

Cada teste ligado a um caso formal leva `@pytest.mark.ct("CT-xx")`. A opção `--ct-report`, definida em `tests/conftest.py`, grava o resultado real em JSON. `tools/relatorio_testes.py` junta esse resultado às especificações e gera o capítulo 7 e o capítulo 8. Assim, "Resultado Obtido" nunca é digitado à mão.

`Autoplayer`, em `xadrez/ui/autoplay.py`, joga por eventos reais de mouse e teclado. É usado pelos testes de interface, pela captura de telas, pelo benchmark e pela demonstração automática.
