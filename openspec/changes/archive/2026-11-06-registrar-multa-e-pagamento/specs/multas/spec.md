# Spec Delta

## Purpose

Calcular e registrar a multa por atraso na devolução, com política explícita e configurável, histórico imutável, abono administrativo rastreável e consulta protegida.

## ADDED Requirements

### Requirement: Política de multa por atraso é explícita e configurável

O sistema SHALL calcular a multa por atraso a partir do vencimento (`due_at`) e do instante de devolução gerado pelo servidor (`returned_at`), usando três parâmetros inteiros configurados no backend:
- diária em centavos (`XANO_FINE_DAILY_CENTS`, padrão 300);
- tolerância em minutos (`XANO_FINE_GRACE_MINUTES`, padrão 120);
- teto em centavos (`XANO_FINE_CAP_CENTS`, padrão 9000).

Se o atraso for menor ou igual à tolerância, SHALL NOT haver multa. Caso contrário, os dias de atraso SHALL ser `ceil((returned_at − due_at) / 24 h)` e o valor SHALL ser `min(dias × diária, teto)`. Valores SHALL ser inteiros em centavos, sem ponto flutuante. Parâmetro ausente ou vazio SHALL usar o valor padrão. Parâmetro preenchido e inválido (não numérico, negativo, diária zero ou teto menor que a diária) SHALL fazer a devolução atrasada ser recusada sem efeitos. A devolução sem atraso SHALL NOT depender dessa configuração.

#### Scenario: Devolução dentro da tolerância
- **WHEN** a locação vence às 20:00 e é devolvida às 21:30 do mesmo dia, com tolerância de 120 minutos
- **THEN** nenhuma multa é criada

#### Scenario: Atraso de poucas horas
- **WHEN** a locação vence às 20:00 e é devolvida às 23:00 do mesmo dia
- **THEN** é criada multa de 1 dia, no valor de 300 centavos

#### Scenario: Atraso de vários dias
- **WHEN** a locação é devolvida 49 horas após o vencimento
- **THEN** é criada multa de 3 dias, no valor de 900 centavos

#### Scenario: Teto aplicado
- **WHEN** a locação é devolvida 45 dias após o vencimento
- **THEN** a multa registra 45 dias e o valor de 9000 centavos

#### Scenario: Configuração inválida com atraso
- **WHEN** a devolução está atrasada e algum parâmetro da política está preenchido com valor inválido
- **THEN** a devolução é recusada sem registro, sem alteração de status e sem liberar o exemplar

### Requirement: Multa é gerada atomicamente com a devolução e preserva a política aplicada

A multa SHALL ser criada na mesma unidade atômica da devolução, com status `open`, e SHALL guardar:
- locação e cliente (identificador e nome);
- dias de atraso, diária, tolerância e teto aplicados;
- valor;
- instante e conta responsável.

Cada locação SHALL ter no máximo uma multa por atraso, garantido na persistência. O valor e o retrato da política SHALL NOT ser alterados depois da criação, nem por mudanças posteriores na configuração. Devoluções registradas antes da publicação desta capacidade SHALL NOT gerar multa retroativa.

#### Scenario: Política alterada depois
- **WHEN** a diária configurada muda após a geração de uma multa
- **THEN** a multa existente mantém o valor e a diária originais

#### Scenario: Falha na geração
- **WHEN** a inserção da multa falha antes do commit
- **THEN** a locação continua `active`, sem registro de devolução e com a ocupação preservada

### Requirement: Saldo e situação da multa são consistentes

O saldo SHALL ser `amount_cents − paid_cents − waived_cents` e SHALL ser sempre maior ou igual a zero. A multa SHALL ser:
- `open` enquanto houver saldo e não houver abono;
- `paid` quando o saldo chegar a zero por pagamentos;
- `waived` após o abono do saldo restante.

A multa SHALL ser marcada como `paid` somente com pagamentos confirmados que somem o valor devido.

#### Scenario: Pagamento parcial
- **WHEN** uma multa de 900 centavos recebe um pagamento confirmado de 300
- **THEN** a multa continua `open`, com `paid_cents = 300` e saldo de 600

### Requirement: Abono do saldo é administrativo e rastreável

Somente uma conta ativa `admin` SHALL abonar uma multa `open`, informando motivo obrigatório de até 500 caracteres. O abono SHALL gravar o saldo restante como valor abonado, o instante, o responsável e o motivo, e SHALL mudar o status para `waived`, preservando os pagamentos anteriores e o valor original. O abono SHALL exigir `XANO_RENTAL_WRITES_ENABLED == "true"`, ser idempotente por chave de operação da conta e registrar auditoria `waive_fine`.

#### Scenario: Abono por administrador
- **WHEN** um `admin` abona uma multa de 900 centavos com 300 pagos, informando motivo
- **THEN** a multa fica `waived`, com 600 centavos abonados e o pagamento de 300 preservado

#### Scenario: Abono negado
- **WHEN** um `member` tenta abonar, ou o motivo está vazio, ou a multa não está `open`
- **THEN** a operação é recusada sem alterar a multa

### Requirement: Consulta protegida de multas e resumo

Contas ativas `member` e `admin` SHALL consultar:
- a lista paginada de multas, filtrável por situação, cliente e locação;
- o detalhe da multa, com seus pagamentos;
- o resumo com a quantidade de multas `open` e o saldo total em aberto;
- os parâmetros vigentes da política.

As respostas SHALL NOT incluir CPF nem contatos do cliente. Requisições sem autenticação válida, de contas inativas ou de papel desconhecido SHALL ser recusadas antes da leitura dos dados.

#### Scenario: Resumo real
- **WHEN** existem duas multas `open` com saldos de 300 e 600 centavos
- **THEN** o resumo informa `open_count = 2` e `open_balance_cents = 900`
