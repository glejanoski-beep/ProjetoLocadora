# Especificação: Fundação de autenticação, autorização e auditoria

## Requisitos

### Requisito 1: Sanitização de auditoria

O sistema DEVE registrar somente metadados mínimos e não sensíveis nos eventos de autenticação e administração.

#### Cenário: Login registrado sem credenciais

- **Dado** que um usuário realiza login com sucesso
- **Quando** o evento de login é criado
- **Então** o evento contém o identificador do usuário, a ação, o recurso ou contexto permitido e o resultado
- **E** não contém senha, hash de senha, token, objeto completo de usuário ou dados de recuperação

#### Cenário: Atualização de senha registrada sem segredo

- **Dado** que uma senha é alterada
- **Quando** o evento de auditoria é criado
- **Então** o evento identifica o usuário e a ação
- **E** não contém a senha anterior, a nova senha, hash ou token

### Requisito 2: Proteção de endpoints

Endpoints que consultam ou alteram dados de usuários DEVEM exigir autenticação e autorização no backend conforme o nível da operação.

#### Cenário: Envio de boas-vindas não autorizado

- **Dado** que uma requisição tenta enviar e-mail para um usuário
- **Quando** não há autenticação válida ou o papel não possui permissão
- **Então** a operação é rejeitada
- **E** nenhum e-mail é enviado
- **E** o usuário alvo não é exposto além do necessário para a resposta

#### Cenário: Operação administrativa autorizada

- **Dado** que um usuário autenticado possui o papel exigido
- **Quando** solicita uma operação administrativa permitida
- **Então** o backend permite a operação
- **E** registra o evento correspondente sem dados sensíveis

### Requisito 3: Estado de acesso do usuário

O sistema DEVE distinguir usuários ativos de usuários desativados e aplicar essa condição nos fluxos de autenticação.

#### Cenário: Usuário desativado tenta autenticar

- **Dado** que o usuário está desativado
- **Quando** tenta login comum ou login por magic link
- **Então** a autenticação é rejeitada
- **E** nenhum novo token de acesso é criado

#### Cenário: Usuário ativo autentica

- **Dado** que o usuário está ativo e apresenta credenciais válidas
- **Quando** realiza login
- **Então** o sistema cria o token conforme a política vigente
- **E** registra o evento de autenticação

### Requisito 4: Recuperação de senha sem enumeração

O pedido público de recuperação DEVE apresentar resposta indistinguível para e-mails cadastrados e não cadastrados.

#### Cenário: E-mail cadastrado

- **Dado** que o e-mail pertence a um usuário
- **Quando** é solicitado um link de recuperação
- **Então** o sistema processa o pedido e envia o link conforme a configuração existente
- **E** retorna uma resposta genérica

#### Cenário: E-mail não cadastrado

- **Dado** que o e-mail não pertence a um usuário
- **Quando** é solicitado um link de recuperação
- **Então** o sistema retorna a mesma resposta genérica
- **E** não revela se o e-mail existe

### Requisito 5: Consumo único de magic link

Um magic link DEVE ser utilizável uma única vez, inclusive quando houver requisições concorrentes.

#### Cenário: Primeiro consumo válido

- **Dado** que o token é válido, não expirou e ainda não foi usado
- **Quando** é consumido
- **Então** o sistema cria o acesso autorizado
- **E** marca o token como usado de forma indivisível

#### Cenário: Reuso concorrente

- **Dado** que duas requisições tentam consumir o mesmo token simultaneamente
- **Quando** a primeira requisição o consome
- **Então** no máximo uma requisição recebe o novo token de acesso
- **E** as demais são rejeitadas como token usado ou inválido

### Requisito 6: Rastreabilidade de autorização

Operações de autenticação, autorização, recuperação e administração DEVEM possuir eventos auditáveis com usuário, ação, recurso quando aplicável e resultado.

#### Cenário: Acesso negado auditado

- **Dado** que uma operação é rejeitada por falta de autenticação ou permissão
- **Quando** o fluxo termina
- **Então** o sistema registra a ação e o resultado negado
- **E** não registra credenciais, tokens ou dados sensíveis desnecessários
