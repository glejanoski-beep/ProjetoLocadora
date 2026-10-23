# Spec Delta

## MODIFIED Requirements

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
