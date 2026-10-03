## Context

A aplicação Reflex ainda é o scaffold inicial. O Xano já oferece `POST /auth/login`, `GET /auth/me`, papéis `member/admin`, estado `is_active` e tokens de acesso com validade de 24 horas. A autenticação OIDC do `reflex-enterprise` não é compatível com o endpoint de credenciais Xano existente e adicionaria um provedor externo não definido pelo projeto.

## Goals / Non-Goals

**Goals:**
- Integrar login e sessão Reflex com os endpoints Xano existentes.
- Manter o bearer Xano no servidor e aplicar proteções Reflex a páginas e eventos internos.
- Expor na interface somente dados não secretos necessários para apresentar a identidade do funcionário.

**Non-Goals:**
- Cadastro ou provisionamento de contas pela interface.
- Redefinição de senha, já especificada na capability `recuperacao-segura`.
- Criar uma matriz nova de permissões; `member` e `admin` podem entrar, enquanto o backend continua decidindo autorização por operação.
- Revogar remotamente tokens Xano no logout nesta Change, pois não há endpoint de revogação existente.

## Decisions

### Usar os endpoints Xano atuais

O evento de login do Reflex chama `POST /auth/login`; após sucesso, consulta `GET /auth/me` usando o token recebido. A URL base da API será configurada por ambiente e nunca hardcoded. Credenciais e token não serão enviados para componentes ou vars públicas. A resposta de `auth/me` deve incluir `is_active` para revalidar o estado de acesso ao restaurar a sessão.

**Alternativa considerada:** usar o fluxo `reflex-enterprise` OIDC. Não foi escolhido porque o backend atual autentica por senha Xano, não há IdP OIDC definido e a adoção adicionaria uma dependência e arquitetura de identidade novas.

### Guardar o bearer em estado backend-only por sessão

O token Xano ficará em um campo backend-only do `rx.State` (nome privado iniciado por `_`), e não em `rx.Cookie`, `rx.LocalStorage`, `rx.SessionStorage` ou outro valor serializado para o browser. Na versão Reflex instalada, esses campos são classificados como backend vars e não entram nos deltas enviados ao cliente. O browser receberá apenas dados não secretos da identidade, como nome, e-mail e papel.

**Alternativa considerada:** cookie gerenciado por `rx.Cookie` ou storage do browser. Não foi escolhida para o bearer porque a API disponível não oferece `HttpOnly` e o token ficaria acessível ao JavaScript do cliente.

Não será adicionado Redis ou outro serviço de sessão nesta Change. A execução inicial usará o StateManager Reflex existente e deverá operar com uma instância ou afinidade de sessão. Escala horizontal sem afinidade exige configurar um StateManager compartilhado em mudança de deployment própria.

### Proteger páginas e eventos no Reflex, sem substituir Xano

A tela `/login` será pública. Páginas e eventos do backoffice exigirão uma sessão Reflex autenticada. Chamadas protegidas enviadas ao Xano continuarão autenticadas e autorizadas no backend; o guard Reflex melhora o fluxo de navegação, mas não será tratado como controle de segurança para APIs.

### Tratar login, recuperação e logout como fluxos distintos

Login inválido, conta inexistente ou desativada terão mensagem genérica. A recuperação de senha continuará usando a rota e contratos de `recuperacao-segura`. Logout limpa o token backend-only e os dados da sessão Reflex e redireciona ao login. O token emitido pelo Xano pode permanecer válido até sua expiração de 24 horas, mas o app deixa de mantê-lo após logout.

## Risks / Trade-offs

- **Estado Reflex armazenado em memória não sobrevive a reinício do processo e exige afinidade ou estado compartilhado em múltiplas instâncias** -> para o deployment inicial, exigir uma única instância/afinidade e encerrar a sessão pedindo novo login após perda do estado; antes de escalar horizontalmente, configurar um state manager compartilhado.
- **Token Xano não é revogado remotamente no logout** -> mantê-lo apenas no estado backend-only, não expor o bearer ao browser e limitar a sessão efetiva do app ao tempo de vida do estado Reflex; revogação remota fica para uma mudança que adicione suporte backend.
- **Usuário pode ser desativado depois de receber token Xano** -> revalidar `is_active` em `auth/me` ao restaurar sessão e limpar a sessão Reflex se estiver desativado; tokens Xano já emitidos permanecem válidos até expirar, portanto endpoints futuros deverão validar estado de acesso no backend.
- **A rota e URL pública do Xano variam por ambiente** -> obter a base da API de configuração de ambiente e validar configuração ausente sem revelar segredos.
