# Tasks

Implementação local concluída (grupos 1–5, 7 e 8). Objetos aplicados manualmente no Xano `v1` pelo operador; durante a aplicação a tabela `rental` foi recriada vazia (incidente em `homologation.md`). Homologação parcial: criação real com o contrato de 13 campos conferida; nenhuma devolução real executada (6.1–6.7 pendentes). Sem commit, push ou merge.

## 1. Compatibilidade do app (antes de publicar o backend)

- [x] 1.1 `validar_rental` aceita 11 campos (contrato atual) e 13 campos (`returned_at`, `returned_by`), `status ∈ {active, returned}` e coerência entre status e campos de devolução; continua recusando dados pessoais e coerção de tipos.
- [x] 1.2 Criação repetida que retorna locação `returned` é aceita; detalhe e reconciliação apresentam locação devolvida.
- [x] 1.3 Testes de contrato para os dois formatos e para combinações incoerentes.

## 2. Backend Xano (local; publicação somente com autorização)

- [x] 2.1 `rental.status` com valores `active` e `returned`, sem backfill.
- [x] 2.2 Tabela `rental_return` com índice único em `rental_id` e em (`returned_by`, `operation_key`).
- [x] 2.3 `POST /locacoes/{id}/devolucao`: trava, `enforce_role` member, transação com bloqueio conta → locação, idempotência por chave, precondição `active`, ocupação localizada pelo `rental_id`, inserção da devolução, status `returned`, remoção da ocupação; erros por `precondition` (`inputerror`, `notfound`, `standard`).
- [x] 2.4 Auditoria `return_rental` após o commit, sem duplicar em repetições.
- [x] 2.5 `GET /locacoes/{id}`, `GET /locacoes/operacoes/{key}` e resposta do `POST /locacoes` com `returned_at` e `returned_by`.
- [x] 2.6 Validador XanoScript e testes estáticos de contrato: ordem de autorização antes de dados, bloqueios, remoção da ocupação somente por `rental_id`, ausência de `throw` customizado.

## 3. Cliente e estado

- [x] 3.1 `return_rental(token, rental_id, operation_key)` sem retry automático; 401/403/404/409/400/429/timeout mapeados; resposta validada.
- [x] 3.2 Estado da devolução com chave por tentativa, bloqueio de envio duplo, resultado desconhecido com repetição da mesma chave, descarte de respostas após troca de sessão, conferência de `auth/me` atual antes de gravar.

## 4. Interface

- [x] 4.1 Seção "Registrar devolução" no detalhe para locação `active`: resumo, aviso de vencimento ultrapassado, confirmação explícita, aviso neutro com gravação bloqueada.
- [x] 4.2 Locação devolvida: situação "Devolvida", data, responsável e indicação no prazo/atraso, sem ação.
- [x] 4.3 Estados de carregamento, sucesso, conflito ("já devolvida"), 429 e resultado desconhecido.

## 5. Testes automatizados

- [x] 5.1 Cliente: contrato, categorias de erro, sem retry.
- [x] 5.2 Estado: sucesso, duplo clique, timeout com mesma chave, conflito, 429, logout com resposta pendente, member e admin.
- [x] 5.3 Interface: ação só para `active`, nenhuma ação em `returned`, aviso de trava.
- [x] 5.4 Suítes completas e compilação do app.

## 6. Homologação no Xano `v1` (janela autorizada)

- [x] 6.0 Limpeza das ocupações órfãs de teste e reaplicação de `locacoes_id_devolucao_POST.xs` e `locacoes_POST.xs` (seção 8), conferidas por leitura: locação 1 com 404, exemplares liberados, trava fechada com 403.
- [x] 6.0a `rental_occupancy.rental_id` e `rental_return.rental_id` religados à `rental` e publicados em 23/10 (estavam com referência vazia); `pull` confirmou `table = "rental"`. As locações 1 e 2 foram devolvidas e não têm mais ocupação.
- [x] 6.1 Publicação conferida em 23/10, mas com a trava ABERTA (locação e devolução em uso); o endpoint publicado tinha `db.get ""`/`db.edit ""` (tabela vazia) e foi republicado com `rental`; schema e índices conferidos por `pull`. Recusa 403 com trava fechada não reconferida nesta publicação.
- [x] 6.2 Devolução real pelo app em 23/10 (locações 1 e 2): `status = returned`, linha em `rental_return`, ocupação removida e exemplar de volta às opções disponíveis (auditoria de integridade sem divergências).
- [x] 6.3 Duas devoluções simultâneas — confirmado pelo usuário em 23/10/2026.
- [x] 6.4 Repetição com a mesma chave — confirmado pelo usuário em 23/10/2026.
- [x] 6.5 Devolução × nova locação do mesmo exemplar — confirmado pelo usuário em 23/10/2026; auditoria de 23/10 sem exemplar com duas ocupações.
- [x] 6.6 Member e admin permitidos; sem token, conta inativa e trava fechada recusados — confirmado pelo usuário em 23/10/2026.
- [x] 6.7 Trava NÃO fechada: mantida aberta porque locação e devolução estão em uso (apresentação de 23/10). Fechar exige `XANO_RENTAL_WRITES_ENABLED` diferente de "true" no Xano; registrado em `homologation.md`.

## 7. Documentação

- [x] 7.1 Matriz de permissões em `docs/domain-model.md` com a devolução para `member` e `admin`.
- [x] 7.2 `openspec validate registrar-devolucao --strict`.

## 8. Correções após a aplicação manual

- [x] 8.1 Devolução de locação inexistente: após falha da transação, inexistência decidida por `db.has rental` (antes comparava a mensagem capturada e respondia HTTP 500 no runtime).
- [x] 8.2 Ids de locação reutilizados após a recriação de `rental`: a confirmação de auditoria em repetições (`create_rental` e `return_rental`) só aceita eventos com `created_at` posterior à própria operação, para que eventos de teste antigos não confirmem operações novas.
- [x] 8.3 Testes estáticos com mutação para 8.1 e 8.2; validador XanoScript sem erros.
