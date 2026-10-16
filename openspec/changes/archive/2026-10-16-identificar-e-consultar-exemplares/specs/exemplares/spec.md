## Purpose

Permitir identificar individualmente cada cópia física, associá-la a um filme existente e consultar essa relação por meio de operações protegidas.

## ADDED Requirements

### Requirement: Cada exemplar possui identificador único

O sistema SHALL persistir cada exemplar com um identificador que não possa identificar mais de um exemplar. A unicidade SHALL comparar exatamente o valor informado, sem normalização de espaços ou caixa, e SHALL ser garantida no backend/banco de dados, não somente pela interface.

#### Scenario: Identificador já utilizado

- **WHEN** uma operação tenta persistir um exemplar com o mesmo valor de identificador já associado a outro exemplar
- **THEN** o backend recusa a operação
- **AND** nenhum segundo exemplar com esse identificador é persistido

#### Scenario: Tentativas concorrentes com o mesmo identificador

- **WHEN** duas operações concorrentes tentam persistir exemplares com o mesmo valor de identificador
- **THEN** no máximo uma operação persiste um exemplar com esse identificador
- **AND** a outra operação recebe uma falha explícita

### Requirement: Exemplar pertence a filme existente

O sistema SHALL associar cada exemplar persistido a um filme existente. O backend SHALL validar a existência do filme antes de persistir o exemplar.

#### Scenario: Associação a filme existente

- **WHEN** um administrador autorizado solicita a criação de um exemplar associado a um filme existente
- **THEN** o exemplar é persistido com a associação a esse filme

#### Scenario: Associação a filme inexistente

- **WHEN** uma operação tenta criar um exemplar associado a um filme inexistente
- **THEN** o backend recusa a operação
- **AND** nenhum exemplar é persistido

### Requirement: Usuários autorizados consultam exemplares e seu filme

O sistema SHALL permitir que usuários ativos com papel `member` ou `admin` consultem exemplares. Cada resultado SHALL identificar individualmente o exemplar e informar a qual filme existente pertence.

#### Scenario: Consulta de exemplares associados a filmes

- **WHEN** um usuário autorizado consulta os exemplares
- **THEN** a resposta identifica cada exemplar individualmente
- **AND** informa o filme associado a cada exemplar

#### Scenario: Consulta sem exemplares cadastrados

- **WHEN** um usuário autorizado consulta e não há exemplares cadastrados
- **THEN** a consulta retorna um resultado vazio válido

### Requirement: Cadastro de exemplares exige administrador

O sistema SHALL permitir somente a usuários ativos com papel `admin` cadastrar exemplares. A autorização SHALL ser verificada no backend; ocultar ou desabilitar controles na interface SHALL NOT substituir essa autorização. Edição e exclusão de exemplares não fazem parte desta capability nesta change.

#### Scenario: Administrador cadastra exemplar

- **WHEN** um usuário ativo `admin` solicita o cadastro de um exemplar com dados válidos
- **THEN** o backend autoriza a operação, sujeita aos requisitos de unicidade e associação a filme existente

#### Scenario: Member tenta cadastrar exemplar

- **WHEN** um usuário ativo `member` solicita diretamente o cadastro de um exemplar
- **THEN** o backend recusa a operação
- **AND** nenhum exemplar é persistido

#### Scenario: Conta sem autorização válida

- **WHEN** uma conta não autenticada, inativa ou com papel não reconhecido solicita uma operação protegida de exemplar
- **THEN** o backend recusa a operação antes de consultar ou alterar dados protegidos
