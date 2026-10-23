# Spec Delta

## ADDED Requirements

### Requirement: Administrador associa uma capa opcional ao filme

O filme SHALL ter o campo opcional `capa`, armazenado no storage do Xano com acesso público. `POST catalogo-filmes/filmes/{id}/capa` SHALL aceitar somente `admin`, SHALL exigir filme existente e SHALL aceitar somente imagem JPEG, PNG ou WebP de até 2 MB, conferida pelo tipo e tamanho reais do arquivo gravado; fora disso SHALL apagar o arquivo e responder erro de entrada. Ao substituir uma capa, a anterior SHALL ser apagada somente depois que o filme referenciar a nova. `DELETE catalogo-filmes/filmes/{id}/capa` SHALL aceitar somente `admin`, SHALL desassociar e apagar a capa. Ambos SHALL registrar auditoria (`update_film_cover`, `remove_film_cover`) e responder `{film, audit_succeeded}`. Os endpoints de leitura, criação e edição de filme SHALL devolver `capa` como objeto do storage ou `null`, sem alterar os demais campos do contrato. A capa SHALL NOT alterar exemplares, disponibilidade ou locações.

#### Scenario: Envio de capa válida

- **WHEN** um administrador envia uma imagem WebP de 500 KB para um filme existente
- **THEN** o filme passa a devolver `capa` com o `path` público e a auditoria registra `update_film_cover`

#### Scenario: Arquivo recusado

- **WHEN** o arquivo excede 2 MB ou não é JPEG, PNG ou WebP
- **THEN** o endpoint responde erro de entrada e o filme mantém a capa anterior

#### Scenario: Usuário sem permissão

- **WHEN** um `member` tenta enviar ou remover uma capa
- **THEN** o Xano recusa a operação e nada é gravado
