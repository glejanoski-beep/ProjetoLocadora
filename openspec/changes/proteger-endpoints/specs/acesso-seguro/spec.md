# Especificação: Acesso seguro

## Requisitos

### Requisito 1: Autenticação de endpoints

Endpoints que consultam ou alteram dados de usuários DEVEM exigir autenticação válida.

#### Cenário: Chamada não autenticada

- **Dado** que uma requisição não possui autenticação válida
- **Quando** chama uma operação protegida
- **Então** a operação é rejeitada
- **E** nenhum efeito colateral ocorre

### Requisito 2: Autorização por papel

Operações administrativas DEVEM verificar no backend o papel exigido antes da execução.

#### Cenário: Papel insuficiente

- **Dado** que o usuário está autenticado, mas não possui o papel exigido
- **Quando** solicita uma operação administrativa
- **Então** a operação é rejeitada
- **E** nenhum e-mail ou alteração é executado

### Requisito 3: Usuário desativado

Usuários desativados NÃO DEVEM receber novos tokens de acesso.

#### Cenário: Login bloqueado

- **Dado** que o usuário está desativado
- **Quando** tenta login comum ou por magic link
- **Então** a autenticação é rejeitada
- **E** nenhum novo token é criado

### Requisito 4: Usuário ativo

Usuários ativos com credenciais válidas DEVEM continuar podendo autenticar conforme a política vigente.
