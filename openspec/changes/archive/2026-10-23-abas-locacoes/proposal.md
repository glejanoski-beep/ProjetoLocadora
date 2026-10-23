# Proposal

## Why

A lista "Locações registradas" misturava ativas e devolvidas em cartões altos, o que confundia o balcão. Depois de devolver, a pessoa não via onde a locação foi parar.

## What Changes

- `GET /locacoes` aceita o filtro opcional `status` (`active` | `returned`); sem ele, comportamento idêntico (o dashboard não muda). Valor inválido é erro de entrada.
- Lista com abas "Ativas (n)" e "Devolvidas (n)", filtro aplicado no Xano (paginação correta), linhas compactas e clicáveis (número, filme, cliente · exemplar, data de retirada ou devolução, selo "Vencida").
- Devolução confirmada leva à lista na aba "Devolvidas", com aviso "Locação #N devolvida." (e o alerta de auditoria, se houver). Nova locação leva à aba "Ativas".

**Não objetivos:** busca na lista, outras situações além de ativa/devolvida.

## Capabilities

### Modified Capabilities

- `registro-locacao`: abas na lista de locações e destino após a devolução.

## Impact

- Xano: `api/locacoes/locacoes_GET.xs` (publicado em `v1`, 149184).
- App: `locacoes_client.py`, `locacoes_state.py`, `locacoes_ui.py`, `assets/locacoes.css`.
- Testes: `test_locacoes_listagem.py`, `test_locacoes_devolucao.py`.
