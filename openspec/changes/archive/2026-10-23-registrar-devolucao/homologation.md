# Homologação — registrar-devolucao

Estado em 23/10/2026: **parcial**. Pré-requisitos e criação real conferidos; nenhuma devolução
real foi executada até esta revisão. Credenciais e dados pessoais ficam fora deste relatório.

## Aplicação no Xano `v1`

A CLI do Xano disponível localmente autentica em outro workspace (151867), sem os objetos do
aplicativo; o push não foi usado. O operador aplicou manualmente, pela interface, as tabelas
`rental` (enum `returned`, `returned_at`, `returned_by`) e `rental_return`, o endpoint
`POST /locacoes/{id}/devolucao` e as projeções de 13 campos.

## Incidente: tabela `rental` recriada

Durante a aplicação manual, a tabela `rental` foi excluída e recriada vazia. Não havia histórico
nem backup no Xano. Verificação somente de leitura, após a aplicação:

| Verificação | Resultado |
| --- | --- |
| `GET /locacoes/1`, `/2`, `/3` | HTTP 404 "Locação não encontrada." |
| Exemplares 1 e 4 | Fora da lista de disponíveis: ocupações das locações 1 e 2 sobreviveram sem locação |
| Auditoria | Evento `create_rental` da locação 1 preservado em `event_log` |
| Trava de gravação | Encontrada aberta no servidor; fechada pelo operador em seguida |
| Devolução de locação inexistente com a trava aberta | HTTP 500 em vez de 404, sem gravação (locação ausente) |

As locações 1 e 2 eram dados de teste e **não serão reconstruídas**. Decisão do operador:
remover somente as duas ocupações órfãs (exemplar 1/locação 1 e exemplar 4/locação 2),
preservando exemplares, filmes, clientes e `event_log`.

Consequências tratadas no código local (tasks 8.1–8.2):

- a numeração de `rental` recomeça em 1; eventos antigos de auditoria com o mesmo id não podem
  confirmar a auditoria de uma operação nova, então a conferência em repetições passou a exigir
  `created_at` posterior à própria operação;
- a devolução de locação inexistente passa a responder 404 por `db.has rental`, não pela mensagem
  do erro capturado.

Enquanto as ocupações órfãs existirem, a próxima locação receberia o id 1 e a ocupação seria
recusada pelo índice único de `rental_occupancy.rental_id`. A trava deve continuar fechada até a
limpeza.

## Resultados reais

Após a limpeza das ocupações órfãs e a reaplicação de `locacoes_id_devolucao_POST.xs` e
`locacoes_POST.xs` pelo operador, com a trava fechada (leituras e chamadas recusadas pela trava):

| Verificação | Resultado |
| --- | --- |
| `GET /locacoes/1` | HTTP 404 "Locação não encontrada." |
| Exemplares disponíveis | CAR-001, CREED-001 e 001 (exemplares do filme sem condição/status elegível continuam fora) |
| `POST /locacoes/0/devolucao` e `POST /locacoes` com ids 0 | HTTP 403 "Registro de locação ainda não habilitado." |
| App na porta 3000 com o código atual | Nova locação sem erros, aviso de trava, confirmação indisponível; locação inexistente exibida como não encontrada |

Janela de gravação aberta pelo operador (Xano e `.env`); criações pelo app:

| Verificação | Resultado |
| --- | --- |
| Locação 1 (CREED-001) e locação 2 (CAR-001), conta 3 | `GET` com HTTP 200, contrato de 13 campos, `status = active`, `returned_at`/`returned_by` nulos |
| Auditoria | Um evento `create_rental` com sucesso para cada locação (#926 e #933) |
| Disponibilidade | CREED-001 e CAR-001 saíram da lista; resta 001 |
| Ocupação da locação 1 | Operador relatou linha de `rental_occupancy` gravada **sem `rental_id`**: o campo perdeu a ligação quando `rental` foi recriada. Correção do esquema e do valor ainda não confirmada |

Não houve devolução: as locações 1 e 2 continuam `active` e não há evento `return_rental`.
Estrutura de `rental_return` e índices únicos não são visíveis pela API; a conferência depende
da interface do Xano.

## Pendências para concluir

1. Operador: confirmar `rental_occupancy.rental_id` como inteiro obrigatório ligado à `rental`
   recriada, com índice único, e as ocupações das locações 1 e 2 com o `rental_id` correto. Sem
   isso, a devolução responde "Ocupação inconsistente; devolução não registrada.".
2. Operador: conferir na interface os índices únicos de `rental_return` (`rental_id`;
   `returned_by` + `operation_key`).
3. Com autorização explícita e janela aberta: tarefas 6.2–6.6, usando as locações 1 e 2.
4. Fechar a trava no Xano e no `.env` e registrar o fechamento (6.7).

## Atualização de 23/10/2026

- O endpoint `POST /locacoes/{id}/devolucao` publicado tinha a tabela vazia (`db.get ""`, `db.edit ""`), e toda devolução respondia 500. Ele foi republicado com `rental`. `rental_return.rental_id` e `rental_occupancy.rental_id` tiveram a referência à `rental` restaurada.
- Falhas da transação passam a registrar o motivo interno no `event_log` (`return_rental`, `failed: …`), nunca na resposta.
- Devoluções reais confirmadas pelo app (locações 1 e 2). A auditoria de integridade (ocupação × ativas, `rental_return` × devolvidas, sobreposição por exemplar) não encontrou divergências.
- A trava `XANO_RENTAL_WRITES_ENABLED` permanece **aberta** por decisão de uso (apresentação). A tarefa 6.7 não fechou a trava.
- Cenários 6.3 a 6.6 confirmados pelo usuário; não há evidência automatizada registrada aqui.
