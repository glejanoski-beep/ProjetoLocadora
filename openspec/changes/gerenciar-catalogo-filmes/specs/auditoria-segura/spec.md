# Auditoria Segura

## ADDED Requirements

### Requirement: Criações e edições de filmes são auditadas com metadados mínimos

O sistema SHALL registrar cada criação ou edição de filme confirmada com a ação, o resultado, o usuário autenticado e o identificador do recurso necessários à rastreabilidade, reutilizando o mecanismo de auditoria existente. O evento SHALL NOT conter o objeto completo do filme, credenciais, tokens ou dados alheios à rastreabilidade da operação.

#### Scenario: Criação de filme auditada

- **WHEN** o Xano confirma a criação de um filme
- **THEN** o sistema registra ação, resultado, usuário autenticado e identificador do filme
- **AND** omite o objeto completo e dados que não sejam necessários à rastreabilidade

#### Scenario: Edição de filme auditada

- **WHEN** o Xano confirma a edição de um filme
- **THEN** o sistema registra ação, resultado, usuário autenticado e identificador do filme
- **AND** omite o objeto completo e dados que não sejam necessários à rastreabilidade

#### Scenario: Operação sem gravação confirmada

- **WHEN** uma criação ou edição falha antes de ser confirmada
- **THEN** o sistema não registra a operação como alteração bem-sucedida
- **AND** a interface não apresenta confirmação de sucesso

#### Scenario: Falha de auditoria após gravação confirmada

- **WHEN** a gravação do filme é confirmada, mas o registro de auditoria falha
- **THEN** o resultado informa explicitamente que a gravação foi confirmada e a auditoria não foi concluída
- **AND** o sistema não afirma que a gravação foi revertida nem apresenta a operação completa como sucesso
- **AND** a estratégia não pressupõe atomicidade que não esteja confirmada pelo Xano
