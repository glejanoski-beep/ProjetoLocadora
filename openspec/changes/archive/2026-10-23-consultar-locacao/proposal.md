# Proposal

## Why

O detalhe de uma locação já existia (`GET /locacoes/{id}` e a rota `/locacoes/[rental_id]`), mas só era alcançável pelo link exibido logo após registrar, não tinha testes de estado e tratava identificador inválido como "não encontrada" depois de consultar o Xano. A interface de locações também foi reorganizada sem especificação própria. Esta Change torna o detalhe acessível e confiável e documenta a interface de locações, preparando a futura devolução, que dependerá dessa tela.

## What Changes

- Campo "Abrir locação pelo número" em `/locacoes/nova` e no detalhe; valida inteiro positivo antes de navegar.
- Tela `/locacoes/[rental_id]` na identidade visual do CineGestão: número, situação, indicação de vencimento ultrapassado, cliente, exemplar, filme, datas no horário de Brasília e responsável.
- Estados explícitos do detalhe: carregando, pronto, identificador inválido (sem requisição), não encontrada, falha de conexão, 401, 403 e limite de requisições (429) com espera.
- Documentação da interface de registro já implementada: três etapas, cartões, paginação de 10 itens, pendências, aviso de gravação bloqueada e conferência de condição recolhida para admin.

**Não objetivos:** devolução, cancelamento, alteração de prazo ou status, listagem de locações, novos endpoints, mudanças no Xano, multas ou habilitar gravações.

## Capabilities

### New Capabilities

- `interface-locacoes`: interface Reflex de registro e consulta de locações.

### Modified Capabilities

Nenhuma. `registro-locacao` e `disponibilidade-locacao` mantêm contratos e regras; o detalhe usa a consulta protegida já especificada.

## Impact

- App: `ProjetoLocadora/locacoes_state.py`, `ProjetoLocadora/locacoes_ui.py`, `assets/locacoes.css`, `tests/test_locacoes_detail.py`.
- Xano: nenhuma alteração. Contrato usado: `GET /locacoes/{id}` (member e admin), 11 campos.
- Validação real somente de leitura, com as locações existentes 1 e 2.
