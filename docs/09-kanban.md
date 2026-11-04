# 9. Gestão do projeto: Kanban

## 9.1 Situação real

O enunciado pede evidência de uso de metodologia ágil, com prints mostrando a evolução das tarefas ao longo do semestre. Este capítulo registra só o que aconteceu de fato.

- O histórico real do projeto começa em 2026-11-03, conforme o `git log` abaixo. Não existe histórico anterior a essa data.
- O quadro no GitHub Projects ainda não foi criado, porque o repositório ainda não foi publicado. Por isso, ainda não há nenhum print de quadro.
- O script `tools/preparar_github.py` deixa o quadro pronto para ser criado, com as tarefas abaixo, quando o grupo autorizar a publicação.
- Os prints precisam ser capturados pelo grupo ao longo do uso. Eles não podem ser gerados depois, nem reconstruídos com datas passadas.

## 9.2 Colunas e tarefas

As colunas são as pedidas no enunciado. A fonte das tarefas é `docs/kanban/tarefas.json`. O limite de WIP proposto para a coluna "Em Andamento (WIP)" é de 3 tarefas.

<!-- GERADO:kanban -->
| Coluna | ID | Tarefa | Marco | Evidência |
|---|---|---|---|---|
| Backlog / A Fazer | T13 | Publicar o repositório no GitHub, com autorização do grupo | E4 | ainda não feita |
| Backlog / A Fazer | T14 | Confirmar pelo CI: Python 3.10, Linux e macOS (RNF02) | E4 | ainda não feita |
| Backlog / A Fazer | T15 | Criar o quadro no GitHub Projects e capturar os prints | E4 | ainda não feita |
| Backlog / A Fazer | T16 | Conferir a capa e entregar o PDF de requisitos e telas | E1 | ainda não feita |
| Backlog / A Fazer | T17 | Entregar o PDF de casos de uso | E2 | ainda não feita |
| Backlog / A Fazer | T18 | Entregar o PDF de classes e sequência | E3 | ainda não feita |
| Backlog / A Fazer | T19 | Entregar a documentação unificada e o código | E4 | ainda não feita |
| Backlog / A Fazer | T20 | Montar os slides e dividir a fala entre os integrantes | E5 | ainda não feita |
| Backlog / A Fazer | T21 | Ensaiar a demonstração e a defesa técnica | E5 | ainda não feita |
| Em Andamento (WIP) | T10 | Escrever requisitos, telas, UML, arquitetura, testes e PDF | E4 | em execução, sem commit |
| Em Andamento (WIP) | T12 | Gerar a documentação final depois das correções | E4 | em execução, sem commit |
| Concluído | T01 | Definir design, contratos e identificadores | E4 | commit 714b188 |
| Concluído | T02 | Implementar o motor de regras oficiais | E4 | commit 411f20f |
| Concluído | T03 | Testar o motor, com perft e casos CT-01 a CT-21 | E4 | commit 411f20f |
| Concluído | T04 | Implementar o pipeline 3D em numpy e pygame | E4 | commit ed3143c |
| Concluído | T05 | Testar os gráficos, casos CT-30 a CT-36 | E4 | commit ed3143c |
| Concluído | T06 | Implementar menu, partida, HUD, pausa, promoção e vitória | E4 | commit 02e2248 |
| Concluído | T07 | Testar a interface por eventos, casos CT-40 a CT-49 | E4 | commit 02e2248 |
| Concluído | T08 | Travar em 60 FPS reais e eliminar o quadro lento ao iniciar | E4 | commit c5c150b |
| Concluído | T09 | Auditar o código e atacar o jogo (QA), casos CT-50 em diante | E4 | commit 86de291 |
| Concluído | T11 | Aplicar as correções apontadas pelo QA | E4 | commit 86de291 |
<!-- FIM:kanban -->

## 9.3 Evolução real pelo git

Tabela gerada do `git log`, com as datas e as mensagens originais dos commits.

<!-- GERADO:evolucao -->
| Data e hora | Commit | Mensagem |
|---|---|---|
| 2026-11-03 20:26 | `714b188` | chore: estrutura inicial do projeto e documento de design |
| 2026-11-03 21:00 | `411f20f` | feat(core): motor de regras oficiais do xadrez |
| 2026-11-03 21:10 | `ed3143c` | feat(graphics): pipeline 3D low-poly proprio em numpy e pygame |
| 2026-11-04 01:55 | `02e2248` | feat(ui): menu, partida, HUD, pausa, promocao e tela de vitoria |
| 2026-11-04 01:56 | `c5c150b` | fix(ui): trava em 60 FPS reais e elimina o quadro lento ao iniciar a partida |
| 2026-11-04 14:09 | `86de291` | fix: corrige os defeitos provados pelo QA e acrescenta os testes de ataque |
<!-- FIM:evolucao -->

## 9.4 Prints do quadro

Espaços reservados. Nenhum destes prints existe ainda. O grupo deve substituir cada item pela imagem real, com a data real da captura.

| Momento | Situação |
|---|---|
| Quadro logo depois de criado | A capturar pelo grupo |
| Tarefas de correção do QA em andamento | A capturar pelo grupo |
| Documentação em revisão | A capturar pelo grupo |
| Slides da apresentação em andamento | A capturar pelo grupo |
| Quadro antes da entrega final | A capturar pelo grupo |

Para criar o quadro:

```
python tools/preparar_github.py              # só mostra o que faria
gh auth refresh -s project                   # dá ao token o escopo necessário
python tools/preparar_github.py --executar   # cria etiquetas, marcos, issues e quadro
```
