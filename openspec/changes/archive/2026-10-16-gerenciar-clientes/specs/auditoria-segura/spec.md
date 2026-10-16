# Spec Delta

## ADDED Requirements

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
