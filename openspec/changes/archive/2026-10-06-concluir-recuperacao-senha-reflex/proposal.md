# Proposal

## Why

A recuperação de senha já possui endpoints Xano protegidos contra enumeração e reuso, mas o frontend Reflex ainda exibe apenas uma tela informativa. Por isso, o usuário não consegue solicitar o link pela interface nem concluir a definição de uma nova senha.

## What Changes

- Criar a tela Reflex `/recuperar-senha` para solicitar um magic link.
- Usar `http://localhost:3000` como URL pública do frontend neste ambiente de desenvolvimento.
- Fazer o link enviado pelo Xano apontar para `/redefinir-senha` no frontend Reflex.
- Consumir o magic link automaticamente ao abrir `/redefinir-senha`.
- Manter o token de autenticação resultante somente no estado privado do servidor Reflex.
- Criar formulário de nova senha e confirmação.
- Chamar `POST /reset/update_password` após o consumo válido do magic link.
- Tratar token ausente, inválido, expirado ou já utilizado com mensagens genéricas.
- Exibir sucesso e permitir retorno ao login.

A decisão confirmada é consumir o magic link ao abrir a tela, mesmo que o usuário possa fechar a página antes de salvar a senha. Essa consequência é aceita nesta Change.

## Capabilities

### New Capabilities

### Modified Capabilities

- `recuperacao-segura`: adicionar o contrato das telas Reflex, URL de desenvolvimento, consumo do token ao abrir a tela e conclusão da troca de senha.

## Impact

- Frontend Reflex em `ProjetoLocadora/ProjetoLocadora.py`.
- Cliente HTTP Xano em `ProjetoLocadora/xano_client.py`.
- Configuração de URL do frontend usada pelo endpoint Xano de solicitação de recuperação.
- Endpoint Xano `reset/request-reset-link` para montar links com `http://localhost:3000`.
- Endpoints existentes `reset/magic-link-login` e `reset/update_password`.
- Não inclui recuperação em produção, domínio público definitivo, Redis, provedor externo de identidade ou mudança na política de autenticação.
