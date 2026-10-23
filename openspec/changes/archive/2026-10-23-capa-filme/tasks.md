# Tasks

Sem commit, push ou merge. Publicação no Xano `v1` somente com autorização explícita.

## 1. Xano (XanoScript versionado)

- [x] 1.1 `film.capa` opcional (`image?`).
- [x] 1.2 `POST catalogo-filmes/filmes/{id}/capa`: `admin`, filme existente, `file?` → `storage.create_image` público, confere `mime`/`size`, edita, apaga a anterior, audita.
- [x] 1.3 `DELETE catalogo-filmes/filmes/{id}/capa`: `admin`, desassocia, apaga, audita.
- [x] 1.4 `capa` no `output` de GET lista, GET por id, POST e PATCH.
- [x] 1.5 Publicado em 2026-10-23 no workspace 149184, branch `v1`, somente os 7 arquivos da capa (prévia: `film` atualizada com 1 campo, 4 endpoints atualizados, 2 criados). Conferido por `pull`: `enforce_role`/`log_event` presentes, sem placeholders, lógica idêntica à local. Fumaça sem token: rotas existem e recusam (401 com arquivo; 400 sem arquivo).
- [x] 1.6 Conferência com filme real: o upload de arquivo foi barrado pelo plano do Xano (HTTP 403 "Not supported. Please upgrade your Xano instance.", filme 5, 23/10) e foi substituído pela capa por link (seção 4), conferida no Creed; remoção e recusa a `member` confirmado pelo usuário em 23/10/2026.

## 2. Reflex

- [x] 2.1 `validar_capa`: tamanho e assinatura binária; nome gerado.
- [x] 2.2 Transporte multipart (httpx e `curl.exe`), `upload_film_cover_xano`, `remove_film_cover_xano`, `capa_url` derivada do `path`.
- [x] 2.3 Área de capa na edição (prévia, enviar/trocar, remover, estados) e capa no card do acervo.

## 3. Validação

- [x] 3.1 `tests/test_capa_filme.py`; suíte completa.
- [x] 3.2 `reflex compile --dry` e `openspec validate capa-filme --strict`.
- [x] 3.3 Conferência no navegador após a publicação no Xano — confirmado pelo usuário em 23/10/2026.

## 4. Capa por link (plano do Xano sem storage)

O storage do Xano respondeu 403 "Not supported. Please upgrade your Xano instance." no envio real (filme 5): o plano atual não permite armazenar arquivos. Alternativa adotada sem nova tecnologia:

- [x] 4.1 `film.capa_link` (texto, até 500) e `PUT catalogo-filmes/filmes/{id}/capa-link` (`admin`, somente `https://` sem espaços, aspas ou `<>`, vazio limpa, auditoria `update_film_cover_link`); `DELETE .../capa` limpa também o link; `capa_link` no `output` dos endpoints de filme.
- [x] 4.2 Reflex: `capa_url` usa o arquivo do storage e, sem ele, o link; campo "Link da imagem" com "Usar link" na edição; o 403 de plano agora gera mensagem própria, não "sem permissão".
- [x] 4.3 Publicado em `v1` (149184) e conferido por `pull`. A primeira versão do regex usava `\/` e recusava qualquer link (o XanoScript não preserva o escape); foi corrigida e conferida contra o filme inexistente 999999 (`http`, espaço e `"><script>` recusados; https válido aceito).
- [x] 4.4 Capa do Creed (id 5) gravada pelo endpoint com a sessão do admin; releitura confirma o link e os demais campos intactos.

## 5. Capa na tela de exemplares

- [x] 5.1 Miniatura de `/exemplares` usa a capa do catálogo para qualquer perfil (`exemplar_covers`); `exemplar_films` (manutenção) continua só para admin; falha do catálogo para member só omite as capas.
- [x] 5.2 Testes de estado e UI; suítes completas e `reflex compile --dry`.
