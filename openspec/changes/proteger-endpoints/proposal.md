# Proposal: Proteger endpoints e acessos

## Problema

O endpoint de envio de boas-vindas não declara autenticação, a verificação de papéis não está integrada aos fluxos existentes e não há estado explícito para impedir acesso de usuários desativados.

## Objetivo

Garantir que operações de usuários sejam protegidas por autenticação, autorização e estado de acesso verificados no backend.

## Escopo

- Proteger o envio de e-mail de boas-vindas.
- Integrar a verificação de papel aos endpoints administrativos da fundação.
- Adicionar estado de acesso com padrão ativo.
- Rejeitar usuários desativados no login comum e no login por magic link.

## Fora do escopo

- Matriz completa de permissões da locadora.
- Recuperação de senha e consumo de magic links.
- Cadastro de clientes, filmes, exemplares ou locações.

## Resultado esperado

Nenhuma operação administrativa da fundação depende apenas do frontend ou de um papel não verificado; usuários desativados não recebem novos tokens.
