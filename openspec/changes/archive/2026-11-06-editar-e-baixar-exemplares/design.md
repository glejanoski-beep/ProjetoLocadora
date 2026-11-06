# Design

## Context

- `exemplar` tem `identificador` (índice único), `filme_id`, `operational_condition` (`unverified | available | unavailable`) e os campos da última conferência.
- Uma cópia é elegível para locação só com condição `available`, filme `active` e sem ocupação.
- `POST /locacoes` bloqueia conta → cliente → exemplar → filme e exige `available`.
- `rental` guarda cópias de `exemplar_identifier`, `film_id` e `film_title` do momento da locação.
- O cadastro de exemplares (`POST /exemplares`) não usa a trava `XANO_RENTAL_WRITES_ENABLED`. É manutenção de cadastro, não operação de locação.
- Preconditions dentro de `db.transaction` sem `try_catch` respondem com o código HTTP correto, como em `PATCH /locacoes/exemplares/{id}/condicao`, já homologado.

## Decisions

### Baixa como estado do exemplar, não exclusão

Campos novos e anuláveis em `exemplar`:
- `retired_at`: preenchido indica que a cópia está baixada;
- `retired_by`;
- `retire_kind`: `lost | damaged | discarded | other`;
- `retire_reason`.

Sem backfill: os exemplares existentes continuam ativos.

A baixa também grava `operational_condition = "unavailable"`, com `condition_confirmed_at/by` e `condition_reason = "Baixa: <motivo>"`. Assim, `POST /locacoes` e `GET /locacoes/exemplares-disponiveis` já recusam ou omitem a cópia, sem mudar a regra de elegibilidade. A conferência operacional passa a recusar exemplar baixado, para que ninguém o volte a `available` sem reativação.

A alternativa de um enum `status` separado exigiria alterar as duas consultas de elegibilidade e a criação de locação. A solução escolhida reaproveita a invariante que já existe.

Reativar limpa os campos de baixa e volta a condição para `unverified`. A cópia precisa de nova conferência antes de ser alugada, porque não se presume que um exemplar encontrado está apto. A baixa e a reativação ficam registradas no log de eventos com o tipo e o motivo.

### Edição com proteção do histórico

`PATCH /exemplares/{id}` recebe `identificador` e `filme_id` (formulário completo). Na transação, bloqueia conta → exemplar, e então:
1. Exige que o exemplar exista e não esteja baixado.
2. Identificador não vazio e único entre os demais exemplares, por comparação exata, com o índice único como última garantia.
3. Se `filme_id` mudou: exige filme existente e nenhuma locação registrada para a cópia (`db.has rental` por `exemplar_id`). Mensagem: "Exemplar com locações registradas não pode trocar de filme."
4. Atualiza só `identificador` e `filme_id`.

O identificador pode mudar mesmo com histórico, porque cada locação guarda o identificador do seu momento. A troca de filme, ao contrário, faria a cópia "pertencer" a outro filme em relatórios e na ocupação.

### Concorrência

A baixa bloqueia conta → exemplar e só então verifica a ocupação.
- Se a criação da locação chegou antes, ela segurava o bloqueio do exemplar até o commit. A baixa vê a ocupação e é recusada ("Exemplar alugado: registre a devolução antes da baixa.").
- Se a baixa chegou antes, a criação encontra a condição `unavailable` e é recusada.

A edição usa a mesma ordem. Por isso uma locação criada ao mesmo tempo faz a troca de filme ser recusada.

### Permissões e trava

As três operações exigem `admin` ativo (`enforce_role` e conferência da conta bloqueada), sem a trava de gravação de locações, como o cadastro. Todas auditam após o commit, e falha de auditoria não desfaz a operação.

### Contrato da listagem

`GET /exemplares` acrescenta `baixado` (bool), `baixa_tipo` (texto ou vazio) e `baixa_motivo` (texto ou vazio). O app normaliza respostas antigas, sem esses campos, como cópia ativa, para continuar funcionando antes da publicação.

### Interface

Em `/exemplares`, para `admin`, cada cópia é um botão que abre o diálogo "Exemplar <identificador>". O diálogo tem:
- edição de identificador e filme, com o seletor de filme desabilitado e uma explicação quando a troca for recusada;
- "Dar baixa", com tipo, motivo e confirmação;
- "Reativar", só para cópia baixada, com motivo.

Para `member`, a cópia continua sendo só um dado. "Mostrar baixados" (padrão desligado) inclui as cópias baixadas, com o selo "Baixado" e o tipo. As contagens por filme e o resumo consideram só as cópias ativas, e o resumo informa quantas estão baixadas.

## Risks / Trade-offs

- **O histórico de baixas fica só no log de eventos:** aceitável para o porte atual. Uma tabela própria pode vir depois.
- **O total do dashboard inclui baixados:** documentado como fora do escopo, para não mudar um contrato já homologado.
- **Reativação exige nova conferência:** é um passo a mais para o admin, mas evita alugar uma cópia que não foi verificada.

## Migration Plan

1. App tolerante à listagem antiga.
2. Publicar no `v1`: campos novos em `exemplar`, endpoints novos, listagem e conferência atualizadas.
3. Conferir com um exemplar de teste: editar, dar baixa (confirmar que some das opções de locação), reativar e conferir.
4. Rollback: remover os endpoints. Os campos anuláveis não afetam o restante.
