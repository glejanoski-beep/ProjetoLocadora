# Proposal

## Why

Depois de registrar uma locação, o funcionário só a reencontrava digitando o número em "Abrir locação pelo número"; ao voltar à tela de registro, o formulário recomeça e a locação some da vista. Não havia como consultar locações antigas sem conhecer o número. O backend não tinha endpoint de listagem (`consultar-locacao` deixou a listagem como não objetivo).

## What Changes

- Novo endpoint `GET /locacoes` no grupo Locações: leitura paginada (`page`, `per_page` de 1 a 50), mais recentes primeiro, `member` e `admin`, mesma projeção de 13 campos do detalhe, sem CPF nem dados de contato.
- Cliente `list_rentals` com validação estrita da página e de cada item pelo contrato do detalhe.
- Seção persistente "Locações registradas" abaixo do formulário em `/locacoes/nova`: número, filme e exemplar, cliente, retirada, situação (ativa, devolvida, vencida) e link para o detalhe existente (`/locacoes/{id}`).
- Estados de carregamento, lista vazia e erro, isolados do formulário; paginação de 10 itens para locações antigas; "Atualizar lista".
- Atualização automática da primeira página após registro confirmado (inclusive pela consulta da tentativa pendente).

**Não objetivos:** devolução nesta tela, filtros e busca, alteração de locações, mudanças em regras de negócio, publicação no Xano pelo agente.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `interface-locacoes`: seção "Locações registradas" na tela de registro.
- `registro-locacao`: consulta paginada das locações registradas.

## Impact

- App: `ProjetoLocadora/locacoes_client.py`, `ProjetoLocadora/locacoes_state.py`, `ProjetoLocadora/locacoes_ui.py`, `assets/locacoes.css`.
- Xano (local, aplicação manual pelo operador): `xano/xano/api/locacoes/locacoes_GET.xs`. Até a aplicação, a seção informa que a listagem ainda não está disponível no serviço; o formulário continua funcionando.
- Cota do plano (10 requisições / 20 s): a abertura da tela passa a usar uma requisição a mais e reaproveita a conferência recente de `auth/me`.
- Testes: `tests/test_locacoes_listagem.py`; doubles de `list_rentals` em `tests/test_locacoes_state.py` e `tests/test_session_check_reuse.py`.
