# Evidências de verificação

## Escopo e limites

Este registro distingue evidência estática dos arquivos, testes locais com
mocks, validação de sintaxe e execução integrada. Nenhuma função, teste ou
operação foi executado no Xano remoto. Evidência local não comprova
comportamento no runtime nem ausência de efeitos operacionais.

## Validações realizadas

| Tipo | Execução | Resultado | Limite |
|---|---|---|---|
| Testes Python | `python -m unittest discover -v` | 38 testes passaram; nenhuma falha | Inclui testes estáticos e mockados; não é integração Xano |
| Testes Python direcionados | `tests.test_enforce_role_contract` | 17 testes passaram na execução após os contratos do cadastro e de boas-vindas | Verificações estruturais dos arquivos XanoScript |
| Testes Python direcionados | `tests.test_reflex_auth_state tests.test_enforce_role_contract` | 32 testes passaram na execução após os fluxos Reflex com mocks | Não executa Xano nem navegação no browser |
| Sintaxe XanoScript | `enforce_role.xs` | Válido | Sintaxe não prova comportamento |
| Sintaxe XanoScript | `enforce_role.xs`, `log_event.xs` | Ambos válidos | Sintaxe não comprova persistência de auditoria nem ausência de efeitos |
| Sintaxe XanoScript | `auth/me_GET.xs`, `my_events_GET.xs` | Ambos válidos | Não prova chamadas/respostas no runtime |
| Sintaxe XanoScript | `update_password_POST.xs` | Válido | Não prova alteração nem recusa de senha em execução |
| Sintaxe XanoScript | `signup_POST.xs` | Válido | Não prova criação real, emissão de token ou preservação de registros |
| Sintaxe XanoScript | `send_welcome_email_POST.xs` | Válido | Não prova autorização nem envio/ausência de e-mail |
| Compilação Reflex | `.venv\Scripts\reflex.exe compile --dry` | Não iniciou; o Controle de Aplicativo do Windows bloqueou o executável | Sem resultado de compilação |
| Compilação Reflex | `python -m reflex compile --dry` | Falhou ao carregar `ctypes._ctypes`, bloqueado pela política do Windows | Não há evidência de incompatibilidade de versões |
| Formatação do diff | `git diff --check` | Sem erros nas verificações em que foi executado | Não valida comportamento funcional |

Os totais de 38 e 32/17 correspondem a execuções distintas da suíte em etapas
anteriores; não devem ser somados como se fossem uma única execução.

## Matriz de cenários e correspondência

“Coberto localmente” abaixo significa somente a correspondência indicada; não
implica aprovação no Xano. “Não executado” significa ausência de evidência de
runtime para o caso.

| Cenário exigido | Evidência local correspondente | Estado no runtime Xano |
|---|---|---|
| `admin` e `member` ativos aceitos pelo helper Reflex | `tests.test_reflex_auth_state.TestReflexAuthState.test_member_and_admin_active_users_are_allowed` | Não executado |
| Login Reflex de `admin` e `member` com identidade ativa simulada | `tests.test_reflex_auth_state.TestReflexAuthFlows.test_login_accepts_active_member_and_admin` (mock de `login_xano` e `get_me_xano`) | Não executado; o mock não autentica no Xano |
| `auth/me` chama a guarda `member` antes de ler/devolver identidade | `tests.test_enforce_role_contract.TestEnforceRoleContract.test_auth_me_checks_role_before_reading_or_returning_user_data` (inspeção estática) | Não executado |
| `logs/user/my_events` chama a guarda antes da consulta e mantém filtro `$auth.id` | `tests.test_enforce_role_contract.TestEnforceRoleContract.test_my_events_checks_role_before_query_and_keeps_user_filter` (inspeção estática) | Não executado |
| Requisição a endpoint protegido sem autenticação | Arquivos declaram `auth = "user"`; nenhum teste local exercita o comportamento do runtime de autenticação | Não executado |
| Conta inexistente recusada por `enforce_role` | `test_checks_user_existence_before_account_state` verifica somente a ordem estática da precondition | Não executado |
| Conta explicitamente inativa recusada e recusa auditada antes do `throw` | `test_only_explicit_false_marks_account_inactive` e `test_unrecognized_user_role_is_audited_then_denied` inspecionam estrutura/código | Não executado; evento e interrupção efetivos não observados |
| Conta legada sem estado explícito compatível | `test_only_explicit_false_marks_account_inactive` verifica a guarda estática; `test_legacy_account_without_active_flag_remains_allowed` cobre o helper Python Reflex, não Xano | Não executado no Xano |
| Papel de usuário ausente/desconhecido recusado | `test_accepts_only_recognized_roles_for_both_access_levels` e `test_unrecognized_user_role_is_audited_then_denied` inspecionam níveis, guarda e auditoria | Não executado |
| Papel mínimo inválido recusado | `test_rejects_unrecognized_minimum_role` verifica a precondition estática | Não executado |
| `member` insuficiente para papel mínimo `admin` | `test_role_insufficiency_is_audited_then_denied` verifica a rama e ordem de auditoria/throw no fonte | Não executado |
| `member` recusado em envio de boas-vindas antes de consulta/envio | `test_welcome_email_requires_admin_before_lookup_and_send` verifica configuração estática e ordem | Não executado |
| `admin` inativo recusado sem envio de e-mail | A guarda precede `util.send_email` segundo o teste acima; não há mock/teste de execução do endpoint Xano | Não executado; ausência de envio não comprovada |
| Envio autorizado por `admin` ativo a destinatário fictício | Nenhum teste local executa ou simula o endpoint de envio | Não executado |
| Atualização de senha passa pela guarda `member` antes de operações sensíveis | `test_update_password_checks_role_before_password_operations` (inspeção estática) | Não executado |
| Conta descartável ativa atualiza senha | Nenhum teste local correspondente | Não executado |
| Conta desativada não altera senha | A ordem estática da guarda foi verificada, mas não há teste de estado persistido antes/depois | Não executado; ausência de alteração não comprovada |
| Entrada de cadastro não controla `role`, nova conta declara `member` | `test_public_signup_does_not_accept_user_controlled_role` e `test_public_signup_assigns_member_explicitly` (inspeção estática) | Não executado com requisição manipulada |
| Cadastro cria e retorna token de acesso | `test_public_signup_creates_and_returns_auth_token` verifica chamadas/atribuições/resposta no texto | Não executado; emissão e uso do token não comprovados |
| Papéis/estados de contas existentes preservados pelo cadastro | `test_public_signup_does_not_change_existing_user_roles_or_states` confirma que o arquivo não contém `db.edit/delete user`; não observa dados antes/depois | Não verificado no runtime |
| Contrato estrutural do helper e GUID preservado | `test_preserves_function_signature_and_guid` e testes estáticos associados | Não executado no runner Xano |
| Contrato estrutural de auditoria sem campos proibidos | `test_audit_helper_persists_only_declared_metadata` e verificações de recusas auditadas, ambos estáticos | Persistência e conteúdo real de evento não verificados |
| Bearer de entrada encaminhado por `get_me_xano` | `test_get_me_sends_bearer_token_using_local_mock_transport` usa `httpx.MockTransport`; não abre conexão de rede | Não executado contra Xano |
| Revalidação Reflex de conta inativa limpa sessão e redireciona | `test_session_revalidation_clears_inactive_account` mocka `get_me_xano` com `is_active=False` | Não integrado; depende da resposta simulada |
| Logout limpa sessão e redireciona ao login | `test_logout_clears_session_and_redirects_to_login` executa o handler local | Não é teste Xano |
| Navegação real do browser, sessões dos dois papéis e desativação durante sessão | Nenhum teste browser/end-to-end identificado | Não executado |
| Recusa não executa efeito operacional e auditoria mínima é persistida | Testes estáticos verificam ordem e campos pretendidos, não execução ou persistência | Não comprovado; sem Xano, não se afirma ausência de efeito |

A auditoria de recusa é uma escrita prevista pela especificação. Isso não
comprova que o evento foi persistido, nem que o efeito operacional solicitado
foi ou não executado.

## Capacidades futuras

As APIs operacionais de clientes, filmes, exemplares, locações, devoluções,
multas e pagamentos não fazem parte da implementação desta Change. Seus cenários
devem ser definidos e testados nas Changes correspondentes; não há evidência
local ou remota de execução dessas capacidades nesta Change.

## Estado OpenSpec

Conforme os critérios acadêmicos registrados em `tasks.md`, a tarefa 4.3 foi
concluída como consolidação documental da correspondência entre cenários e
evidências disponíveis. Essa conclusão não comprova integração real com o
Xano, persistência de auditoria nem ausência de efeitos operacionais.

A compilação Reflex continua bloqueada pelo Controle de Aplicativo do Windows
e não foi concluída. Os cenários de runtime Xano permanecem identificados na
matriz como não executados ou não comprovados; a conclusão documental de 4.3
não altera esse estado de evidência.
