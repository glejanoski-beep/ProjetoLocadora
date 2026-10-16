## ADDED Requirements

### Requirement: Cadastro administrativo de exemplares é auditado com metadados mínimos

O sistema SHALL registrar cada cadastro de exemplar confirmado com a ação, o resultado, o usuário autenticado e a identificação do recurso necessários à rastreabilidade, reutilizando o mecanismo de auditoria existente. O evento SHALL NOT conter o objeto completo do exemplar ou dados alheios à rastreabilidade da operação.

#### Scenario: Cadastro de exemplar auditado

- **WHEN** o backend confirma o cadastro de um exemplar
- **THEN** registra a ação, o resultado, o usuário autenticado e a identificação do exemplar
- **AND** omite o objeto completo do exemplar

#### Scenario: Falha antes do cadastro

- **WHEN** o cadastro de exemplar falha antes de ser confirmado
- **THEN** o sistema não registra a operação como alteração bem-sucedida
- **AND** a interface não apresenta confirmação de sucesso

#### Scenario: Falha de auditoria após gravação

- **WHEN** o cadastro do exemplar é confirmado, mas o registro de auditoria falha
- **THEN** o resultado informa explicitamente que a gravação foi confirmada e a auditoria não foi concluída
- **AND** o sistema não afirma que a gravação foi revertida nem apresenta a operação completa como sucesso
