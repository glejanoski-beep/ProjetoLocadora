# Design

## Armazenamento

- Coluna `image? capa?` em `film`, guardando o objeto inteiro retornado pelo storage (`access`, `path`, `name`, `type`, `size`, `mime`, `meta`).
- Input do endpoint declarado `file? capa` — a documentação do Xano (`xanoscript_docs/file-uploads.md`) indica que somente `file` popula `.path` no upload multipart; `image?` falha com `Missing param: path`.
- `storage.create_attachment` com `access = "public"`. Depois de gravado, o endpoint confere `mime` (JPEG, PNG ou WebP) e `size` (≤ 2 MB); fora disso apaga o arquivo e responde `inputerror`. `create_image` foi descartado porque recusa extensões desconhecidas com erro fatal (HTTP 500) em vez de erro de entrada.
- Troca: grava a nova, edita o filme e só então apaga a anterior (`storage.delete_file`). Uma falha no meio nunca deixa o filme sem capa válida.
- O objeto do storage não tem `url`: arquivos públicos são servidos na origem da instância + `path`. O Reflex monta a URL com a origem de `XANO_CATALOG_API_URL` e aceita somente `path` que comece com `/vault/` e não contenha `..`, espaço ou aspas; caso contrário trata como sem capa.

## Validação em duas camadas

- Reflex: até 2 MB e assinatura binária (JPEG `FF D8 FF`; PNG `89 50 4E 47 0D 0A 1A 0A`; WebP `RIFF....WEBP`). O nome enviado ao Xano é gerado (`capa-{id}.{ext}`), nunca o nome do arquivo do usuário.
- Xano: papel `admin`, existência do filme, `mime` e `size` reais do arquivo gravado. A interface não é mecanismo de segurança.

## Transporte

`_authenticated_request` ganha suporte a um arquivo multipart. Fora do Windows usa `httpx` (`files=`); no Windows segue o transporte `curl.exe` existente com `form = "capa=@<temporário>;type=<mime>;filename=<nome>"`, sem o cabeçalho JSON, e apaga o temporário no `finally`. Timeout de 30 s para upload.

## Auditoria

Mesmo padrão dos demais escritos: `{film, audit_succeeded}`; falha de auditoria após a gravação vira `XanoAuditError` e a interface não repete a operação.
