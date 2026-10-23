# Inspeção e validação inicial

Data: 21/10/2026, horário de Brasília. Este documento descreve evidências; não representa implementação ou homologação de locação.

## Repositório e colaboração

- A pasta inicial do chat não continha checkout do ProjetoLocadora. O projeto foi localizado em `/home/usuario/Projetos/ProjetoLocadora` e copiado por clone independente para a pasta deste chat, sem modificar o checkout original.
- Origem confirmada: `https://github.com/glejanoski-beep/ProjetoLocadora.git`. Fetch remoto concluído; `HEAD` e `origin/main` coincidem em `1a21fc87e33dd63bcb17ada97b891f3b0e85046f`.
- PR #2, `feat: adicionar resumo administrativo do acervo na dashboard`, foi integrado em 19/10/2026; merge `b895b1159a5cccac14ab98f02af77994e4c5a4ee` é ancestral da main atual. Existem commits posteriores de organização e consolidação do login.
- Nova branch exclusivamente local: `codex/registrar-locacao`, criada da main remota atualizada.
- Branches remotas consultadas: `main`, `feature/marcelo`, `work`. Busca de PRs retornou #1 (permissões operacionais) e #2 (dashboard). Não foi encontrado módulo, schema ou API de locação nas evidências consultadas. Isso não exclui trabalho ainda não enviado por um colega; não foram enviadas mensagens a terceiros.
- `AGENTS.md`, instruções especializadas, overview, domínio, config e specs OpenSpec existentes foram consultados. Há change de dashboard ainda não arquivada; ela permanece intacta.
- Skills Reflex exigidas estão versionadas em `.agents/skills/`: `reflex-docs`, `setup-python-env`, `reflex-process-management`. Não foi necessário instalar skills nem editar Reflex durante esta fase.

## Xano e contratos existentes

Consulta autenticada exclusivamente de leitura pelo perfil `ProjetoFacu`, workspace `149184`, branch `v1`. Export de 40 documentos obtido sem flags de registros ou ambiente; nenhuma criação, execução de endpoint operacional, push, apply, migração ou publicação realizada. O export temporário não integra a proposta e não deve ser commitado integralmente.

- Tabelas publicadas: `user`, `customer`, `film`, `exemplar`, `event_log`.
- `customer`: identidade estável, situação `active|inactive` e bloqueio manual; sem saldo financeiro ou bloqueio por inadimplência implementado.
- `exemplar`: `id`, `identificador`, `filme_id`; identificador único; sem condição operacional, disponibilidade ou locação.
- `film`: catálogo com situação `active|inactive` e valor em centavos, sem controle real de disponibilidade por exemplar.
- APIs publicadas: autenticação/recuperação, clientes, catálogo, exemplares, logs e resumo administrativo; nenhum grupo/endpoint de locação no export publicado.
- `Quick Start/enforce_role` publicado consulta papel e estado atuais e preserva conta legada sem estado explícito. Essa política deve ser reutilizada antes de dados protegidos.
- Não foram inspecionados registros de clientes nem empréstimos fora do sistema. Não se pode concluir disponibilidade física a partir da ausência de tabela de locações.

## Divergências que exigem preservar recursos

O export publicado não é idêntico byte a byte à main. Parte das diferenças é formatação, organização de diretórios e metadados; não devem ser tratadas como autorização para sincronizar tudo.

- `exemplar` tem GUID local `7R9-qJX04Jtpd64Y87VGGbrI2-I` e remoto `8vzM3sxxeTHrTxaJGPUfK1JI8ZA`, apesar de campos e índices equivalentes. Uma atualização futura deve identificar e preservar a tabela publicada, evitando duplicação/recriação.
- `customer.bloqueio_manual_ativo` remoto é opcional sem default explícito; local declara default falso. A API publicada de criação atribui falso, mas registro legado nulo deve manter semântica compatível e não gerar bloqueio fictício.
- Export remoto organiza catálogo em `catalogo_de_filmes/` e rotas de detalhe em subdiretórios; local usa `catalogo_filmes/` e alguns nomes planos. Confirmar nomes de recursos e rotas, não inferir ausência pela diferença do caminho do arquivo.
- As APIs e funções possuem outras diferenças de serialização/metadados; a inspeção focada não equivale a auditoria semântica integral de todo o workspace. Nenhum desses arquivos foi substituído.

## Validação inicial da base

- `python -m unittest discover -v`: **127 testes aprovados** usando o ambiente existente do checkout original, com imports do código da cópia deste chat.
- Descoberta adicional em `ProjetoLocadora/tests`: a execução completa ficou sem encerrar e foi interrompida; não é reportada como aprovação.
- Reexecução dessa descoberta excluindo explicitamente os cinco métodos com `windows` no nome: **52 testes aprovados**, cinco não executados nessa reexecução. Total confirmado: **179 testes aprovados**.
- Não houve alteração de testes ou transporte para mascarar o problema. Os cinco métodos específicos são `test_windows_catalog_create_sends_invalid_test_payload_without_write`, `test_windows_catalog_list_uses_schannel_declared_route`, `test_windows_catalog_preserves_safe_server_request_id`, `test_windows_login_rejects_http_errors_without_logging_response_body` e `test_windows_login_uses_native_curl_and_stdin_for_credentials`, todos em `test_catalogo_client.TestCatalogClient`.
- Compilação Reflex não executada nesta fase de documentação. Testes da base não comprovam locação, migração, integridade concorrente ou rollback no Xano.

## Limite do fluxo

A skill `.github/skills/openspec-propose/SKILL.md` determina criar artefatos de planejamento e parar antes de implementação na mesma resposta. A solicitação atual condiciona a implementação à autorização do fluxo. A entrega desta fase é a change revisável; uma nova solicitação de APPLY autorizará implementação local, e alterações remotas continuam sujeitas à autorização específica do usuário.
