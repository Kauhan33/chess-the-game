# Chess - The Game: design e contratos

Documento-base do projeto A3 de Computação Gráfica e Realidade Virtual, Grupo 09.
É a fonte única de arquitetura, nomes e IDs (RF, RNF, UC, CT). Se o código
precisar divergir daqui, atualize este arquivo no mesmo trabalho.

## 1. Decisões já tomadas pelo grupo

| Tema | Decisão | Motivo |
|---|---|---|
| Gráficos | 3D low-poly com pipeline próprio em numpy + pygame | Matrizes, malhas, luz e clique por raio ficam explícitos e explicáveis na banca; não depende de driver de GPU |
| Regras | Oficiais completas: roque, en passant, promoção, afogamento e empates | A rubrica cobra regras oficiais; perft dá validação objetiva |
| Modo de jogo | 2 jogadores locais, em turnos alternados | Exigência do enunciado |

## 2. Regras do projeto

- **Privacidade:** o repositório não pode ter nome completo de integrante, RA nem
  nome de professor, nem em código, documentos, imagens, metadados ou autoria de
  commit. Esses dados ficam só em `entrega/` (ignorada pelo git), lidos de
  `entrega/dados_capa.json`. O PDF do enunciado fica em `docs/referencias/`, também
  ignorada, e nunca deve ser citado com o nome dos professores.
- **Publicação:** nada vai para o GitHub sem autorização explícita do aluno. Commits
  locais são feitos pelo coordenador; agentes não rodam `git add`, `commit` ou `push`.
- **Idioma:** identificadores em inglês, alinhados aos nomes do enunciado (`GameEngine`,
  `Board`, `Piece`, `Player`, `Vector2D`, `ParticleSystem`). Comentários, docstrings,
  textos de tela e documentos em português do Brasil.
- **Honestidade:** "Resultado Obtido", prints e métricas vêm sempre de execução real.
  Nunca escrever resultado, data ou evolução de Kanban que não aconteceu.
- **Estilo:** skill `clean-code` (funções pequenas, guard clauses, sem helpers
  inúteis, nomes que dizem a intenção). Não criar classe só para constar no diagrama.

## 3. Arquitetura em camadas

```
xadrez/
├── core/       regras do jogo. Python puro: sem pygame, sem numpy.
├── graphics/   computação gráfica. numpy + pygame. Não conhece as regras.
└── ui/         cenas, HUD e entrada. Liga core e graphics.
```

Regra de dependência: `ui -> core` e `ui -> graphics`. `core` e `graphics` nunca se
importam entre si; `tests/test_arquitetura.py` garante isso. A `ui` traduz os tipos
do `core` para os valores simples que `graphics` espera: casa como `(file, rank)` e
tipo de peça como texto (`"pawn"`, `"knight"`, `"bishop"`, `"rook"`, `"queen"`, `"king"`).

### Convenções de coordenadas

- **Casa:** `file` 0..7 = colunas a..h; `rank` 0..7 = fileiras 1..8. Casa escura
  quando `(file + rank) % 2 == 0` (a1 é escura).
- **Mundo:** y para cima, tabuleiro no plano `y = 0`, cada casa mede 1 unidade.
  Centro da casa: `x = file - 3.5`, `z = 3.5 - rank`. As brancas ficam em z positivo.
- **Câmera:** `yaw = 0` olha pelo lado das brancas; `yaw = pi` pelo das pretas.
- **Matrizes:** numpy `(4, 4)` de float, vetor coluna: `p' = M @ p`.
- **Pipeline:** Modelo -> Mundo -> Visão -> Recorte -> NDC -> Tela.

## 4. Contrato de `xadrez.core`

Tudo reexportado em `xadrez/core/__init__.py`.

```python
class Color(Enum):          # WHITE, BLACK; .opposite; .label ("Brancas"/"Pretas")
class PieceType(Enum):      # PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
                            # .value = "pawn"...; .points = 1,3,3,5,9,0; .symbol = P,N,B,R,Q,K
class Square(NamedTuple):   # file, rank; from_name("e4"); .name; is_valid()

@dataclass(frozen=True, slots=True)
class Move:                 # origin, target, promotion=None, is_castling=False,
                            # is_en_passant=False, is_double_push=False; .uci

class Piece(ABC):           # color, kind (PieceType), pseudo_legal_moves(board, sq), attacks(board, sq)
class SlidingPiece(Piece)   # base de Rook, Bishop e Queen (a "colisão" de caminho fica aqui)
class Rook, Bishop, Queen, Knight, King, Pawn

class Board:
    # grade 8x8, turn, castling_rights, en_passant_target, halfmove_clock, fullmove_number
    initial() / from_fen(fen) / to_fen()
    piece_at(sq), place(sq, piece), remove(sq), pieces(color) -> iterador de (Square, Piece)
    king_square(color), is_attacked(sq, by_color), attackers_of(sq, by_color)
    apply(move) e undo()    # pilha de desfazer

# rules.py: funções puras sobre Board
legal_moves(board, color=None), legal_moves_from(board, sq), is_in_check(board, color),
is_checkmate(board), is_stalemate(board), has_insufficient_material(board), perft(board, depth)

class Player:               # name, color, match_points, captured (list[PieceType]), material_score
class TimeControl:          # minutes, increment; presets: UNLIMITED, BLITZ_5, RAPID_10, CLASSIC_30
class ChessClock:           # remaining(color), elapsed(color), tick(color, dt), is_flagged(color)

class GameState(Enum):      # IN_PROGRESS, PAUSED, FINISHED
class EndReason(Enum):      # CHECKMATE, STALEMATE, INSUFFICIENT_MATERIAL, FIFTY_MOVES,
                            # THREEFOLD_REPETITION, TIMEOUT, RESIGNATION, AGREEMENT; .label em pt-BR
class GameResult:           # winner (Color | None), reason (EndReason)
class MoveError(Enum):      # GAME_NOT_ACTIVE, NO_PIECE, NOT_YOUR_TURN, ILLEGAL_MOVE,
                            # LEAVES_KING_IN_CHECK, PROMOTION_REQUIRED; .message em pt-BR

@dataclass
class MoveOutcome:
    ok: bool; error: MoveError | None; move: Move | None; piece: Piece | None
    captured: Piece | None; captured_square: Square | None   # difere do alvo no en passant
    rook_path: tuple[Square, Square] | None                  # roque, para animar a torre
    promoted_to: PieceType | None; gives_check: bool
    result: GameResult | None; san: str

class GameEngine:
    def __init__(self, white_name="Jogador 1", black_name="Jogador 2",
                 time_control=TimeControl.UNLIMITED, fen=None)
    board, players (dict[Color, Player]), clock, state, result, history (list[str] em SAN)
    turn, current_player, in_check, checked_king_square, checking_pieces
    legal_moves_from(sq) -> list[Move]
    is_promotion_move(origin, target) -> bool
    play(origin, target, promotion=None) -> MoveOutcome  # entrada inválida vira erro, nunca exceção
    threatened_pieces(color) -> list[Square]             # peças de color atacadas, sem contar o rei
    attackers_of(sq) -> list[Square]
    pause(); resume(); tick(dt) -> GameResult | None
    resign(color=None); agree_draw()
    restart()     # mesma disposição de cores; placar da série mantido
    rematch()     # cores invertidas; placar da série mantido
    material_balance() -> int
```

Regras combinadas: empate por 50 lances e por tripla repetição são automáticos; tempo
esgotado perde, salvo se o adversário só tiver o rei (empate); vitória vale 1 ponto na
série e empate vale 0,5; pontuação de material soma os valores das peças capturadas.

### Decisões do motor que a interface precisa respeitar

- `legal_moves_from` devolve 4 jogadas para a mesma casa na promoção: tire as repetidas ao desenhar.
- `play` responde `PROMOTION_REQUIRED` só se a jogada for legal; peão cravado recebe
  `LEAVES_KING_IN_CHECK` antes, então o diálogo de promoção não abre à toa.
- `tick` devolve o resultado só no quadro em que o tempo acaba e depois `None`.
  `remaining` vale `math.inf` em `TimeControl.UNLIMITED`.
- `resign` e `agree_draw` valem também durante a pausa.
- `restart` e `rematch` voltam ao FEN do construtor, ou à posição oficial se não houver.
- `material_balance` são os pontos capturados das brancas menos os das pretas.
- `attackers_of(sq)` devolve os inimigos da peça na casa; com a casa vazia, os adversários de quem joga.
- Também exportados: `STARTING_FEN`, `AppliedMove`, `has_legal_moves`, `leaves_king_in_check`,
  `legal_en_passant_moves`, `position_key`, `move_to_san`. Atributos extras: `Board.grid`
  (`[file][rank]`), `Move.captured_square`, `Piece.symbol`, `Square.is_dark`, `GameResult.is_draw`,
  `TimeControl.is_unlimited`, `ChessClock.add_increment`, `GameEngine.time_control`.

## 5. Contrato de `xadrez.graphics`

```python
# vector.py
class Vector2D:  # x, y; + - * /; dot, length, normalized, rotated, lerp, reflect(normal)
class Vector3D:  # x, y, z; o mesmo e cross; as_array(), from_array()

# matrix.py: funções que retornam numpy (4, 4)
identity(), translation(x, y, z), scaling(sx, sy=None, sz=None), rotation_x(a),
rotation_y(a), rotation_z(a), compose(*matrices), look_at(eye, target, up),
perspective(fov_y, aspect, near, far), viewport(x, y, w, h),
planar_shadow(light_dir, plane_y=0.0), transform_points(m, points) -> (N, 3)
square_to_world(file, rank) -> (x, 0, z); world_to_square(x, z) -> (file, rank) | None
piece_matrix(file, rank, facing=0.0)   # matriz-modelo de peça parada; em cache, somente leitura

# camera.py
class Camera:
    # distance e fov_y padrão mudaram de 11.5 e 38 graus: daquele jeito a borda do tabuleiro saía da tela.
    def __init__(self, viewport=(0, 0, 1280, 720), yaw=0.0, pitch=radians(52), distance=16.5, fov_y=radians(30), target=None)
    set_viewport(x, y, w, h); view_matrix; projection_matrix
    project(points) -> (pontos_tela (N, 2), profundidade (N,))
    screen_ray(sx, sy) -> (origem, direção)   # dois Vector3D
    pick_plane(sx, sy, plane_y=0.0) -> (x, z) | None
    pick_square(sx, sy) -> (file, rank) | None   # None fora do viewport ou do tabuleiro
    pick_piece(sx, sy, pieces) -> (file, rank) | None   # pieces: (file, rank, altura); ver abaixo
    orbit_to(yaw, duration=0.8); orbit_by(dyaw, dpitch=0.0); zoom_by(factor); update(dt); is_moving
    view_projection_matrix; viewport_matrix; eye; yaw; pitch; distance; viewport; revision

# mesh.py e models.py
class Mesh:   # vertices (N, 3), faces (M, 4), face_normals, face_centers, face_shades, face_neighbors,
              # height, radius, transformed(matrix). Triângulo repete o último índice.
lathe(profile, segments), extrude(polygon_2d, depth), box(w, h, d), merge(*meshes)
PIECE_KINDS; build_piece_meshes() -> dict[str, Mesh]
IVORY; EBONY; FACING_WHITE; FACING_BLACK   # cor das peças e `facing` por lado

# lighting.py
class DirectionalLight:  # direction, color, ambient, diffuse; shade(normals, base_color) -> cores

# color_matrix.py: requisito "indicação por matriz de cores"
class CellState(IntEnum):  # NONE, LAST_MOVE, PATH, CAPTURE, THREAT, CHECK, SELECTED, CURSOR (prioridade crescente)
class ColorMatrix:
    def __init__(self, light_square=..., dark_square=..., palette=None)   # o tema da Interface entra aqui
    states: numpy (8, 8) uint8 indexado por [file, rank]
    clear(), set(file, rank, state), set_many(squares, state), state_at(file, rank)
    # set mantém o estado de maior prioridade; NONE sempre limpa; casa inválida é ignorada
    rgb(time=0.0) -> numpy (8, 8, 3) uint8   # base do tabuleiro + paleta + pulso por estado

# animation.py
easing: linear, ease_in_out_cubic, ease_out_back, ease_out_bounce
class Tween: start, end, duration, easing; update(dt), value, is_done
# Todas têm update(dt), progress, is_done e model_matrix(). `square` é (file, rank).
class PieceAnimation(origin, target, duration=0.38, arc_height=None, facing=0.0)  # arco: translação + rotação + escala
class CaptureAnimation(square, duration=0.45, facing=0.0)
class SpawnAnimation(square, duration=0.45, facing=0.0)
class KingFallAnimation(square, direction=(1.0, 0.0), duration=0.95, base_radius=0.34, facing=0.0)

# particles.py
class ParticleSystem:
    def __init__(self, capacity=2000, gravity=-9.8, floor_y=0.0, restitution=0.45, seed=None, drag=0.55)
    emit(position, count, color, speed, life, size, bias=(0, 0, 0))   # speed, life e size aceitam (mín, máx)
    capture_burst(position, color); trail(position, color); victory_fireworks(position, colors)
    update(dt)              # gravidade, arrasto, colisão com o piso por reflexão do vetor velocidade
    alive_count; positions; colors; sizes; alphas

# renderer.py
class Renderer3D:
    def __init__(self, camera, light=None)
    begin(surface); draw_board(rgb_matrix); add_mesh(mesh, model_matrix, color, tint=None, tint_amount=0.0, cast_shadow=True)
    add_marker(file, rank, kind, color)    # ponto = caminho; anel = captura (forma, além de cor)
    add_particles(system); flush()         # sombras, ordenação do pintor, desenho
    render_icon(mesh, color, size) -> pygame.Surface   # em cache
    light; polygons_drawn; sprites_built
# kind: MARKER_DOT, MARKER_RING, MARKER_CORNERS (cursor e seleção), MARKER_TRIANGLE (ameaça).
# color de marcador aceita alpha: (r, g, b, a).

# board_model.py e backdrop.py: geometria do tabuleiro e fundo procedural, internos ao renderizador.
```

`pick_piece`: em ângulo, a cabeça de uma peça cobre a casa de trás na tela. `pick_square` só olha
o plano do tabuleiro, então clicar na cabeça escolhe a casa errada. Para selecionar peças, a
Interface deve chamar `pick_piece` com as peças visíveis (altura em `meshes[kind].height`). Se o
raio não tocar nenhuma, ela cai em `pick_square`.

Cache do renderizador: `add_mesh` compara malha, matriz e cor com o quadro anterior. Reenviar a
mesma peça a cada quadro é barato. A primeira vez que a câmera para, a camada do tabuleiro e os
sprites são refeitos em alguns quadros.

## 6. Contrato de `xadrez.ui`

```python
class Scene(ABC):   # handle_event(event), update(dt), draw(surface), resize(size), next_scene
class App:          # janela 1280x720 redimensionável, relógio a 60 FPS, troca de cenas
                    # run(); run_frame() em tempo real; step(dt) determinístico, para testes e ferramentas
                    # menu_scene(), game_scene(), game_over_scene(): as cenas se chamam em ciclo, então passam pelo App
class MenuScene     # nomes dos 2 jogadores, controle de tempo, giro de câmera, ajuda de controles
class GameScene     # tabuleiro 3D + HUD; seleção, promoção, pausa, reinício, animações
class GameOverScene # vencedor, motivo, placar da série, fogos; revanche ou menu
class Hud; widgets: Button, TextInput, Selector, FocusGroup
theme.py            # paleta e tipografia, com fallback de fontes do sistema
drawing.py          # placas de cantos cortados, brilho e chão de madeira
board_view.py       # BoardView: apresentação 3D, animações, partículas e câmera da partida
overlays.py         # pausa e confirmações (ChoiceOverlay), PromotionDialog, HelpOverlay
debug_panels.py     # PerformancePanel (F3) e DidacticPanel (F4)
match.py            # MatchOptions e formatação de relógio e placar
autoplay.py         # Autoplayer: joga por eventos reais; serve a testes, benchmark, captura e demonstração
```

`BoardView.pick` decide a casa do clique com `Camera.pick_piece`, que testa o pixel contra a silhueta
projetada de cada malha, da peça mais próxima do olho para a mais distante. Assim, o que o jogador vê
é o que ele aciona (achados QA-02 e QA-03, que derrubaram a primeira versão, baseada em cilindros). O
chão do painel usa `render_backdrop`, importado direto de `xadrez.graphics.backdrop`.

Controles: mouse (clique seleciona e move; botão direito arrasta e orbita; roda dá
zoom) e teclado (setas movem o cursor, relativas à visão atual; Enter ou Espaço confirma; Esc
cancela a seleção e, sem seleção, abre a pausa; P pausa; R reinicia com confirmação; T liga o giro
por turno; V volta à vista padrão; H ou F1 mostra a ajuda; F3 mostra FPS; F4 abre o modo didático).

## 7. Identificadores

### Requisitos funcionais

| ID | Requisito |
|---|---|
| RF01 | Identificar os 2 jogadores e escolher modo (tempo e câmera) no menu |
| RF02 | Montar o tabuleiro 8x8 na posição oficial |
| RF03 | Alternar turnos, começando pelas brancas, e recusar jogada fora do turno |
| RF04 | Validar o movimento estrito das 6 peças, com colisão de caminho e captura |
| RF05 | Aceitar as jogadas especiais: roque, en passant e promoção |
| RF06 | Validar xeque: nenhuma jogada pode deixar o próprio rei em xeque |
| RF07 | Detectar fim de jogo: xeque-mate, afogamento, empates, tempo e desistência |
| RF08 | Permitir selecionar e mover por mouse e por teclado |
| RF09 | Indicar caminhos válidos por matriz de cores (seleção, movimento, captura, último lance) |
| RF10 | Dar feedback visual de peças sob ameaça e de rei em xeque |
| RF11 | Exibir HUD com jogadores, vez, cronômetro, pontuação, capturas e lances |
| RF12 | Pausar e retomar, congelando o relógio e a entrada |
| RF13 | Reiniciar, pedir revanche e voltar ao menu, mantendo o placar da série |
| RF14 | Exibir tela de fim de jogo com vencedor, motivo e animação de vitória |
| RF15 | Animar movimentos e capturas com transformações e partículas |
| RF16 | Girar, orbitar e aproximar a câmera, com clique correto em qualquer ângulo |

### Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF01 | Desempenho: 60 FPS travados em 1280x720 |
| RNF02 | Portabilidade: Python 3.10+ em Windows, Linux e macOS |
| RNF03 | Responsividade: resposta visual à entrada em até 1 quadro |
| RNF04 | Estética e acessibilidade: paleta coerente e estados por cor e por forma |
| RNF05 | Arquitetura em camadas, com motor testável sem interface |
| RNF06 | Qualidade: cobertura de pelo menos 90% em `core` |
| RNF07 | Robustez: entrada inválida e redimensionamento nunca derrubam o jogo |

### Casos de uso

UC01 Iniciar Partida · UC02 Executar Jogada · UC03 Pausar Jogo · UC04 Reiniciar Partida ·
UC05 Promover Peão (extend de UC02) · UC06 Consultar Caminhos e Ameaças · UC07 Verificar
Xeque e Fim de Jogo (Motor de Regras; include de UC02) · UC08 Encerrar Partida
(desistência ou empate) · UC09 Pedir Revanche ou Voltar ao Menu.

### Casos de teste

Cada teste automatizado leva `@pytest.mark.ct("CT-xx")`, e `--ct-report` grava o resultado
real em JSON. Faixas: motor CT-01 a CT-29, gráficos CT-30 a CT-39, interface CT-40 a CT-49,
ataques do QA a partir de CT-50.

| ID | Foco | RF |
|---|---|---|
| CT-01 | Posição inicial oficial | RF02 |
| CT-02 | Alternância de turnos, brancas começam | RF03 |
| CT-03 | Jogada fora do turno é recusada | RF03 |
| CT-04 | Movimentos válidos de cada peça | RF04 |
| CT-05 | Movimento proibido é recusado | RF04 |
| CT-06 | Colisão: peça deslizante é bloqueada por peça no caminho | RF04 |
| CT-07 | Cavalo salta sem colisão | RF04 |
| CT-08 | Captura atualiza a pontuação de material | RF04, RF11 |
| CT-09 | Roque válido e roques proibidos | RF05 |
| CT-10 | En passant válido e fora da janela | RF05 |
| CT-11 | Promoção exige escolha e troca a peça | RF05 |
| CT-12 | Peça cravada: jogada que expõe o rei é recusada | RF06 |
| CT-13 | Xeque-mate encerra a partida | RF07 |
| CT-14 | Afogamento é empate | RF07 |
| CT-15 | Empates: material insuficiente, 50 lances, tripla repetição | RF07 |
| CT-16 | Tempo esgotado encerra a partida | RF07, RF11 |
| CT-17 | Perft: contagem de posições confere com valores de referência | RF04, RF05, RF06 |
| CT-18 | Placar da série: vitória vale 1, empate vale 0,5 | RF11, RF13 |
| CT-19 | Cálculo de peças sob ameaça | RF10 |
| CT-20 | Pausa congela o relógio e recusa jogada | RF12 |
| CT-21 | Reiniciar e revanche | RF13 |
| CT-30 | Matrizes: translação, rotação, escala e composição | RF15, RF16 |
| CT-31 | Câmera: ida e volta mundo, tela e casa em vários ângulos | RF16 |
| CT-32 | Matriz de cores: estado vira cor, com prioridade | RF09 |
| CT-33 | Partículas: gravidade, reflexão no piso e tempo de vida | RF15 |
| CT-34 | Malhas: normais para fora e faces válidas | RF15 |
| CT-35 | Animação: interpolação e easing | RF15 |
| CT-36 | Render: corte de faces traseiras e ordem de pintura | RF15 |
| CT-40 | Menu inicia partida com nomes e tempo escolhidos | RF01 |
| CT-41 | Clique seleciona e preenche a matriz de cores | RF08, RF09 |
| CT-42 | Teclado seleciona e executa jogada | RF08 |
| CT-43 | Clique fora do turno dá aviso e não altera o jogo | RF03 |
| CT-44 | Ameaça e xeque aparecem na matriz de cores | RF10 |
| CT-45 | Pausa bloqueia a entrada | RF12 |
| CT-46 | Partida completa por eventos até a tela de vitória | RF07, RF14 |
| CT-47 | Revanche troca cores e mantém o placar; menu volta ao início | RF13 |
| CT-48 | Promoção pelo diálogo | RF05 |
| CT-49 | Redimensionar a janela mantém o clique correto | RNF07, RF16 |
| CT-50 | Partidas aleatórias contra gerador e detector independentes | RF04, RF05, RF06 |
| CT-51 | Bordas de promoção, en passant e roque | RF05, RF06 |
| CT-52 | Precedência entre fins de jogo no mesmo lance | RF07 |
| CT-53 | Tripla repetição, roque perdido e en passant | RF07 |
| CT-54 | Material insuficiente por captura e promoção subpotente | RF07 |
| CT-55 | Relógio, desistência, série, revanche e pretas primeiro | RF07, RF11, RF12, RF13 |
| CT-56 | Entradas absurdas e FEN malformadas | RF04, RNF07 |
| CT-57 | Macaco: eventos aleatórios com invariantes | RNF07 |
| CT-58 | Corridas entre relógio, voo, pausa, promoção e fim | RF05, RF07, RF12 |
| CT-59 | Clique: o que se vê é o que se aciona | RF08, RF16 |
| CT-60 | Clique duplo e eventos no mesmo quadro | RF12, RNF07 |
| CT-61 | Nomes: caracteres perigosos, largura e ajuda | RF01, RNF07 |
| CT-62 | Janelas e números extremos | RF16, RNF07 |
| CT-63 | Fim de jogo, revanche, menu e HUD | RF11, RF13, RF14 |
| CT-64 | Vazamento de memória | RNF01, RNF07 |
| CT-65 | Sem rede, sem execução dinâmica, sem escrita | RNF05, RNF07 |
| CT-66 | PNG, autoria, e-mails e caminhos pessoais | RNF05 |
| CT-67 | Python 3.10 e portabilidade | RNF02 |

## 8. Divisão do time

Um agente escrevendo por conjunto de arquivos. QA só lê, em cópia congelada.

| Agente | Escreve em | Skills |
|---|---|---|
| Motor | `xadrez/core/`, `tests/core/` | clean-code |
| Gráficos | `xadrez/graphics/`, `tests/graphics/`, `tools/benchmark.py` | clean-code |
| Interface | `xadrez/ui/`, `main.py`, `tests/ui/`, `tools/capturar_telas.py` | clean-code, frontend-design, ui-ux-pro-max, ui-design-system |
| Documentação | `docs/`, `README.md`, `tools/` (UML, relatório, PDF) | clean-code, anthropic-skills:pdf, watermarks-remover:clean-user-facing-text |
| QA | só relatório; testes novos em `tests/ataque/` | code-reviewer, senior-security |
| Coordenador | `.gitignore`, `pyproject.toml`, `tests/conftest.py`, git | brainstorming, clean-code |

## 9. Definição de pronto

Testes passando, cobertura medida, jogo executado de verdade, prints olhados, varredura
de dados pessoais limpa e documentação coerente com o código.

## 10. Versão 1.1: modos, CPU, rede, contas e histórico

Tudo das seções anteriores continua valendo. O jogo existente é mantido, e o modo Treinamento é o padrão.

Decisões do grupo:

- **Modos:** Treinamento mostra tudo, como na versão 1.0. Partida não mostra caminhos, capturas, ameaças nem avisos de xeque. Nos dois, as regras são as oficiais: lance ilegal é recusado. Na Partida, a recusa não explica o motivo, para não virar dica.
- **CPU:** níveis Easy, Medium, Hard e Hardcore, com a cor escolhida pelo jogador.
- **Rede:** só rede local, sem servidor: um cria a sala e o outro digita um código de 7 letras.
- **Contas:** login com senha, guardado neste computador, com "Jogar como convidado". Convidado não grava histórico.

No modo Partida ficam só os indicadores neutros, que dizem o que aconteceu e não o que fazer: a peça selecionada, o cursor e o último lance. A planilha do HUD e o texto de "Copiar PGN" omitem `+` e `#` enquanto a partida corre. O PGN gravado guarda a notação completa.

### 10.1 Novas camadas

```
xadrez/
├── core/    + ai.py (CPU), pgn.py. Continua Python puro.
├── data/    contas e histórico em disco. Python puro: sem pygame e sem numpy.
├── net/     sala em rede local por socket. Python puro: sem pygame e sem numpy.
├── graphics/
└── ui/      liga tudo.
```

Regra de dependência: `core` e `graphics` seguem como estão, sem conhecer as outras camadas. `data` pode importar `core`. `net` pode importar `core`. `ui` importa todas. `tests/test_arquitetura.py` passa a conferir `data` e `net`.

### 10.2 Contrato de `xadrez.core`: acréscimos

```python
# ai.py
class Difficulty(Enum):   # EASY, MEDIUM, HARD, HARDCORE
                          # .label = "Easy", "Medium", "Hard", "Hardcore"; .description em pt-BR
def choose_move(board: Board, difficulty: Difficulty, rng: random.Random | None = None,
                should_stop: Callable[[], bool] | None = None, max_seconds: float | None = None) -> Move
    # Devolve sempre uma jogada legal. Não altera `board`: trabalha em uma cópia, para poder rodar em outra thread.
    # `should_stop` cancela a busca. `max_seconds` limita o tempo, para a CPU não perder no relógio.

# pgn.py
def game_to_pgn(engine: GameEngine, event: str = "Chess - The Game", date: str | None = None) -> str
    # PGN válido: cabeçalhos White, Black, Result, Date, TimeControl e, se preciso, SetUp e FEN.

# types.py: EndReason ganha ABANDONMENT ("Adversário desconectou")
# clock.py: TimeControl ganha BLITZ_3_2, CLASSIC_15_10. Os presets antigos continuam.
# engine.py: GameEngine ganha abandon(color) -> GameResult e final_fen -> str
#            e, para a sala em rede ser a autoridade do resultado, finish_with(result) -> GameResult e take_back_last_move()
```

Acréscimos feitos na implementação: `search_board.py` (tabuleiro compacto de inteiros, só para a busca, provado pelos mesmos perft do motor) e `evaluation.py`; `analyze` e `SearchReport`; `Board.copy()`, `Board.undoable_moves` e `GameEngine.start_fen`.

**CPU em thread, não em processo.** Medido com a cena de `tools/benchmark.py`: thread com o intervalo padrão do Python deixa a tela em 9,5 FPS; com `sys.setswitchinterval(0.0002)` durante a busca, 58,7 FPS (58,9 sem CPU); com a câmera girando, é preciso também dormir 1 ms em cada `should_stop`. Processo separado daria 58,7 FPS com mais nós por segundo, mas exigiria `multiprocessing` e `freeze_support` no executável, um risco a mais na demonstração. Regra: copiar o tabuleiro com `board.copy()` na thread principal, antes de iniciar a thread, porque `legal_moves_from` faz `apply` e `undo` temporários no tabuleiro real.

### 10.3 Contrato de `xadrez.data`

```python
# paths.py
def data_dir() -> Path    # %APPDATA%/ChessTheGame, ~/Library/Application Support/ChessTheGame ou ~/.local/share/chess-the-game
                          # A variável de ambiente CHESS_THE_GAME_DATA substitui o local: é o que os testes usam.

# accounts.py
class AccountError(Exception): ...   # mensagem em pt-BR, pronta para a tela
class AccountStore:
    def __init__(self, directory: Path | None = None)
    def create(self, username: str, password: str) -> None     # 3 a 16 caracteres; senha de no mínimo 8
    def authenticate(self, username: str, password: str) -> bool
    def usernames(self) -> list[str]
    # PBKDF2-HMAC-SHA256 com sal por usuário. Nunca grava a senha. Nome sem diferenciar maiúsculas.

# history.py
@dataclass(frozen=True)
class MatchRecord:        # played_at (ISO), opponent, opponent_kind ("local", "cpu", "rede"), difficulty | None, color,
                          # outcome ("vitoria", "derrota", "empate"), reason, moves, seconds, time_control, mode, pgn, final_fen
class HistoryStore:
    def __init__(self, username: str, directory: Path | None = None)
    def add(self, record: MatchRecord) -> None     # mantém as 50 mais recentes
    def records(self) -> list[MatchRecord]         # mais recente primeiro
    def stats(self) -> HistoryStats                # played, wins, losses, draws
```

Regras: escrita atômica (arquivo temporário e troca). Arquivo corrompido não derruba o jogo: é guardado com outro nome, e a lista começa vazia. O histórico lido do disco é entrada não confiável: ao carregar, cada texto é cortado no limite do campo, e lances e duração param em um teto, sem perder o registro. Nada disso vai para o repositório.

### 10.4 Contrato de `xadrez.net`

```python
# room_code.py
def encode_room_code(ipv4: str) -> str      # 7 caracteres: ip * 6 + conferência, em base 31 (sem 0, O, 1, I, L)
def decode_room_code(code: str) -> str      # levanta ValueError com mensagem em pt-BR se o código for inválido
def local_ipv4() -> str                     # IP desta máquina na rede local, sem enviar pacote

# session.py
DEFAULT_PORT = 50507
class HostSession:
    def __init__(self, name: str, time_control: TimeControl, port: int = DEFAULT_PORT, bind: str = "0.0.0.0")
    code: str; start(); poll() -> list[NetEvent]; send_*(...); close()
class ClientSession:
    def __init__(self, name: str, code_or_host: str, port: int = DEFAULT_PORT, timeout: float = 5.0)
    start(); poll() -> list[NetEvent]; send_*(...); close()
# Comum: send_move(uci, clock_ms), send_resign(), send_draw_offer(), send_draw_answer(accept), send_rematch(), send_bye(), is_authority
# Só HostSession: send_result(result, plies)
# NetEvent: PeerJoined(name), GameStart(white, black, your_color, minutes, increment), MoveReceived(uci, clock_ms),
#           PeerResigned(), DrawOffered(), DrawAnswered(accept), RematchRequested(), PeerLeft(reason), NetworkError(message),
#           GameDecided(result, plies), só em quem entrou na sala
```

Protocolo: uma mensagem JSON por linha, com versão, hoje a 2. Quem cria a sala joga de brancas na primeira partida e é a autoridade do resultado: valida as jogadas, mede os dois relógios, decide o fim e manda `result`, com vencedor, motivo e em que lance a partida parou. Regras completas em `docs/plans/notas-ui.md`. Uma thread cuida do socket e entrega os eventos a `poll()`: a interface só espera em `close()`, por pouco tempo. Sinal de vida a cada 2 s, e 8 s sem resposta viram `PeerLeft`.

Segurança, porque a entrada vem da rede e não é confiável: só JSON, nunca `pickle` ou `eval`; linha de no máximo 4096 bytes; tipos conferidos; mensagem inválida encerra a conexão; o segundo a tentar entrar é recusado; a porta só fica aberta enquanto a sala existe. Quem recebe uma jogada a valida no próprio `GameEngine` antes de aceitar: jogada ilegal do outro lado encerra a sala. Quem entrou também confere o `result` contra o próprio tabuleiro.

### 10.5 Contrato de `xadrez.ui`: acréscimos

```python
class LoginScene        # entrar, criar conta, jogar como convidado
class MenuScene         # abas Jogar e Meu histórico; adversário, nível, cor, modo e tempo
class LobbyScene        # sala em rede: código grande, copiar convite, aguardando; ou digitar o código
class HistoryScene      # estatísticas, lista, detalhes, copiar PGN (ou aba dentro do menu)
class GameMode(Enum)    # TRAINING, MATCH, em match.py
class CpuPlayer         # roda choose_move fora do quadro; a tela não pode travar
MatchOptions            # ganha mode, opponent_kind, difficulty, human_color
GameScene               # copiar PGN, virar tabuleiro, arrastar peça, indicador "CPU pensando"
```

Divergências da implementação:

- **Histórico é aba do menu, não `HistoryScene`.** Está em `HistoryPanel` (`history_panel.py`): estatísticas e lista no painel, e a partida aberta como folha de papel sobre a mesa.
- **`App()` não tem contas nem rede.** Abre no menu como convidado, e "Criar sala" só avisa. O jogo do jogador é `App(require_login=True)`, que é o `main()` de `app.py`. Assim, testes e ferramentas não tocam a pasta de dados nem abrem porta, nem por um clique do macaco. Os testes de rede passam `App(network=...)`, com sessões em `127.0.0.1`. `LoginScene` e `LobbyScene` são cenas à parte, e só existem nesses dois casos.
- **Ordem dos tempos:** Sem limite, Blitz 3+2, Blitz 5, Rápida 10+0, Clássica 30 e Clássica 15+10. Clássica 30 vem antes de 15+10 porque `tests/ataque/` espera que ela venha logo depois de Rápida 10+0, como na versão 1.0.
- **Contra a CPU não há "Propor empate".** Não há com quem combinar.
- **Módulos a mais:** `arena_scene.py` (a mesa ao fundo e a base das telas fora da partida), `clipboard.py`, `cpu_player.py`, `match_record.py` e `net_link.py` (a sessão entre as cenas e as regras da mesa em rede). Resultado, tempo e proposta de empate em rede: ver `docs/plans/notas-ui.md`.

### 10.6 Identificadores novos

| ID | Requisito |
|---|---|
| RF17 | Oferecer os modos Treinamento e Partida |
| RF18 | Jogar contra a CPU nos níveis Easy, Medium, Hard e Hardcore, escolhendo a cor |
| RF19 | Jogar em rede local por sala com código de 7 letras |
| RF20 | Entrar com conta e senha, criar conta ou jogar como convidado |
| RF21 | Guardar as últimas 50 partidas da conta, com estatísticas, PGN e FEN final |
| RF22 | Copiar o PGN da partida |
| RF23 | Arrastar a peça para jogar e virar o tabuleiro |
| RF24 | Oferecer os tempos Blitz 3+2, Rápida 10+0 e Clássica 15+10 |
| RNF08 | Segurança: senha nunca gravada em claro; entrada da rede tratada como não confiável |
| RNF09 | A CPU pensando não pode derrubar os 60 FPS |

Casos de uso novos: UC10 Jogar contra a CPU; UC11 Criar sala em rede; UC12 Entrar em sala; UC13 Entrar na conta; UC14 Consultar histórico; UC15 Copiar PGN.

Casos de teste novos: motor e IA de CT-70 a CT-79; dados de CT-80 a CT-84; rede de CT-85 a CT-89; interface de CT-90 a CT-99; ataques do QA a partir de CT-100.

| ID | Foco | RF |
|---|---|---|
| CT-70 | CPU sempre devolve jogada legal, sem alterar o tabuleiro | RF18 |
| CT-71 | CPU acha mate em 1 nos níveis Medium, Hard e Hardcore | RF18 |
| CT-72 | CPU acha mate em 2 nos níveis Hard e Hardcore | RF18 |
| CT-73 | CPU não entrega a dama de graça a partir do Medium | RF18 |
| CT-74 | A força cresce com o nível, em partidas entre os níveis | RF18 |
| CT-75 | Cancelamento e limite de tempo da busca são respeitados | RF18, RNF09 |
| CT-76 | PGN válido, com resultado e cabeçalhos | RF21, RF22 |
| CT-77 | Tempos com incremento | RF24 |
| CT-80 | Conta: criar, entrar, recusar senha errada e nome repetido | RF20 |
| CT-81 | Senha nunca aparece no arquivo | RNF08 |
| CT-82 | Histórico: mantém 50, ordem e estatísticas | RF21 |
| CT-83 | Arquivo corrompido não derruba o jogo | RF20, RF21 |
| CT-85 | Código de sala: ida e volta, e recusa de código inválido | RF19 |
| CT-86 | Partida inteira entre duas sessões por socket | RF19 |
| CT-87 | Queda de conexão vira evento, sem travar | RF19 |
| CT-88 | Mensagens inválidas e maliciosas são recusadas | RF19, RNF08 |
| CT-90 | Modo Partida esconde caminhos, ameaças e xeque; Treinamento mostra | RF17 |
| CT-91 | Partida contra a CPU até o fim, por eventos | RF18 |
| CT-92 | CPU pensando não bloqueia a entrada nem o desenho | RF18, RNF09 |
| CT-93 | Login, criação de conta e convidado | RF20 |
| CT-94 | Partida encerrada entra no histórico da conta | RF21 |
| CT-95 | Duas instâncias do jogo em rede, por eventos | RF19 |
| CT-96 | Arrastar a peça para jogar | RF23 |
| CT-97 | Virar o tabuleiro mantém o clique correto | RF23 |
| CT-98 | Copiar PGN | RF22 |
