# Proposal

## Why

O dashboard mantinha "Locações ativas" e "Movimentação de locações" vazios porque não havia fonte real de locações. A Change `listar-locacoes` criou `GET /locacoes`, então esses indicadores podem usar dados reais. Os gráficos também não mostravam detalhes ao passar o cursor.

## What Changes

- Card "Locações ativas" com o total real de locações ativas e quantas estão com vencimento ultrapassado, para `member` e `admin`.
- "Movimentação de locações": barras por dia com retiradas e devoluções dos últimos 14 dias (horário de Brasília), legenda, total do período e link "Ver locações".
- Detalhe ao passar o cursor ou focar pelo teclado: tooltip do dia (data, dia da semana, retiradas, devoluções) e, no "Acervo por gênero", participação percentual no acervo exibido.
- Animação de entrada das barras e destaque no hover, desativados por `prefers-reduced-motion`.
- Leitura limitada a 3 páginas de 50 locações (cota do plano Xano); acima disso, os textos informam que as contagens são das locações mais recentes.
- "Atualizar" (admin) recarrega o resumo e as locações como eventos separados; a carga das locações tem estado próprio e não apaga o resumo.

**Não objetivos:** multas ("Multas pendentes" continua vazio), filtros de período, novos endpoints, alteração do Xano.

## Capabilities

### Modified Capabilities

- `interface-dashboard`: indicadores e painel de locações com dados reais; detalhes ao passar o cursor.

## Impact

- App: `ProjetoLocadora/dashboard_state.py`, `ProjetoLocadora/dashboard.py`, `ProjetoLocadora/ProjetoLocadora.py`, `assets/dashboard.css`.
- Xano: nenhuma alteração; usa `GET /locacoes` (Change `listar-locacoes`).
- Testes: `tests/test_dashboard_locacoes.py`; ajustes em `tests/test_dashboard_ui.py`, `tests/test_dashboard_session.py` e `tests/test_dashboard_genres.py`.
