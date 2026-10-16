# Auditoria Segura

## Purpose

Definir eventos de auditoria mínimos e seguros para os fluxos de autenticação e administração, preservando rastreabilidade sem registrar credenciais ou dados pessoais desnecessários.

## Requirements

### Requirement: Eventos de auditoria contêm somente metadados permitidos

O sistema SHALL registrar somente a ação, o resultado, o usuário autenticado quando conhecido e o contexto do recurso estritamente necessário para rastreabilidade. Os eventos SHALL NOT conter senhas, hashes, tokens, dados de recuperação ou objetos completos de usuário.

#### Scenario: Login bem-sucedido auditado

- **WHEN** um usuário realiza login com sucesso
- **THEN** o evento registra a ação, o resultado e o identificador do usuário
- **AND** omite senha, hash, token, dados de recuperação e o objeto completo do usuário

#### Scenario: Alteração de senha auditada

- **WHEN** a senha de um usuário é alterada
- **THEN** o evento registra a ação, o resultado e o identificador do usuário
- **AND** omite a senha anterior, a nova senha, hashes e tokens

### Requirement: Falhas anônimas de autenticação são auditadas sem identificar a pessoa

O sistema SHALL permitir registrar falhas relevantes de autenticação sem usuário autenticado, mantendo o identificador do usuário nulo e armazenando somente metadados mínimos da ação e do resultado.

#### Scenario: Tentativa de login rejeitada sem identidade autenticada

- **WHEN** uma tentativa de login é rejeitada antes de existir uma identidade autenticada
- **THEN** o evento registra a ação e o resultado negado com `user_id` nulo
- **AND** não registra o e-mail ou outro identificador submetido, senha, hash, token ou endereço IP

#### Scenario: Operação administrativa negada a usuário autenticado

- **WHEN** uma operação administrativa é negada a um usuário autenticado
- **THEN** o evento registra a ação, o resultado negado e o identificador desse usuário
- **AND** omite credenciais, tokens e objetos completos de usuário

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

### Requirement: Alterações de clientes são auditadas sem dados pessoais

O sistema SHALL registrar cada criação, atualização, mudança de situação cadastral, aplicação de bloqueio manual e remoção de bloqueio manual confirmada com ação, resultado, usuário autenticado e identificador interno do cliente. O evento SHALL NOT conter CPF, nome, e-mail, telefone, motivo textual do bloqueio ou o objeto completo do cliente.

#### Scenario: Criação de cliente auditada

- **WHEN** o backend confirma a criação de um cliente
- **THEN** o evento registra a ação, o resultado, o usuário autenticado e o `id` do cliente
- **AND** omite os dados pessoais e o objeto completo do cliente

#### Scenario: Atualização cadastral auditada

- **WHEN** o backend confirma uma atualização dos dados, situação ou bloqueio manual de um cliente
- **THEN** o evento identifica o tipo de ação e o `id` do cliente com metadados mínimos
- **AND** não registra valores anteriores ou posteriores dos dados pessoais nem o motivo textual do bloqueio

#### Scenario: Alteração recusada

- **WHEN** uma operação de cliente falha ou é recusada antes da gravação
- **THEN** o sistema não registra a alteração como bem-sucedida
- **AND** qualquer auditoria de recusa segue o contrato de autorização vigente sem dados pessoais

#### Scenario: Auditoria falha após gravação

- **WHEN** a alteração do cliente é confirmada, mas o evento de auditoria falha
- **THEN** a resposta distingue a gravação confirmada da falha de auditoria
- **AND** não orienta repetir cegamente a alteração nem afirma que a gravação foi revertida

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
