# Spec Delta

## ADDED Requirements

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
