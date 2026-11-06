# Spec Delta

## Purpose

Oferecer ao administrador edição, baixa e reativação por cópia e exibir exemplares baixados sem confundi-los com o acervo ativo.

## MODIFIED Requirements

### Requirement: Exemplares são apresentados agrupados por filme com dados reais

A rota `/exemplares` SHALL exibir, para uma sessão válida, a barra superior compartilhada com “Exemplares” como página atual, a etiqueta “ACERVO”, o título “Exemplares”, a barra de filtros e uma lista com uma linha por filme. Cada linha SHALL exibir o título do filme, “ID do filme”, a contagem de exemplares ativos com a unidade no singular ou plural e os identificadores dos exemplares. Para não administradores, os identificadores SHALL ser apenas dados, sem ações; para administradores, cada identificador SHALL abrir as ações da cópia. Empréstimo e devolução SHALL NOT ser oferecidos nesta tela. Gênero e ano do filme SHALL ser exibidos somente quando a lista de filmes estiver disponível (administradores). Filmes sem exemplares SHALL aparecer, com contagem 0, somente quando essa lista estiver disponível. Para os demais perfis, SHALL ser exibidos apenas os filmes que possuem exemplares. A miniatura do filme SHALL ser decorativa, com um entre cinco gradientes determinados de forma estável pelo `id` do filme. A tela SHALL NOT exibir exemplares, filmes, identificadores ou totais inventados.

#### Scenario: Administrador com lista de filmes
- **WHEN** a consulta de exemplares e a de filmes são concluídas
- **THEN** os filmes aparecem na ordem da lista de filmes, inclusive os sem exemplares, com gênero e ano
- **AND** o resumo indica “N exemplares · X de Y filmes com cópia”, contando somente exemplares ativos

#### Scenario: Usuário sem permissão de administrador
- **WHEN** um usuário não administrador abre a tela
- **THEN** vê somente os filmes com exemplares, sem gênero, ano ou resumo de filmes, e o resumo indica apenas “N exemplares”

## ADDED Requirements

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
