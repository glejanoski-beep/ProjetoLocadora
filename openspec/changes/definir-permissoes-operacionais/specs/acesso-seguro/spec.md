# Spec Delta

## ADDED Requirements

### Requirement: Cadastro público concede acesso automático como member

O sistema SHALL manter o cadastro público criando contas com papel `member` e acesso automático ao backoffice quando ativas, sem aprovação administrativa prévia e sem exigir vínculo com Funcionário. O cadastro público SHALL NOT conceder papel `admin`. Os papéis e estados das contas existentes SHALL ser preservados.

#### Scenario: Nova conta pública ativa
- **WHEN** uma pessoa conclui um cadastro público válido
- **THEN** a conta recebe o papel `member` e pode entrar no backoffice sem aprovação prévia
- **AND** suas operações permanecem limitadas às permissões de `member`

#### Scenario: Tentativa de obter privilégio administrativo no cadastro
- **WHEN** uma requisição de cadastro público tenta atribuir papel `admin`
- **THEN** o sistema não concede esse papel

#### Scenario: Contas existentes após a mudança
- **WHEN** a política é aplicada
- **THEN** contas existentes conservam seus papéis e estados
- **AND** nenhum vínculo com Funcionário é exigido para autenticar

### Requirement: Operações protegidas verificam o estado atual da conta

O backend SHALL recusar operações protegidas de contas inexistentes, explicitamente desativadas ou com papel não reconhecido, mesmo com token ainda válido. A verificação SHALL ocorrer antes de consultar dados protegidos ou produzir efeitos operacionais. Estado legado sem valor explícito SHALL continuar tratado como ativo, conforme a compatibilidade vigente.

#### Scenario: Conta desativada depois da emissão do token
- **WHEN** uma conta explicitamente desativada chama uma operação protegida com token não expirado
- **THEN** o backend recusa a operação
- **AND** não devolve dados protegidos nem executa alteração ou envio de e-mail

#### Scenario: Papel não reconhecido
- **WHEN** uma conta com papel ausente ou não reconhecido chama uma operação protegida
- **THEN** o backend recusa a operação sem executar o efeito solicitado

#### Scenario: Conta legada com papel válido
- **WHEN** uma conta sem estado de acesso explícito e com papel reconhecido solicita uma operação permitida
- **THEN** a ausência do estado não causa recusa por desativação

### Requirement: Admin possui acesso geral sujeito às regras de negócio

O sistema SHALL autorizar contas ativas `admin` a executar as operações implementadas da locadora. Essa autorização SHALL NOT dispensar validações de negócio, disponibilidade, consistência financeira ou preservação do histórico.

#### Scenario: Operação administrativa válida
- **WHEN** uma conta ativa `admin` solicita uma operação administrativa implementada com dados válidos
- **THEN** a operação é autorizada

#### Scenario: Operação administrativamente permitida viola invariante
- **WHEN** uma conta ativa `admin` solicita uma operação que viola uma regra de negócio
- **THEN** a operação é recusada apesar do papel administrativo

### Requirement: Member consulta cadastros sem alterá-los

O sistema SHALL autorizar contas ativas `member` a consultar cadastros de clientes, filmes e exemplares pelas operações implementadas. Criar, alterar, inativar ou excluir esses cadastros SHALL exigir `admin`. Registrar uma locação e seus efeitos controlados sobre o exemplar SHALL NOT ser tratado como manutenção livre do cadastro.

#### Scenario: Consulta de cadastro por member
- **WHEN** uma conta ativa `member` chama uma consulta implementada de clientes, filmes ou exemplares
- **THEN** a consulta é autorizada dentro do contrato de dados da operação

#### Scenario: Alteração direta de cadastro por member
- **WHEN** uma conta ativa `member` chama diretamente uma API de criação, alteração ou inativação de cadastro
- **THEN** o backend recusa a operação
- **AND** o cadastro permanece inalterado

### Requirement: Member registra transações operacionais permitidas

O sistema SHALL autorizar contas ativas `member` a incluir locações, registrar pagamentos e registrar multas pelas operações implementadas, sujeitas às regras de negócio de cada capacidade. Registrar pagamentos SHALL atualizar a quitação somente conforme o saldo; registrar multas SHALL respeitar a política de cálculo. Esta política SHALL NOT criar capacidades operacionais ausentes.

#### Scenario: Registro operacional válido por member
- **WHEN** uma conta ativa `member` solicita inclusão de locação, registro de pagamento ou registro de multa por uma operação implementada
- **THEN** o papel permite a operação
- **AND** o efeito depende das validações do respectivo domínio

#### Scenario: Valor ou condição operacional inválida
- **WHEN** uma conta ativa `member` solicita uma transação incompatível com a regra de negócio
- **THEN** a operação é recusada sem registrar a transação inválida

### Requirement: Ajustes privilegiados e gestão de acessos exigem admin

O sistema SHALL restringir a `admin` a gestão de papéis e estado de acesso, estornos, cancelamentos e ajustes de transações financeiras quando essas operações forem implementadas. A permissão de registrar pagamentos ou multas SHALL NOT autorizar `member` a executar esses ajustes. Operações não especificadas SHALL NOT receber permissão implícita de `member`.

#### Scenario: Member solicita ajuste financeiro
- **WHEN** uma conta ativa `member` solicita estorno, cancelamento ou ajuste financeiro por uma API implementada
- **THEN** o backend recusa a operação sem alterar o histórico ou saldo

#### Scenario: Member solicita alteração de acesso
- **WHEN** uma conta ativa `member` solicita atribuição de papel ou alteração de estado de acesso
- **THEN** o backend recusa a operação

#### Scenario: Operação sem permissão definida para member
- **WHEN** uma operação protegida não possui permissão explícita de `member`
- **THEN** o sistema não concede esse acesso por omissão

### Requirement: Recusas de autorização mantêm auditoria segura

O sistema SHALL registrar recusas por estado de acesso ou papel com os metadados mínimos permitidos pela auditoria existente. A recusa SHALL NOT executar o efeito operacional solicitado; o evento de auditoria de recusa é permitido. Credenciais, tokens e objetos completos de usuário SHALL NOT ser registrados.

#### Scenario: Operação recusada e auditada
- **WHEN** uma conta autenticada identificável é recusada por desativação ou papel insuficiente
- **THEN** o sistema registra ação, resultado e identificador dessa conta sem segredos
- **AND** o efeito operacional solicitado não ocorre

#### Scenario: Recusa sem identidade verificável
- **WHEN** uma recusa é registrada sem identidade autenticada verificável
- **THEN** o evento não atribui a ação a uma identidade fornecida pelo solicitante
- **AND** respeita o contrato de auditoria anônima vigente
