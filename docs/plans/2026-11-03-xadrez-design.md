# Xadrez The Game: design e contratos

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

# camera.py
class Camera:
    def __init__(self, viewport=(0, 0, 1280, 720), yaw=0.0, pitch=radians(52), distance=11.5, fov_y=radians(38))
    set_viewport(x, y, w, h); view_matrix; projection_matrix
    project(points) -> (pontos_tela (N, 2), profundidade (N,))
    screen_ray(sx, sy) -> (origem, direção)
    pick_plane(sx, sy, plane_y=0.0) -> (x, z) | None
    pick_square(sx, sy) -> (file, rank) | None
    orbit_to(yaw, duration); orbit_by(dyaw, dpitch); zoom_by(factor); update(dt); is_moving

# mesh.py e models.py
class Mesh:   # vertices (N, 3), faces, face_normals, face_centers
lathe(profile, segments), extrude(polygon_2d, depth), box(w, h, d), merge(*meshes)
PIECE_KINDS; build_piece_meshes() -> dict[str, Mesh]

# lighting.py
class DirectionalLight:  # direction, color, ambient, diffuse; shade(normals, base_color) -> cores

# color_matrix.py: requisito "indicação por matriz de cores"
class CellState(IntEnum):  # NONE, LAST_MOVE, PATH, CAPTURE, THREAT, CHECK, SELECTED, CURSOR (prioridade crescente)
class ColorMatrix:
    states: numpy (8, 8) uint8 indexado por [file, rank]
    clear(), set(file, rank, state), set_many(squares, state), state_at(file, rank)
    rgb(time=0.0) -> numpy (8, 8, 3) uint8   # base do tabuleiro + paleta + pulso por estado

# animation.py
easing: linear, ease_in_out_cubic, ease_out_back, ease_out_bounce
class Tween: start, end, duration, easing; update(dt), value, is_done
class PieceAnimation:   # arco de movimento: model_matrix() compõe translação + rotação + escala
class CaptureAnimation; class SpawnAnimation; class KingFallAnimation

# particles.py
class ParticleSystem:
    def __init__(self, capacity=2000, gravity=-9.8, floor_y=0.0, restitution=0.45, seed=None)
    emit(position, count, color, speed, life, size)
    capture_burst(position, color); trail(position, color); victory_fireworks(position, colors)
    update(dt)              # gravidade, arrasto, colisão com o piso por reflexão do vetor velocidade
    alive_count; positions; colors; sizes; alphas

# renderer.py
class Renderer3D:
    def __init__(self, camera, light=None)
    begin(surface); draw_board(rgb_matrix); add_mesh(mesh, model_matrix, color, tint=None, tint_amount=0.0, cast_shadow=True)
    add_marker(file, rank, kind, color)    # ponto = caminho; anel = captura (forma, além de cor)
    add_particles(system); flush()         # sombras, ordenação do pintor, desenho
    render_icon(mesh, color, size) -> pygame.Surface
```

## 6. Contrato de `xadrez.ui`

```python
class Scene(ABC):   # handle_event(event), update(dt), draw(surface), next_scene
class App:          # janela 1280x720 redimensionável, relógio a 60 FPS, troca de cenas; run()
class MenuScene     # nomes dos 2 jogadores, controle de tempo, giro de câmera, ajuda de controles
class GameScene     # tabuleiro 3D + HUD; seleção, promoção, pausa, reinício, animações
class GameOverScene # vencedor, motivo, placar da série, fogos; revanche ou menu
class Hud; widgets: Button, TextInput, Selector
theme.py            # paleta e tipografia, com fallback de fontes do sistema
```

Controles: mouse (clique seleciona e move; botão direito arrasta e orbita; roda dá
zoom) e teclado (setas movem o cursor; Enter ou Espaço confirma; Esc cancela; P pausa;
R reinicia com confirmação; T liga o giro por turno; F3 mostra FPS).

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
