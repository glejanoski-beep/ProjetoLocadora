# Proposal

## Why

O acervo mostra um "pôster" de cor sólida com título e ano porque o filme não tem imagem. Uma capa real facilita reconhecer o filme no balcão. Tentativas anteriores gravaram imagens no servidor Reflex (`uploaded_files/`), que não é persistente nem fica associado ao filme no Xano.

## What Changes

- Tabela `film`: campo opcional `capa` (imagem no storage do Xano, acesso público — capa não é dado sensível).
- `POST catalogo-filmes/filmes/{id}/capa` (multipart, somente `admin`): recebe uma imagem JPEG, PNG ou WebP de até 2 MB, grava no storage, associa ao filme, apaga a capa anterior e audita (`update_film_cover`).
- `DELETE catalogo-filmes/filmes/{id}/capa` (somente `admin`): desassocia e apaga a capa, com auditoria (`remove_film_cover`).
- Endpoints de leitura e escrita de filme passam a devolver `capa` (objeto do storage ou `null`). Campo aditivo: o restante do contrato não muda.
- Reflex: validação no servidor (tamanho e assinatura binária, sem confiar no nome), envio multipart ao Xano, URL pública montada a partir da origem do Xano e do `path`.
- Tela de edição de filme: área de capa com prévia, enviar/trocar e remover. Cadastro novo não tem capa: ela é enviada depois, na edição.
- Acervo: o card mostra a capa; sem capa, mantém o pôster de cor.

**Não objetivos:** capa no cadastro inicial, recorte/redimensionamento, várias imagens por filme, capas nas telas de locação e dashboard (Change futura).

## Capabilities

### Modified Capabilities

- `catalogo-filmes`: campo e endpoints de capa.
- `interface-acervo`: capa no card e na edição.

## Impact

- Xano (branch `v1`): `table/film.xs`, `api/catalogo_filmes/filmes_GET.xs`, `filmes_id_GET.xs`, `filmes_POST.xs`, `filmes_id_PATCH.xs`, novos `filmes_id_capa_POST.xs` e `filmes_id_capa_DELETE.xs`.
- App: `ProjetoLocadora/xano_client.py`, `ProjetoLocadora/catalogo_filmes.py`, `ProjetoLocadora/ProjetoLocadora.py`, `assets/acervo.css`.
- Testes: `tests/test_capa_filme.py` e ajustes pontuais.
- Rollback: remover a área de capa da interface; o campo opcional e os arquivos podem permanecer sem efeito.
