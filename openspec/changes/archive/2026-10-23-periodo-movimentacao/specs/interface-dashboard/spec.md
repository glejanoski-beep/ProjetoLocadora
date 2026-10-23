# Spec Delta

## ADDED Requirements

### Requirement: Movimentação com período selecionável

O painel "Movimentação de locações" SHALL oferecer os períodos "7 dias", "14 dias" e "1 mês" (30 dias), iniciando em 14 dias, com o período atual indicado por `aria-pressed`. A troca SHALL recalcular as colunas, o total e os textos do período a partir das locações já carregadas, SHALL NOT fazer nova consulta ao Xano e SHALL NOT alterar os contadores de locações ativas e vencidas. Cada período SHALL exibir uma coluna por dia de Brasília terminando hoje; em 1 mês, o eixo SHALL rotular um dia a cada cinco, incluindo hoje. Valores fora das opções SHALL ser ignorados.

#### Scenario: Troca para 1 mês

- **WHEN** o funcionário seleciona "1 mês"
- **THEN** o gráfico mostra 30 colunas com retiradas e devoluções reais e o total "… em 1 mês", sem nova requisição
