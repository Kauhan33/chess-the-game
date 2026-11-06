# 2. Protótipos de tela e UI/UX

## 2.1 Wireframes e telas reais

Os wireframes são esboços de baixa fidelidade, em tons de cinza, gerados por `tools/gerar_wireframes.py`. Eles mostram a organização de cada tela. Os prints ao lado são do jogo real, gerados por `tools/capturar_telas.py`, que chega a cada tela por eventos de mouse e teclado. Os nomes nos prints são sempre "Jogador 1" e "Jogador 2", e nada é lido da pasta de dados de ninguém.

| Wireframe | Print real |
|---|---|
| ![Wireframe da tela de entrada](img/wireframes/wireframe_login.png) | ![Tela de entrada](img/tela_login.png) |
| ![Wireframe do menu](img/wireframes/wireframe_menu.png) | ![Menu em 2 jogadores](img/tela_menu.png) |
| ![Wireframe do menu contra a CPU](img/wireframes/wireframe_menu_cpu.png) | ![Menu contra a CPU](img/tela_menu_cpu.png) |
| ![Wireframe da sala](img/wireframes/wireframe_sala.png) | ![Sala criada, com o código](img/tela_sala.png) |
| ![Wireframe de entrar na sala](img/wireframes/wireframe_entrar_sala.png) | ![Entrar em uma sala](img/tela_entrar_sala.png) |
| ![Wireframe do histórico](img/wireframes/wireframe_historico.png) | ![Histórico, com uma partida aberta](img/tela_historico.png) |
| ![Wireframe da partida](img/wireframes/wireframe_partida.png) | ![Partida em andamento](img/tela_partida.png) |
| ![Wireframe do modo Partida](img/wireframes/wireframe_modo_partida.png) | ![Modo Partida, com a mesma seleção de "Caminhos válidos"](img/tela_modo_partida.png) |
| ![Wireframe do fim de jogo](img/wireframes/wireframe_fim_de_jogo.png) | ![Tela de vitória](img/tela_vitoria.png) |

**Tela principal da partida.** O tabuleiro é a área jogável. O painel da direita traz o HUD: placa de cada jogador com nome, pontuação e cronômetro, as peças capturadas, a planilha de lances, a linha com o modo e o tempo e os botões. O indicador de vez aparece de três formas: a placa acesa, a etiqueta "Joga agora" e a faixa no alto do tabuleiro.

**Fim de jogo.** O painel da partida vira o resultado, no mesmo lugar. O tabuleiro continua à vista, com a posição final e os fogos. Os botões oferecem revanche, volta ao menu e cópia do PGN. A partida vencida é escrita como em uma planilha de torneio: `1 - 0`, `0 - 1` ou `½ - ½`.

## 2.2 Telas da versão 1.1 e por que são assim

Nenhuma tela nova é um formulário solto. Login, menu e sala são a mesma mesa, com o tabuleiro girando à esquerda e o painel de nogueira à direita. `Tableau` é um só no jogo inteiro, então trocar de tela não faz a mesa pular nem refaz o fundo.

### Entrada

| Decisão | Por quê |
|---|---|
| "Jogar como convidado" na mesma tela, sem etapa a mais | Quem só quer jogar não precisa de conta. Criar conta é uma escolha, e a nota embaixo diz o que se perde sem ela. |
| Controle "Entrar" e "Criar conta" no alto do formulário | Os dois caminhos usam os mesmos campos. Ao criar, só entra "Repita a senha". |
| Mensagem única para senha errada e conta inexistente | Dizer qual dos dois falhou ensinaria quais nomes de conta existem. |
| Campo de senha desenha círculos, sem passar pela fonte | A senha nunca entra no cache de texto do tema, e não há glifo ausente em nenhuma máquina. |
| A nota diz que as contas ficam só neste computador | Evita a suposição de que a conta segue a pessoa para outra máquina. |
| Erro com triângulo e texto, com espaço reservado | Não depende só da cor (RNF04), e o formulário não pula quando o erro aparece. |

| | |
|---|---|
| ![Erro de senha, com a mesma mensagem para conta inexistente](img/tela_login_erro.png) | ![Criar conta, com a repetição da senha](img/tela_criar_conta.png) |

### Menu: adversário, modo, nível e tempo

| Decisão | Por quê |
|---|---|
| Abas "Jogar" e "Meu histórico", só com texto e filete de latão | Ficam acima dos campos na hierarquia, sem virar mais uma fileira de botões. |
| O formulário muda com o adversário | Mostra só o que importa: nomes e câmera em 2 jogadores, nível e cor contra a CPU, nome e sala em rede. |
| Controle segmentado em adversário, modo, nível e cor | Todas as opções ficam à vista, e a escolhida acende com a placa de latão. |
| Seletor com setas no tempo e na câmera | A lista de 6 tempos não cabe na largura em um controle segmentado. |
| Frase embaixo do modo e do nível | Explica a escolha na hora, e o espaço fica reservado para o formulário não pular. |
| Menu começa em Treinamento e em Easy | Treinamento é o comportamento da versão 1.0. Quem nunca jogou contra a CPU começa pelo nível mais fácil. |

| | |
|---|---|
| ![Menu em rede local](img/tela_menu_rede.png) | ![Histórico para o convidado, com o convite](img/tela_historico_convidado.png) |

### Sala em rede

| Decisão | Por quê |
|---|---|
| O código é o único elemento grande | É o que se dita para o outro jogador, de longe. |
| A sala mostra o modo e o tempo, que valem para os dois | Os dois jogam a mesma partida. Quem entra com outro modo no menu lê na faixa qual vale, em vez de descobrir jogando. |
| Código sem 0, O, 1, I e L | São os caracteres que se confundem ao ditar. O campo aceita minúsculas e espaços. |
| "Copiar convite" é o botão em foco | Quem está no mesmo chat não precisa ditar nada. |
| A sala avisa quando não há rede local | Sem rede, o código é o de `127.0.0.1` e só serve neste computador. A tela diz isso, em vez de fazer alguém esperar. |
| Erro de conexão cita código, rede e firewall | São as três causas prováveis, e a pessoa pode conferir cada uma. |
| Na partida, "Pausar" vira "Opções" | Em rede, o relógio não para. A tela diz "O relógio continua correndo.". |
| Proposta de empate em um cartão sobre a planilha, sem véu | Quem recebe vê o tabuleiro inteiro e continua jogando. Jogar um lance recusa, e assim ninguém perde no relógio só por receber propostas. |

| | |
|---|---|
| ![Partida em rede, do lado de quem criou a sala](img/tela_rede_partida.png) | ![Cartão de proposta de empate, sobre a planilha](img/tela_proposta_empate.png) |

### Histórico

| Decisão | Por quê |
|---|---|
| Estatísticas e lista no painel, e a partida aberta sobre a mesa | Abrir uma partida põe uma folha de papel escrita à tinta, com a mesma cor e a mesma sombra da planilha do HUD. A lista continua à vista. |
| Etiqueta de resultado com a palavra escrita | Vitória é a placa acesa, derrota é a placa vermelha e empate fica na sombra. A palavra está sempre lá: nunca só a cor (RNF04). |
| A roda rola o que está sob o mouse | Lista e lances rolam separados. |
| Convidado vê um convite, e não uma lista vazia | A aba explica para que serve a conta. |

| | |
|---|---|
| ![Lista do histórico, com as estatísticas](img/tela_historico_lista.png) | ![Modo Treinamento, na posição de comparação](img/tela_caminhos.png) |

### Modo Partida

| Decisão | Por quê |
|---|---|
| Ficam só peça selecionada, cursor e último lance | Dizem o que aconteceu, não o que fazer. |
| Recusa sempre igual: "Lance inválido.", sem tremor nem anel | O motivo seria uma dica. Lance ilegal, peça do adversário e casa vazia recebem o mesmo aviso. |
| Selecionar peça sem jogada não avisa nada | "Essa peça não tem jogada válida agora." entregaria uma cravada. |
| Planilha e cópia sem `+` e `#` até o fim | A notação contaria o xeque que a tela esconde. Depois do fim, ela volta completa. |
| O fim diz o motivo normalmente | A partida já acabou, e isso não é mais dica: depois do mate, o rei tomba e a casa dele é marcada. |
| Linha discreta "Modo Partida" no HUD | Quem joga sabe em que modo está, sem que isso tome o lugar de nada. |

### Contra a CPU

| Decisão | Por quê |
|---|---|
| A placa da CPU acende igual, com a etiqueta "Pensando" e três pontos em sequência | Mostra que ela não travou, por três círculos a cada quadro. |
| A faixa diz "CPU (Hardcore) está pensando" | O mesmo lugar em que se lê de quem é a vez. |
| Clicar na vez dela dá um aviso curto e não muda nada | "Aguarde: é a vez da CPU." explica por que o clique não fez nada. |
| Sem "Propor empate" | Não há com quem combinar. |
| Sem giro por turno | A câmera fica do lado de quem está na tela. "Virar" dá meia volta quando a pessoa quiser olhar do outro lado. |
| Easy e Medium esperam pelo menos 0,5 s para responder | Jogada instantânea parece defeito. |

![CPU Hardcore pensando](img/tela_cpu_pensando.png)

## 2.3 Outros estados da interface

| | |
|---|---|
| ![Caminhos válidos pela matriz de cores](img/tela_caminhos.png) | ![Peças sob ameaça](img/tela_ameaca.png) |
| ![Rei em xeque](img/tela_xeque.png) | ![Partida pausada](img/tela_pausa.png) |
| ![Diálogo de promoção](img/tela_promocao.png) | ![Partida empatada](img/tela_empate.png) |
| ![Modo didático, tecla F4](img/tela_didatico.png) | ![Painel de desempenho, tecla F3](img/tela_desempenho.png) |
| ![Ajuda de controles](img/tela_ajuda.png) | |

## 2.4 Justificativa gráfica

### Conceito

A interface imita uma mesa de torneio sob a luz de um abajur. O painel lateral é o resto da mesa e traz objetos de uma partida de verdade: uma placa para cada jogador, uma planilha de anotação em papel pautado e um filete de latão entre o painel e o tabuleiro.

A ideia central é que a luz do abajur acompanha quem joga. A placa da vez acende, com fundo claro e brilho quente. A outra fica na sombra. A troca leva 0,28 s e acontece junto com o relógio, assim que o lance é feito.

### Paleta

Todas as cores são quentes e vêm do mesmo mundo. O latão é a única cor de destaque do HUD.

| Papel | Nome no código | Cor |
|---|---|---|
| Madeira mais funda | `WALNUT_SHADOW` | `#17100B` |
| Nogueira, fundo de placa e painel | `WALNUT` | `#2A1B12` |
| Face de botão | `WALNUT_RAISED` | `#422C1C` |
| Borda de placa na sombra | `WALNUT_EDGE` | `#6C4E2E` |
| Latão escuro, borda de placa acesa | `BRASS_DARK` | `#8F6D33` |
| Latão, filete e bordas em foco | `BRASS` | `#C8A15A` |
| Latão claro, títulos e anel de foco | `BRASS_BRIGHT` | `#EBCB8B` |
| Marfim, texto principal e cor das peças | `IVORY` | `#F0E4C8` |
| Papel da planilha | `PAPER` | `#E9DCBE` |
| Tinta, texto sobre fundo claro | `INK` | `#24170E` |
| Texto secundário sobre madeira | `TEXT_MUTED` | `#C9B89A` |
| Alerta de tempo baixo sobre fundo escuro | `ALERT_ON_DARK` | `#FF8A70` |
| Alerta de tempo baixo sobre fundo claro | `ALERT_ON_LIGHT` | `#8C180E` |
| Placa de xeque | `ALERT_PLATE` | `#96241A` |
| Luz do abajur em volta da placa da vez | `LAMP_GLOW` | `#FFBA68` |

### Matriz de cores do tabuleiro

Cada estado de casa tem uma cor, e a maioria também tem uma forma. Assim, a informação não depende só de enxergar a diferença entre as cores (RNF04).

| Estado | Cor | Forma que acompanha a cor | No modo Partida |
|---|---|---|---|
| `LAST_MOVE` último lance | `#C6AC54` | Nenhuma: é só contexto | Aparece |
| `PATH` caminho | `#5CAC6C` | Ponto | Não aparece |
| `CAPTURE` captura | `#D84E3C` | Anel | Não aparece |
| `THREAT` ameaça | `#EC8A2C` | Triângulo, e a peça ganha tint pulsante | Não aparece |
| `CHECK` xeque | `#E02C2C` | Rei com tint vermelho e atacantes com cantos | Só depois do mate |
| `SELECTED` seleção | `#F4CE60` | Cantos, e a peça é levantada | Aparece |
| `CURSOR` cursor | `#68AADE` | Cantos | Aparece |

O azul do cursor é a única cor fria da tela. Em um tabuleiro todo quente, é o que se acha mais rápido.

### Contraste

As razões abaixo foram calculadas com a fórmula WCAG, a partir das cores do código. O teste `test_contraste_dos_textos_passa_de_4_5_para_1`, em `tests/ui/test_ui_tema.py`, exige pelo menos 4,5:1 nos pares principais.

| Par | Razão |
|---|---|
| Relógio em tinta sobre a placa acesa | 9,2:1 |
| Relógio em texto secundário sobre a placa na sombra | 7,9:1 |
| Tempo baixo sobre a placa acesa | 4,9:1 |
| Tempo baixo sobre a placa na sombra | 6,7:1 |
| Tinta sobre o papel da planilha | 12,8:1 |
| Marfim sobre botão | 10,3:1 |
| Texto secundário sobre nogueira | 8,5:1 |
| Marfim sobre a placa de alerta | 6,5:1 |

### Tipografia

O jogo só usa fontes do sistema, sem nada baixado. Cada papel tem uma lista de alternativas, e no fim dela está a fonte padrão do pygame. Há teste que abre o jogo inteiro sem nenhuma fonte do sistema.

| Papel | Windows | Onde aparece |
|---|---|---|
| Serifa de título, em negrito | Palatino Linotype | Título, nomes, lances, avisos e resultado |
| Sem serifa de rótulo | Franklin Gothic Medium | Rótulos, botões, teclas e ajuda |
| Números do relógio | Franklin Gothic Medium, em negrito | Relógio, pontos da série e código da sala |
| Monoespaçada | Consolas | Painéis F3 e F4 e FEN na folha do histórico |

- A Palatino tem algarismos alinhados, o que serve à planilha, e tom de documento de torneio.
- A Franklin Gothic é pesada e clara em tamanho grande. O relógio e o código da sala usam essa fonte porque precisam ser lidos de longe.
- O relógio não treme. `Theme.tabular` desenha cada dígito em uma célula da largura do dígito mais largo.
- Os tamanhos escalam com a janela, de 0,6 a 2 vezes. Em 1280x720, o relógio tem 60 px, e os rótulos, de 13 a 17 px.
- Nenhum glifo de xadrez em Unicode é usado. Os ícones são a própria malha 3D, então não há quadradinho de glifo ausente em nenhuma máquina.

### Forma

Toda placa e todo botão têm cantos cortados, as mesmas diagonais das faces low-poly das peças. O papel da planilha e a folha do histórico são a exceção: têm canto reto e sombra curta, porque são papel em cima da mesa.

## 2.5 Ergonomia

- **Saber de quem é a vez, de longe.** Placa clara contra placa escura é uma inversão total de fundo e texto. Três sinais confirmam: a etiqueta "Joga agora", a faixa "Vez de Jogador 1, Brancas" e, em 2 jogadores, a câmera, que gira para o lado de quem joga.
- **Saber quanto tempo resta, de longe.** O relógio é o maior elemento do painel. Abaixo de 30 s, ele muda de cor. No modo sem limite, mostra o tempo decorrido.
- **Cada jogador tem o seu canto.** As pretas ficam sempre em cima e as brancas sempre embaixo, com a planilha no meio, mesmo com a câmera girando.
- **Avisos no lugar da vez.** A recusa de jogada aparece na mesma faixa em que se lê de quem é a vez, em uma placa clara com triângulo. Em Treinamento, a peça recusada treme, e o xeque usa a placa vermelha.
- **Mouse e teclado.** A partida pode ser jogada inteira por qualquer um dos dois. As setas seguem o que se vê: com a câmera do lado das pretas, "para cima" anda para a fileira menor.
- **Clique e arrasto convivem.** Apertar em peça própria seleciona. Só depois de 6 pixels vira arrasto. Clicar de novo na peça selecionada desmarca ao soltar o botão, não ao apertar. Soltar na própria casa mantém a seleção, e soltar fora do tabuleiro só devolve.
- **Pausa de verdade em 2 jogadores e contra a CPU.** O véu escurece a mesa inteira, o relógio para, e só a sobreposição responde. Em rede, não há pausa.
- **Empate na mesma tela.** Em 2 jogadores, quem propõe abre o pedido. A pergunta traz o nome do outro jogador, que responde ali mesmo.
- **Clique duplo entre telas.** O 2º clique não aciona o que apareceu no mesmo lugar da tela nova: por 0,25 s, o clique até 3 pixels do anterior é descartado.

Em 640x360, os formulários não cabem na janela: "Sair do jogo" sai da tela, e "Iniciar partida" cobre "Ver todos os controles". O jogo não cai, e a partir de 640x480 está tudo certo. Foi aceito como limite (achado QA11-17).

## 2.6 Controles

| Entrada | Ação |
|---|---|
| Clique esquerdo | Seleciona a peça e joga |
| Clique esquerdo, arrastando | Leva a peça até o destino e joga ao soltar |
| Botão direito, arrastando | Gira a câmera |
| Roda do mouse | Aproxima e afasta a câmera. Na aba de histórico, rola o que está sob o mouse |
| Setas | Movem o cursor, conforme a visão |
| Enter ou Espaço | Confirma, como o clique |
| Esc | Cancela a seleção. Sem seleção, abre a pausa |
| P | Pausa a partida. Em rede, abre as opções, sem parar o relógio |
| R | Reinicia, depois de confirmar. Não vale em rede |
| T | Liga ou desliga o giro por turno. Só em 2 jogadores |
| V | Volta à vista padrão |
| F | Vira o tabuleiro |
| C | Copia o PGN da partida |
| A | Aceita a proposta de empate recebida em rede |
| H ou F1 | Mostra a ajuda, que só lista as teclas que valem nesta partida |
| F3 | Mostra FPS e polígonos |
| F4 | Modo didático: matrizes ao vivo |
| F11 | Liga ou desliga a tela cheia |
