# Proposal

## Why

O CineGestão registra a retirada de exemplares, mas não registra a volta. Cada locação permanece `active` e o exemplar continua ocupado para sempre: hoje as locações 1 e 2 mantêm os exemplares 1 e 4 indisponíveis. Sem devolução, o acervo diminui a cada locação. O `design.md` de `registrar-locacao` já previu que a devolução encerraria a locação e liberaria a ocupação na mesma transação, preservando `rental`.

## What Changes

- Registrar a devolução de uma locação ativa a partir do detalhe (`/locacoes/{id}`), localizada pelo número com o campo já existente.
- Persistir a devolução em registro próprio (`rental_return`), único por locação, com instante gerado pelo servidor e responsável derivado da sessão; marcar a locação como `returned` e remover sua ocupação na mesma transação.
- Impedir devolução duplicada e liberação indevida: bloqueio da locação, unicidade por locação, chave de operação por conta e remoção da ocupação somente pelo `rental_id`.
- Repetir com a mesma chave devolve o mesmo resultado; outra devolução de locação já devolvida é recusada.
- Exibir no detalhe a situação devolvida, a data da devolução, o responsável e se houve atraso (devolução após o vencimento), sem calcular multa ou valor.
- Ampliar o contrato de resposta de locação com `returned_at` e `returned_by` e o status `returned`; atualizar o cliente do app antes de publicar o backend.
- Permissão: contas ativas `member` e `admin`, como no registro.
- Reutilizar a trava `XANO_RENTAL_WRITES_ENABLED` (app e Xano).

**Não objetivos:** multas, valores, pagamentos, tolerância, cancelamento ou estorno de devolução, alteração de prazo, devolução parcial, listagem de locações, alteração da condição física pelo `member`, contador de locações ativas no dashboard.

## Capabilities

### New Capabilities

- `devolucao-locacao`: registro protegido e idempotente da devolução, liberação atômica do exemplar e apresentação na interface.

### Modified Capabilities

- `registro-locacao`: o status deixa de ser exclusivamente `active`; as respostas passam a incluir os dados de devolução; a vedação de devolução "neste incremento" é retirada.

## Impact

- Xano (`v1`, publicação somente com autorização): `rental.status` aceita `returned`; nova tabela `rental_return`; novo `POST /locacoes/{id}/devolucao`; `GET /locacoes/{id}`, `GET /locacoes/operacoes/{key}` e a resposta do `POST /locacoes` passam a incluir `returned_at` e `returned_by`.
- App: `locacoes.py` (validador), `locacoes_client.py`, `locacoes_state.py`, `locacoes_ui.py`, `assets/locacoes.css`, testes e `scripts/verify_rental_integrity.py`.
- Documentação: matriz de permissões em `docs/domain-model.md`.
- Homologação com gravações reais em janela autorizada, possivelmente devolvendo as locações 1 e 2.
