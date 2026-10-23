# Proposal

## Why

O dashboard não mostrava nada sobre clientes, embora `GET /clientes` já exista e seja acessível a `member` e `admin`. As locações já carregadas também permitem destacar as vencidas e os clientes que mais alugam, sem novas consultas.

## What Changes

- Card "Clientes cadastrados": total real, quantos estão ativos e quantos têm bloqueio manual.
- Painel "Clientes": os primeiros clientes por nome, com CPF mascarado, situação (Ativo/Inativo) e selo "Bloqueado"; cada linha abre o cadastro; links "Novo cliente" e "Ver todos os clientes".
- Painel "Situação dos clientes": rosca ativos × inativos com percentual de ativos e, à parte, a quantidade com bloqueio manual (independente da situação).
- Painel "Locações vencidas": até 5 locações ativas com vencimento ultrapassado, das mais atrasadas primeiro, com cliente, filme e dias de atraso; cada linha abre a locação.
- Painel "Clientes que mais alugam": até 5 clientes com mais locações (ativas e devolvidas) entre as locações lidas, com barras proporcionais.
- Leitura de clientes limitada a 2 páginas de 50 (cota do plano Xano); acima disso, o texto informa que a situação é a dos primeiros por nome.
- A carga do resumo registra a conferência de sessão que já faz, para locações e clientes a reaproveitarem e "Atualizar" caber na cota.
- "Atualizar" (admin) recarrega resumo, locações e clientes como eventos separados.

**Não objetivos:** multas, filtros, novos endpoints, alteração do Xano.

## Capabilities

### Modified Capabilities

- `interface-dashboard`: indicadores e painéis de clientes; locações vencidas e ranking de clientes a partir das locações.

## Impact

- App: `ProjetoLocadora/dashboard_state.py`, `ProjetoLocadora/dashboard.py`, `ProjetoLocadora/ProjetoLocadora.py`, `assets/dashboard.css`.
- Xano: nenhuma alteração; usa `GET /clientes` e `GET /locacoes`.
- Testes: `tests/test_dashboard_clientes.py`; ajustes em `tests/test_dashboard_ui.py` e `tests/test_dashboard_session.py`.
