# Tasks

Sem alteração no Xano. Sem commit, push ou merge.

## 1. Estado

- [x] 1.1 `resumir_clientes`, `ranking_clientes` e `locacoes_vencidas`.
- [x] 1.2 `load_customers`: member e admin, reaproveita conferência recente de sessão, até 2 páginas de 50, erros sem valores, 401 limpa a sessão e redireciona, resposta tardia descartada.
- [x] 1.3 Resumo registra a conferência de sessão feita, para as cargas seguintes reaproveitarem.

## 2. Interface

- [x] 2.1 Card "Clientes cadastrados"; grade de cards acompanha 3 (member) ou 5 (admin) cards.
- [x] 2.2 Painéis "Clientes", "Situação dos clientes", "Locações vencidas" e "Clientes que mais alugam".
- [x] 2.3 Entrada do dashboard e "Atualizar" disparam também a carga de clientes.

## 3. Validação

- [x] 3.1 `tests/test_dashboard_clientes.py` e ajustes dos testes do dashboard; suíte completa.
- [x] 3.2 `reflex compile --dry`.
- [x] 3.3 `openspec validate dashboard-clientes --strict`.
- [x] 3.4 Conferência no navegador com dados reais (desktop e celular) — confirmado pelo usuário em 23/10/2026.
