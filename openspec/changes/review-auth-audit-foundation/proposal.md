# Proposal: Revisar fundação de autenticação, autorização e auditoria

## Problema

A base Xano atual possui autenticação e registro de eventos, mas ainda contém riscos antes da implementação de clientes, locações e pagamentos. Fluxos de autenticação registram objetos completos de usuário nos logs, o endpoint de boas-vindas não declara autenticação, a autorização por papel não está integrada aos endpoints e o fluxo de recuperação de senha pode revelar a existência de usuários e permitir consumo concorrente de tokens.

## Objetivo

Fortalecer autenticação, autorização e auditoria para que a fundação possa sustentar as próximas funcionalidades do sistema com proteção de dados, controle de acesso e rastreabilidade adequados.

## Escopo

- Sanitizar metadados de auditoria e impedir registro de senhas, hashes, tokens e objetos completos de usuário.
- Proteger o envio de e-mail de boas-vindas com autenticação e autorização adequadas.
- Integrar a verificação de papéis aos endpoints administrativos existentes.
- Definir e aplicar o estado de acesso do usuário.
- Tornar o pedido de recuperação de senha indistinguível para e-mails existentes e inexistentes.
- Impedir reutilização concorrente de magic links.
- Corrigir retornos inconsistentes do fluxo de recuperação.
- Atualizar a cobertura de auditoria para registrar ação, usuário, recurso e resultado sem dados sensíveis.

## Fora do escopo

- Cadastro de clientes, filmes ou exemplares.
- Locações, devoluções, multas e pagamentos.
- Implementação de novas telas Reflex.
- Integração com provedores externos de identidade ou pagamento.
- Redefinição completa da matriz de permissões do domínio da locadora, além dos papéis necessários para proteger a fundação atual.

## Resultado esperado

Os fluxos existentes de autenticação e recuperação não expõem dados sensíveis, os endpoints protegidos validam autorização no backend, os usuários desativados não obtêm acesso e os eventos relevantes permanecem auditáveis sem comprometer credenciais ou tokens.
