# Design

## Context

- `rental` guarda `due_at` e, após a devolução, `returned_at`. Não há valor de locação: a multa não pode ser um percentual do preço.
- `POST /locacoes/{id}/devolucao` executa uma transação com bloqueio conta → locação → ocupação, chave de operação por conta e auditoria após o commit. Erros de negócio usam `precondition` (um `throw` customizado terminou como HTTP 200 no runtime).
- `POST /locacoes` bloqueia conta → cliente → exemplar → filme.
- A cota da conta é de 10 requisições a cada 20 s.
- O plano Xano não oferece armazenamento de arquivos, mas esta change não precisa dele.

## Goals / Non-Goals

**Goals:**
- política de multa simples, previsível e explicável ao cliente no balcão;
- multa gerada atomicamente com a devolução;
- pagamentos que nunca ultrapassam o saldo;
- histórico financeiro imutável, com ajustes rastreáveis;
- bloqueio por inadimplência aplicado no backend.

**Non-Goals:** gateway, recibo fiscal, juros, multa por avaria ou perda, edição do valor, geração retroativa, relatórios.

## Decisions

### Política de cálculo

Como não existe preço de locação, a multa é uma diária fixa:

```
tolerância_ms = XANO_FINE_GRACE_MINUTES × 60 000          (padrão 120 min)
atraso_ms     = returned_at − due_at

se atraso_ms ≤ tolerância_ms:
    dias = 0  → nenhuma multa é criada
senão:
    dias  = ceil(atraso_ms / 86 400 000)                 (blocos de 24 h a partir do vencimento)
    valor = min(dias × XANO_FINE_DAILY_CENTS,            (padrão 300 = R$ 3,00)
                XANO_FINE_CAP_CENTS)                     (padrão 9 000 = R$ 90,00)
```

Exemplos com vencimento em 10/11 às 20:00 (horário de Brasília):

| Devolução | Atraso | Dias | Multa |
| --- | --- | --- | --- |
| 10/11 21:30 | 1 h 30 | — (tolerância) | nenhuma |
| 10/11 23:00 | 3 h | 1 | R$ 3,00 |
| 12/11 19:00 | 47 h | 2 | R$ 6,00 |
| 12/11 21:00 | 49 h | 3 | R$ 9,00 |
| 25/12 20:00 | 45 dias | 45 → teto | R$ 90,00 |

Justificativas:
- **Blocos de 24 h a partir do vencimento, em vez de dias de calendário:** o resultado não depende de fuso nem de horário de verão, é idêntico no backend e na interface e é fácil de explicar ("cada 24 h de atraso é uma diária").
- **Tolerância:** evita multar quem chega minutos depois do horário. Ultrapassada a tolerância, a contagem parte do vencimento, e não do fim da tolerância, para que 3 h de atraso valham uma diária e não zero.
- **R$ 3,00:** valor da ordem de uma diária de locadora, suficiente para estimular a devolução sem ser punitivo.
- **Teto de 30 diárias:** passado um mês, o caso deixa de ser atraso e passa a ser perda ou negociação, que ficam fora deste escopo. Isso evita dívidas sem limite.
- **Centavos inteiros:** nenhuma aritmética de ponto flutuante em valores financeiros.

A função `locacoes/calculate_late_fine` recebe `due_at` e `returned_at` e devolve `{late_days, amount_cents, daily_cents, grace_minutes, cap_cents}`. Variável ausente ou vazia usa o valor padrão (300, 120, 9000): a política funciona sem configuração no painel. Variável preenchida com valor não numérico, negativo, diária zero ou teto menor que a diária faz a função falhar. Nesse caso a devolução atrasada é recusada sem efeitos (*fail-closed*): é preferível bloquear a operação a cobrar um valor errado. A devolução sem atraso (`returned_at <= due_at`) não lê a configuração; a tolerância também é um parâmetro e, por isso, só é conhecida quando a configuração é válida.

`GET /multas/politica` expõe os três parâmetros para a interface calcular a **estimativa** exibida na confirmação de devolução. O valor que vale é sempre o calculado pelo backend no instante da gravação.

### Tabela `fine`

| Campo | Observação |
| --- | --- |
| `id` | |
| `rental_id` | único: uma multa de atraso por locação |
| `customer_id`, `customer_name` | cópia da locação, como em `rental` |
| `late_days`, `daily_cents`, `grace_minutes`, `cap_cents` | retrato da política aplicada |
| `amount_cents` | valor gerado; nunca alterado |
| `paid_cents` | soma dos pagamentos `confirmed` |
| `waived_cents` | saldo abonado (0 se não houve abono) |
| `status` | `open` \| `paid` \| `waived` |
| `created_at`, `created_by` | instante e conta da devolução |
| `waived_at`, `waived_by`, `waive_reason` | anuláveis |

Saldo = `amount_cents − paid_cents − waived_cents`, sempre ≥ 0.

Transições de status:
- `open` → `paid` quando o saldo chega a 0 por pagamento;
- `open` → `waived` por abono do saldo restante;
- `paid` → `open` quando um estorno reabre saldo.

"Parcial" é apenas um rótulo de interface (`open` com `paid_cents > 0`). Índices: `rental_id` único e btree em (`customer_id`, `status`).

### Tabela `payment`

| Campo | Observação |
| --- | --- |
| `id` | |
| `fine_id`, `customer_id` | |
| `amount_cents` | > 0 |
| `method` | `cash` \| `pix` \| `debit_card` \| `credit_card` |
| `paid_at`, `registered_by` | servidor e conta autenticada |
| `operation_key` | único por (`registered_by`, `operation_key`) |
| `status` | `confirmed` \| `reversed` |
| `reversed_at`, `reversed_by`, `reversal_reason` | anuláveis |

Nenhum registro é apagado.

### Geração na devolução

Em `POST /locacoes/{id}/devolucao`, dentro da transação existente, depois de inserir `rental_return` e antes do commit:
1. A função calcula a multa com `due_at` da locação e o `returned_at` gerado no servidor.
2. Se `late_days > 0`, a transação insere `fine` com `status = open`.

Uma falha em qualquer passo desfaz devolução, status, ocupação e multa. A resposta passa a ter `{rental, fine, audit_succeeded}`, com `fine` nulo quando não há multa. A repetição com a mesma chave devolve a multa ligada à locação. Depois do commit, a auditoria registra `create_fine`.

O app deve aceitar a resposta com e sem `fine` **antes** da publicação do backend (mesma estratégia da change de devolução).

### Pagamento

`POST /multas/{id}/pagamentos` recebe `amount_cents`, `method` e `operation_key`:
1. `enforce_role` (`member`) e trava `XANO_RENTAL_WRITES_ENABLED == "true"`.
2. Na transação, bloqueia conta → multa (`lock = true`).
3. A mesma chave já usada por esta conta devolve o pagamento existente se for da mesma multa; se for de outra multa, a resposta é conflito.
4. Exige `status == open`, `0 < amount_cents ≤ saldo` e `method` válido.
5. Insere `payment` (`confirmed`), soma o valor a `paid_cents` e, com saldo 0, muda o status para `paid`.
6. Depois do commit, a auditoria registra `register_payment`.

Dois pagamentos simultâneos na mesma multa ficam serializados pelo bloqueio da multa, e o segundo é revalidado contra o saldo já reduzido.

### Estorno e abono (`admin`)

**`POST /pagamentos/{id}/estorno`** (`reason` obrigatório, até 500 caracteres):
- bloqueia conta → multa → pagamento e exige o pagamento `confirmed`;
- recusa estorno de pagamento de multa `waived`, porque o abono foi decidido sobre o saldo daquele momento;
- marca o pagamento `reversed`, subtrai o valor de `paid_cents` e devolve a multa a `open`;
- registra a auditoria `reverse_payment`.

**`POST /multas/{id}/abono`** (`reason` obrigatório):
- exige multa `open`;
- grava `waived_cents = saldo`, `status = waived`, instante, responsável e motivo;
- mantém os pagamentos anteriores;
- registra a auditoria `waive_fine`.

Os dois endpoints usam a trava de escrita e `operation_key` para idempotência. Como o estado final de cada um é único (pagamento estornado ou multa abonada), a repetição devolve o registro atual.

### Bloqueio financeiro na locação

Em `POST /locacoes`, depois de bloquear o cliente, é exigida a ausência de `fine` com `customer_id` do cliente e `status = open`. Caso contrário, a operação é recusada com "Cliente com multa em aberto." A ordem de bloqueios não muda.

Pagamento e abono bloqueiam conta → multa, e nunca o cliente, por isso não há ciclo com a criação de locação.

Uma corrida entre a geração da multa (devolução) e uma nova locação do mesmo cliente pode deixar a nova locação passar com a multa ainda não confirmada. O risco é aceito: a multa existe e bloqueia a próxima locação.

### Consultas

| Endpoint | Retorno |
| --- | --- |
| `GET /multas` | paginado; filtros `status`, `customer_id` e `rental_id` |
| `GET /multas/{id}` | multa com seus pagamentos |
| `GET /multas/resumo` | `{open_count, open_balance_cents}` |
| `GET /pagamentos` | paginado; filtros `customer_id` e `fine_id` |
| `GET /locacoes` | ganha o filtro opcional `customer_id` |

Permissões:
- consultas: `member` e `admin`;
- pagamento: `member` e `admin`;
- estorno e abono: somente `admin`.

As respostas não incluem CPF nem contatos.

### Interface

- `/multas`:
  - abas "Em aberto" (padrão), "Quitadas", "Abonadas" e "Todas";
  - linha com cliente, filme e exemplar, dias, valor, pago e saldo;
  - detalhe com o retrato da política, os pagamentos e o formulário de pagamento (valor sugerido = saldo, meio, confirmação explícita);
  - ações de `admin`: "Estornar" por pagamento e "Abonar saldo", ambas com motivo e confirmação.
- Detalhe da locação:
  - multa estimada na confirmação de devolução, rotulada como estimativa;
  - depois da devolução, a multa gerada com link para `/multas/{id}`.
- Nova locação: ao selecionar um cliente, o app consulta `GET /multas?customer_id&status=open` e mostra "Multa em aberto" como motivo de inelegibilidade. O backend continua sendo a autoridade.
- Dashboard: card "Multas pendentes" com o saldo total em aberto e a nota "N multa(s) em aberto"; "Multas" ativo na navegação. "Relatórios" continua "Em breve".
- Cliente: abas "Locações", "Multas" e "Pagamentos" com listas reais paginadas e o saldo em aberto em destaque.
- Valores: formatação `R$ 1.234,56` a partir de centavos, feita apenas no app.

## Risks / Trade-offs

- **Variáveis da política mal configuradas:** a devolução atrasada é recusada. Mitigação: conferência no checklist de publicação e mensagem clara.
- **Diária fixa sem relação com o preço:** é aceitável porque não há preço de locação. Uma change futura pode introduzir esse preço.
- **Corrida entre a multa e uma nova locação:** risco aceito e documentado.
- **Cota de 10 req/20 s:** a página de detalhe da multa usa `auth/me` + `GET /multas/{id}`, e o pagamento usa `auth/me` + POST + releitura.
- **Comportamento real de `lock` e índices únicos:** só a homologação comprova. As travas ficam fechadas até lá.

## Migration Plan

1. Tornar o app compatível com a resposta de devolução com e sem `fine` (sem publicar nada).
2. Publicar no `v1` (a trava `XANO_RENTAL_WRITES_ENABLED` já está aberta por decisão de uso; fechá-la suspende locação, devolução e operações financeiras):
   - as variáveis da política;
   - as tabelas e a função;
   - os endpoints novos e alterados.
3. Homologar em janela autorizada:
   - devolução no prazo, na tolerância, atrasada e com teto;
   - pagamento parcial e total;
   - concorrência de pagamentos;
   - estorno e abono;
   - bloqueio financeiro;
   - permissões.
4. Rollback: fechar as travas sem apagar `fine` nem `payment`. Para desligar a geração na devolução, republicar o endpoint anterior; as multas já geradas permanecem.
