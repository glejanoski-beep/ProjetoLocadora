# Proposal

## Why

Hoje qualquer pessoa pode se cadastrar e entrar como `member`, mas não há como promover alguém a `admin`, rebaixar um administrador ou desativar a conta de quem saiu da locadora sem editar a tabela direto no Xano. O backend já recusa contas desativadas (`enforce_role` e login), então falta só a operação administrativa e a tela.

## What Changes

- Página `/usuarios`, somente para `admin`, com a lista de contas internas: nome, e-mail, papel, situação (ativa ou desativada) e data de cadastro, com busca por nome ou e-mail e filtro por situação.
- O admin abre uma conta e pode, com motivo obrigatório:
  - alterar o papel entre "Administrador" (`admin`) e "Funcionário" (`member`);
  - desativar a conta ou reativá-la.
- Regras no backend:
  - o admin não altera a própria conta (nem papel nem situação), o que garante que sempre reste ao menos um admin ativo;
  - nada é excluído; senha, e-mail e nome não são alterados por esta tela;
  - a resposta nunca inclui senha nem dados de recuperação de senha;
  - toda alteração fica no log de eventos (`update_user`).
- Backend: `GET /usuarios` e `PATCH /usuarios/{id}` no grupo `Locações`, como multas e relatórios, sem nova URL de API no `.env`.
- Navegação: novo link "Usuários". Para `member`, a página informa que o conteúdo é restrito a administradores e não consulta o backend.

**Não objetivos:**
- criar contas pelo admin (o cadastro público continua sendo o caminho) e convites por e-mail;
- editar nome, e-mail ou senha de outra pessoa (a recuperação de senha continua por magic link);
- excluir contas;
- encerrar sessões abertas: o token de quem foi desativado continua existindo, mas toda operação protegida já é recusada por `enforce_role`.

## Capabilities

### New Capabilities

- `gestao-usuarios`: consulta e alteração protegidas do papel e da situação das contas internas.
- `interface-usuarios`: página de usuários com lista, busca, filtro e diálogo de alteração.

### Modified Capabilities

- `interface-dashboard`: a navegação ganha o link "Usuários".

## Impact

- Xano (`v1`, publicação somente com autorização): novos `GET /usuarios` e `PATCH /usuarios/{id}` no grupo `Locações`. Sem tabela nova nem alteração de endpoint existente.
- App: novos `usuarios.py`, `usuarios_client.py`, `usuarios_state.py`, `usuarios_ui.py` e `assets/usuarios.css`; navegação e rota em `ProjetoLocadora.py`; o transporte compartilhado de `multas_client.py` deixa de exigir `XANO_RENTAL_WRITES_ENABLED` para estas escritas; testes.
- Documentação: `docs/domain-model.md` (usuário interno e matriz de permissões).
