# Tasks

APPLY autorizado por blocos e implementação funcional revisada. A preparação local da entrega foi autorizada, sem commit, push ou nova escrita remota. Evidências, aprovações e limitações estão em [delivery.md](./delivery.md). As marcações distinguem implementação verificada de cenários ainda pendentes.

## 1. Preparação da integração aprovada

- [x] 1.1 Registrar a aprovação da proposta, contrato e design e a autorização explícita de APPLY; verificar o registro antes de editar implementação ou operar recursos remotos.
- [ ] 1.2 Coordenar com o grupo os pontos compartilhados (`ProjetoLocadora.py`, configuração, sessão e testes de autenticação), registrando responsáveis e limites do diff; verificar que clientes, catálogo e exemplares não serão refatorados.
- [ ] 1.3 Conferir os recursos necessários de `v1`, o padrão de contagem agregada Xano e o mapeamento de autenticação/negação para 401/403; registrar divergências da exportação local e não sobrescrever recursos alheios.

## 2. API de leitura Xano

- [x] 2.1 Definir o novo grupo Dashboard e `GET dashboard/resumo-acervo` com `auth = "user"` e `Quick Start/enforce_role` admin antes das contagens; verificar ordem no contrato XanoScript e ausência de parâmetros de identidade/papel.
- [x] 2.2 Implementar contagens agregadas independentes de film e exemplar e `generated_at` UTC, sem filtros ou listas; verificar os três campos, ausência de PII e ausência de alteração em tabelas ou endpoints existentes.
- [x] 2.3 Preparar verificações estruturais locais de autorização antes das queries e de agregação sem filtros/join; conferir que a suíte falha se houver contagem anterior à autorização ou exclusão de filmes inativos. Revisão aprovada; testes estruturais locais não comprovam execução no Xano.
- [ ] 2.4 Validar em runtime autorizado contagens de 3 filmes (2 ativos e 1 inativo), 5 exemplares incluindo vínculo com filme inativo, filme sem cópias e base vazia; comparar totais com a base controlada e registrar evidência. Não criar, alterar ou limpar dados compartilhados sem autorização específica; se não houver fixture segura, registrar a lacuna de runtime sem alegar execução.
- [ ] 2.5 Verificar acesso direto como admin ativo e legado, member, anônimo, token inválido/expirado, conta inexistente/desativada e papel alterado/desconhecido; confirmar recusa antes das queries e auditoria mínima sem segredos por inspeção/testes locais, complementando runtime somente no escopo autorizado.

## 3. Adaptador Python dedicado

- [x] 3.1 Adicionar somente a resolução de `XANO_DASHBOARD_API_URL` e o adaptador `dashboard_client.py`, preservando URLs/clientes existentes; testar rota relativa, Bearer servidor, timeout e ausência de token em mensagens/logs.
- [x] 3.2 Definir tipos e validação integral do contrato; testar totais exatos e zero, negativos, booleanos, floats, strings, null, campos ausentes/extras, listas, JSON malformado e horário inválido/sem UTC.
- [x] 3.3 Mapear erros de rede/timeout, serviço 5xx, 401, 403 e resposta inválida para categorias específicas da Dashboard; verificar com respostas mockadas que não há zero de fallback, sucesso parcial ou exposição de corpo remoto.

## 4. Estado e ciclo de sessão Reflex

- [x] 4.1 Criar `DashboardState` em módulo próprio, obtendo sessão do estado existente sem duplicar tokens e mantendo os módulos atuais isolados; verificar com testes locais estado por sessão, ausência de token público e importação sem ciclos.
- [x] 4.2 Implementar entrada e Atualizar com revalidação de sessão, bloqueio local de member e estados inicial/carregando/sucesso/falha/sem permissão; testar transições, limpeza de valores ao iniciar e ausência de chamadas para member inclusive por evento direto.
- [x] 4.3 Integrar limpeza e revisão privada de sessão nos pontos mínimos de logout, `_clear_session` e troca de identidade/papel; testar admin→member, admin→admin, perda de sessão e rejeição de respostas tardias ou superadas.
- [x] 4.4 Encadear validação existente e carregamento da Dashboard em `/` e `/backoffice` sem tornar a guarda geral exclusiva de admin; verificar redirecionamento de anônimo e acesso mantido de member nas duas entradas.

## 5. Cartões e navegação

- [x] 5.1 Criar componentes dedicados com os dois rótulos de quantidade cadastrada, horário de geração e Atualizar; verificar carregamento perceptível, controle indisponível durante consulta e exibição de 0 como sucesso.
- [x] 5.2 Apresentar falhas de rede/serviço, resposta inválida e ausência de permissão sem números antigos ou presumidos; verificar tentativa manual recuperável e o fluxo existente de login em 401.
- [x] 5.3 Preservar cabeçalho, sessão, Sair e links de filmes/clientes/exemplares, mantendo indicadores futuros como indisponíveis; verificar que total de exemplares não preenche disponibilidade nem valores financeiros e que member continua navegando.

## 6. Verificação integrada e entrega

- [x] 6.1 Executar testes locais de independência dos totais frente aos filtros de título/gênero/listas e de atualização após mudança de cadastro simulada; verificar que nenhum filtro dispara consulta de resumo e não existe polling.
- [ ] 6.2 Executar regressões relevantes de autenticação, catálogo, clientes e exemplares e compilar o Reflex seguindo reflex-process-management; registrar comandos e resultados, sem executar deploy como efeito da compilação.
- [ ] 6.3 Verificar visualmente as duas entradas como admin/member, zero, falhas e logout, usando backend simulado quando necessário; registrar evidências e distinguir testes mockados, estruturais e runtime realmente executados.
- [x] 6.4 Revisar diff final e documentação de integração/URL no escopo do APPLY, conferir ausência de migrações, alterações de tabelas e mudanças alheias; registrar riscos remanescentes e resultado da validação OpenSpec antes de qualquer entrega remota autorizada.

## Pendências e alcance das evidências

- 1.2: autorização do grupo para integração pontual comunicada pelo usuário; nomes e responsáveis pela revisão de cada módulo compartilhado ainda não registrados.
- 1.3: schemas e função foram comparados na preparação anterior; contrato publicado conferido em metadados. Mapeamento efetivo 401/403 e configuração de history continuam sem confirmação integral.
- 2.4 e 2.5: permanecem pendentes; sucesso real admin com 5 filmes/4 exemplares não substitui fixtures controladas nem a matriz de segurança runtime.
- 6.2: regressões locais e compilação aprovadas, mas cinco testes Windows não encerraram na auditoria anterior; tarefa não considerada plenamente concluída.
- 6.3: faltam verificações visuais de member, zero e logout, além da cobertura visual das duas entradas.
