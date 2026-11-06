# Spec Delta

## Purpose

Registrar pagamentos de multas, totais ou parciais, sem ultrapassar o saldo, com idempotência, estorno administrativo rastreável e consulta protegida.

## ADDED Requirements

### Requirement: Pagamento exige conta interna autorizada e trava de escrita

O backend SHALL verificar existência, estado e papel atuais da conta antes de registrar um pagamento. Contas ativas `member` e `admin` SHALL poder registrar pagamentos. O responsável e o instante SHALL ser derivados da sessão e do servidor, sem aceitar esses valores do formulário. A operação SHALL ser recusada sem efeitos enquanto `XANO_RENTAL_WRITES_ENABLED` não for `true` no backend; a interface SHALL respeitar a variável de mesmo nome no app.

#### Scenario: Trava fechada
- **WHEN** a trava de escrita está fechada
- **THEN** o pagamento é recusado sem gravação e a interface mantém a ação indisponível

### Requirement: Pagamento nunca ultrapassa o saldo

O backend SHALL exigir multa existente com status `open`, valor inteiro em centavos maior que zero e menor ou igual ao saldo, e meio `cash`, `pix`, `debit_card` ou `credit_card`. A leitura da multa SHALL ser protegida contra alterações concorrentes. Na mesma unidade atômica, o backend SHALL inserir o pagamento como `confirmed`, atualizar o valor pago e, se o saldo chegar a zero, mudar a multa para `paid`.

#### Scenario: Quitação total
- **WHEN** é pago exatamente o saldo de uma multa `open`
- **THEN** o pagamento fica `confirmed` e a multa fica `paid`

#### Scenario: Valor acima do saldo
- **WHEN** o valor informado é maior que o saldo, zero ou negativo
- **THEN** o pagamento é recusado sem gravação

#### Scenario: Pagamentos simultâneos
- **WHEN** dois pagamentos de 600 centavos chegam ao mesmo tempo para uma multa com saldo de 900
- **THEN** exatamente um é confirmado e o outro é recusado por exceder o saldo restante

#### Scenario: Multa não aberta
- **WHEN** a multa está `paid` ou `waived`
- **THEN** o pagamento é recusado sem gravação

### Requirement: Repetição do pagamento permite reconciliar o resultado

Cada tentativa SHALL carregar uma chave de operação única por conta, garantida na persistência. A repetição com a mesma chave e a mesma multa SHALL devolver o pagamento original, sem novo registro. A mesma chave usada para outra multa SHALL ser recusada como conflito. A auditoria `register_payment` SHALL ser registrada uma única vez após o commit.

#### Scenario: Resposta perdida
- **WHEN** a primeira requisição foi confirmada, mas a resposta não chegou, e o app repete com a mesma chave
- **THEN** o backend devolve o mesmo pagamento e a multa não recebe um segundo pagamento

### Requirement: Estorno é administrativo e preserva o histórico

Somente uma conta ativa `admin` SHALL estornar um pagamento `confirmed`, com motivo obrigatório de até 500 caracteres e com a trava de escrita aberta. O estorno SHALL marcar o pagamento como `reversed`, com instante, responsável e motivo, subtrair o valor do total pago e devolver a multa a `open`. Pagamentos SHALL NOT ser apagados nem ter o valor alterado. O estorno de um pagamento de multa `waived` SHALL ser recusado. O estorno SHALL ser idempotente e registrar auditoria `reverse_payment`.

#### Scenario: Estorno de multa quitada
- **WHEN** um `admin` estorna um pagamento de 300 de uma multa `paid` de 300
- **THEN** o pagamento fica `reversed`, a multa volta a `open` e o saldo volta a ser 300

#### Scenario: Estorno negado
- **WHEN** um `member` tenta estornar, o motivo está vazio ou o pagamento já está `reversed`
- **THEN** a operação é recusada sem alterações

### Requirement: Consulta protegida de pagamentos

Contas ativas `member` e `admin` SHALL consultar a lista paginada de pagamentos, filtrável por cliente e por multa, com valor, meio, instante, responsável, situação e dados de estorno, sem CPF nem contatos.

#### Scenario: Histórico do cliente
- **WHEN** a lista é filtrada por um cliente
- **THEN** aparecem somente os pagamentos das multas desse cliente, inclusive os estornados
