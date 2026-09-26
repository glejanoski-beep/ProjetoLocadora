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
