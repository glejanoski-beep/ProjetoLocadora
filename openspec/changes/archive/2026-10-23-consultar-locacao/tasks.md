# Tasks

APPLY autorizado somente para esta Change, sem alterações no Xano, sem gravações reais, sem commit, push ou merge.

## 1. Estado

- [x] 1.1 Validar o número da rota antes de consultar o backend; distinguir `invalid`, `notfound`, `error` e `ready` em `detail_state`.
- [x] 1.2 Tratar 401 (encerra a sessão), 403 (sem dados), falha de conexão (com nova tentativa) e 429 (espera do `Retry-After`).
- [x] 1.3 Evento `open_rental` que valida inteiro positivo e navega para `/locacoes/{número}`.
- [x] 1.4 Situação legível e indicação de vencimento ultrapassado derivadas apenas dos campos do contrato.

## 2. Interface

- [x] 2.1 Campo "Abrir locação pelo número" em `/locacoes/nova` e no detalhe.
- [x] 2.2 Detalhe na identidade visual atual, somente de consulta, com estados de carregamento, erro e nova tentativa.

## 3. Verificação

- [x] 3.1 Testes de `load_detail`, `open_rental`, formatação e estrutura da interface (`tests/test_locacoes_detail.py`).
- [x] 3.2 Suítes completas e compilação do app.
- [x] 3.3 Navegador com as locações reais 1 e 2, somente leitura, desktop e celular.
- [x] 3.4 `openspec validate consultar-locacao --strict`.
