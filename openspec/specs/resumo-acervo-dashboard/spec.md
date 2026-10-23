# resumo-acervo-dashboard Specification

## Purpose
Permitir ao administrador consultar os totais reais de filmes e exemplares cadastrados, com autorização no backend, atualização explícita e isolamento da sessão, preservando o backoffice dos demais usuários.

## Requirements

### Requirement: Resumo conta todos os cadastros sem inferir disponibilidade

O sistema SHALL oferecer uma consulta de agregação somente de leitura que conte todos os registros de `film` e todos os registros de `exemplar`, separadamente. O total de filmes SHALL incluir ativos e inativos, inclusive filmes sem exemplares. Os totais SHALL ser independentes de filtros, paginação ou listas carregadas do catálogo. A consulta SHALL NOT criar tabelas de Dashboard, alterar `film` ou `exemplar`, nem calcular disponibilidade ou indicadores operacionais/financeiros. Cada total SHALL ser exato para sua leitura; não é exigido snapshot simultâneo entre tabelas durante alterações concorrentes.

#### Scenario: Filmes ativos e inativos com várias cópias

- **GIVEN** uma base estável com 2 filmes ativos e 1 inativo, um deles sem exemplares, e 5 exemplares distribuídos entre os demais filmes
- **WHEN** um administrador autorizado consulta o resumo
- **THEN** os totais são exatamente 3 filmes e 5 exemplares
- **AND** os exemplares associados ao filme inativo também são contados

#### Scenario: Base vazia

- **WHEN** um administrador consulta uma base sem filmes nem exemplares
- **THEN** a resposta é um sucesso válido com os dois totais iguais a 0

#### Scenario: Filme sem exemplares

- **WHEN** um administrador consulta uma base com 1 filme e nenhum exemplar
- **THEN** o resumo informa 1 filme e 0 exemplares

#### Scenario: Filtros do catálogo não afetam os totais

- **GIVEN** a base tem 3 filmes e 5 exemplares e o catálogo filtrado exibe apenas 1 filme
- **WHEN** o administrador consulta ou atualiza o resumo
- **THEN** os totais continuam sendo 3 e 5
- **AND** alterar título, gênero ou página do catálogo não muda o contrato nem dispara consulta automática do resumo

#### Scenario: Consulta preserva os dados e contratos existentes

- **WHEN** a agregação é executada
- **THEN** nenhum cadastro, disponibilidade, locação ou registro financeiro é alterado
- **AND** não são criadas tabelas nem modificados schemas ou contratos das APIs existentes
- **AND** somente a auditoria mínima de recusas já prevista pela política de acesso pode produzir seu registro de segurança

### Requirement: Autorização administrativa precede as contagens

A API SHALL exigir autenticação `user` válida e validar no backend existência, estado atual e papel `admin` da conta antes de consultar qualquer dado de `film` ou `exemplar`. Conta legada sem estado explícito SHALL continuar tratada como ativa pela política existente. Contas inexistentes, explicitamente inativas ou sem papel reconhecido SHALL ser recusadas, mesmo com token ainda válido. O papel informado pelo cliente SHALL NOT conceder autorização.

#### Scenario: Admin ativo ou legado autorizado

- **WHEN** uma conta autenticada admin ativa, ou admin legada sem estado explícito, consulta o resumo
- **THEN** o backend valida a conta e o papel antes de executar as duas contagens

#### Scenario: Member chama diretamente a API

- **WHEN** um member ativo chama a agregação diretamente, inclusive informando papel admin em dados da requisição
- **THEN** o backend recusa por ausência de permissão
- **AND** nenhuma consulta às tabelas film ou exemplar é executada nem total é retornado

#### Scenario: Token ausente inválido ou expirado

- **WHEN** uma requisição sem token válido solicita o resumo
- **THEN** a API rejeita por falta de autenticação antes das contagens
- **AND** não retorna totais

#### Scenario: Conta deixa de ser autorizada depois do login

- **WHEN** um token ainda válido é usado após desativação, remoção da conta ou mudança de admin para member ou papel desconhecido
- **THEN** a autorização considera a conta atual e recusa o resumo antes das contagens
- **AND** não retorna dados protegidos

### Requirement: Contrato mínimo é validado integralmente

O sucesso SHALL retornar somente `total_filmes` e `total_exemplares` como inteiros JSON não negativos e `generated_at` como horário de conclusão da geração no backend, em string RFC 3339 UTC com sufixo Z. A resposta SHALL NOT conter dados pessoais, credenciais, registros individuais ou campos adicionais. A aplicação SHALL rejeitar payload incompleto ou inválido sem coerção nem aproveitamento parcial dos totais.

#### Scenario: Resposta válida apresentada

- **WHEN** a consulta retorna dois inteiros não negativos e horário UTC válido nos três campos contratados
- **THEN** a aplicação aceita o resumo integral e apresenta os totais e o horário de geração

#### Scenario: Tipos ou valores inválidos

- **WHEN** qualquer total é negativo, booleano, fracionário, string ou null
- **THEN** a aplicação trata a resposta como inválida sem converter os valores ou apresentar sucesso

#### Scenario: Estrutura ou horário inválido

- **WHEN** o sucesso HTTP contém JSON malformado, lista, campo obrigatório ausente, campo extra ou timestamp inválido ou sem UTC
- **THEN** a aplicação apresenta falha de resposta inválida sem exibir números nem horário como válidos

### Requirement: Atualização distingue carregamento sucesso e erros

A Dashboard SHALL consultar o resumo após validação da sessão ao entrar por `/backoffice` ou `/` e SHALL oferecer Atualizar manual para admin. SHALL NOT realizar polling. Ao iniciar uma consulta SHALL retirar totais e horário anteriores, apresentar carregamento e impedir consultas duplicadas pelo controle manual. Sucesso SHALL mostrar os dois cartões com rótulos de quantidade cadastrada; 0 SHALL ser apresentado como valor válido. Falha de rede/timeout, erro de serviço, resposta inválida e ausência de permissão SHALL ser distinguidos e SHALL NOT virar zero, sucesso parcial ou totais antigos.

#### Scenario: Entrada autenticada e carregamento

- **WHEN** um admin entra por qualquer uma das duas rotas da Dashboard
- **THEN** a sessão é validada antes da consulta e a seção mostra carregamento sem números presumidos
- **AND** Atualizar fica indisponível enquanto a requisição está em andamento

#### Scenario: Zero é exibido como sucesso

- **WHEN** a resposta válida contém os dois totais iguais a 0
- **THEN** os cartões mostram 0 e o horário de geração, sem mensagem de falha ou dados indisponíveis

#### Scenario: Atualização manual após mudança de cadastro

- **GIVEN** a base estável passou de 3 para 4 filmes e mantém 5 exemplares
- **WHEN** o admin seleciona Atualizar
- **THEN** a sessão é revalidada e uma nova consulta apresenta 4 e 5 com novo horário de geração
- **AND** nenhuma atualização periódica é iniciada

#### Scenario: Falha de rede ou serviço após sucesso anterior

- **WHEN** uma consulta sofre falha de conexão, timeout ou erro de serviço, inclusive após resultado anterior
- **THEN** a seção mostra erro recuperável e opção Atualizar, sem totais ou horário anteriores
- **AND** os links do backoffice permanecem utilizáveis

#### Scenario: Falha de resposta inválida

- **WHEN** a resposta não atende ao contrato integral
- **THEN** a seção identifica resposta inválida e permite nova tentativa manual sem mostrar valores parciais

#### Scenario: Perda de autenticação ou autorização

- **WHEN** a consulta é rejeitada por autenticação inválida ou permissão insuficiente
- **THEN** totais e horário são limpos
- **AND** autenticação inválida segue o fluxo existente de encerramento de sessão e login
- **AND** permissão insuficiente apresenta acesso restrito sem retirar a navegação ainda autorizada

### Requirement: Sessão e navegação existentes são preservadas

A Dashboard SHALL usar a sessão existente sem expor token ao navegador, armazenamento cliente, URL, mensagens ou logs. Seus dados e erros SHALL ficar isolados dos módulos de clientes, filmes e exemplares. `/backoffice` e `/` SHALL continuar acessíveis a admin e member ativos; member SHALL manter links e funcionalidades já autorizados sem consultar nem receber os totais protegidos.

#### Scenario: Member usa o backoffice

- **WHEN** um member ativo entra na Dashboard
- **THEN** vê uma indicação de acesso restrito na seção dos totais sem disparar a agregação
- **AND** pode usar os links de filmes, clientes e exemplares conforme os contratos existentes

#### Scenario: Member dispara evento manual diretamente

- **WHEN** um member tenta disparar o evento de Atualizar sem usar o botão da interface
- **THEN** a aplicação não consulta a agregação nem envia totais ao navegador
- **AND** a API permanece protegida independentemente desse bloqueio local

#### Scenario: Transporte e falhas não expõem credenciais

- **WHEN** a aplicação consulta o resumo ou registra/apresenta uma falha
- **THEN** o token é utilizado somente no servidor para autenticar a chamada ao Xano
- **AND** nenhum token, corpo bruto de erro remoto ou dado pessoal é incluído no estado público ou nos logs da Dashboard

#### Scenario: Erro isolado do resumo

- **WHEN** o resumo falha
- **THEN** estados, filtros, formulários e contratos de clientes, catálogo e exemplares permanecem preservados

### Requirement: Dados não sobrevivem à mudança de sessão

O sistema SHALL limpar os indicadores, horário e estado transitório da Dashboard após logout, limpeza de sessão, troca de conta ou perda de autorização. SHALL descartar respostas de consultas iniciadas sob sessão ou requisição que já não seja a atual, inclusive entre duas contas admin.

#### Scenario: Logout após consulta

- **WHEN** o admin encerra a sessão depois de consultar o resumo
- **THEN** os totais e horário são retirados do estado e da apresentação
- **AND** a tela de login não recebe dados da Dashboard

#### Scenario: Troca de admin para member ou outro admin

- **WHEN** uma conta é substituída por outra no mesmo contexto da aplicação
- **THEN** nenhum valor da sessão anterior é reutilizado
- **AND** somente uma nova consulta autorizada pode preencher os indicadores da nova sessão

#### Scenario: Resposta chega depois do logout ou troca de conta

- **WHEN** uma consulta antiga termina após logout ou troca de conta
- **THEN** sua resposta é descartada sem restaurar totais, horário ou sucesso

#### Scenario: Resposta antiga chega depois de consulta mais recente

- **WHEN** uma resposta de requisição superada chega após a requisição atual
- **THEN** ela não substitui os dados ou o estado da requisição atual

### Requirement: Indicadores futuros permanecem indisponíveis

Indicadores de locações, disponibilidade, multas e finanças ainda não implementados SHALL permanecer explicitamente indisponíveis, sem números, moeda ou histórico simulados. O total cadastrado de exemplares SHALL NOT preencher o cartão de exemplares disponíveis.

#### Scenario: Totais cadastrados carregados com sucesso

- **WHEN** a Dashboard apresenta totais válidos de filmes e exemplares
- **THEN** os demais indicadores continuam com “—” e indicação de dados indisponíveis
- **AND** nenhum total cadastrado é apresentado como disponibilidade ou saldo financeiro
