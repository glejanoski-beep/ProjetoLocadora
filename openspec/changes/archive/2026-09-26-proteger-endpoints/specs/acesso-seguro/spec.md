## Purpose

Define autenticação, autorização por papel e estado de acesso para proteger operações internas e administrativas da locadora no backend.

## ADDED Requirements

### Requirement: Operações protegidas exigem autenticação

Endpoints que consultam ou alteram dados existentes ou executam operações internas SHALL exigir autenticação válida. Endpoints públicos de login e cadastro SHALL continuar acessíveis sem sessão, aplicando suas próprias validações.

#### Scenario: Chamada não autenticada a uma operação protegida

- **WHEN** uma requisição sem autenticação válida chama uma operação protegida
- **THEN** o backend rejeita a operação
- **AND** nenhum efeito colateral é executado

#### Scenario: Cadastro público de conta

- **WHEN** uma pessoa envia dados válidos ao endpoint público de cadastro
- **THEN** o sistema pode criar a conta com o papel público permitido
- **AND** a requisição não recebe privilégios administrativos

### Requirement: Operações administrativas verificam o papel no backend

Operações administrativas SHALL verificar no backend o papel exigido antes de consultar dados protegidos ou executar efeitos colaterais.

#### Scenario: Papel insuficiente

- **WHEN** um usuário autenticado sem o papel exigido solicita uma operação administrativa
- **THEN** o backend rejeita a operação
- **AND** nenhum e-mail ou alteração administrativa é executado

#### Scenario: Administrador autorizado

- **WHEN** um administrador autenticado solicita uma operação permitida ao papel de administrador
- **THEN** o backend executa a operação após validar o papel

### Requirement: Usuários desativados não recebem novos tokens de acesso

Usuários explicitamente desativados SHALL NOT receber novos tokens por login comum ou login por magic link. Registros legados sem valor explícito de estado SHALL permanecer ativos para compatibilidade.

#### Scenario: Login bloqueado para usuário desativado

- **WHEN** um usuário desativado tenta autenticar por senha ou magic link
- **THEN** a autenticação é rejeitada
- **AND** nenhum novo token de acesso é criado

#### Scenario: Registro legado sem estado explícito

- **WHEN** um usuário existente não possui valor explícito para o estado de acesso
- **THEN** o sistema o trata como ativo para preservar compatibilidade

### Requirement: Usuários ativos continuam podendo autenticar

Usuários ativos com credenciais válidas SHALL continuar podendo autenticar conforme a política de autenticação vigente.

#### Scenario: Login válido de usuário ativo

- **WHEN** um usuário ativo apresenta credenciais válidas no login comum ou por magic link
- **THEN** o sistema concede autenticação e cria o token conforme a política vigente
