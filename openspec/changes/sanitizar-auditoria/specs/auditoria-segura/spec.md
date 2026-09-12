# Especificação: Auditoria segura

## Requisitos

### Requisito 1: Metadados mínimos

O sistema DEVE registrar somente metadados necessários para rastreabilidade.

#### Cenário: Login auditado

- **Dado** que um usuário realiza login
- **Quando** o evento é criado
- **Então** ele identifica usuário, ação e resultado
- **E** não contém senha, hash, token ou objeto completo de usuário

### Requisito 2: Alteração de senha auditada

O sistema DEVE registrar a alteração de senha sem registrar qualquer segredo.

#### Cenário: Senha alterada

- **Dado** que a senha foi alterada
- **Quando** o evento é criado
- **Então** ele identifica o usuário e a ação
- **E** não contém senha anterior, nova senha, hash ou token

### Requisito 3: Falhas rastreáveis

O sistema DEVE registrar falhas relevantes de autenticação e administração sem dados sensíveis.

#### Cenário: Operação negada

- **Dado** que uma operação é rejeitada
- **Quando** o fluxo termina
- **Então** o evento registra ação e resultado negado
- **E** omite credenciais e tokens
