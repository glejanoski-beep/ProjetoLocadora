# Preparação da entrega — Dashboard

## Escopo e aprovações

Registro de 18/10/2026. O usuário informou a aprovação do grupo para a Dashboard, criação de API própria e integração pontual no Reflex. Proposta, contrato e design foram revisados; APPLY foi autorizado por blocos. A autorização atual abrange somente preparação local da entrega, sem commit ou push. A API foi criada e publicada pelo usuário no painel web Xano; esta preparação não criou nem modificou recursos remotos.

O autor da contribuição é responsável pela Dashboard. Os responsáveis nominais pela revisão dos pontos compartilhados ainda precisam ser registrados com o grupo (1.2 pendente). Limites: módulos próprios Dashboard; configuração adiciona somente URL do grupo; arquivo principal recebe integração de sessão, guardas, rotas e renderização; testes de autenticação usam acesso entre estados. Não há refatoração de regras de catálogo, clientes ou exemplares, migração ou alteração de tabelas. A modernização visual será outra Change.

## Recursos confirmados em leitura oficial

Consulta GET à Metadata API da instância, usando o perfil CLI existente sem divulgar sua credencial. Nenhum endpoint de negócio foi executado nesta preparação.

| Recurso | Evidência |
|---|---|
| Workspace | 149184 (caminho da Metadata API consultado) |
| Grupo | Dashboard, ID 437089, branch v1 |
| Canonical | S25tBasj |
| GUID do grupo | nJERFUPt8nD6YoYnbh2Fm1HX6Ms |
| Endpoint | GET dashboard/resumo-acervo, ID 4100746 |
| GUID do endpoint | K_Qigdnx_M9BElEl78V78232X_E |
| Autenticação | Metadado auth 886167; XanoScript publicado declara auth = "user" |
| Base do grupo | https://x8ki-letl-twmt.n7.xano.io/api:S25tBasj (informada pelo usuário e coerente com canonical confirmado) |

Fontes oficiais consultadas: `GET /api:meta/workspace/149184/apigroup/437089` e `GET /api:meta/workspace/149184/apigroup/437089/api/4100746?include_xanoscript=true&include_draft=false&branch=v1`. O script retornou status `ok`. O arquivo `xano/xano/api/dashboard/dashboard.xs` segue o padrão dos grupos locais, usando apenas canonical/GUID confirmados; IDs numéricos ficam neste registro, sem inventar diretivas XanoScript. O data source live é o informado pelo usuário; não foi reconfirmado por essas duas respostas de metadados.

## Consistência local/publicada

O script publicado confirma `api_group = "Dashboard"`, rota GET, input vazio e `Quick Start/enforce_role` com `$auth.id` e `required_role: "admin"` antes das duas queries. Conta film e exemplar independentemente com `return = {type: "count"}`, sem filtros, joins ou escritas de domínio. Preserva `to_int`, guarda de não negatividade, captura única de now após contagens e composição UTC terminada em Z. A resposta contém exatamente os três campos aprovados.

Diferenças de representação: o publicado expande os blocos var e omite `tags = []` e `error_type = "standard"` presentes localmente. O metadado de tags remoto é lista vazia. Não se afirma identidade textual nem equivalência runtime do erro padrão; a lógica local não foi alterada nesta preparação. O comentário obsoleto sobre inexistência do grupo foi corrigido.

`history` não aparece no XanoScript publicado nem nos campos retornados consultados. Não foi inventada configuração local `history = "inherit"`; confirmar no painel/metadados apropriados se necessário. Nenhuma alteração de history, preferência allow_push, data source ou permissão foi realizada. O GUID do endpoint foi registrado aqui, sem acrescentar uma diretiva não necessária ao arquivo existente.

A configuração usa `XANO_DASHBOARD_API_URL` com a base do grupo, sem acrescentar `/dashboard`; o adaptador adiciona `dashboard/resumo-acervo`. URL exige HTTPS e não aceita credenciais, query ou fragmento. `.env` permanece ignorado e não deve entrar no commit. Tokens não fazem parte da documentação ou dos metadados versionados.

## Evidências de funcionamento

**Informadas pelo usuário, em uso real:** admin consultou 5 filmes e 4 exemplares; Atualizar fez nova consulta e atualizou o horário. Carregamento e botão desabilitado foram observados. Horário visual convertido para `America/Sao_Paulo`. Isso comprova o caminho feliz observado, não a matriz completa de segurança ou exatidão em fixtures.

**Locais, com mocks/inspeção:** contrato estrito de resposta, zero válido, categorias de erro sanitizadas, Bearer/timeout/HTTPS, bloqueio de member inclusive por evento direto, revisão de sessão e descarte de respostas tardias, logout/trocas de conta/relogin, duas rotas, carregamento/sucesso/falhas e preservação da navegação. Testes de horário cobrem conversão UTC para São Paulo, mudança de dia/ano e horário de verão histórico, sem alterar o timestamp original.

A auditoria anterior verificou em memória independência dos totais frente a título/gênero/listas do catálogo e atualização simulada de 3/5 para 4/5. Não existe polling na implementação; a inspeção e a observação local sem eventos confirmaram ausência de novas consultas nesse intervalo. Essa evidência não equivale a contagem real no Xano. Testes estruturais leem tokens/blocos e usam mutações em memória; não interpretam ou executam XanoScript.

## Validação local desta preparação

- Suíte: `.venv/bin/python -B` com pytest em `tests`, `ProjetoLocadora/tests` e `.vscode/tests`, `-q -k 'not windows' -p no:cacheprovider --tb=short`, limite de 30 segundos, `.vscode` no sys.path e conexões socket bloqueadas por mocks: **168 testes e 252 subtestes aprovados; 5 testes excluídos**.
- `.venv/bin/reflex compile --dry`, limite de 60 segundos: aprovado, sem servidor ou publicação; skill `reflex-process-management` seguida.
- `openspec validate consultar-resumo-acervo-dashboard --strict`: aprovado nesta preparação.
- `git diff --check`: aprovado nesta preparação; também conferidos os novos arquivos desta etapa.

Cinco testes Windows apresentaram bloqueio de encerramento assíncrono na auditoria anterior. Não foram novamente executados nesta preparação nem considerados aprovados. A tarefa 6.2 permanece pendente apesar das regressões selecionadas e compilação aprovadas.

## Limitações e próximos passos autorizáveis

- 2.4: faltam fixtures runtime de 3 filmes (2 ativos/1 inativo), 5 exemplares, filme sem cópias, vínculo com inativo e base vazia. Não alterar dados compartilhados para produzir essas evidências sem autorização específica.
- 2.5: falta matriz runtime de autenticação/autorização (inclusive 401/403, contas legadas, desativadas, inexistentes e papel alterado/desconhecido), recusa antes das queries e auditoria. Mocks e inspeção não comprovam o HTTP real nem os efeitos da função de segurança.
- 6.3: faltam observações visuais de member, zero e logout, além de completar as duas entradas. Não confundir testes de componentes/estado com uso real no navegador.
- As duas contagens não possuem snapshot simultâneo; escritas concorrentes podem produzir totais de instantes diferentes. generated_at indica geração, não última alteração do acervo.
- `to_int` pode coagir resultados inesperados; a guarda não prova o tipo original do count. O cliente rejeita payloads inválidos, mas o comportamento do Xano exige runtime.
- A disponibilidade de tzdata para ZoneInfo é requisito do ambiente de execução.

Entrega funcional com limitações documentadas, sem arquivar a Change como integralmente validada. Antes de commit, revisar o diff e selecionar somente implementação/testes Dashboard, integrações mínimas, documentos da Change e metadados confirmados do grupo. Excluir `.env`, logs, arquivos gerados e dependências locais. Commit/push e qualquer nova operação remota aguardam autorização.

## Fechamento da revisão local

Diff revisado: alterações rastreadas limitadas à integração Dashboard no módulo principal, configuração dedicada e fixture de autenticação; novos arquivos da Dashboard e da Change permanecem sem commit. Nenhuma migração, alteração de schema ou funcionalidade de domínio foi adicionada. Nesta preparação foram alterados somente este registro, design/tasks, comentário do endpoint e metadados do grupo. A tarefa 6.4 foi concluída como revisão/documentação local, sem implicar conclusão de 2.4, 2.5, 6.2 ou 6.3, nem autorização de entrega remota.
