# Design: Fundação de autenticação, autorização e auditoria

## Decisões

### Sanitização centralizada de eventos

Manter a função existente de registro de eventos como ponto central e alterar seus contratos ou os chamadores para aceitar apenas metadados explicitamente permitidos. Os endpoints não devem enviar objetos completos de usuário para a auditoria.

O evento deve conservar, no mínimo, usuário responsável, ação, resultado e referência do recurso quando aplicável. Segredos não devem entrar no payload do evento.

### Autorização no backend

Proteger endpoints com autenticação explícita e executar a verificação de papel no backend antes da operação sensível. Reutilizar `Quick Start/enforce_role` ou evoluí-la de forma compatível, sem confiar em verificações feitas pelo frontend.

A matriz detalhada de permissões da locadora fica para uma mudança futura; esta mudança cobre a proteção da fundação existente.

### Estado de acesso

Adicionar ao usuário um estado explícito de acesso, com valor padrão ativo, e validar esse estado antes de criar tokens em login comum e magic link. A desativação deve preservar histórico e não remover registros.

### Recuperação de senha

Manter o contrato de e-mail e `$env.$api_baseurl`, mas fazer o endpoint público responder de forma genérica independentemente da existência do e-mail. O fluxo interno não deve devolver token ou sinalizar existência ao chamador público.

O consumo do token deve usar uma atualização condicionada ao estado ainda não usado, ou mecanismo equivalente suportado pelo Xano, para garantir que apenas uma requisição concorrente seja bem-sucedida.

### Compatibilidade

Preservar nomes de recursos, GUIDs e contratos existentes sempre que possível. Alterações incompatíveis na rota do frontend de recuperação devem ser explicitamente documentadas; a rota de demonstração não deve ser tratada como contrato final.

## Validação

Como não há compilador local para XanoScript, validar a sintaxe comparando com recursos existentes, consultar a documentação Xano quando necessário e exercitar os fluxos no ambiente Xano. Os cenários críticos devem cobrir logs sem segredos, autorização, usuário desativado, enumeração e concorrência do magic link.
