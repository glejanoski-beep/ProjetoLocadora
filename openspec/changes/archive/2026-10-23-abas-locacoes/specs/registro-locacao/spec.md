# Spec Delta

## ADDED Requirements

### Requirement: Lista de locações separada em ativas e devolvidas

A lista "Locações registradas" SHALL oferecer as abas "Ativas" e "Devolvidas", iniciando em "Ativas", com o filtro aplicado pelo endpoint `GET /locacoes` por meio do parâmetro opcional `status` (`active` ou `returned`), preservando a paginação de 10 e a ordem mais recente primeiro. Cada aba SHALL exibir a contagem real quando conhecida. O endpoint SHALL recusar outros valores de `status` como erro de entrada e, sem `status`, SHALL listar todas as locações como antes. Cada locação SHALL aparecer em uma linha compacta e clicável com número, filme, cliente, exemplar, data de retirada (ativas) ou de devolução (devolvidas) e o selo "Vencida" quando ativa com vencimento ultrapassado. O cliente SHALL rejeitar uma página cujo item não corresponda à aba pedida.

#### Scenario: Troca de aba

- **WHEN** o funcionário seleciona "Devolvidas"
- **THEN** a lista mostra somente locações devolvidas, da mais recente para a mais antiga, a partir da primeira página

#### Scenario: Depois da devolução

- **WHEN** uma devolução é confirmada com sucesso
- **THEN** o app abre a lista na aba "Devolvidas" com o aviso "Locação #N devolvida."
- **AND** uma devolução com resultado desconhecido ou recusada permanece no detalhe da locação
