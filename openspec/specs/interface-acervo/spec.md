# Interface Acervo Specification

## Purpose

Definir a apresentação, os filtros, a responsividade e os formulários da tela de Acervo (catálogo de filmes) da CINEBYTE LOCADORA, em coerência visual com o login e o dashboard, sem alterar o contrato de `catalogo-filmes`, a autenticação, as permissões ou as regras de negócio.

## Requirements

### Requirement: Acervo apresenta o catálogo real em grade escura

A rota `/filmes` SHALL exibir, para uma sessão válida, a barra superior compartilhada com “Acervo” como página atual (`aria-current`), a etiqueta “ACERVO”, o título “Catálogo de filmes”, a barra de filtros e uma grade de cartões, sobre o fundo escuro e as superfícies de carvão do dashboard, com vermelho `#DC2638` como destaque e as fontes Inter e Space Mono. Cada cartão SHALL exibir somente dados reais retornados pelo Xano: título, gênero, ano de lançamento, classificação indicativa em selo, valor formatado e status. O pôster do cartão SHALL ser decorativo (oculto de tecnologia assistiva), com um entre cinco gradientes determinados de forma estável pelo `id` do filme, e SHALL NOT representar gênero, classificação ou status por cor. A tela SHALL NOT exibir filmes, preços ou contagens de exemplo, nem alternância grade/lista.

#### Scenario: Lista com filmes

- **WHEN** a consulta ao catálogo é concluída com filmes
- **THEN** cada filme aparece em um cartão com seus dados reais
- **AND** o contador “N filmes” e o rodapé “Mostrando X de Y filmes” refletem as quantidades reais

### Requirement: Pesquisa e filtros preservam o comportamento existente

A pesquisa por título e o filtro de gênero, este como campo de texto, SHALL continuar atualizando o estado a cada alteração e SHALL consultar o Xano somente pela ação “Buscar”, que mantém `apply_film_filters` e o contrato existente. O filtro de status “Todos / Ativos / Inativos” SHALL ser um filtro de apresentação sobre a lista já carregada, usando somente os valores `active` e `inactive` do enum de `film.status`, sem nova chamada ao Xano e sem alterar a lista carregada. O status SHALL NOT ser tratado como disponibilidade de exemplares.

#### Scenario: Filtrar por status

- **WHEN** a pessoa seleciona “Inativos”
- **THEN** somente os filmes com `status` igual a `inactive` aparecem, e nenhuma consulta ao Xano é feita
- **AND** o contador e o rodapé indicam a quantidade visível e o total carregado

### Requirement: Estados de carregamento, erro, sucesso e vazio são preservados

A tela SHALL exibir o carregamento com papel `status`, o erro de consulta com papel `alert`, a mensagem de sucesso após salvar com papel `status`, “Nenhum filme encontrado.” quando a consulta não retorna filmes e “Nenhum filme com este status.” quando o filtro de status oculta todos os filmes carregados. Durante erro ou carregamento, a grade SHALL NOT ser exibida.

#### Scenario: Consulta sem filmes

- **WHEN** a consulta ao catálogo é concluída sem filmes
- **THEN** a tela exibe “Nenhum filme encontrado.” e a grade não é exibida durante carregamento ou erro

### Requirement: Ações administrativas continuam restritas a administradores

O botão “Cadastrar filme”, o cartão tracejado de cadastro e o botão de edição de cada cartão SHALL aparecer somente para `admin` e SHALL levar às rotas existentes `/filmes/novo` e `/filmes/{id}/editar`. Os handlers continuam redirecionando perfis sem permissão e sessões inválidas.

#### Scenario: Usuário member no Acervo

- **WHEN** um usuário `member` abre `/filmes`
- **THEN** não vê “Cadastrar filme”, o cartão de cadastro nem a edição dos cartões

### Requirement: Formulários de cadastro e edição mantêm rotas e validações

As rotas `/filmes/novo` e `/filmes/{id}/editar` SHALL permanecer páginas, com o visual de painel de vidro e a barra superior do Acervo, sem modal. SHALL manter os campos Título, Gênero, Ano de lançamento, Classificação indicativa e Valor da locação, os limites de 200 e 100 caracteres, o mínimo de 1888 para o ano, os handlers `capture_film_*` e `submit_film`, a validação existente (`validar_filme`), a exibição do erro com papel `alert` e o redirecionamento a `/filmes` após salvar. A classificação SHALL ser selecionada por botões segmentados com todas as seis opções válidas. O status SHALL aparecer somente na edição. Fechar e Cancelar SHALL voltar ao catálogo sem salvar.

#### Scenario: Edição de filme

- **WHEN** um administrador abre `/filmes/{id}/editar`
- **THEN** a página exibe os campos do filme, a classificação em botões segmentados e o status
- **AND** salvar com dados válidos redireciona a `/filmes`

### Requirement: Layout responsivo

A grade SHALL se adaptar à largura (colunas automáticas de no mínimo 210 px, 150 px abaixo de 640 px), os filtros SHALL quebrar em linhas e ocupar a largura total em celulares, e o formulário SHALL usar uma coluna abaixo de 640 px, sem rolagem horizontal da página. Todos os controles SHALL ter indicação de foco visível.

#### Scenario: Celular

- **WHEN** a tela é exibida com largura inferior a 640 px
- **THEN** a grade usa colunas de no mínimo 150 px, os filtros ocupam a largura total e não há rolagem horizontal

### Requirement: Acervo e edição exibem a capa do filme

O card do acervo SHALL exibir a capa quando o filme tiver uma, com texto alternativo “Capa de {título}” e carregamento preguiçoso; sem capa, ou com `path` fora do formato esperado, SHALL manter o pôster de cor existente. A tela de edição SHALL exibir, somente a administradores, a área “Capa” com prévia, enviar ou trocar (JPEG, PNG ou WebP até 2 MB) e remover. Antes de enviar, o servidor Reflex SHALL validar tamanho e assinatura binária e SHALL gerar o nome do arquivo, sem usar o nome informado pelo usuário. Durante o envio a área SHALL indicar carregamento; erros de validação, de permissão, de limite de requisições e de auditoria SHALL ser exibidos com papel `alert`, sem repetir automaticamente a operação. O cadastro de novo filme SHALL NOT oferecer capa.

#### Scenario: Card com capa

- **WHEN** o acervo lista um filme com capa
- **THEN** o card mostra a imagem da capa no lugar do pôster de cor

#### Scenario: Arquivo inválido na interface

- **WHEN** o administrador escolhe um PDF renomeado para `.jpg`
- **THEN** a interface recusa pelo conteúdo, informa o motivo e nada é enviado ao Xano
