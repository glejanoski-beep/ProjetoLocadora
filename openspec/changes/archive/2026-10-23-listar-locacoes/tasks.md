# Tasks

Implementação concluída; endpoint aplicado manualmente no Xano `v1` pelo operador. Sem commit, push ou merge.

## 1. Backend (local)

- [x] 1.1 `xano/xano/api/locacoes/locacoes_GET.xs`: `enforce_role` member antes da leitura, paginação 1–50, ordem decrescente, projeção de 13 campos, sem escrita.
- [x] 1.2 Validador XanoScript e testes estáticos do contrato.
- [x] 1.3 Aplicação manual no Xano `v1` pelo operador (grupo Locações, `GET /locacoes`); resposta real aceita pelo validador do cliente.

## 2. Cliente e estado

- [x] 2.1 `list_rentals(token, page, per_page)`: validação da página e de cada item por `validar_rental`; 404, 429 e respostas inválidas mapeados.
- [x] 2.2 Estado da lista com carga própria (sem bloquear o formulário), paginação, cooldown de 429, descarte após troca de sessão e recarga da primeira página após registro confirmado.

## 3. Interface

- [x] 3.1 Seção "Locações registradas" em coluna fixa (sticky) à direita do formulário a partir de 1180 px e abaixo dele em telas menores: cartões com número, situação, filme, exemplar, cliente, retirada e link "Detalhes" para `/locacoes/{id}`; "Atualizar lista" e paginação.
- [x] 3.2 Estados de carregamento, vazio e erro.

## 4. Validação

- [x] 4.1 `tests/test_locacoes_listagem.py`; suítes completas.
- [x] 4.2 `openspec validate listar-locacoes --strict`.
- [x] 4.3 Conferência somente leitura no navegador com as locações reais 1 e 2: coluna lateral no desktop (1366 px), empilhada em 1000 px e 390 px, sem rolagem horizontal nem erros de JavaScript.
