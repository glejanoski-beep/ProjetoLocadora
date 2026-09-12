# Design: Auditoria segura

## Decisões

- Manter `Quick Start/log_event` como ponto central de registro.
- Alterar chamadores para enviar somente campos permitidos, nunca objetos completos de usuário.
- Preservar usuário, ação, resultado e recurso/contexto quando aplicável.
- Não alterar a finalidade do log nem remover histórico existente.
- Validar a ausência de segredos comparando os payloads dos fluxos de login, cadastro, consulta, reset e magic link.

## Validação

Como não há compilador local para XanoScript, validar com os recursos existentes e exercitar os fluxos no Xano. Inspecionar os eventos gerados para confirmar que não há senha, hash, token ou dados de recuperação.
