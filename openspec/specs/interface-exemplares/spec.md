# Interface Exemplares Specification

## Purpose

Definir a apresentação, os filtros, o diálogo de cadastro e a responsividade da tela de Exemplares da CINEBYTE LOCADORA, em coerência visual com o login, o dashboard e o Acervo, sem alterar o contrato de `exemplares`, a autenticação, as permissões ou o backend.

## Requirements

### Requirement: Exemplares são apresentados agrupados por filme com dados reais

A rota `/exemplares` SHALL exibir, para uma sessão válida, a barra superior compartilhada com “Exemplares” como página atual, a etiqueta “ACERVO”, o título “Exemplares”, a barra de filtros e uma lista com uma linha por filme. Cada linha SHALL exibir o título do filme, “ID do filme”, a contagem de exemplares ativos com a unidade no singular ou plural e os identificadores dos exemplares. Para não administradores, os identificadores SHALL ser apenas dados, sem ações; para administradores, cada identificador SHALL abrir as ações da cópia. Empréstimo e devolução SHALL NOT ser oferecidos nesta tela. Gênero e ano do filme SHALL ser exibidos somente quando a lista de filmes estiver disponível (administradores). Filmes sem exemplares SHALL aparecer, com contagem 0, somente quando essa lista estiver disponível. Para os demais perfis, SHALL ser exibidos apenas os filmes que possuem exemplares. A miniatura do filme SHALL ser decorativa, com um entre cinco gradientes determinados de forma estável pelo `id` do filme. A tela SHALL NOT exibir exemplares, filmes, identificadores ou totais inventados.

#### Scenario: Administrador com lista de filmes
- **WHEN** a consulta de exemplares e a de filmes são concluídas
- **THEN** os filmes aparecem na ordem da lista de filmes, inclusive os sem exemplares, com gênero e ano
- **AND** o resumo indica “N exemplares · X de Y filmes com cópia”, contando somente exemplares ativos

#### Scenario: Usuário sem permissão de administrador
- **WHEN** um usuário não administrador abre a tela
- **THEN** vê somente os filmes com exemplares, sem gênero, ano ou resumo de filmes, e o resumo indica apenas “N exemplares”

### Requirement: Busca e filtro por filme são filtros de apresentação

A busca por identificador (sem distinção de maiúsculas e minúsculas) e o filtro por filme SHALL atuar somente sobre a lista já carregada, sem nova chamada ao Xano e sem alterar a lista carregada. Quando houver exemplares mas nenhum corresponder aos filtros, a tela SHALL exibir “Nenhum exemplar corresponde aos filtros.”.

#### Scenario: Filtro sem correspondência

- **WHEN** a busca por identificador não corresponde a nenhum exemplar carregado
- **THEN** a tela exibe “Nenhum exemplar corresponde aos filtros.” sem nova chamada ao Xano

### Requirement: Cadastro ocorre em diálogo controlado, restrito a administradores

O botão “Cadastrar exemplar” e o diálogo SHALL ser exibidos somente a administradores, e o diálogo SHALL ser controlado por `exemplar_dialog_open`. O diálogo SHALL preservar os campos “Identificador do exemplar” e “Filme”, os handlers `capture_exemplar_identifier`, `capture_exemplar_film_selection` e `submit_exemplar`, o formato `id | título` da seleção, a validação existente e as mensagens de erro com papel `alert`. Após cadastro bem-sucedido, o diálogo SHALL fechar e a mensagem “Exemplar cadastrado com sucesso.” SHALL ser exibida na página. Em caso de erro de validação ou do Xano, o diálogo SHALL permanecer aberto com a mensagem existente. Fechar ou cancelar SHALL descartar o rascunho sem enviar dados. Usuários não administradores SHALL NOT conseguir abrir o diálogo.

#### Scenario: Cadastro bem-sucedido

- **WHEN** um administrador informa identificador e filme válidos e confirma
- **THEN** o diálogo fecha e a página exibe “Exemplar cadastrado com sucesso.”

### Requirement: Atalhos de cópia pré-selecionam o filme sem gerar identificadores

Para administradores, cada filme presente na lista de filmes SHALL oferecer “Outra cópia” (quando já houver exemplares) ou “Adicionar cópia” (quando não houver) que abre o diálogo com o filme correspondente pré-selecionado por `capture_exemplar_film_selection`. O identificador SHALL ser informado pela pessoa e SHALL NOT ser gerado automaticamente.

#### Scenario: Outra cópia

- **WHEN** um administrador aciona “Outra cópia” em um filme com exemplares
- **THEN** o diálogo abre com o filme pré-selecionado e o identificador em branco

### Requirement: Estados de carregamento, erro, sucesso e vazio são preservados

A tela SHALL exibir o carregamento com papel `status`, o erro de consulta com papel `alert`, o erro de carregamento de filmes (administradores) com papel `alert`, a mensagem de sucesso com papel `status` e “Nenhum exemplar encontrado.” quando não houver exemplares. Durante erro ou carregamento, a lista SHALL NOT ser exibida.

#### Scenario: Sem exemplares

- **WHEN** a consulta de exemplares é concluída sem registros
- **THEN** a tela exibe “Nenhum exemplar encontrado.”

### Requirement: Layout responsivo

Em larguras de até 1100 px cada linha SHALL passar a duas colunas, com os identificadores abaixo. Em até 640 px os filtros SHALL ocupar a largura total, os identificadores SHALL quebrar em várias linhas e o diálogo SHALL respeitar a largura da viewport, sem rolagem horizontal da página. Todos os controles SHALL ter indicação de foco visível.

#### Scenario: Celular

- **WHEN** a tela é exibida com largura de até 640 px
- **THEN** os filtros ocupam a largura total, os identificadores quebram em linhas e não há rolagem horizontal

### Requirement: Miniatura dos exemplares usa a capa do catálogo

A miniatura de cada filme na rota `/exemplares` SHALL exibir a mesma capa do catálogo de filmes (`capa_url`) quando houver, para qualquer perfil, mantendo o gradiente determinado pelo `id` do filme quando não houver capa. Para obter as capas, a tela SHALL consultar o catálogo também para usuários não administradores, sem passar a exibir para eles gênero, ano, filmes sem exemplares ou o resumo de filmes. A falha dessa consulta SHALL apenas omitir as capas para não administradores, sem esconder a lista de exemplares nem exibir erro. A imagem SHALL ser decorativa.

#### Scenario: Exemplar de filme com capa

- **WHEN** um funcionário abre `/exemplares` e o filme do exemplar tem capa no catálogo
- **THEN** a miniatura da linha mostra a capa no lugar do gradiente

#### Scenario: Catálogo indisponível para member

- **WHEN** a consulta do catálogo falha para um usuário `member`
- **THEN** a lista de exemplares aparece normalmente, com os gradientes

### Requirement: Exemplares baixados ficam ocultos por padrão

A tela SHALL ocultar exemplares baixados por padrão e oferecer “Mostrar baixados”. Com a opção ativa, os exemplares baixados SHALL aparecer em seus filmes com o selo “Baixado” e o tipo da baixa (“Perdido”, “Danificado”, “Descartado” ou “Outro”), sem contar na quantidade de exemplares do filme. Quando houver exemplares baixados, o resumo SHALL acrescentar “· N baixado(s)”.

#### Scenario: Opção desligada
- **WHEN** existe um exemplar baixado e “Mostrar baixados” está desligado
- **THEN** o exemplar não aparece na lista, e o resumo informa que há 1 baixado

### Requirement: Ações administrativas por cópia em diálogo

Para administradores, acionar um identificador SHALL abrir o diálogo “Exemplar <identificador>”. Para exemplar ativo, o diálogo SHALL oferecer:
- “Salvar alterações”: identificador e filme, com a mensagem do backend quando a troca de filme ou o identificador for recusado;
- “Dar baixa”: tipo e motivo obrigatórios, com confirmação explícita e aviso de que a cópia sai das opções de locação.

Para exemplar baixado, o diálogo SHALL exibir o tipo e o motivo da baixa e oferecer somente “Reativar”, com motivo obrigatório e aviso de que a cópia volta como “não conferida”. Após sucesso, o diálogo SHALL fechar, a lista SHALL ser atualizada com o retorno do backend e a página SHALL exibir a mensagem de sucesso. Em erro, o diálogo SHALL permanecer aberto com a mensagem com papel `alert`. Usuários não administradores SHALL NOT conseguir abrir o diálogo.

#### Scenario: Baixa confirmada
- **WHEN** o administrador informa tipo e motivo e confirma a baixa
- **THEN** o diálogo fecha, o exemplar some da lista padrão e a página exibe “Baixa registrada.”

#### Scenario: Troca de filme recusada
- **WHEN** o backend recusa a troca de filme por existir histórico de locações
- **THEN** o diálogo permanece aberto com a mensagem do backend
