## ADDED Requirements

### Requirement: Funcionário pode autenticar-se pela interface Reflex

A aplicação SHALL permitir que uma pessoa com conta ativa e papel `member` ou `admin` entre no backoffice usando suas credenciais Xano. A interface SHALL apresentar uma resposta genérica para credenciais inválidas, contas inexistentes ou desativadas, sem revelar qual condição ocorreu.

#### Scenario: Login bem-sucedido

- **WHEN** uma pessoa envia credenciais válidas de uma conta ativa com papel `member` ou `admin`
- **THEN** o sistema inicia uma sessão autenticada e apresenta a área interna da aplicação

#### Scenario: Credenciais inválidas ou conta sem acesso

- **WHEN** uma pessoa envia credenciais inválidas, de uma conta inexistente ou de uma conta desativada
- **THEN** o acesso é recusado com mensagem genérica
- **AND** a interface não revela se a conta existe ou está desativada

#### Scenario: Papel fora dos papéis aceitos

- **WHEN** uma conta autenticada possui papel diferente de `member` e `admin`
- **THEN** a aplicação não concede acesso ao backoffice

### Requirement: Sessão autenticada é mantida e validada

A aplicação SHALL manter a identidade autenticada entre navegações enquanto a autenticação Xano for válida. A autorização das operações protegidas SHALL continuar sendo aplicada pelo backend.

#### Scenario: Navegação com sessão válida

- **WHEN** uma pessoa autenticada navega entre páginas internas com sessão válida
- **THEN** a aplicação mantém o acesso sem solicitar login novamente

#### Scenario: Sessão inválida ou expirada

- **WHEN** uma chamada protegida informa que a autenticação expirou ou é inválida
- **THEN** a aplicação encerra a sessão local
- **AND** direciona a pessoa à tela de login

#### Scenario: Conta desativada durante uma sessão

- **WHEN** a sessão é revalidada e o backend informa que a conta está desativada
- **THEN** a aplicação encerra a sessão local
- **AND** direciona a pessoa à tela de login

### Requirement: Bearer Xano não é exposto ao navegador

A aplicação SHALL manter o token de acesso Xano somente no lado servidor e SHALL NOT incluí-lo em dados de estado, componentes, cookies acessíveis ao JavaScript ou armazenamento do navegador.

#### Scenario: Estado da sessão enviado ao cliente

- **WHEN** a aplicação envia estado ou atualizações Reflex ao navegador
- **THEN** os dados contêm somente informações não secretas necessárias à interface
- **AND** não contêm o bearer Xano

### Requirement: Funcionário pode encerrar a sessão

A aplicação SHALL oferecer uma ação explícita de logout que encerra a sessão local do funcionário.

#### Scenario: Logout concluído

- **WHEN** uma pessoa autenticada solicita logout
- **THEN** a sessão local é removida
- **AND** páginas internas deixam de estar acessíveis até novo login

### Requirement: Páginas e ações internas exigem sessão

A aplicação SHALL exigir sessão autenticada antes de apresentar páginas ou executar ações do backoffice. Essa proteção de interface NÃO substitui autenticação e autorização no backend.

#### Scenario: Acesso direto sem sessão

- **WHEN** uma pessoa sem sessão tenta abrir diretamente uma página interna
- **THEN** a aplicação direciona a pessoa à tela de login

#### Scenario: Ação interna sem sessão válida

- **WHEN** uma sessão ausente, inválida ou expirada tenta iniciar uma ação interna
- **THEN** a interface não executa a ação e solicita novo login
