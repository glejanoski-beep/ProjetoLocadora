# Spec Delta

## ADDED Requirements

### Requirement: Pagamento confirmado por cartão externo é reconciliado com a cobrança

O pagamento interno com método `credit_card` originado por uma cobrança Asaas SHALL ser criado somente a partir de uma confirmação válida e idempotente da cobrança externa. O registro SHALL manter a referência da cobrança e distinguir sua origem de um pagamento manual, sem aceitar que o formulário declare o pagamento como confirmado.

#### Scenario: Confirmação externa de pagamento
- **WHEN** uma cobrança Asaas vinculada a uma multa é confirmada
- **THEN** o backend cria ou localiza o único pagamento interno correspondente
- **AND** atualiza `paid_cents` e `status` da multa conforme o saldo

#### Scenario: Tentativa manual declara cartão externo
- **WHEN** o cliente tenta registrar pagamento manual informando uma referência Asaas inexistente ou não confirmada
- **THEN** o backend recusa a operação sem alterar a multa

### Requirement: Pagamento externo mantém reconciliação e histórico

O backend SHALL impedir dois pagamentos internos confirmados para a mesma cobrança Asaas, preservar os registros originais e permitir consulta da referência externa por usuários autorizados sem expor credenciais ou dados completos de cartão.

#### Scenario: Evento confirmado repetido
- **WHEN** uma confirmação da mesma cobrança é processada mais de uma vez
- **THEN** o sistema devolve ou mantém o mesmo pagamento interno
- **AND** o saldo da multa não é reduzido novamente

#### Scenario: Consulta de histórico
- **WHEN** um usuário autorizado consulta os pagamentos da multa
- **THEN** consegue distinguir cartão confirmado via Asaas de pagamentos manuais
- **AND** não visualiza segredos do provedor
