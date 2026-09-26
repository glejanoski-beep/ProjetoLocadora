## Purpose

Define a recuperação de senha por magic link com respostas que protegem a privacidade e tokens de uso único integrados à interface Reflex.

## ADDED Requirements

### Requirement: Resposta de recuperação não revela cadastro

O sistema DEVE apresentar respostas públicas indistinguíveis para pedidos de recuperação associados a e-mails cadastrados e não cadastrados.

#### Scenario: Pedido para e-mail cadastrado

- **WHEN** uma pessoa solicita recuperação usando um e-mail cadastrado
- **THEN** o sistema processa o envio do magic link e retorna uma resposta genérica

#### Scenario: Pedido para e-mail não cadastrado

- **WHEN** uma pessoa solicita recuperação usando um e-mail não cadastrado
- **THEN** o sistema retorna a mesma resposta genérica sem revelar a inexistência do cadastro

### Requirement: Magic link pode ser consumido uma única vez

O sistema DEVE aceitar um magic link válido no máximo uma vez, inclusive quando houver tentativas de consumo concorrentes.

#### Scenario: Primeiro consumo válido

- **WHEN** um magic link válido, não expirado e ainda não utilizado é consumido
- **THEN** o sistema concede o acesso previsto pelo fluxo de recuperação e marca o token como utilizado

#### Scenario: Tentativas concorrentes de consumo

- **WHEN** duas requisições tentam consumir simultaneamente o mesmo magic link
- **THEN** no máximo uma requisição recebe acesso e as demais são rejeitadas

### Requirement: Token de recuperação não é exposto

O sistema NÃO DEVE devolver o token de recuperação ao chamador público nem registrá-lo em eventos de auditoria.

#### Scenario: Pedido público de recuperação

- **WHEN** uma pessoa solicita um magic link
- **THEN** a resposta pública não contém o token de recuperação

#### Scenario: Auditoria de recuperação

- **WHEN** uma ação do fluxo de recuperação é registrada em auditoria
- **THEN** o evento não contém token, senha, hash de senha ou objeto completo do usuário

### Requirement: Link usa rota de recuperação do frontend Reflex

O link enviado para recuperação DEVE direcionar para uma rota existente e documentada do frontend Reflex, e NÃO DEVE depender da rota de demonstração do template.

#### Scenario: Abertura do link de recuperação

- **WHEN** a pessoa abre o link recebido por e-mail
- **THEN** o navegador acessa a rota `/redefinir-senha` do frontend Reflex com os parâmetros necessários ao fluxo
