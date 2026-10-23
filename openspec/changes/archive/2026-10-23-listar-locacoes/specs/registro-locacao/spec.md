# Spec Delta

## ADDED Requirements

### Requirement: Consulta paginada das locações registradas

O backend SHALL expor `GET /locacoes` somente para contas autenticadas com papel `member` ou `admin`, conferindo o papel antes de qualquer leitura. A resposta SHALL ser `{items, page, per_page, total}`, ordenada por número decrescente, com `per_page` entre 1 e 50 e erro de entrada para paginação inválida. Cada item SHALL usar a mesma projeção de 13 campos de `GET /locacoes/{id}` e SHALL NOT incluir CPF, contato, chave de operação ou motivo de condição. A consulta SHALL NOT gravar dados e SHALL NOT depender de `XANO_RENTAL_WRITES_ENABLED`.

#### Scenario: Funcionário consulta a primeira página
- **WHEN** um `member` ou `admin` autenticado solicita `GET /locacoes?page=1&per_page=10`
- **THEN** recebe até 10 locações, mais recentes primeiro, e o total registrado

#### Scenario: Sem autorização
- **WHEN** a requisição não tem token válido ou a conta não é `member`/`admin` ativa
- **THEN** a consulta é recusada antes de ler locações

#### Scenario: Paginação inválida
- **WHEN** `page` é menor que 1 ou `per_page` está fora de 1 a 50
- **THEN** a resposta é erro de entrada, sem dados
