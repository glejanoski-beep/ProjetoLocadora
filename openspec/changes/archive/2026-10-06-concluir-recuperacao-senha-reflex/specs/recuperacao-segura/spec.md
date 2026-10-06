## ADDED Requirements

### Requirement: Funcionário pode solicitar recuperação pela interface Reflex

A aplicação SHALL oferecer uma tela pública `/recuperar-senha` que envie o e-mail informado ao endpoint público de solicitação de recuperação. A resposta exibida SHALL ser genérica para e-mails existentes e inexistentes.

#### Scenario: Solicitação enviada

- **WHEN** uma pessoa informa um e-mail e envia o formulário
- **THEN** a aplicação chama o endpoint de solicitação de recuperação
- **AND** exibe uma confirmação genérica sem revelar se o cadastro existe

#### Scenario: Solicitação com e-mail ausente ou inválido

- **WHEN** uma pessoa envia o formulário sem um e-mail válido
- **THEN** a aplicação não envia a requisição
- **AND** exibe uma mensagem de validação sem revelar dados de cadastro

### Requirement: Magic link é consumido ao abrir a tela de redefinição

A aplicação SHALL ler `magic_token` e `email` da URL `/redefinir-senha` e consumir o magic link ao carregar a tela. O token de autenticação retornado SHALL permanecer somente no estado privado do servidor Reflex.

#### Scenario: Link válido aberto

- **WHEN** uma pessoa abre `/redefinir-senha?magic_token=...&email=...` com um link válido
- **THEN** a aplicação chama o endpoint de login por magic link
- **AND** mantém o token retornado somente no estado privado do servidor
- **AND** exibe o formulário para definir a nova senha

#### Scenario: Link inválido, expirado ou usado

- **WHEN** a pessoa abre a tela com parâmetros ausentes ou um magic link inválido, expirado ou já usado
- **THEN** a aplicação não exibe o formulário de nova senha
- **AND** apresenta uma mensagem genérica
- **AND** oferece retorno para `/login`

### Requirement: Funcionário pode definir nova senha pela tela Reflex

A aplicação SHALL permitir informar nova senha e confirmação depois que o magic link for consumido com sucesso, enviando os dados ao endpoint protegido de atualização de senha com o token mantido no estado privado.

#### Scenario: Senhas válidas e iguais

- **WHEN** a pessoa informa uma senha válida e a confirmação correspondente
- **THEN** a aplicação chama o endpoint de atualização de senha autenticado
- **AND** exibe confirmação de sucesso
- **AND** oferece retorno à tela de login

#### Scenario: Senhas divergentes ou inválidas

- **WHEN** a pessoa informa senhas divergentes ou que não atendem à validação mínima
- **THEN** a aplicação não chama o endpoint de atualização
- **AND** exibe uma mensagem de validação

### Requirement: Link de recuperação usa URL de desenvolvimento do Reflex

No ambiente de desenvolvimento, o endpoint Xano de solicitação SHALL montar o link usando `http://localhost:3000` como base do frontend e SHALL preservar a rota `/redefinir-senha` e seus parâmetros necessários.

#### Scenario: Link enviado em desenvolvimento

- **WHEN** o Xano envia um e-mail de recuperação no ambiente local
- **THEN** o link direciona para `http://localhost:3000/redefinir-senha`
- **AND** não direciona para a base da API Xano
