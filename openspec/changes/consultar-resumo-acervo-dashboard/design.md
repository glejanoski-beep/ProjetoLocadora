# Design

## Context

Motivação e escopo em [proposal.md](./proposal.md). Este design é necessário porque a mudança atravessa Xano, transporte Python, sessão e apresentação Reflex.

Evidências locais consultadas:
- `ProjetoLocadora/ProjetoLocadora.py`: `State` centraliza autenticação e estados de outros módulos; `_xano_auth_token` é privado; `require_session` usa `get_me_xano`; `_clear_session`, `_set_user`, login e logout controlam a identidade. `render_dashboard` é usado por `/` e `/backoffice` e mantém links para `/filmes`, `/clientes` e `/exemplares`. Os cartões de locações ativas, exemplares disponíveis e multas pendentes já indicam dados indisponíveis.
- `ProjetoLocadora/xano_client.py` e `config.py`: clientes HTTP e URLs por grupo; `get_me_xano` retorna `None` para diferentes falhas. A nova consulta precisa distinguir suas próprias categorias de erro sem alterar esse contrato compartilhado.
- `xano/xano/api/catalogo_filmes/filmes_GET.xs`: consulta filtrável por título/gênero para `member`; `api/exemplares/exemplares_GET.xs`: lista com associação ao filme, não agregação.
- `xano/xano/table/film.xs`: `status` active/inactive; `table/exemplar.xs`: identidade e vínculo com filme, sem contrato atual de disponibilidade.
- `function/quick_start/enforce_role.xs`: consulta conta atual, recusa inatividade e papel inválido e audita recusas. `acesso-seguro` preserva estado legado ausente como ativo.
- `openspec/changes/gerenciar-clientes/` permanece presente, com tarefas concluídas; seu trabalho já ocupa o módulo principal e não deve ser refeito. Changes arquivadas de login, permissões, catálogo e exemplares fundamentam os contratos consolidados.

Esta análise usa a exportação e o código locais, sem verificar nem modificar recursos remotos. Divergências do branch `v1` devem ser conferidas no APPLY antes de qualquer escrita.

## Goals / Non-Goals

**Goals:** manter fluxo unidirecional Xano → adaptador Python → estado Reflex exclusivo → cartões; autorização em cada consulta; sessão única; isolamento de erros e dados; contrato mínimo verificável.

**Non-Goals:** extrair ou refatorar o `State` inteiro, reorganizar transportes existentes, alterar permissões gerais, implementar módulos de colegas, migrar schemas ou produzir snapshot transacional entre tabelas.

## Decisions

### 1. Grupo e endpoint de agregação próprios

Propor grupo `Dashboard`, rota `GET dashboard/resumo-acervo` relativa à base do novo grupo, sem filtros nem paginação. Usar `auth = "user"` e executar `Quick Start/enforce_role` com `$auth.id` e `required_role: "admin"` antes de qualquer acesso a `film` ou `exemplar`. Identidade e papel não são parâmetros do cliente. A rotina existente preserva auditoria mínima de recusas; a consulta não grava dados de negócio e não exige novo log de sucesso.

Executar contagem agregada de todos os registros de cada tabela, sem join, filtro de status ou carregamento de listas para o Python. Cada contagem é exata para sua leitura; sob escritas concorrentes, não há promessa de snapshot atômico das duas tabelas. `generated_at` representa conclusão da geração do resumo, não horário de última alteração do acervo. Não modificar tabelas, índices nem APIs atuais.

Alternativas: contar listas no frontend seria dependente de filtros/paginação e trafegaria dados desnecessários; somar estoque ou inferir disponibilidade alteraria o significado; tabela materializada exigiria sincronização e persistência fora de escopo.

### 2. Contrato mínimo e validação integral

Resposta HTTP 200 com objeto contendo somente:

| Campo | Contrato |
|---|---|
| `total_filmes` | Inteiro JSON >= 0; todos os registros de film, inclusive inativos |
| `total_exemplares` | Inteiro JSON >= 0; todos os registros de exemplar |
| `generated_at` | String RFC 3339 UTC com sufixo Z, gerada pelo backend |

Exemplo documental: `{"total_filmes": 3, "total_exemplares": 5, "generated_at": "2026-10-18T15:00:00Z"}`. Zero é sucesso real. O adaptador valida o objeto integral, campos, tipos, sinal e timestamp parseável; rejeita campos extras, ausências, null, booleanos (inclusive a equivalência bool/int do Python), floats e strings numéricas. Não aceita sucesso parcial.

Sem autenticação válida: HTTP 401; autorização negada: HTTP 403 conforme o mapeamento Xano existente, a conferir no runtime antes de concluir o APPLY. Ambos limpam dados; 401 segue encerramento/redirecionamento já existente, 403 exibe ausência de permissão sem bloquear a navegação autorizada. Timeout/conexão e 5xx são falhas recuperáveis; JSON ou schema inválido é resposta inválida. Não exibir corpo remoto, tokens ou exceções brutas.

Alternativa de retornar listas ou dados de usuário foi descartada por minimização; converter erros em zero ocultaria falhas.

### 3. Adaptador e estado isolados

Propor `ProjetoLocadora/dashboard_client.py` para transporte, validação e erros específicos; `dashboard_state.py` para `DashboardState(rx.State)`; `dashboard.py` para componentes. O adaptador recebe o token somente de código servidor, usa Bearer e timeout finito (10 s, alinhado ao padrão atual), não persiste payloads ou credenciais e não altera os clientes existentes. Propor `XANO_DASHBOARD_API_URL` própria, sem trocar URLs atuais ou embutir `canonical` inventado.

O estado Dashboard acessa o `State` existente por mecanismos nativos de comunicação entre estados Reflex, com importação localizada quando necessária para evitar ciclo. Não criar autenticação duplicada, nova cópia persistente de token ou estado global compartilhado. Expor ao navegador somente apresentação, totais validados, timestamp e mensagens sanitizadas. Referência oficial consultada: [State Overview](https://reflex.dev/docs/state/overview/); detalhes de integração devem seguir a versão instalada e a skill reflex-docs no APPLY.

Alternativas: acrescentar tudo ao `State` monolítico ampliaria conflitos; herdar todos os estados de catálogo/clientes para a Dashboard acoplaria módulos sem necessidade.

### 4. Carregamento e apresentação

Um evento próprio de entrada deve primeiro concluir a validação atual de sessão e seus redirecionamentos, e só então carregar o resumo para admin. Integrar esse fluxo nas duas rotas que renderizam a Dashboard. Não mudar `require_session` para exigir admin. Para member, limpar o estado Dashboard, mostrar mensagem de acesso restrito na seção de indicadores e não chamar a agregação, mesmo se um evento manual for disparado diretamente.

Estados: inicial (sem valores), carregando, sucesso, erro de rede/serviço, resposta inválida, sem permissão. Ao iniciar atualização, limpar valores e timestamp anteriores; durante carregamento, mostrar indicador visual e desabilitar Atualizar. No sucesso, mostrar os dois cartões “Total de filmes cadastrados” e “Total de exemplares cadastrados” e horário de geração; zero é exibido como 0. Em erro, não mostrar números antigos ou zero de fallback; oferecer Atualizar para falhas recuperáveis. Não há polling, retry periódico ou atualização ao alterar filtros de outro módulo.

Manter cabeçalho, sessão, Sair e links existentes. Os indicadores futuros mantêm “— / Dados indisponíveis”; total de exemplares nunca preenche “Exemplares disponíveis”. Falha do resumo não esconde links. Alternativa de manter valor antigo durante falha foi descartada para tornar inequívoca a validade da primeira entrega.

### 5. Limpeza de sessão e respostas tardias

Adicionar somente pontos mínimos de integração para invalidar a Dashboard no logout, limpeza da sessão e mudança de identidade/papel. Limpar totais, timestamp, mensagens anteriores e loading; na perda de permissão, permitir apenas a mensagem correspondente. A sessão continua fonte de verdade.

Manter revisão privada de sessão e identificador de requisição. Antes de aceitar qualquer resposta, comparar identidade, revisão de sessão e requisição atual; respostas de consultas iniciadas antes de logout, nova conta ou nova requisição são descartadas. O controle não pode depender somente do papel, pois dois administradores também podem alternar contas. Atualizar manualmente revalida a sessão antes da agregação. Mesmo que a interface ainda tenha papel antigo, o Xano verifica a conta atual.

Alternativa de limpar apenas a interface no logout permite que uma resposta tardia repovoe os dados. Não há promessa de revogação instantânea por notificação externa: mudanças remotas serão detectadas na próxima validação/consulta, sem polling.

## Risks / Trade-offs

- [Conflitos no módulo principal e sessão] → coordenar imports, eventos das rotas, `_clear_session`, `_set_user` e logout com responsáveis por login/clientes/catálogo/exemplares; diff mínimo, sem refatoração transversal.
- [Configuração compartilhada] → acrescentar somente a URL do novo grupo e sua documentação no APPLY; manter contratos e testes existentes. Arquivos de ambiente não devem receber segredos versionados.
- [Exportação pode divergir de v1] → conferir somente recursos necessários e sua sintaxe de contagem no APPLY; não inventar IDs nem sobrescrever trabalho remoto do grupo.
- [Contagens em momentos próximos, sem snapshot comum] → documentar horário de geração e testar exatidão em base estável; reavaliar snapshot apenas em mudança futura se necessário.
- [Volume futuro] → agregação no banco, sem listas/N+1; sem índices ou cache novos nesta entrega.
- [Revogação remota com cartão já aberto] → limpar na próxima entrada/Atualizar/validação, em qualquer 401/403 e em transição local; sem ampliar para notificações ou polling.
- [Verificação runtime pode exigir fixtures remotas] → priorizar testes locais mockados/estruturais; planejar dados controlados com o grupo e autorização específica antes de criar ou alterar dados. Nenhuma preparação remota faz parte deste PROPOSE.

## Migration Plan

Somente planejamento nesta fase. Após revisão e autorização explícita de APPLY: confirmar o contrato e recursos atuais de `v1`, implementar/validar endpoint e adaptador, integrar estado/cartões e limpeza, executar verificações proporcionais e apresentar resultados. Qualquer publicação deve respeitar o escopo autorizado no APPLY; a regra do projeto exige usar `v1`, sem branch Xano isolado. Nenhuma migração de tabelas ou dados.

Se for necessário rollback após entrega autorizada, retirar a integração dos indicadores e desabilitar somente a nova consulta, preservando login, navegação e recursos dos colegas; não apagar tabelas ou registros.

## Open Questions

- O `canonical` e a base efetiva do novo grupo serão conhecidos no APPLY; não alteram o contrato relativo proposto.
- Horário pode ser apresentado em formato local com indicação de fuso, mantendo o valor UTC original validado; a formatação visual pode ser definida na revisão.

Antes de APPLY, aprovar o contrato/rota propostos, os módulos dedicados e pontos mínimos de sessão, a política de ocultar valores durante atualização/erro, o tratamento das duas rotas e a limitação de consistência temporal. As decisões de escopo e papéis informadas pelo usuário já estão aprovadas.

## Registro da entrega

O planejamento acima é preservado como histórico das decisões aprovadas. O APPLY foi autorizado por blocos e a API foi criada pelo usuário no painel web. Canonical/base efetivos, evidências locais e reais, apresentação em America/Sao_Paulo, divergências da representação remota e pendências estão em [delivery.md](./delivery.md). Nenhuma promessa de snapshot comum ou validação runtime completa foi acrescentada.
