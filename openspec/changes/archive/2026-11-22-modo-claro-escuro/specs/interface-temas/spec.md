# Spec Delta

## Purpose

Permitir que pessoas autenticadas alternem a aparência entre os modos escuro e claro sem alterar o conteúdo, o layout ou os comportamentos da interface.

## ADDED Requirements

### Requirement: Barra superior oferece alternância de tema

A barra superior compartilhada SHALL apresentar um botão simples de alternância de modo de cor entre o botão "Sair" e o bloco com nome, perfil e avatar do usuário. O controle SHALL indicar a ação disponível por ícone e rótulo acessível, preservando a ordem visual da interface. Ativá-lo SHALL alternar imediatamente entre "escuro" e "claro" sem recarregar a página, redirecionar o usuário ou alterar dados da sessão.

#### Scenario: Alternar para o modo claro

- **WHEN** uma pessoa autenticada ativa o controle enquanto a aplicação está no modo escuro
- **THEN** a interface muda para a paleta clara
- **AND** a sessão, a página atual e os dados exibidos permanecem intactos

#### Scenario: Alternar para o modo escuro

- **WHEN** uma pessoa autenticada ativa o controle enquanto a aplicação está no modo claro
- **THEN** a interface muda para a paleta escura atual
- **AND** nenhum conteúdo ou controle muda de posição

#### Scenario: Leitura por tecnologia assistiva

- **WHEN** o controle recebe foco
- **THEN** seu nome acessível informa o modo que será ativado
- **AND** o foco permanece perceptível sem alterar o layout

### Requirement: Preferência de tema persiste

A aplicação SHALL preservar a preferência escolhida entre navegações e atualizações da página. O modo escuro SHALL ser o padrão quando não houver preferência anterior. A preferência SHALL permanecer separada da autenticação e SHALL seguir aplicada após logout e ao retornar à tela de login.

#### Scenario: Navegação entre páginas

- **WHEN** a pessoa muda o tema e navega para outra rota autenticada
- **THEN** a nova página abre no mesmo tema

#### Scenario: Nova sessão sem preferência

- **WHEN** uma pessoa usa a aplicação pela primeira vez ou sem preferência armazenada
- **THEN** a interface inicia no modo escuro atual

### Requirement: Paleta clara mantém contraste e estados visuais

O modo claro SHALL usar uma paleta nova baseada em superfícies claras, texto escuro legível, bordas discretas e o vermelho de destaque da marca em tom compatível com contraste adequado. O tema SHALL preservar a semântica visual de sucesso, erro, carregamento, seleção, desabilitado e foco, sem usar cor isoladamente para comunicar estado.

#### Scenario: Leitura de conteúdo principal

- **WHEN** o modo claro está ativo
- **THEN** textos principais, rótulos e informações secundárias apresentam contraste legível sobre suas superfícies

#### Scenario: Interação em modo claro

- **WHEN** campos, botões, links e controles recebem foco, hover ou estado pressionado
- **THEN** cada estado permanece perceptível e não reduz a legibilidade

### Requirement: Todas as superfícies usam o tema selecionado

Todas as páginas da aplicação, incluindo login, dashboard, acervo, exemplares, clientes, locações, multas, relatórios e usuários, SHALL usar a paleta correspondente ao tema ativo. Todos os modais, diálogos, formulários, menus, confirmações, estados vazios, estados de erro e outras janelas abertas durante o uso SHALL usar os mesmos tokens de cor.

#### Scenario: Navegação pela aplicação

- **WHEN** o tema está ativo em uma rota autenticada e a pessoa abre outra página
- **THEN** fundos, superfícies, textos, bordas e controles usam a paleta do tema ativo

#### Scenario: Abertura de diálogo

- **WHEN** uma janela ou diálogo é aberto em qualquer página
- **THEN** o fundo, o painel, campos, ações e mensagens seguem o tema ativo

### Requirement: Alternância não altera o design

A troca de tema SHALL alterar somente cores, opacidades e efeitos de superfície diretamente relacionados à paleta. SHALL NOT alterar larguras, alturas, posições, grades, espaçamentos, fontes, animações, conteúdo, navegação ou hierarquia visual existentes.

#### Scenario: Comparação dos modos

- **WHEN** as mesmas telas são comparadas nos modos claro e escuro
- **THEN** a estrutura e as dimensões permanecem equivalentes
- **AND** a única diferença funcional visível é a apresentação das cores
