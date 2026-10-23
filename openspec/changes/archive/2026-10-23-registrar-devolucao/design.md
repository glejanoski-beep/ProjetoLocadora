# Design

## Context

`rental` guarda o histórico permanente (`status` só `active`). `rental_occupancy` garante exclusividade, com índices únicos por `exemplar_id` e por `rental_id`. Disponível para nova locação = condição `available` + filme `active` + nenhuma ocupação. O `POST /locacoes` usa transação com `db.get ... lock=true` na ordem conta → cliente → exemplar → filme, chave de operação única por conta e auditoria após o commit. No runtime Xano, `throw` customizado terminou como HTTP 200; erros de negócio usam `precondition` com `inputerror`.

## Goals / Non-Goals

**Goals:** devolução atômica e idempotente, histórico preservado, liberação exata do exemplar, contrato compatível e interface clara.

**Non-Goals:** multas, pagamentos, cancelamento de devolução, condição física informada pelo `member`, listagem.

## Decisions

### Registro próprio de devolução

Tabela `rental_return`: `id`, `rental_id` (único), `returned_at` (servidor), `returned_by` (conta autenticada), `operation_key` (único por `returned_by` + chave). A locação só passa a `returned` com esse registro, como pede o domínio ("não deve ser marcada como devolvida sem um registro de devolução válido"). `rental` não perde campos; `due_at` e `rented_at` não são alterados. Atraso não é gravado: deriva de `returned_at > due_at`.

Alternativa descartada: só colunas de devolução em `rental`. Não dá unicidade própria nem chave de operação separada da criação.

Decisão de implementação: além de `rental_return`, `rental` recebe cópias anuláveis `returned_at` e `returned_by`, gravadas na mesma transação que cria o registro de devolução e muda o status. As consultas existentes apenas acrescentam os dois campos à projeção, sem nova consulta nem montagem de objeto. `rental_return` continua sendo a fonte da unicidade e da idempotência.

### Transação

`POST /locacoes/{id}/devolucao` (entrada: `operation_key`):

1. `enforce_role` (`member`) e trava `XANO_RENTAL_WRITES_ENABLED == "true"`.
2. Em `db.transaction`: bloquear a conta (`user`, ativa, `member|admin`), depois a locação (`rental`, `lock=true`).
3. Se já existe `rental_return` desta conta com a mesma chave: devolver esse resultado se for da mesma locação; caso contrário, conflito "Chave já utilizada para outra operação."
4. Exigir `status == "active"`; senão, conflito "Locação já devolvida."
5. Exigir a ocupação com `rental_id` desta locação. Ausente com status `active` é inconsistência: abortar com erro padrão, sem corrigir.
6. Inserir `rental_return`, atualizar `rental.status = "returned"`, apagar a ocupação pelo `rental_id`.
7. Após o commit, auditoria `return_rental`; falha de auditoria não desfaz a devolução.

A ordem conta → locação não forma ciclo com a criação (conta → cliente → exemplar → filme), que não bloqueia `rental`. Corrida devolução × nova locação do mesmo exemplar: a criação encontra a ocupação até o commit da devolução, e o índice único de `rental_occupancy.exemplar_id` impede duas ocupações. Duas devoluções simultâneas: o bloqueio da locação as serializa, e o índice único de `rental_return.rental_id` garante uma só no banco.

### Ocupação e histórico

Apagar a linha de `rental_occupancy` não apaga histórico: ela é a trava de exclusividade, e o histórico fica em `rental` e `rental_return`. Nada é removido de `rental`.

### Condição do exemplar

A devolução não altera `operational_condition`. O exemplar volta a ficar disponível se a última conferência continuar `available` e o filme estiver `active`, cumprindo "só volta ao estado disponível se sua condição permitir". Avaria constatada é registrada pela operação administrativa de condição já existente.

### Contrato e compatibilidade

As respostas de locação passam a ter 13 campos: os 11 atuais + `returned_at` (timestamp ou `null`) + `returned_by` (int ou `null`); `status ∈ {active, returned}`, coerentes entre si. O validador do app aceita os dois formatos antes da publicação do backend, para não quebrar o detalhe. A repetição da criação com a mesma chave pode devolver uma locação já devolvida, e isso deve ser aceito.

### Interface

O detalhe (`/locacoes/{id}`) ganha a seção "Registrar devolução" somente para locação `active`, com resumo, aviso de atraso e confirmação explícita. Chave gerada uma vez por tentativa; timeout ou resposta inválida viram resultado desconhecido, e a repetição usa a mesma chave. Com a trava desligada, aviso neutro e botão indisponível. Locação devolvida mostra "Devolvida", a data, o responsável e se foi no prazo ou com atraso, sem ação.

### Permissão

`member` e `admin`, como "Incluir locações" na matriz; a matriz em `docs/domain-model.md` deve registrar a devolução.

## Risks / Trade-offs

- [Avaria só tratada depois pelo admin] → exemplar danificado devolvido por um `member` volta a aparecer disponível até o admin alterar a condição.
- [Publicação do backend antes do app] → o detalhe recusaria a resposta de 13 campos; mitigação: publicar o cliente compatível primeiro.
- [Cota de 10 requisições/20 s] → devolução usa `auth/me` atual + POST + releitura; manter em 3 chamadas.
- [Comportamento real de `lock` e índices] → só a homologação em `v1` comprova; manter a trava fechada até lá.

## Migration Plan

1. App compatível com 11 e 13 campos (sem publicar nada).
2. Publicar no `v1`, com a trava fechada: enum `returned`, `rental_return`, endpoint e respostas ampliadas.
3. Homologação em janela autorizada; fechar a trava ao final.
4. Rollback: desativar o endpoint e manter a trava fechada, sem apagar `rental_return` nem reverter status.
