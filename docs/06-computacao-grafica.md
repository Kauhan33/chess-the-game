# 6. Computação gráfica

Este capítulo serve de roteiro para a defesa oral. Para cada conceito da ementa, traz a ideia em uma frase, a fórmula, o arquivo e a função onde ela está e como mostrar no jogo rodando. As teclas que mais ajudam são F3 (desempenho) e F4 (modo didático). O botão direito arrastando orbita a câmera.

## 6.1 O caminho de um vértice

Todo ponto de uma peça passa pela mesma sequência:

```
Modelo -> Mundo -> Visão -> Recorte -> NDC -> Tela
```

| Etapa | O que acontece | Onde está |
|---|---|---|
| Modelo para Mundo | A matriz-modelo põe a peça na casa | `piece_matrix` em `xadrez/graphics/matrix.py`, `_build_geometry` em `xadrez/graphics/renderer.py` |
| Mundo para Visão | O mundo é levado para a base da câmera | `look_at` em `xadrez/graphics/matrix.py` |
| Visão para Recorte | A projeção prepara a perspectiva | `perspective` em `xadrez/graphics/matrix.py` |
| Recorte para NDC | Divide-se por w, e o que está longe encolhe | `_visible_polygons` em `xadrez/graphics/renderer.py` |
| NDC para Tela | Vira pixel | `viewport` em `xadrez/graphics/matrix.py` |

## 6.2 Coordenadas de mundo e de tela

**Em uma frase.** O mundo tem o tabuleiro no plano y = 0, com cada casa medindo 1 unidade. A tela tem pixels, com y crescendo para baixo.

**Fórmula.**

```
Casa para mundo:   x = file - 3,5        z = 3,5 - rank
Mundo para casa:   file = piso(x + 4)    rank = piso(4 - z)
NDC para tela:     sx = x0 + (ndc_x + 1) w / 2
                   sy = y0 + (1 - ndc_y) h / 2
```

Exemplo: e2 é `file = 4` e `rank = 1`, logo x = 0,5 e z = 2,5. O sinal em `sy` inverte porque, na tela, y cresce para baixo.

**Onde está.** `square_to_world`, `world_to_square` e `viewport` em `xadrez/graphics/matrix.py`. `Camera.project` em `xadrez/graphics/camera.py`.

**Como mostrar.** Aperte F4 e passe o mouse sobre o tabuleiro. O bloco "Raio do mouse" mostra o pixel e a casa atingida. O próprio F4 é uma demonstração de viewport: o tabuleiro encolhe para abrir espaço ao painel, e o clique continua certo. Redimensione a janela e clique de novo.

## 6.3 Do clique à casa: o caminho inverso

**Em uma frase.** Para saber em que casa o jogador clicou, o pipeline roda ao contrário e vira um raio no mundo, que é testado contra as peças e contra o tabuleiro.

**Fórmula.**

```
ndc_x = 2 (sx - x0) / w - 1
ndc_y = 1 - 2 (sy - y0) / h
Ponto no near = inversa(P V) (ndc_x, ndc_y, -1, 1), dividido por w
Ponto no far  = inversa(P V) (ndc_x, ndc_y, +1, 1), dividido por w
Raio: origem o = near, direção d = normalizar(far - near)
Plano y = 0:  t = (0 - o.y) / d.y   e   ponto = o + t d
```

**Onde está.** `screen_ray`, `pick_plane`, `pick_square` e `pick_piece` em `xadrez/graphics/camera.py`. `BoardView.pick` em `xadrez/ui/board_view.py`. O diagrama da seção 4.7 mostra a sequência.

**Como mostrar.** Com F4 aberto, orbite a câmera com o botão direito e mova o mouse. Origem, direção e casa mudam ao vivo. Clique na cabeça de uma peça alta: quem é selecionada é ela, e não a casa de trás. Clique no peão e2, que aparece por trás do rei: quem é selecionado é o peão, porque o teste é pela silhueta que se vê.

## 6.4 Translação, rotação e escala por matrizes

**Em uma frase.** Cada transformação é uma matriz 4x4, e combiná-las é multiplicar. A quarta coordenada (coordenada homogênea) é o que permite escrever a translação como produto.

**Fórmula.**

```
T(x, y, z)           S(sx, sy, sz)        Ry(a)
1 0 0 x              sx 0  0  0           cos a   0  sen a  0
0 1 0 y              0  sy 0  0             0     1    0    0
0 0 1 z              0  0  sz 0          -sen a   0  cos a  0
0 0 0 1              0  0  0  1             0     0    0    1
```

A convenção é vetor coluna: `p' = M @ p`. Em `compose(A, B, C)`, o produto é `A @ B @ C`, logo C é aplicada primeiro ao ponto. A ordem importa: escalar e depois transladar é diferente de transladar e depois escalar.

**Onde está.** `translation`, `scaling`, `rotation_x`, `rotation_y`, `rotation_z`, `compose` e `transform_points` em `xadrez/graphics/matrix.py`.

Exemplos reais de composição:

| Situação | Matriz | Onde está |
|---|---|---|
| Peça parada | `T(casa) @ Ry(orientação)` | `piece_matrix` |
| Peça voando | `T(posição) @ R(inclinação) @ Ry(orientação) @ S(esticada)` | `PieceAnimation.model_matrix` |
| Peça capturada | `T @ Ry(giro) @ S(1 - e)` | `CaptureAnimation.model_matrix` |
| Rei tombando | `T(casa) @ T(p) @ R @ T(-p) @ Ry(orientação)` | `KingFallAnimation.model_matrix` |

O rei tomba em torno da borda da base, que não é a origem. Por isso a rotação fica entre `T(p)` e `T(-p)`: o ponto p vai para a origem, gira e volta, então não sai do lugar.

**Como mostrar.** Selecione uma peça: ela sobe um pouco (translação). Jogue: ela voa, inclina e estica (as três transformações juntas). Capture: a peça encolhe girando. Dê xeque-mate: o rei tomba.

## 6.5 Câmera: visão e projeção perspectiva

**Em uma frase.** A matriz de visão leva o mundo para o ponto de vista da câmera, e a projeção faz o que está longe ficar menor.

**Fórmula.**

```
Olho, em esféricas:  horizontal = distância cos(pitch)
                     olho = alvo + (horizontal sen(yaw), distância sen(pitch), horizontal cos(yaw))

Base da câmera:      f = normalizar(alvo - olho)
                     r = normalizar(f x up)
                     u = r x f

Perspectiva:         foco = 1 / tan(fov_y / 2)
                     x_ndc = foco x / (aspecto (-z))
                     y_ndc = foco y / (-z)
```

A última linha da matriz de projeção faz w = -z. É a divisão por w que encolhe o que está longe. Os valores padrão são pitch de 52 graus, distância de 16,5 e campo de visão de 30 graus.

**Onde está.** `look_at` e `perspective` em `xadrez/graphics/matrix.py`. `Camera.eye`, `view_matrix` e `projection_matrix` em `xadrez/graphics/camera.py`. Em janela estreita, `_build_projection` abre o campo de visão para o tabuleiro não ser cortado.

**Como mostrar.** Com F4 aberto, olhe a "Matriz de visão". Orbite com o botão direito: a parte de rotação (as 3 primeiras colunas) muda. Use a roda: muda a última coluna, que tem a posição. A tecla V volta à vista padrão.

## 6.6 Vetores

**Em uma frase.** Vetor é direção e tamanho. O produto escalar mede o quanto duas direções concordam, e o produto vetorial dá uma direção perpendicular às duas.

**Fórmula e uso real.**

| Operação | Fórmula | Onde o jogo usa |
|---|---|---|
| Produto escalar | `a.b = ax bx + ay by + az bz` | Corte de faces (`_visible_polygons`) e Lambert (`DirectionalLight.shade`) |
| Produto vetorial | `a x b`, perpendicular aos dois | Base da câmera (`look_at`) e normais das faces (`compute_face_normals`) |
| Normalizar | `v / tamanho(v)` | Direção do raio (`screen_ray`) e da luz |
| Interpolar | `a + (b - a) t` | Posição da peça em voo (`PieceAnimation.position`, com `Vector2D.lerp`) |
| Rotação 2D | `x' = x cos a - y sen a`, `y' = x sen a + y cos a` | Círculos dos marcadores (`_circle_points`, com `Vector2D.rotated`) |
| Reflexão | `v' = v - 2 (v.n) n` | Implementada e testada em `Vector2D.reflect` e `Vector3D.reflect` |

**Onde está.** `xadrez/graphics/vector.py`.

As contas em massa não usam essas classes. Malhas e partículas ficam em arrays numpy, porque um laço de objetos Python custaria caro demais a cada quadro. A reflexão das partículas no piso, por exemplo, é a mesma fórmula escrita em numpy, em `_bounce_on_floor`. Os métodos `reflect` das classes de vetor não são chamados pelo jogo: só os testes os usam.

**Como mostrar.** Em F4, a linha "direção" do raio é um vetor normalizado. Mova o mouse e veja os componentes mudarem.

## 6.7 Colisão

**Em uma frase.** O jogo tem quatro tipos de colisão: peça contra peça no caminho, raio contra o plano, raio contra a peça e partícula contra o piso.

| Colisão | Ideia | Onde está |
|---|---|---|
| Caminho das peças | Percorre cada direção e para na primeira peça. A casa dela é atacada, as de trás não. | `SlidingPiece.attacks` em `xadrez/core/pieces.py` |
| Raio contra plano | `t = (y_plano - o.y) / d.y` | `Camera.pick_plane` |
| Raio contra peça | Cilindro envolvente descarta o que está longe; depois, o pixel é testado contra as faces projetadas da malha, da peça mais próxima para a mais distante | `_ray_touches_bounds` e `_pixel_inside_any_face` em `xadrez/graphics/camera.py` |
| Partícula contra piso | Reflete a velocidade na normal, perdendo energia | `ParticleSystem._bounce_on_floor` em `xadrez/graphics/particles.py` |

**Fórmula.**

```
Raio contra cilindro, em (x, z), com m = origem do raio - centro da peça:
  a = d.x^2 + d.z^2
  b = m.x d.x + m.z d.z
  c = m.x^2 + m.z^2 - r^2
  a t^2 + 2 b t + c = 0   =>   t = (-b -+ raiz(b^2 - a c)) / a
  Depois confere se y, entre a entrada e a saída, está na altura da peça.

Pixel p dentro de uma face projetada, com vértices v0..v3 (produto vetorial 2D em cada aresta):
  s_i = (v_i+1 - v_i) x (p - v_i)
  Dentro da face: todos os s_i têm o mesmo sinal.

Partícula contra piso, com n = (0, 1, 0) e restituição e = 0,45:
  v' = v - (1 + e) (v.n) n
```

Com e = 1, é a reflexão perfeita. Com e menor que 1, só a componente normal perde energia, e a tangencial fica.

**Como mostrar.** Na posição inicial, clique na torre a1: "Essa peça não tem jogada válida agora.", porque os vizinhos bloqueiam o caminho. Clique no cavalo: ele tem jogadas, porque salta. Faça uma captura e olhe as faíscas quicando no tabuleiro.

## 6.8 Primitivas e malhas

**Em uma frase.** Cada peça é uma malha: uma lista de vértices e uma lista de faces, montada a partir de primitivas simples.

**Fórmula.** A superfície de revolução gira um perfil (raio, y) em torno do eixo y:

```
p(a) = (r cos a, y, -r sen a)
Normal da face: n = (v2 - v0) x (v3 - v1)
```

O seno negativo e a ordem anti-horária dos vértices fazem a normal apontar para fora. Toda face é guardada como quadrilátero, e um triângulo repete o último índice. A forma fixa permite processar a cena inteira em arrays.

**Onde está.** `Mesh`, `lathe`, `box`, `merge` e `triangulate_polygon` em `xadrez/graphics/mesh.py`. As peças estão em `xadrez/graphics/models.py`: os corpos nascem de `lathe`, as ameias da torre e a cruz do rei usam `box`, as pontas da coroa da dama são pequenos `lathe`, e a cabeça do cavalo é uma silhueta facetada. O tabuleiro está em `xadrez/graphics/board_model.py`. A função `extrude` existe e é testada, mas nenhuma peça a usa.

Tamanho real das malhas:

<!-- GERADO:malhas -->
| Peça | Vértices | Faces |
|---|---|---|
| Peão | 73 | 75 |
| Cavalo | 118 | 130 |
| Bispo | 127 | 126 |
| Torre | 139 | 130 |
| Dama | 142 | 146 |
| Rei | 107 | 106 |

Na posição inicial, as 32 peças somam 3248 faces. Com as 64 casas, são 3312 polígonos, o valor que a tecla F3 mostra no começo da partida.
<!-- FIM:malhas -->

**Como mostrar.** Aperte F3: "polígonos em cena" conta as casas e as faces das peças, e cai a cada captura. Orbite e aproxime com a roda para ver as facetas.

## 6.9 Cores: a matriz de cores

**Em uma frase.** Uma matriz 8x8 guarda o estado de cada casa, e uma única operação de arrays transforma os estados em cores.

**Fórmula.**

```
cor = base (1 - a) + destaque a
Pulso, na ameaça e no xeque:
  pulso = 0,5 + 0,5 sen(2 pi f t), com f = 1,1 Hz
  a = a_min + (a_max - a_min) pulso
```

Os estados têm prioridade crescente: 0 nenhum, 1 último lance, 2 caminho, 3 captura, 4 ameaça, 5 xeque, 6 seleção e 7 cursor. Um estado de prioridade menor não sobrescreve um maior.

**Onde está.** `ColorMatrix` e `CellState` em `xadrez/graphics/color_matrix.py`. Quem decide os estados é `_paint_highlights` em `xadrez/ui/game_scene.py`.

**Como mostrar.** Com F4 aberto, olhe a "Matriz de cores". Selecione uma peça: aparecem o 6 na origem e os 2 e 3 nos destinos, na mesma casa em que a cor muda no tabuleiro. Mova o mouse: o 7 acompanha.

## 6.10 Iluminação

**Em uma frase.** Uma face é mais clara quanto mais virada para a luz. Sobre isso, somam-se uma borda e um brilho que dependem de onde a câmera está.

**Fórmula.**

```
l = oposto da direção da luz, normalizado
Lambert:   difusa = max(0, n.l)
Ambiente:  céu = 0,65 + 0,35 (n.y + 1) / 2
           I = 0,40 céu + 0,72 difusa
           cor = base I cor_da_luz

v = direção da face ao olho
Borda:     (1 - n.v)^3
Brilho:    (n.h)^34, com h = normalizar(v + l)  (Blinn-Phong)
```

A luz é direcional, com direção (0,42, -1, -0,30) e cor quente (1, 0,93, 0,82), como um abajur distante. As faces perto da mesa ainda recebem um escurecimento de contato.

**Onde está.** `DirectionalLight.shade` em `xadrez/graphics/lighting.py`. `_final_colors` em `xadrez/graphics/renderer.py`. `_with_contact_shade` em `xadrez/graphics/models.py`.

**Como mostrar.** Orbite a câmera em volta de uma peça. A parte difusa não muda, porque depende só da normal e da luz. O brilho e a borda mudam, porque dependem do olho. A borda fria é o que impede a peça de ébano de sumir contra a casa escura.

## 6.11 Sombra

**Em uma frase.** Uma matriz achata cada peça no plano do tabuleiro, na direção da luz.

**Fórmula.** O ponto p viaja pelo raio `p + t d` até o plano y = y0:

```
t  = (y0 - p.y) / d.y
x' = x - (d.x / d.y) (y - y0)
y' = y0
z' = z - (d.z / d.y) (y - y0)
```

Tudo isso é linear em (x, y, z, 1), então cabe em uma matriz. A última linha é (0, 0, 0, 1), porque a luz direcional é um ponto no infinito e não há divisão por w.

**Onde está.** `planar_shadow` em `xadrez/graphics/matrix.py`. `_Instance.shadow_outline`, `_ShadowLayer` e `_draw_shadows` em `xadrez/graphics/renderer.py`.

Para não desenhar uma sombra por face, o contorno de cada peça é reduzido a um polígono de 24 pontos. Os polígonos são pintados em cinza em uma máscara de meia resolução, suavizada e multiplicada sobre o tabuleiro de uma vez. Como cada pixel é multiplicado uma só vez, duas sombras sobrepostas não escurecem em dobro.

**Como mostrar.** Jogue um lance e olhe a sombra acompanhar a peça em voo. Na posição inicial, olhe as sombras de peças vizinhas: onde se sobrepõem, não ficam mais escuras.

## 6.12 Partículas

**Em uma frase.** São até 2000 pontos com posição, velocidade, cor e tempo de vida, atualizados de uma vez em arrays.

**Fórmula.**

```
Euler semi-implícito, a cada quadro:
  v.y = v.y + g dt            g = -9,8
  v   = v exp(-k dt)          k = 0,55 (arrasto)
  p   = p + v dt

Transparência: a = 1 - (idade / vida)^2
Tamanho:       s = base (1 - 0,5 idade / vida)
Na tela:       raio em pixels = s foco_em_pixels / profundidade
```

**Onde está.** `ParticleSystem` em `xadrez/graphics/particles.py`. O desenho é `_draw_particle_system` em `xadrez/graphics/renderer.py`, com blend aditivo: luz soma e nunca escurece.

| Efeito | Quantidade | Método |
|---|---|---|
| Captura | 60 partículas (34 lascas e 26 faíscas) | `capture_burst` |
| Rastro da peça em voo | 2 por quadro | `trail` |
| Fogos de vitória | 140 por estouro | `victory_fireworks` |
| Poeira do pouso | 8 | `emit`, em `BoardView._land` |

**Como mostrar.** Aperte F3 e olhe o contador "partículas". Faça uma captura. Termine a partida: os fogos sobem o contador, e dá para ver as partículas caindo e quicando.

## 6.13 Animação

**Em uma frase.** Uma animação é uma interpolação no tempo: o progresso vai de 0 a 1, passa por uma curva de easing e vira uma matriz.

**Fórmula.**

```
Tween:       valor = início + (fim - início) e(t), com t = decorrido / duração
Cúbica:      4 t^3 na primeira metade, espelhada na segunda
Back:        1 + (c + 1)(t - 1)^3 + c (t - 1)^2, com c = 1,70158
Bounce:      quatro arcos de parábola de altura decrescente
Arco do voo: y = 4 h t (1 - t), com h = 0,28 + 0,09 distância
```

| Animação | Duração | Curva | Efeito |
|---|---|---|---|
| `PieceAnimation` | 0,38 s | Cúbica | Arco, inclinação de até 13 graus e até 7% de esticada |
| `CaptureAnimation` | 0,45 s | Cúbica | Encolhe girando 1,5 volta e sobe um pouco |
| `SpawnAnimation` | 0,45 s | Back | A peça promovida nasce e passa um pouco do tamanho |
| `KingFallAnimation` | 0,95 s | Bounce | O rei tomba 96 graus e quica |

**Onde está.** `xadrez/graphics/animation.py`. O giro da câmera também usa `Tween`, em `Camera.orbit_to`.

**Como mostrar.** Jogue um lance longo e um curto: o arco do longo é mais alto. Promova um peão. Dê xeque-mate para ver o rei quicar.

## 6.14 Controle de framerate

**Em uma frase.** Cada quadro tem um prazo de 1/60 s, e tudo o que se move usa o tempo real decorrido, não a contagem de quadros.

**Fórmula.**

```
Próximo prazo = prazo anterior + 1/60
Atraso de mais de um quadro: próximo prazo = agora + 1/60
Movimento:  posição = posição + velocidade dt
dt usado no quadro = min(dt real, 0,1 s)
```

Cada prazo parte do prazo anterior, não de "agora". Assim, um atraso pequeno é compensado no quadro seguinte em vez de se acumular. O sono vai até 2 ms antes do prazo, e o resto é espera ativa, porque o sono do sistema não é preciso.

**Onde está.** `FramePacer` em `xadrez/ui/frame_pacer.py`. `App.run_frame` e `App.step` em `xadrez/ui/app.py`.

**Por que isso foi necessário.** `pygame.time.Clock.tick(60)` trabalha em milissegundos inteiros. Medido em janela real, ele dava 59,1 FPS. Depois do `FramePacer`, a mesma demonstração deu 60,0 FPS médios em 1286 quadros, com intervalo médio de 16,66 ms. Os números completos estão na seção 7.6.

**O que mantém o quadro barato.** Com a câmera em movimento, o renderizador redesenha os polígonos. Com ela parada, o tabuleiro vira uma camada pronta e cada peça vira um sprite, feitos aos poucos: no máximo 8 sprites por quadro. O texto do HUD também fica em cache.

**Como mostrar.** Aperte F3 e olhe o FPS e os milissegundos por quadro. O número do painel é uma média móvel de poucos quadros e oscila um pouco em torno de 60. A medida da partida inteira é a da seção 7.6. Orbite a câmera: "redesenhados agora" sobe. Solte: ele cai a zero em poucos quadros, porque a imagem vem das camadas prontas.

## 6.15 O que aparece na tela: corte e ordem de pintura

**Em uma frase.** Faces de costas para a câmera são descartadas, e o resto é pintado de trás para a frente.

**Fórmula.**

```
A face é visível se n.(olho - centro) > 0
Plano near: a face sai se algum vértice tiver w <= 0,5
Ordem:      posto do objeto x 1000 - distância da face
```

A ordem do pintor tem dois níveis. Primeiro vem o objeto, pela distância do centro dele ao olho. Depois vem a face, dentro do objeto. Olhar só a distância de cada face erraria quando a peça alta de trás tem o topo mais perto do olho que a base da peça da frente.

**Onde está.** `_visible_polygons` e `_draw_objects_as_polygons` em `xadrez/graphics/renderer.py`. O teste CT-36 lê os pixels para conferir que a peça da frente cobre a de trás.

**Como mostrar.** Orbite até olhar uma fileira de peças de lado: as da frente cobrem as de trás em qualquer ângulo.

## 6.16 O que o projeto não usa

Para não haver dúvida na arguição:

- **Texturas:** não há mapeamento de textura. Os veios da madeira são quadriláteros finos sobre as casas, e o fundo é uma imagem procedural calculada por tamanho de janela.
- **Spritesheets:** não há arquivo de spritesheet. O enunciado permite spritesheets ou modelos low-poly, e o grupo usou modelos. Os "sprites" citados aqui são imagens geradas pelo próprio pipeline a partir das malhas, quando a câmera para.
- **Shaders e GPU:** nada roda em shader. O desenho é feito na CPU, com numpy para as contas e pygame para preencher os polígonos.
- **Z-buffer:** a ordem de pintura resolve a visibilidade.

## 6.17 Roteiro de demonstração

Uma sequência curta que passa por todos os conceitos. O enunciado exige executar o jogo na banca, com uma partida curta que mostre a interação entre os dois jogadores e as telas de vitória ou derrota. O mate do passo 8 termina em 7 meios-lances. Também há `python tools/demo_automatica.py`, que joga sozinho até a vitória e serve de plano B.

| Passo | Ação no jogo | Conceito |
|---|---|---|
| 1 | No menu, digitar os nomes, escolher o tempo e iniciar | RF01 e fluxo de telas |
| 2 | F3 | Framerate e contagem de polígonos |
| 3 | Clicar na torre a1 e depois no cavalo b1 | Colisão de caminho e salto |
| 4 | F4, mover o mouse e orbitar | Mundo e tela, raio, matriz de visão |
| 5 | Selecionar uma peça com F4 aberto | Matriz de cores |
| 6 | Jogar `e4 e5 Bc4 Nc6 Qh5 Nf6` | Matrizes em voo, sombra e ameaças |
| 7 | Clicar em uma peça do adversário | Jogada fora do turno e mensagem do motor |
| 8 | Jogar `Qxf7#` | Captura, partículas, rei tombando e fogos |
| 9 | Revanche com cores trocadas | Placar da série |
