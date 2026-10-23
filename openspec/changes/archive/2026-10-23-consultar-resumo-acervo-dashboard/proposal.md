# Proposal

## Why

A Dashboard atual apresenta indicadores indisponíveis e não oferece um resumo real do acervo cadastrado. O objetivo desta primeira entrega é permitir ao administrador consultar totais confiáveis de filmes e exemplares, sem confundir cadastro com disponibilidade para locação ou interferir nas entregas do grupo.

## What Changes

- Adicionar somente dois indicadores reais: total de todos os registros de `film` (ativos e inativos) e total de todos os registros de `exemplar`.
- Propor uma API Xano de agregação somente de leitura, com autenticação `user` e autorização de conta ativa `admin` no backend antes das contagens; preservar a compatibilidade vigente de contas legadas sem estado explícito.
- Retornar dois inteiros não negativos e horário de geração, sem dados pessoais, listas de registros ou credenciais.
- Integrar Xano → adaptador Python → estado próprio da Dashboard no Reflex → cartões, reutilizando a sessão privada existente.
- Consultar ao entrar na Dashboard e oferecer Atualizar manual, sem polling; distinguir carregamento, sucesso, zero válido, falha de rede, resposta inválida e ausência de permissão.
- Limpar resultados e invalidar respostas pendentes após logout, troca de conta ou perda de autorização.
- Preservar `/backoffice` para `admin` e `member`, inclusive seus links e funcionalidades permitidas; `member` não consulta nem recebe os indicadores protegidos.
- Manter indicadores operacionais e financeiros futuros explicitamente indisponíveis, sem zeros, saldos ou disponibilidade inventados.

**Não objetivos:** implementar disponibilidade, locações, devoluções, multas, pagamentos, relatórios adicionais, gráficos, filtros de Dashboard, polling, cache persistente, novas tabelas ou alterações em `film` e `exemplar`; alterar regras, contratos ou funcionalidades dos colegas. Este PROPOSE cria exclusivamente planejamento; implementação e qualquer operação remota dependem de autorização posterior.

## Capabilities

### New Capabilities

- `resumo-acervo-dashboard`: Consulta administrativa dos totais cadastrados, estados de apresentação, atualização e isolamento de sessão, preservando o backoffice compartilhado.

### Modified Capabilities

Nenhuma. `acesso-seguro`, `auditoria-segura`, `catalogo-filmes` e `exemplares` permanecem com seus contratos; a permissão da nova agregação é específica e não restringe as consultas existentes de `member`.

## Impact

- Futuro grupo e endpoint de leitura Xano próprios para a Dashboard no branch `v1`; reutilização de `Quick Start/enforce_role` e de sua auditoria mínima de recusas, sem modificar essas funções.
- Futuro adaptador e estado/componentes dedicados; integração pontual no módulo principal Reflex, no carregamento das rotas `/` e `/backoffice` e no ciclo de sessão. Nenhuma migração de dados.
- URL do novo grupo independente das URLs de autenticação, catálogo, clientes e exemplares; seu identificador será obtido no APPLY, sem assumir um `canonical` existente.
- Verificação futura de contagens exatas, ativos/inativos, base vazia, independência dos filtros, autorização direta, sigilo de tokens, navegação, logout/troca de conta, respostas tardias e erros.
- Pontos compartilhados com o grupo: `ProjetoLocadora/ProjetoLocadora.py`, `ProjetoLocadora/config.py`, sessão e testes de autenticação; coordenar alterações mínimas e preservar o trabalho de clientes, catálogo e exemplares. Detalhes e riscos em `design.md`.
