# Proposal: Sanitizar auditoria e logs

## Problema

Os fluxos atuais de autenticação enviam objetos completos de usuário para os logs, com risco de registrar hashes de senha, tokens e dados de recuperação.

## Objetivo

Tornar a auditoria segura e reutilizável antes da implementação de clientes, locações e pagamentos.

## Escopo

- Definir metadados mínimos permitidos nos eventos.
- Remover segredos e objetos completos de usuário dos chamadores de auditoria.
- Registrar ação, usuário, recurso quando aplicável e resultado.
- Auditar sucessos e falhas relevantes sem dados sensíveis, inclusive falhas anônimas com `user_id` nulo e metadados mínimos.

## Fora do escopo

- Autorização de endpoints.
- Alterações no fluxo de recuperação de senha.
- Cadastro ou operação da locadora.

## Resultado esperado

Nenhum log de autenticação ou administração contém senha, hash, token, dados de recuperação, identificadores submetidos em tentativas anônimas ou objeto completo de usuário.
