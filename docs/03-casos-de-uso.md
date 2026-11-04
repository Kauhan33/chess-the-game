# 3. Casos de uso

## 3.1 Diagrama

![Diagrama de casos de uso](uml/img/casos_de_uso.png)

**Atores.** Jogador 1 e Jogador 2 são especializações de Jogador: qualquer um deles faz as mesmas ações, cada um na sua vez. O Sistema / Motor de Regras é o ator que decide o que é legal e quando a partida termina.

**Relacionamentos.**

- UC02 inclui UC06: toda jogada passa pela seleção, que calcula e mostra os caminhos.
- UC02 inclui UC07: todo lance aceito é seguido da verificação de xeque e de fim de jogo.
- UC05 estende UC02: só acontece quando o peão chega à última fileira.
- UC08 estende UC03: desistir e propor empate são opções da tela de pausa.

As mensagens entre aspas nos fluxos abaixo são os textos reais do jogo.

## 3.2 Especificação

### UC01 Iniciar Partida

| | |
|---|---|
| **Atores** | Jogador 1, Jogador 2 |
| **Pré-condição** | O jogo está aberto no menu inicial. |
| **Pós-condição** | Há uma partida em andamento, com as brancas na vez e o relógio correndo. |

**Fluxo principal**

1. O sistema mostra os campos "Brancas" e "Pretas", os seletores "Tempo por jogador" e "Câmera" e o botão "Iniciar partida".
2. Os jogadores digitam os nomes, de até 16 caracteres.
3. Os jogadores escolhem o tempo: "Sem limite de tempo", "Blitz: 5 minutos", "Rápida: 10 minutos" ou "Clássica: 30 minutos".
4. Os jogadores escolhem a câmera: "Gira a cada turno" ou "Fixa no lado das Brancas".
5. Um dos jogadores aciona "Iniciar partida".
6. O sistema cria o motor com essas opções, monta o tabuleiro na posição oficial e mostra a partida.

**Fluxos alternativos**

- **A1, só teclado:** Tab e as setas verticais movem o foco. As setas laterais trocam a opção do seletor. Enter avança e, no botão, inicia a partida.
- **A2, nome vazio:** o campo vazio, ou só com espaços, vira "Jogador 1" ou "Jogador 2".
- **A3, ajuda:** "Ver todos os controles" ou F1 abre a lista de controles sobre o menu.
- **A4, sair:** o botão "Sair" encerra o jogo.

**Fluxo de exceção**

- **E1, caractere que a fonte não desenha:** o caractere é ignorado e o nome continua sendo digitado.

### UC02 Executar Jogada

| | |
|---|---|
| **Atores** | Jogador da vez, Motor de Regras |
| **Pré-condição** | Partida em andamento, sem peça no ar e sem sobreposição aberta. |
| **Pós-condição** | A peça está na casa de destino, o lance está na planilha e a vez e o relógio passaram ao adversário. |

**Fluxo principal**

1. O jogador clica em uma peça da sua cor.
2. O sistema seleciona a peça, levanta o modelo e mostra os caminhos (UC06).
3. O jogador clica em uma casa de destino válida.
4. O motor valida a jogada e a executa.
5. O sistema anima o voo da peça, soma as capturas ao painel e anota o lance em SAN na planilha.
6. O motor verifica xeque e fim de jogo (UC07).
7. Quando a peça pousa, a placa do adversário acende e a faixa mostra "Vez de Jogador 2, Pretas". Com o giro ligado, a câmera vai para o lado dele.

**Fluxos alternativos**

- **A1, teclado:** as setas movem o cursor, e Enter ou Espaço fazem o papel do clique.
- **A2, trocar de peça:** clicar em outra peça da própria cor troca a seleção.
- **A3, cancelar:** clicar de novo na peça selecionada, clicar fora do tabuleiro ou apertar Esc limpa a seleção.
- **A4, roque e en passant:** a torre também voa no roque. No en passant, a captura é marcada na casa vazia de destino.
- **A5, promoção:** o peão chega à última fileira e o sistema abre o diálogo (UC05).
- **A6, peça sem jogada:** a peça é selecionada e a faixa mostra "Essa peça não tem jogada válida agora.".

**Fluxos de exceção**

Em todos eles, a faixa mostra a mensagem por 3 s, a casa treme, a seleção é limpa e o estado da partida não muda.

- **E1, tentativa fora do turno:** clique em peça do adversário sem seleção. Mensagem: "Essa peça é do adversário.".
- **E2, casa vazia sem seleção:** "Não há peça nessa casa.".
- **E3, jogada inválida:** a casa não está no padrão da peça. Mensagem: "Essa peça não pode fazer esse movimento.".
- **E4, jogada que expõe o rei:** "Essa jogada deixa o seu rei em xeque.".
- **E5, clique com a peça no ar:** o clique é ignorado até o pouso. O cursor e o relógio continuam.

### UC03 Pausar Jogo

| | |
|---|---|
| **Atores** | Jogador 1, Jogador 2 |
| **Pré-condição** | Partida em andamento, sem animação de fim de jogo. |
| **Pós-condição** | A partida volta ao estado anterior, com o relógio correndo de onde parou. |

**Fluxo principal**

1. O jogador aperta P, ou Esc sem peça selecionada, ou o botão "Pausar".
2. O sistema congela o relógio e as animações, escurece a mesa e mostra "Partida pausada" e "O relógio está parado.".
3. O jogador escolhe "Retomar", ou aperta P ou Esc.
4. O sistema fecha a sobreposição e devolve o relógio e o tabuleiro.

**Fluxos alternativos**

- **A1, opções da pausa:** "Reiniciar partida" (UC04), "Propor empate" e "Desistir" (UC08) e "Voltar ao menu" (UC09).
- **A2, painéis:** F3 e F4 continuam funcionando com a pausa aberta.

**Fluxos de exceção**

- **E1, tentativa de jogar:** cliques no tabuleiro e no painel, setas e atalhos não têm efeito enquanto a pausa está aberta.
- **E2, partida encerrada:** depois do fim do jogo, a pausa não abre.

### UC04 Reiniciar Partida

| | |
|---|---|
| **Atores** | Jogador 1, Jogador 2 |
| **Pré-condição** | Partida em andamento ou pausada. |
| **Pós-condição** | Tabuleiro na posição inicial, com as mesmas cores, relógios de volta ao tempo inicial e placar da série mantido. A partida abandonada não dá pontos. |

**Fluxo principal**

1. O jogador aperta R, ou escolhe "Reiniciar partida" na pausa.
2. O sistema pergunta "Reiniciar a partida?", com "O tabuleiro volta ao início." e "O placar da série é mantido.".
3. O jogador confirma em "Reiniciar".
4. O sistema reinicia o motor, limpa as animações e volta à vista padrão.

**Fluxo alternativo**

- **A1, desistir de reiniciar:** o foco começa na opção segura, "Voltar". Com ela, ou com Esc, nada muda.

**Fluxo de exceção**

- **E1, durante a animação de fim:** a tecla R não tem efeito.

### UC05 Promover Peão

| | |
|---|---|
| **Atores** | Jogador da vez, Motor de Regras |
| **Pré-condição** | A peça selecionada é um peão e o destino válido está na última fileira. Estende UC02. |
| **Pós-condição** | O peão sai e a peça escolhida nasce na casa de destino, com animação. |

**Fluxo principal**

1. O sistema abre o diálogo "Promoção do peão", com "Escolha a peça. Esc cancela o lance.".
2. O jogador escolhe "Dama", "Torre", "Bispo" ou "Cavalo".
3. O motor executa a jogada com a peça escolhida.
4. A peça voa e a nova peça nasce crescendo, com partículas.

**Fluxos alternativos**

- **A1, teclado:** as setas laterais e Enter escolhem, e as teclas 1 a 4 escolhem direto.
- **A2, cancelar:** Esc fecha o diálogo sem jogar e limpa a seleção.

**Fluxos de exceção**

- **E1, peão cravado:** o destino nem aparece como válido. Tentar a casa dá "Essa jogada deixa o seu rei em xeque." e o diálogo não abre.
- **E2, tempo esgotado na escolha:** o relógio segue correndo no diálogo. Se o tempo acabar, o diálogo fecha e a partida termina.

### UC06 Consultar Caminhos e Ameaças

| | |
|---|---|
| **Atores** | Jogador da vez, Motor de Regras |
| **Pré-condição** | Partida em andamento. |
| **Pós-condição** | A matriz de cores mostra o estado atual. A partida não muda. |

**Fluxo principal**

1. No início do turno, o motor calcula quais peças de quem joga estão ameaçadas e se há xeque.
2. O sistema marca as peças ameaçadas com cor de ameaça, triângulo e tint pulsante.
3. O jogador seleciona uma peça da sua cor.
4. O motor devolve as jogadas legais dela.
5. O sistema marca a origem em amarelo com cantos, os caminhos em verde com ponto e as capturas em vermelho com anel.

**Fluxos alternativos**

- **A1, xeque:** o rei fica vermelho, os atacantes ganham cantos e a faixa mostra "Xeque! Jogador 1 precisa defender o rei.".
- **A2, cursor:** a casa sob o mouse ou o cursor do teclado fica azul com cantos, exceto a selecionada.
- **A3, modo didático:** F4 mostra a matriz de estados em números, ao lado do tabuleiro.
- **A4, girar a câmera:** o jogador orbita ou aproxima a câmera para ver melhor, e os cliques continuam certos.

**Fluxo de exceção**

- **E1, peça do adversário:** o motor não devolve jogadas fora do turno. O fluxo segue a exceção E1 do UC02.

### UC07 Verificar Xeque e Fim de Jogo

| | |
|---|---|
| **Atores** | Motor de Regras |
| **Pré-condição** | Um lance acabou de ser aceito, ou o relógio avançou. Incluído em UC02. |
| **Pós-condição** | A partida continua com o estado de xeque atualizado, ou está encerrada com resultado. |

**Fluxo principal**

1. O motor verifica se o lado da vez tem alguma jogada legal.
2. Se tem, verifica material insuficiente, tripla repetição e regra dos 50 lances, nessa ordem.
3. Nenhuma condição vale. A partida continua e o sistema atualiza os alertas no início do turno.

**Fluxos alternativos**

- **A1, xeque-mate:** sem jogadas e em xeque. O adversário vence, a faixa mostra "Xeque-mate! Jogador 1 venceu.", o rei tomba e há fogos por 2,2 s antes da tela final.
- **A2, afogamento ou empate automático:** sem vencedor, com 0,5 ponto para cada. A faixa mostra, por exemplo, "Empate: Afogamento". A tela final vem em 0,9 s.
- **A3, tempo esgotado:** a cada quadro, `tick` confere o relógio de quem joga. Quem zerou perde, salvo se o adversário só tiver o rei, caso em que é empate.

**Fluxo de exceção**

- **E1, lance depois do fim:** o motor responde "A partida não está ativa." e nada muda.

### UC08 Encerrar Partida

| | |
|---|---|
| **Atores** | Jogador 1, Jogador 2, Motor de Regras |
| **Pré-condição** | A pausa está aberta. Estende UC03. |
| **Pós-condição** | A partida está encerrada, com os pontos somados à série, e a tela final aparece. |

**Fluxo principal: desistência**

1. O jogador da vez escolhe "Desistir" na pausa.
2. O sistema pergunta "Desistir da partida?", com "Jogador 1 entrega a partida." e "A vitória vai para Jogador 2.".
3. O jogador confirma em "Desistir".
4. O motor registra a vitória do adversário por desistência.

**Fluxo alternativo: empate por acordo**

1. O jogador da vez escolhe "Propor empate".
2. O sistema mostra "Proposta de empate", com "Jogador 1 propõe empate." e "Jogador 2, você aceita?".
3. O outro jogador escolhe "Aceitar empate".
4. O motor registra o empate, com 0,5 ponto para cada.

**Fluxos de exceção**

- **E1, empate recusado:** "Recusar", ou Esc, fecha tudo, e a faixa mostra "Jogador 2 recusou o empate.". A partida segue.
- **E2, desistência cancelada:** "Voltar", ou Esc, retorna à pausa. O foco já começa nessa opção.

### UC09 Pedir Revanche ou Voltar ao Menu

| | |
|---|---|
| **Atores** | Jogador 1, Jogador 2 |
| **Pré-condição** | A tela de fim de jogo está aberta. Para voltar ao menu, a pausa também serve. |
| **Pós-condição** | Nova partida com o placar mantido, ou menu com os nomes lembrados e uma série nova. |

**Fluxo principal: revanche**

1. O sistema mostra o resultado, o vencedor, o motivo, o número de lances e o placar da série.
2. O jogador escolhe "Revanche com cores trocadas".
3. O motor inverte as cores e começa outra partida, com o mesmo placar.
4. O sistema limpa as animações e volta à vista padrão.

**Fluxo alternativo: voltar ao menu**

1. O jogador escolhe "Voltar ao menu".
2. O sistema mostra o menu, com os nomes e as opções da partida anterior.
3. A próxima partida cria um motor novo, com o placar zerado.

**Fluxo de exceção**

- **E1, voltar ao menu pela pausa:** o sistema pergunta "Voltar ao menu?", com "A partida é abandonada e o placar" e "da série começa de novo.". "Voltar" ou Esc cancela.
