# Spec Delta

## ADDED Requirements

### Requirement: Miniatura dos exemplares usa a capa do catálogo

A miniatura de cada filme na rota `/exemplares` SHALL exibir a mesma capa do catálogo de filmes (`capa_url`) quando houver, para qualquer perfil, mantendo o gradiente determinado pelo `id` do filme quando não houver capa. Para obter as capas, a tela SHALL consultar o catálogo também para usuários não administradores, sem passar a exibir para eles gênero, ano, filmes sem exemplares ou o resumo de filmes. A falha dessa consulta SHALL apenas omitir as capas para não administradores, sem esconder a lista de exemplares nem exibir erro. A imagem SHALL ser decorativa.

#### Scenario: Exemplar de filme com capa

- **WHEN** um funcionário abre `/exemplares` e o filme do exemplar tem capa no catálogo
- **THEN** a miniatura da linha mostra a capa no lugar do gradiente

#### Scenario: Catálogo indisponível para member

- **WHEN** a consulta do catálogo falha para um usuário `member`
- **THEN** a lista de exemplares aparece normalmente, com os gradientes
