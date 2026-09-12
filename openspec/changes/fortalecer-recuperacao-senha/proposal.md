# Proposal: Fortalecer recuperação de senha

## Problema

O fluxo atual pode revelar se um e-mail existe, depende de rota de demonstração e não garante consumo único do magic link em requisições concorrentes.

## Objetivo

Tornar a recuperação de senha segura contra enumeração, reuso e condições de corrida, preservando os contratos necessários com Xano e Reflex.

## Escopo

- Responder de forma genérica para e-mails existentes e inexistentes.
- Impedir que o chamador público receba token ou confirmação de existência.
- Garantir consumo único do magic link mesmo sob concorrência.
- Corrigir o retorno interno inconsistente do gerador de token.
- Documentar a rota real de recuperação do frontend quando definida.

## Fora do escopo

- Alteração geral de autenticação e papéis.
- Cadastro e operação da locadora.
- Integração com provedor externo de identidade.

## Resultado esperado

O fluxo de recuperação não permite enumeração de usuários nem reutilização de magic links, e sua integração com o frontend possui contrato explícito.
