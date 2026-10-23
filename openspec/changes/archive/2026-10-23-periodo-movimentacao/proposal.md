# Proposal

## Why

O gráfico "Movimentação de locações" mostrava sempre 14 dias. O balcão quer comparar a última semana e o último mês.

## What Changes

- Seletor "7 dias | 14 dias | 1 mês" no painel; padrão 14 dias.
- A troca recalcula o gráfico sobre as locações já lidas (até 3 páginas de 50), sem nova consulta ao Xano; contadores do card não mudam.
- Uma coluna por dia do período; em 1 mês, barras mais finas e rótulo do eixo a cada 5 dias (incluindo hoje).
- Subtítulo, total do período e mensagem de vazio acompanham o período.

**Não objetivos:** períodos personalizados, nova leitura para períodos longos.

## Capabilities

### Modified Capabilities

- `interface-dashboard`: período selecionável na movimentação.

## Impact

- App: `dashboard_state.py`, `dashboard.py`, `assets/dashboard.css`. Xano: nenhuma alteração.
- Testes: `tests/test_dashboard_locacoes.py`.
