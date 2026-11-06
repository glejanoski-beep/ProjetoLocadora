# Spec Delta

## Purpose

Ativar "Multas" na navegação e alimentar o card "Multas pendentes" com o resumo real.

## MODIFIED Requirements

### Requirement: Barra superior identifica a marca, o usuário e a navegação

A barra SHALL exibir a marca "CINEBYTE LOCADORA" com o logotipo do login, a navegação horizontal e o usuário autenticado com nome real, perfil traduzido (`admin` → "Administrador", demais → "Funcionário") e iniciais calculadas a partir do primeiro e do último nome reais. Sem nome, SHALL ser exibido "Funcionário" e um ícone neutro. A ação "Sair" SHALL continuar encerrando a sessão e redirecionando para `/login`. A navegação SHALL conter links funcionais para:
- "Visão geral" (`/backoffice`);
- "Acervo" (`/filmes`);
- "Exemplares" (`/exemplares`);
- "Clientes" (`/clientes`);
- "Locações" (`/locacoes/nova`);
- "Multas" (`/multas`).

A página atual SHALL ser indicada por `aria-current`. "Relatórios" SHALL aparecer desabilitado (`aria-disabled`), com a indicação "Em breve", sem link ou destino.

#### Scenario: Item sem página implementada
- **WHEN** a pessoa tenta ativar "Relatórios"
- **THEN** nenhuma navegação ocorre e a indicação "Em breve" permanece visível

#### Scenario: Acesso às multas
- **WHEN** a pessoa ativa "Multas"
- **THEN** a navegação abre `/multas`, e o item fica indicado como página atual

### Requirement: Indicadores usam apenas dados reais ou estados vazios explícitos

Os cards "Filmes cadastrados" e "Exemplares cadastrados" SHALL exibir exclusivamente os totais do `DashboardState`, preservando os estados de carregamento, sucesso (inclusive zero), proibido, sessão inválida, resposta inválida, indisponível e erro, com as mesmas mensagens e papéis acessíveis. O resumo SHALL ser exibido somente a administradores; os demais perfis SHALL ver a mensagem de restrição.

"Atualizar" e o horário da consulta ("Gerado em … (horário de Brasília)") SHALL aparecer somente a administradores. "Atualizar" SHALL permanecer desabilitado durante o carregamento e nos estados proibido e sessão inválida; ao ser acionado, SHALL recarregar o resumo e, em eventos separados, as locações e o resumo de multas.

"Locações ativas" SHALL exibir, para `member` e `admin`, o total de locações com situação ativa obtido de `GET /locacoes`, com a quantidade de vencimento ultrapassado. Durante o carregamento SHALL exibir "…", e sem resposta válida SHALL exibir "—" sem valor inventado. A leitura SHALL se limitar a 3 páginas de 50 locações; havendo mais, o texto SHALL informar que a contagem é das locações mais recentes.

"Multas pendentes" SHALL exibir, para `member` e `admin`, o saldo total em aberto obtido de `GET /multas/resumo`, formatado em reais, com a nota "N multa(s) em aberto". Durante o carregamento SHALL exibir "…", e sem resposta válida SHALL exibir "—" com "Indisponível no momento", sem afetar os demais cards.

#### Scenario: Ausência de dados inventados
- **WHEN** o dashboard é exibido
- **THEN** nenhum número, nome, data ou estatística de exemplo aparece como se fosse real

#### Scenario: Locações ativas reais
- **WHEN** um funcionário autenticado abre o dashboard e a listagem de locações responde
- **THEN** o card mostra o total de locações ativas e quantas estão com vencimento ultrapassado

#### Scenario: Falha da listagem
- **WHEN** a listagem falha, retorna 404, 429 ou resposta inválida
- **THEN** o card mostra "—" com "Indisponível no momento" e o resumo do acervo não é afetado

#### Scenario: Multas pendentes reais
- **WHEN** o resumo informa duas multas em aberto com saldo de 900 centavos
- **THEN** o card mostra "R$ 9,00" e "2 multas em aberto"

#### Scenario: Nenhuma multa pendente
- **WHEN** o resumo informa zero multas em aberto
- **THEN** o card mostra "R$ 0,00" e "Nenhuma multa em aberto"
