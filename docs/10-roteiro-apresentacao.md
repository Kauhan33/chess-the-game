# 10. Roteiro da apresentação

O enunciado dá de 12 a 15 minutos por grupo: 10 minutos de apresentação e demonstração, mais 5 de arguição. Todos os integrantes precisam falar, e o jogo precisa rodar na hora, com uma partida curta entre os dois jogadores e as telas de vitória ou derrota.

## 10.1 Divisão da fala

O grupo tem 3 integrantes, e a fala fica dividida em partes parecidas. Os tempos somam 8 min 40 s. A folga de 1 min 20 s é para não estourar os 10 minutos.

| Quem | Slides | Assunto | Tempo |
|---|---|---|---|
| Integrante 1 | Capa, O que construímos, Como provamos as regras, Três camadas, Casos de uso, Classes | Escopo, regras, arquitetura e UML | 2 min 40 s |
| Integrante 2 | O pipeline, Malhas, Do pixel à peça, Matriz de cores, Vetores em movimento | Matrizes, malhas, luz, clique, matriz de cores e partículas | 2 min 45 s |
| Integrante 3 | 60 FPS, Testes, Agora ao vivo, Perguntas | Framerate, qualidade e demonstração | 3 min 15 s |

## 10.2 Antes de a banca começar

1. Abra o jogo pelo `ChessTheGame.exe` e confirme que ele chega ao menu. Se a máquina tiver Python, teste também `python main.py`.
2. Conecte o projetor e aperte F11 para a tela cheia.
3. Deixe o menu aberto com os nomes já digitados e o tempo em 5 minutos.
4. Deixe `tools/demo_automatica.py` à mão, se a máquina tiver Python: é o plano B, porque joga sozinho.
5. Deixe o PDF unificado aberto em outra janela, para mostrar um diagrama se perguntarem.

## 10.3 Demonstração, em cerca de 2 min 20 s

Os Integrantes 1 e 2 jogam, e o Integrante 3 narra. A planilha do jogo usa a notação internacional: Q é dama, N é cavalo, B é bispo.

| Lance | Quem clica | O que narrar |
|---|---|---|
| 1. e4 | Brancas | Selecionar o peão mostra os caminhos em verde, com ponto. A peça voa em arco. |
| 1... e5 | Pretas | A câmera girou para o lado de quem joga. Só a matriz V mudou. |
| 2. Bc4 | Brancas | Antes de jogar, clique em uma peça preta: aparece "Essa peça é do adversário." e ela treme. |
| 2... Nc6 | Pretas | Aperte F4: a matriz de visão e a matriz de estados aparecem em números. |
| 3. Qh5 | Brancas | O peão preto em f7 fica destacado como ameaça, em laranja e pulsando. |
| 3... Nf6 | Pretas | Selecionar uma peça mostra as capturas em vermelho, com anel. Feche o F4. |
| 4. Qxf7# | Brancas | Faíscas quicando no piso, rei tombando e fogos. |
| Fim | Qualquer um | Tela de vitória com placar. "Revanche com cores trocadas" mantém o placar da série. |

## 10.4 Perguntas prováveis

Cada integrante responde pela parte que apresentou. As fórmulas completas estão no capítulo 6.

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
