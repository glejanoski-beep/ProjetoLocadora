# Tasks

Sem alteração no Xano. Sem commit, push ou merge.

## 1. Estado

- [x] 1.1 `resumir_locacoes`: ativas, vencidas e retiradas/devoluções por dia de Brasília (14 dias), alturas proporcionais e textos no plural.
- [x] 1.2 `load_rentals`: member e admin, reaproveita conferência recente de sessão, até 3 páginas de 50, erros sem valores, sessão recusada limpa e redireciona, resposta tardia descartada.
- [x] 1.3 Participação percentual por gênero.

## 2. Interface

- [x] 2.1 Card "Locações ativas" com estados de carregamento, sucesso e erro; "Multas pendentes" inalterado.
- [x] 2.2 Painel de movimentação com legenda, barras, total do período, "Ver locações" e "Tentar novamente".
- [x] 2.3 Tooltip do dia e destaque do gênero ao passar o cursor ou focar; animação de entrada; `prefers-reduced-motion`.
- [x] 2.4 Entrada do dashboard dispara resumo e locações; "Atualizar" recarrega ambos como eventos separados.

## 3. Validação

- [x] 3.1 `tests/test_dashboard_locacoes.py` e ajustes dos testes do dashboard; suítes completas.
- [x] 3.2 `openspec validate dashboard-locacoes --strict`.
- [x] 3.3 Conferência somente leitura no navegador com as locações reais: card com 2 ativas, 14 colunas com tooltip ao passar o cursor (abre ao lado, sem cobrir a legenda), participação por gênero no hover, celular sem rolagem horizontal e sem erros de JavaScript.
