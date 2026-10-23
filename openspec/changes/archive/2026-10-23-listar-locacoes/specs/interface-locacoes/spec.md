# Spec Delta

## ADDED Requirements

### Requirement: Locações registradas na tela de registro

A tela `/locacoes/nova` SHALL manter o formulário de registro e exibir a seção persistente "Locações registradas" em coluna à direita do formulário em telas largas e abaixo dele em telas estreitas, com as locações obtidas de `GET /locacoes`, mais recentes primeiro, em páginas de 10. Cada linha SHALL mostrar número, filme e exemplar, cliente, retirada no horário de Brasília, situação ("Ativa", "Devolvida" e indicação de vencimento ultrapassado para locação ativa) e uma ação que abre o detalhe em `/locacoes/{id}`. A seção SHALL ter estados distintos de carregamento, lista vazia e erro, e uma falha da lista SHALL NOT bloquear nem apagar o formulário. Após um registro confirmado, a seção SHALL recarregar a primeira página. A seção SHALL NOT exibir dados fictícios nem oferecer devolução.

#### Scenario: Locação recém-registrada aparece na lista
- **WHEN** o registro é confirmado pelo backend
- **THEN** a seção recarrega a primeira página e a nova locação aparece com link para o detalhe

#### Scenario: Locações antigas por página
- **WHEN** existem mais de 10 locações
- **THEN** a seção oferece "Anteriores" e "Próximas", sem requisição fora dos limites

#### Scenario: Listagem indisponível
- **WHEN** o endpoint de listagem não responde, retorna 404 ou dados inválidos
- **THEN** a seção exibe erro próprio, sem linhas, e o formulário continua utilizável

#### Scenario: Nenhuma locação
- **WHEN** o backend retorna página vazia
- **THEN** a seção informa "Nenhuma locação registrada", sem tratar como erro

#### Scenario: Limite de requisições
- **WHEN** a listagem recebe 429
- **THEN** a seção informa a espera e não envia nova consulta antes do `Retry-After`
