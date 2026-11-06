# Spec Delta

## Purpose

Consolidar, por período, locações, devoluções, multas, pagamentos e filmes mais alugados a partir dos registros persistidos, com acesso restrito a administradores.

## ADDED Requirements

### Requirement: Relatórios exigem administrador e não gravam dados

O backend SHALL verificar existência, estado e papel atuais da conta antes de qualquer leitura e SHALL permitir o relatório somente a contas ativas `admin`. A consulta SHALL NOT gravar dados nem depender de `XANO_RENTAL_WRITES_ENABLED`. As respostas SHALL NOT conter CPF, contatos ou nomes de clientes.

#### Scenario: Membro sem acesso
- **WHEN** uma conta `member` solicita o relatório
- **THEN** a requisição é recusada antes de ler locações, multas ou pagamentos

#### Scenario: Administrador
- **WHEN** uma conta ativa `admin` solicita o relatório de um período válido
- **THEN** recebe os indicadores agregados do período e da situação atual

### Requirement: Período é um intervalo validado

O relatório SHALL receber o período como dois instantes UTC em milissegundos, `from` e `to`, formando o intervalo semiaberto `[from, to)`. O backend SHALL exigir `0 < from < to` e `to − from` de no máximo 366 dias, recusando como erro de entrada qualquer outro valor.

#### Scenario: Período inválido
- **WHEN** `from` é maior ou igual a `to`, ou o intervalo passa de 366 dias
- **THEN** a resposta é erro de entrada, sem dados

### Requirement: Indicadores de locações e financeiros têm definição explícita

No período, o relatório SHALL informar:
- retiradas: locações com retirada no intervalo;
- devoluções: locações com devolução no intervalo;
- devoluções com atraso: devoluções posteriores ao vencimento, sem considerar a tolerância da multa;
- multas geradas: quantidade e valor das multas criadas no intervalo;
- abonos: quantidade e valor abonado das multas abonadas no intervalo;
- pagamentos recebidos: quantidade e valor dos pagamentos registrados no intervalo cujo status atual é `confirmed`, com o valor separado por meio de pagamento;
- estornos: quantidade e valor dos pagamentos estornados no intervalo.

Na situação atual, independente do período, SHALL informar as locações ativas, as ativas com vencimento ultrapassado e o saldo das multas em aberto, junto com o instante de geração. Todos os valores SHALL ser inteiros em centavos.

#### Scenario: Pagamento estornado depois
- **WHEN** um pagamento de 300 centavos registrado no período foi estornado depois
- **THEN** ele não entra nos pagamentos recebidos e aparece nos estornos do período em que foi estornado

#### Scenario: Atraso dentro da tolerância
- **WHEN** uma locação foi devolvida 1 hora após o vencimento, sem gerar multa
- **THEN** ela conta como devolução com atraso e não altera as multas geradas

#### Scenario: Período sem movimento
- **WHEN** não há retiradas, devoluções, multas nem pagamentos no período
- **THEN** os indicadores do período são zero, e a situação atual continua sendo informada

### Requirement: Filmes mais alugados distinguem filme de exemplar

O relatório SHALL informar, para cada filme com pelo menos uma retirada no período, o identificador, o título atual, a quantidade de retiradas no período e a quantidade de exemplares cadastrados do filme. A contagem SHALL ser feita por filme, somando as retiradas de todos os seus exemplares, sem contar exemplares como locações.

#### Scenario: Filme com várias cópias
- **WHEN** um filme com 3 exemplares teve 5 retiradas no período, em exemplares diferentes
- **THEN** ele aparece com 5 locações e 3 exemplares
