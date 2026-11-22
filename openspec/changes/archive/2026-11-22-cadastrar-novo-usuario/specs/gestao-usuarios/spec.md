# Spec Delta

## ADDED Requirements

### Requirement: Admin cria conta interna básica sem senha inicial

O backend SHALL permitir que uma conta ativa `admin` crie uma conta interna informando nome, e-mail e papel (`admin` ou `member`). O nome SHALL ser obrigatório e SHALL ter no máximo 200 caracteres. A conta criada SHALL iniciar ativa, SHALL NOT receber senha padrão e SHALL permitir que o usuário realize a primeira definição de senha pelo fluxo existente de “Esqueci minha senha” e magic link. O backend SHALL rejeitar nome vazio ou excessivo, e-mail inválido, e-mail duplicado, papel inválido e tentativas de `member` ou conta inativa.

#### Scenario: Criação por administrador

- **WHEN** um administrador envia nome e e-mail válidos e seleciona `member`
- **THEN** o backend cria uma conta ativa sem senha inicial
- **AND** devolve o identificador, nome, e-mail, papel e situação da conta

#### Scenario: Papel administrador

- **WHEN** um administrador cria uma conta selecionando `Administrador`
- **THEN** o backend cria a conta com papel `admin`

#### Scenario: E-mail duplicado

- **WHEN** o administrador tenta criar uma conta com e-mail já cadastrado
- **THEN** o backend rejeita a operação sem criar registro
- **AND** informa que o e-mail já está em uso

#### Scenario: Membro tenta criar conta

- **WHEN** uma conta `member` chama o endpoint de criação
- **THEN** o backend recusa antes de criar ou consultar a conta

#### Scenario: Primeiro acesso sem senha compartilhada

- **WHEN** a conta criada ainda não possui senha
- **THEN** o usuário consegue solicitar um link de redefinição pelo fluxo existente
- **AND** define sua própria senha antes de autenticar normalmente
