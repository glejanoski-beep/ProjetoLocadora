# Interface Dashboard Specification

## Purpose

Definir a apresentação, a navegação, a responsividade e os estados do dashboard do backoffice da CINEBYTE LOCADORA, em coerência visual com a tela de login, sem alterar autenticação, consultas ao Xano, permissões ou regras de negócio existentes.

## Requirements

### Requirement: Dashboard reproduz a vitrine escura da CINEBYTE LOCADORA

As rotas `/` e `/backoffice` SHALL exibir, para uma sessão válida, fundo quase preto (`#07070A`) com superfícies translúcidas em tom de carvão, bordas brancas de baixa opacidade e cantos arredondados. A composição SHALL apresentar, nesta ordem: barra superior arredondada, título “Visão geral” com subtítulo contextual, quatro cards de indicadores e dois painéis de gráficos. O vermelho `#DC2638` SHALL ser a cor de destaque (marca), os textos principais SHALL ser claros e as informações secundárias cinza. Títulos e textos SHALL usar “Inter” e detalhes técnicos (e-mail, horário da consulta, etiqueta “Em breve”) SHALL usar “Space Mono”. O botão de alternância de modo de cor SHALL NOT aparecer no dashboard; as configurações globais e as demais telas SHALL permanecer inalteradas.

#### Scenario: Composição completa em desktop

- **WHEN** uma pessoa autenticada abre `/backoffice` em uma janela de desktop
- **THEN** barra superior, cabeçalho, quatro cards em uma linha e os dois painéis aparecem na ordem definida
- **AND** o subtítulo é “Painel administrativo · Locadora” para administradores e “Painel do funcionário · Locadora” para os demais perfis

### Requirement: Barra superior identifica a marca, o usuário e a navegação

A barra SHALL exibir a marca “CINEBYTE LOCADORA” com o logotipo do login, a navegação horizontal e o usuário autenticado com nome real, perfil traduzido (`admin` → “Administrador”, demais → “Funcionário”) e iniciais calculadas a partir do primeiro e do último nome reais. Sem nome, SHALL ser exibido “Funcionário” e um ícone neutro. A ação “Sair” SHALL continuar encerrando a sessão e redirecionando para `/login`. A navegação SHALL conter links funcionais para “Visão geral” (`/backoffice`), “Acervo” (`/filmes`), “Exemplares” (`/exemplares`) e “Clientes” (`/clientes`) e “Locações” (`/locacoes/nova`), com a página atual indicada por `aria-current`. “Multas” e “Relatórios” SHALL aparecer desabilitados (`aria-disabled`), com a indicação “Em breve”, sem link ou destino.

#### Scenario: Item sem página implementada

- **WHEN** a pessoa tenta ativar “Multas” ou “Relatórios”
- **THEN** nenhuma navegação ocorre e a indicação “Em breve” permanece visível

### Requirement: Indicadores usam apenas dados reais ou estados vazios explícitos

Os cards “Filmes cadastrados” e “Exemplares cadastrados” SHALL exibir exclusivamente os totais do `DashboardState`, preservando os estados de carregamento, sucesso (inclusive zero), proibido, sessão inválida, resposta inválida, indisponível e erro, com as mesmas mensagens e papéis acessíveis. O resumo SHALL ser exibido somente a administradores; os demais perfis SHALL ver a mensagem de restrição. “Atualizar” e o horário da consulta (“Gerado em … (horário de Brasília)”) SHALL aparecer somente a administradores, e “Atualizar” SHALL permanecer desabilitado durante carregamento e nos estados proibido e sessão inválida; ao ser acionado, SHALL recarregar o resumo e, em evento separado, as locações. “Locações ativas” SHALL exibir, para `member` e `admin`, o total de locações com situação ativa obtido de `GET /locacoes`, com a quantidade de vencimento ultrapassado; durante o carregamento SHALL exibir “…”, e sem resposta válida SHALL exibir “—” sem valor inventado. A leitura SHALL se limitar a 3 páginas de 50 locações; havendo mais, o texto SHALL informar que a contagem é das locações mais recentes. “Multas pendentes” SHALL exibir “—” e “Sem dados ainda” enquanto não existir fonte de dados.

#### Scenario: Ausência de dados inventados

- **WHEN** o dashboard é exibido
- **THEN** nenhum número, nome, data ou estatística de exemplo aparece como se fosse real

#### Scenario: Locações ativas reais

- **WHEN** um funcionário autenticado abre o dashboard e a listagem de locações responde
- **THEN** o card mostra o total de locações ativas e quantas estão com vencimento ultrapassado

#### Scenario: Falha da listagem

- **WHEN** a listagem falha, retorna 404, 429 ou resposta inválida
- **THEN** o card mostra “—” com “Indisponível no momento” e o resumo do acervo não é afetado

### Requirement: Acervo por gênero usa o catálogo real; locações permanecem vazias

O painel “Acervo por gênero” SHALL exibir, somente a administradores, a distribuição dos filmes cadastrados (ativos e inativos) por gênero, calculada a partir da lista de filmes retornada pelo endpoint existente do catálogo, sem alterar o contrato da API. Os gêneros SHALL ser agrupados sem diferenciar maiúsculas, minúsculas e espaços repetidos, mantendo a grafia do primeiro filme; SHALL ser ordenados do maior para o menor; SHALL exibir no máximo seis gêneros, com o excedente agrupado em “Outros”; e cada barra SHALL ser proporcional ao maior total exibido, com a contagem “N filme(s)”. Ao passar o cursor ou focar a linha pelo teclado, o gênero SHALL ser destacado e SHALL revelar a participação percentual no acervo exibido. Durante o carregamento o painel SHALL indicar o estado de carregamento; sem filmes SHALL exibir “Nenhum filme cadastrado.”; e, se a consulta ao catálogo falhar, SHALL exibir uma mensagem de erro com papel `alert` sem invalidar os totais do resumo. Para usuários não administradores o painel SHALL informar que a distribuição está disponível apenas a administradores e SHALL NOT consultar o catálogo. O painel SHALL oferecer o link “Ver acervo” para `/filmes`. A distribuição SHALL ser descartada nas mesmas transições de sessão e de erro que invalidam o resumo.

“Movimentação de locações” SHALL exibir, para `member` e `admin`, barras por dia dos últimos 14 dias no horário de Brasília, com retiradas (data de retirada) e devoluções (data de devolução) das locações obtidas de `GET /locacoes`, alturas proporcionais ao maior valor diário, legenda, total do período e link “Ver locações”. Ao passar o cursor ou focar uma coluna pelo teclado, a coluna SHALL ser destacada e SHALL exibir data, dia da semana, retiradas e devoluções; cada coluna SHALL ter rótulo acessível equivalente. As animações de entrada e de destaque SHALL respeitar `prefers-reduced-motion`. Sem movimento no período, o painel SHALL informar “Nenhuma retirada ou devolução nos últimos 14 dias.”; antes da resposta SHALL manter a área vazia, sem barras; e, em falha, SHALL exibir a mensagem com papel `alert` e “Tentar novamente”. Os dados de locações SHALL ser descartados nas transições de sessão que invalidam o dashboard.

#### Scenario: Distribuição real

- **WHEN** um administrador carrega o dashboard e o catálogo é consultado com sucesso
- **THEN** cada gênero aparece com sua contagem real e uma barra proporcional
- **AND** nenhum gênero, número ou percentual de exemplo é exibido

#### Scenario: Detalhe ao passar o cursor

- **WHEN** o usuário passa o cursor ou foca uma coluna da movimentação
- **THEN** a coluna é destacada e mostra data, dia da semana, retiradas e devoluções reais do dia

#### Scenario: Movimentação real

- **WHEN** a listagem de locações responde
- **THEN** cada dia dos últimos 14 mostra suas retiradas e devoluções reais, inclusive zero

### Requirement: Layout responsivo preserva a composição

Em larguras de até 1100 px os cards SHALL ocupar duas colunas, os painéis SHALL empilhar e a navegação SHALL passar para uma segunda linha com rolagem horizontal própria. Em até 640 px os cards SHALL ocupar uma coluna, o nome do usuário e a tag “LOCADORA” SHALL ser ocultados e a página SHALL NOT produzir rolagem horizontal. Todos os controles SHALL ter indicação de foco visível.

#### Scenario: Celular estreito

- **WHEN** o dashboard é exibido em uma viewport de aproximadamente 390 px
- **THEN** a página não excede a largura da viewport
- **AND** marca, navegação, ações e cards permanecem acessíveis

### Requirement: Dashboard exibe clientes reais

O dashboard SHALL exibir, para `member` e `admin`, o card “Clientes cadastrados” com o total retornado por `GET /clientes`, a quantidade de ativos e a de clientes com bloqueio manual; durante o carregamento SHALL exibir “…”, e sem resposta válida SHALL exibir “—” sem valor inventado. A leitura SHALL se limitar a 2 páginas de 50 clientes; havendo mais, o texto SHALL informar que a situação é a dos primeiros por nome. O painel “Clientes” SHALL listar até 6 clientes em ordem alfabética, com CPF somente mascarado, situação cadastral e selo de bloqueio manual, e cada linha SHALL abrir `/clientes/{id}`. O painel “Situação dos clientes” SHALL exibir ativos e inativos em gráfico de rosca com o percentual de ativos, legenda com as contagens e rótulo acessível, e SHALL exibir à parte a quantidade com bloqueio manual. Em falha, os painéis SHALL exibir a mensagem com papel `alert` e “Tentar novamente”, e o card SHALL exibir “Indisponível no momento”. Os dados de clientes SHALL ser descartados nas transições de sessão que invalidam o dashboard; token recusado SHALL encerrar a sessão e redirecionar ao login.

#### Scenario: Clientes reais

- **WHEN** um funcionário autenticado abre o dashboard e a listagem de clientes responde
- **THEN** o card, a lista e a rosca mostram somente contagens e clientes reais

#### Scenario: Falha da listagem de clientes

- **WHEN** a listagem de clientes falha ou atinge o limite do plano
- **THEN** o card mostra “—” e os painéis mostram a mensagem de erro, sem afetar resumo e locações

### Requirement: Dashboard destaca locações vencidas e clientes que mais alugam

A partir das locações já lidas para a movimentação, o painel “Locações vencidas” SHALL listar até 5 locações ativas com vencimento ultrapassado, das mais atrasadas primeiro, com cliente, filme e dias de atraso, e cada linha SHALL abrir `/locacoes/{id}`; sem vencidas SHALL informar que não há locação vencida. O painel “Clientes que mais alugam” SHALL exibir até 5 clientes com mais locações (ativas e devolvidas), com barras proporcionais ao maior total e link para o cadastro; quando a leitura for parcial, o subtítulo SHALL informar que considera as locações mais recentes. Ambos SHALL seguir os estados de carregamento e erro das locações e SHALL NOT fazer consultas adicionais.

#### Scenario: Vencidas em ordem de atraso

- **WHEN** há locações ativas com vencimento ultrapassado
- **THEN** elas aparecem da mais atrasada para a menos, com os dias reais de atraso

### Requirement: Movimentação com período selecionável

O painel "Movimentação de locações" SHALL oferecer os períodos "7 dias", "14 dias" e "1 mês" (30 dias), iniciando em 14 dias, com o período atual indicado por `aria-pressed`. A troca SHALL recalcular as colunas, o total e os textos do período a partir das locações já carregadas, SHALL NOT fazer nova consulta ao Xano e SHALL NOT alterar os contadores de locações ativas e vencidas. Cada período SHALL exibir uma coluna por dia de Brasília terminando hoje; em 1 mês, o eixo SHALL rotular um dia a cada cinco, incluindo hoje. Valores fora das opções SHALL ser ignorados.

#### Scenario: Troca para 1 mês

- **WHEN** o funcionário seleciona "1 mês"
- **THEN** o gráfico mostra 30 colunas com retiradas e devoluções reais e o total "… em 1 mês", sem nova requisição
