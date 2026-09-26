# Design: Auditoria segura

## Decisões

- Manter `Quick Start/log_event` como ponto central de registro.
- Alterar o contrato de `Quick Start/log_event` para aceitar `user_id` opcional, compatível com a coluna nullable existente em `event_log`.
- Alterar chamadores para enviar somente campos permitidos, nunca objetos completos de usuário.
- Preservar usuário quando autenticado, ação e resultado; incluir recurso/contexto somente quando necessário.
- Para falhas anônimas de login, registrar `user_id` nulo e somente ação/resultado; não registrar o identificador informado, IP ou qualquer credencial.
- Registrar falhas administrativas negadas com o usuário autenticado, ação e resultado, sem dados sensíveis.
- Não alterar a finalidade do log nem remover histórico existente.
- Validar a ausência de segredos comparando os payloads dos fluxos de login, cadastro, consulta, reset e magic link.

## Validação

Como não há compilador local para XanoScript, validar com os recursos existentes e exercitar os fluxos no Xano. Inspecionar eventos de sucesso, falha autenticada e falha anônima para confirmar `user_id` nulo no último caso e ausência de senha, hash, token, e-mail submetido, endereço IP ou dados de recuperação.
