# Interface Clientes Specification

## Purpose

Definir a apresentação, a busca, a paginação, os formulários e o detalhe das telas de Clientes da CINEBYTE LOCADORA, em coerência visual com o login, o dashboard, o Acervo e os Exemplares, sem alterar o contrato de `clientes`, a autenticação, as permissões ou o backend.

## Requirements

### Requirement: Lista de clientes apresenta somente o resumo minimizado

A rota `/clientes` SHALL exibir, para uma sessão válida, a barra superior compartilhada com “Clientes” como página atual, a etiqueta “CADASTRO”, o título “Clientes”, a barra de busca e uma tabela com as colunas Cliente (avatar com iniciais do nome real e nome), CPF mascarado, Situação, Bloqueio manual e a ação “Consultar”, que leva a `/clientes/{id}`. A listagem SHALL NOT exibir e-mail, telefone, CPF completo ou qualquer dado pessoal além do resumo retornado pelo servidor. A situação SHALL ser apresentada como “Ativo” ou “Inativo” a partir de `active` ou `inactive`, e o bloqueio manual SHALL ser apresentado como condição independente (“Bloqueado” ou “Sem bloqueio”). O resumo da lista SHALL indicar somente o total real retornado pelo servidor (“N clientes”) e SHALL NOT calcular totais de ativos ou bloqueados a partir da página atual. A tela SHALL NOT oferecer exclusão de clientes nem exibir dados ou métricas de exemplo.

#### Scenario: Lista com clientes

- **WHEN** a consulta é concluída com clientes
- **THEN** cada cliente aparece em uma linha com os campos do resumo
- **AND** em telas estreitas as linhas passam a cartões empilhados com o rótulo de cada campo

### Requirement: Busca e paginação preservam o comportamento do servidor

A busca por nome e por CPF completo SHALL atualizar o estado a cada alteração e consultar o servidor somente pela ação “Buscar”, que retorna à página 1. A paginação SHALL continuar no servidor, com “Anterior”, “Próxima” e o indicador “Página X · N cliente(s)”, desabilitando as ações quando não houver página correspondente.

### Requirement: Estados de carregamento, erro, sucesso e vazio são preservados

A tela SHALL exibir o carregamento com papel `status`, o erro de consulta com papel `alert`, a mensagem de sucesso com papel `status` e “Nenhum cliente encontrado.” quando a consulta não retorna clientes. Durante erro ou carregamento, a tabela SHALL NOT ser exibida.

### Requirement: Cadastro e edição mantêm rotas, validações e a distinção entre situação e bloqueio

As rotas `/clientes/novo` e `/clientes/{id}/editar` SHALL permanecer páginas, com o visual de painel de vidro e a barra superior de Clientes, sem modal. SHALL manter os campos Nome completo, CPF, E-mail e Telefone, os limites de 200 e 254 caracteres, o aviso “Informe ao menos um contato: e-mail ou telefone.”, os handlers `capture_customer_*` e `submit_customer`, a normalização e a validação existentes (CPF sem pontuação, e-mail em minúsculas, telefone de 10 ou 11 dígitos), a exibição do erro com papel `alert` e o redirecionamento a `/clientes` após salvar. A unicidade de CPF e de e-mail SHALL continuar garantida pelo backend, com a mensagem retornada exibida. A situação cadastral (`active` ou `inactive`) SHALL ser alterável somente na edição, por botões segmentados rotulados “Ativo” e “Inativo”, e a inativação SHALL substituir qualquer exclusão. Cancelar e fechar SHALL voltar à lista sem salvar. Somente administradores SHALL acessar estas rotas, conforme os handlers existentes.

### Requirement: Detalhe apresenta dados protegidos e controla o bloqueio manual

A rota `/clientes/{id}` SHALL exibir o nome com avatar e selos de situação cadastral e de bloqueio manual, “Dados do cliente” (CPF, e-mail, telefone, situação e bloqueio manual, com “Não informado” para contatos ausentes) e, para administradores, “Editar cadastro” e “Controle de bloqueio manual”. O controle SHALL manter `toggle_customer_manual_block` e `capture_customer_block_reason`, exigir motivo de até 500 caracteres para aplicar o bloqueio, exibir o motivo quando o bloqueio estiver ativo, indicar que o bloqueio é registrado em nome do usuário autenticado e permitir remover o bloqueio sem alterar a situação cadastral. Usuários não administradores SHALL consultar o detalhe sem “Editar cadastro” nem o controle de bloqueio.

### Requirement: Histórico e pendências permanecem sem dados até os domínios de origem

O detalhe SHALL exibir a seção “Histórico e pendências” com as abas “Locações”, “Multas” e “Pagamentos” desabilitadas e identificadas como “Em breve”, e a mensagem “Aguardando implementação das capacidades de locações, multas e pagamentos. Nenhum saldo ou histórico financeiro é apresentado nesta versão.”. A seção SHALL NOT exibir valores, saldos, listas ou registros fictícios.

### Requirement: Layout responsivo

Em até 1100 px o detalhe SHALL passar a uma coluna; em até 900 px a tabela SHALL virar cartões empilhados; em até 640 px os campos do formulário e os dados do cliente SHALL usar uma coluna e a busca SHALL ocupar a largura total, sem rolagem horizontal da página. Todos os controles SHALL ter indicação de foco visível.
