# Spec Delta

## ADDED Requirements

### Requirement: Acervo e edição exibem a capa do filme

O card do acervo SHALL exibir a capa quando o filme tiver uma, com texto alternativo “Capa de {título}” e carregamento preguiçoso; sem capa, ou com `path` fora do formato esperado, SHALL manter o pôster de cor existente. A tela de edição SHALL exibir, somente a administradores, a área “Capa” com prévia, enviar ou trocar (JPEG, PNG ou WebP até 2 MB) e remover. Antes de enviar, o servidor Reflex SHALL validar tamanho e assinatura binária e SHALL gerar o nome do arquivo, sem usar o nome informado pelo usuário. Durante o envio a área SHALL indicar carregamento; erros de validação, de permissão, de limite de requisições e de auditoria SHALL ser exibidos com papel `alert`, sem repetir automaticamente a operação. O cadastro de novo filme SHALL NOT oferecer capa.

#### Scenario: Card com capa

- **WHEN** o acervo lista um filme com capa
- **THEN** o card mostra a imagem da capa no lugar do pôster de cor

#### Scenario: Arquivo inválido na interface

- **WHEN** o administrador escolhe um PDF renomeado para `.jpg`
- **THEN** a interface recusa pelo conteúdo, informa o motivo e nada é enviado ao Xano
