# Design: Acesso seguro

## Decisões

- Adicionar autenticação explícita aos endpoints protegidos.
- Reutilizar ou evoluir `Quick Start/enforce_role` para validar permissões no backend.
- Adicionar ao usuário um estado explícito de acesso com valor padrão ativo para compatibilidade.
- Aplicar a validação de estado antes da criação de tokens no login comum e no login por magic link.
- Preservar usuários e histórico ao desativar acesso.
- Manter a matriz completa de permissões da locadora para uma change futura.

## Validação

Exercitar chamadas autenticadas, não autenticadas, com papel insuficiente, com usuário ativo e com usuário desativado no ambiente Xano.
