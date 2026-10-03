## Why

O sistema possui login e validação de identidade no Xano, mas o frontend Reflex ainda não oferece uma tela de acesso nem mantém uma sessão autenticada. Sem essa integração, funcionários não conseguem usar o backoffice e páginas/ações futuras não têm um fluxo de identidade utilizável.

## What Changes

- Criar no Reflex uma experiência de login para contas ativas com papel `member` ou `admin`.
- Integrar o formulário ao endpoint de login Xano e consultar a identidade autenticada pelo endpoint `auth/me`.
- Manter a sessão do funcionário entre navegações e encerrá-la por logout ou quando a autenticação for inválida/expirada.
- Restringir páginas e ações internas a uma sessão autenticada, sem tratar a interface como substituta da autorização no backend.
- Não oferecer cadastro de funcionários nesta interface. O endpoint público Xano existente permanece inalterado; por decisão confirmada, qualquer conta ativa `member` ou `admin`, inclusive criada por esse endpoint, poderá entrar.

## Capabilities

### New Capabilities

### Modified Capabilities
- `acesso-seguro`: especificar o fluxo de login, sessão e logout pelo frontend Reflex para contas ativas autorizadas.

## Impact

- Frontend Reflex em `ProjetoLocadora/ProjetoLocadora.py` e configuração de URL do backend.
- APIs Xano existentes de login e consulta da identidade autenticada; pode ser necessário ajustar seus contratos para suportar o fluxo de sessão.
- Segurança de armazenamento e envio do token Xano, proteção de rotas e tratamento de erros de autenticação.
- A Change não inclui cadastro/provisionamento de contas, recuperação de senha, matriz completa de permissões ou funcionalidades de clientes/locações.
