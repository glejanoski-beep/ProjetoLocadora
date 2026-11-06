# Spec Delta

## Purpose

Tornar inelegível para nova locação o cliente com multa em aberto e permitir listar as locações de um cliente.

## MODIFIED Requirements

### Requirement: Cliente e exemplar são elegíveis no momento do registro

O backend SHALL exigir:
- cliente existente com situação `active`, sem bloqueio manual ativo e sem multa com status `open`;
- exemplar existente com condição operacional confirmada `available`;
- filme associado existente e `active`;
- ausência de ocupação por locação.

Bloqueio manual ausente SHALL ser tratado como não aplicado, conforme a compatibilidade do cadastro. O backend SHALL revalidar essas condições durante a operação protegida contra concorrência. A verificação de multa em aberto SHALL consultar apenas as multas persistidas do cliente, SHALL ser independente do bloqueio manual e SHALL NOT alterar o cadastro do cliente.

#### Scenario: Seleção válida
- **WHEN** cliente, exemplar e filme atendem às condições no momento da gravação
- **THEN** a locação pode ser registrada após as demais validações

#### Scenario: Seleção inválida ou desatualizada
- **WHEN** o cliente está inativo ou bloqueado, o exemplar não é elegível, ou alguma referência não existe ou foi alterada desde a seleção
- **THEN** o backend recusa sem criar locação nem ocupação

#### Scenario: Cliente com multa em aberto
- **WHEN** o cliente possui ao menos uma multa `open`, mesmo que parcialmente paga
- **THEN** o backend recusa com "Cliente com multa em aberto." sem criar locação nem ocupação

#### Scenario: Multa quitada ou abonada
- **WHEN** todas as multas do cliente estão `paid` ou `waived`
- **THEN** a multa não impede uma nova locação

### Requirement: Consulta paginada das locações registradas

O backend SHALL expor `GET /locacoes` somente para contas autenticadas com papel `member` ou `admin`, conferindo o papel antes de qualquer leitura. A resposta SHALL ser `{items, page, per_page, total}`, ordenada por número decrescente, com `per_page` entre 1 e 50 e erro de entrada para paginação inválida. A consulta SHALL aceitar os filtros opcionais `status` (`active` ou `returned`) e `customer_id` (inteiro positivo), combináveis. Cada item SHALL usar a mesma projeção de 13 campos de `GET /locacoes/{id}` e SHALL NOT incluir CPF, contato, chave de operação ou motivo de condição. A consulta SHALL NOT gravar dados e SHALL NOT depender de `XANO_RENTAL_WRITES_ENABLED`.

#### Scenario: Funcionário consulta a primeira página
- **WHEN** um `member` ou `admin` autenticado solicita `GET /locacoes?page=1&per_page=10`
- **THEN** recebe até 10 locações, mais recentes primeiro, e o total registrado

#### Scenario: Locações de um cliente
- **WHEN** a consulta informa `customer_id`
- **THEN** recebe somente as locações desse cliente, e o total considera o filtro

#### Scenario: Sem autorização
- **WHEN** a requisição não tem token válido ou a conta não é `member`/`admin` ativa
- **THEN** a consulta é recusada antes de ler locações

#### Scenario: Paginação inválida
- **WHEN** `page` é menor que 1 ou `per_page` está fora de 1 a 50
- **THEN** a resposta é erro de entrada, sem dados
