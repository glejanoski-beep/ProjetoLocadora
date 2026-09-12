# Especificação: Recuperação de senha segura

## Requisitos

### Requisito 1: Resposta sem enumeração

O pedido público de recuperação DEVE apresentar resposta indistinguível para e-mails cadastrados e não cadastrados.

#### Cenário: E-mail cadastrado

- **Dado** que o e-mail pertence a um usuário
- **Quando** é solicitado um link
- **Então** o processamento ocorre conforme a configuração
- **E** a resposta pública é genérica

#### Cenário: E-mail não cadastrado

- **Dado** que o e-mail não pertence a um usuário
- **Quando** é solicitado um link
- **Então** a resposta pública é igual à do e-mail cadastrado
- **E** a existência do usuário não é revelada

### Requisito 2: Token de uso único

Um magic link válido DEVE ser consumido uma única vez, inclusive sob concorrência.

#### Cenário: Reuso concorrente

- **Dado** que duas requisições tentam consumir o mesmo token
- **Quando** a primeira o consome
- **Então** no máximo uma requisição recebe acesso
- **E** as demais são rejeitadas

### Requisito 3: Proteção do token

O sistema NÃO DEVE devolver token de recuperação ao chamador público nem registrá-lo em auditoria.

### Requisito 4: Contrato do frontend

O link deve apontar para uma rota real e documentada do frontend Reflex, sem manter a rota de demonstração como contrato definitivo.
