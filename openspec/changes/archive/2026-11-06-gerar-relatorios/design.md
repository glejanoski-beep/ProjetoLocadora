# Design

## Context

- `rental` guarda `rented_at`, `due_at`, `status`, `returned_at`, `film_id` e `film_title`.
- `fine` guarda `created_at`, `amount_cents`, `waived_at` e `waived_cents`.
- `payment` guarda `paid_at`, `amount_cents`, `method`, `status` e `reversed_at`.
- `exemplar.filme_id` liga cada cópia ao seu filme.
- O XanoScript não tem um agrupamento simples por coluna que devolva lista. O volume de dados da locadora é pequeno (dezenas a poucos milhares de linhas por ano).
- A cota do plano é de 10 requisições a cada 20 s.
- O dashboard já lê até 150 locações no app para os indicadores. Os relatórios precisam de totais completos do período, então a agregação fica no backend.

## Goals / Non-Goals

**Goals:**
- números corretos e completos no período, calculados pelo backend em uma única requisição;
- definições explícitas de cada indicador;
- nenhum dado pessoal;
- acesso restrito a `admin`.

**Non-Goals:** exportação, séries temporais, comparação de períodos e relatórios por cliente.

## Decisions

### Período

O app converte o período escolhido (datas no horário de Brasília) em dois instantes UTC em milissegundos:
- `from` é 00:00 do dia inicial;
- `to` é 00:00 do dia seguinte ao final (intervalo semiaberto `[from, to)`).

O backend recebe `from` e `to` como inteiros e exige `0 < from < to` e `to − from ≤ 366 dias`. Ele não interpreta fuso horário: a conversão fica num único lugar (o app), testada, e o backend só compara instantes.

Atalhos (todos fechados em hoje):
- "Últimos 7 dias" e "Últimos 30 dias": incluem o dia de hoje;
- "Este mês": do dia 1 até hoje;
- "Mês anterior": o mês civil completo.

O padrão ao abrir é "Últimos 30 dias". Datas de início e fim informadas manualmente são inclusivas.

### Definições dos indicadores

| Indicador | Definição |
| --- | --- |
| Retiradas | locações com `rented_at` em `[from, to)` |
| Devoluções | locações com `returned_at` em `[from, to)` |
| Devoluções com atraso | dessas, as com `returned_at > due_at` (atraso bruto, sem a tolerância da multa) |
| Multas geradas | multas com `created_at` no período: quantidade e soma de `amount_cents` |
| Pagamentos recebidos | pagamentos com `paid_at` no período e status atual `confirmed`: total e total por meio |
| Estornos | pagamentos com `reversed_at` no período: quantidade e soma de `amount_cents` |
| Abonos | multas com `waived_at` no período: quantidade e soma de `waived_cents` |
| Locações ativas agora | `status = active` no instante da consulta |
| Vencidas agora | ativas com `due_at` anterior ao instante da consulta |
| Saldo em aberto agora | soma de `amount − paid − waived` das multas `open` |

Um pagamento recebido no período e estornado depois deixa de contar como recebido (o status atual é `reversed`) e aparece em "Estornos" no período em que foi estornado. Assim, o total recebido nunca inclui dinheiro devolvido.

"Atraso" no relatório é o atraso bruto (devolução após o vencimento). Por isso pode haver devolução atrasada sem multa, quando ficou dentro da tolerância. A tela explica essa diferença.

### Filmes mais alugados

O backend percorre os filmes do catálogo e, para cada um, conta:
- as retiradas no período;
- os exemplares cadastrados.

Ele devolve só os filmes com pelo menos uma retirada: `{film_id, film_title, rentals, exemplars}`. Os filmes do catálogo são poucos, então N consultas de contagem são aceitáveis neste porte. A alternativa de devolver todas as locações do período para o app agrupar aumentaria a resposta sem necessidade.

O app ordena por retiradas (decrescente) e, em empate, por título. Mostra os 10 primeiros, com "N locações · M exemplares". O título vem do catálogo atual.

### Endpoint

`GET /relatorios/operacional?from&to` (grupo `Locações`, `auth = user`):
1. `enforce_role` com `admin`, antes de qualquer leitura.
2. Validação do período.
3. Consultas apenas de leitura, filtradas por intervalo, com projeção mínima, sem dados pessoais nem nomes de clientes.
4. Agregação com `foreach`, só com inteiros.

Resposta:

```
{
  from, to, generated_at,
  rentals:   {checkouts, returns, late_returns, active_now, overdue_now},
  fines:     {generated_count, generated_cents, waived_count, waived_cents, open_balance_cents},
  payments:  {received_cents, received_count, by_method: {cash, pix, debit_card, credit_card}, reversed_count, reversed_cents},
  films:     [{film_id, film_title, rentals, exemplars}]
}
```

O endpoint não depende de `XANO_RENTAL_WRITES_ENABLED` e não grava auditoria, porque é uma leitura sem efeitos, como as demais consultas.

### Interface

- `/relatorios`:
  - cabeçalho com o período ativo ("01/10/2026 a 31/10/2026, horário de Brasília");
  - atalhos de período, datas manuais e "Gerar relatório";
  - cartões agrupados em "Locações no período", "Financeiro no período" e "Situação atual", com o horário de geração;
  - lista "Filmes mais alugados" com barras proporcionais ao primeiro colocado.
- Estados: carregamento, erro com "Tentar novamente", 429 sem nova tentativa automática, e período sem movimento (os cartões mostram zero e a lista informa "Nenhuma locação no período.").
- Para `member`: mensagem de restrição, sem chamada ao backend.
- Valores monetários formatados pelo app a partir de centavos.

### Permissão

Somente `admin`. Os relatórios consolidam valores financeiros e o desempenho da operação. A matriz de `docs/domain-model.md` recebe a linha "Consultar relatórios consolidados: `admin`", sem conceder nada a `member` por analogia.

## Risks / Trade-offs

- **Consultas por filme (N+1):** aceitável no porte atual. Se o catálogo crescer muito, mover para agregação SQL ou para uma tabela de contagem.
- **Período longo com muitas linhas:** o limite de 366 dias e a projeção mínima contêm o custo.
- **Título atual do filme no ranking:** a locação guarda o título do momento da retirada, mas o ranking agrupa por `film_id` e mostra o título atual do catálogo. É aceitável, porque o ranking é por filme, não por título.
- **"Agora" difere entre indicadores:** os indicadores de situação atual usam o instante da consulta, informado por `generated_at`.

## Migration Plan

1. App e testes locais.
2. Publicar o endpoint no `v1` (somente leitura, sem tabela nova).
3. Conferir com um `admin` real que os totais batem com as tabelas, para um período conhecido.
4. Rollback: remover o link e o endpoint, sem impacto em dados.
