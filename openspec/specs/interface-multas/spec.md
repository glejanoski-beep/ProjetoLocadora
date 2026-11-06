# interface-multas Specification

## Purpose
Oferecer no backoffice Reflex a consulta de multas, o registro de pagamentos e os ajustes administrativos, usando somente dados persistidos.

## Requirements

### Requirement: Página de multas lista dados reais por situação

A rota `/multas` SHALL exigir sessão válida e exibir as abas "Em aberto" (padrão), "Quitadas", "Abonadas" e "Todas". Cada linha SHALL mostrar cliente, filme e exemplar, data da devolução, dias de atraso, valor, valor pago e saldo. Multa `open` com valor pago maior que zero SHALL ser identificada como "Parcial". Valores SHALL ser formatados como `R$ 1.234,56` a partir de centavos. A página SHALL ter paginação, estados de carregamento, lista vazia, erro com "Tentar novamente" e limite de requisições (429) sem novas tentativas automáticas, e SHALL NOT exibir valores fictícios.

#### Scenario: Lista vazia
- **WHEN** não há multas em aberto
- **THEN** a aba informa "Nenhuma multa em aberto." sem valores de exemplo

### Requirement: Detalhe da multa e registro de pagamento

O detalhe SHALL apresentar:
- locação (com link), cliente, vencimento e devolução;
- política aplicada (dias, diária, tolerância e teto);
- valor, pago, abonado e saldo;
- lista de pagamentos com meio, instante, responsável e situação.

Para multa `open`, SHALL oferecer "Registrar pagamento", com valor sugerido igual ao saldo e editável, escolha do meio e confirmação explícita. A interface SHALL validar valor positivo e não superior ao saldo antes do envio, gerar uma chave por tentativa, impedir envio duplicado e tratar timeout ou resposta inválida como resultado desconhecido, com repetição da mesma chave. Com a trava de escrita (`XANO_RENTAL_WRITES_ENABLED`) fechada, SHALL exibir aviso neutro e manter a ação indisponível.

#### Scenario: Pagamento confirmado
- **WHEN** o usuário confirma um pagamento válido
- **THEN** a tela apresenta o pagamento e o saldo retornados pelo backend

#### Scenario: Saldo alterado por outra pessoa
- **WHEN** o backend recusa o pagamento por exceder o saldo
- **THEN** a tela informa o conflito e recarrega o detalhe

### Requirement: Ajustes administrativos exigem motivo e confirmação

Somente para `admin`, o detalhe SHALL oferecer "Estornar" em cada pagamento `confirmed` de multa não abonada e "Abonar saldo" em multa `open`. As duas ações SHALL exigir motivo de até 500 caracteres e confirmação explícita, informando que a operação fica registrada em nome do usuário. Para `member`, essas ações SHALL NOT ser exibidas. A interface não é mecanismo de segurança: o backend SHALL continuar recusando essas operações para `member`.

#### Scenario: Membro no detalhe
- **WHEN** um `member` abre o detalhe de uma multa
- **THEN** vê "Registrar pagamento", mas não vê "Estornar" nem "Abonar saldo"

### Requirement: Sessão isolada

Após logout, troca de conta ou perda de autorização, respostas pendentes de multas e pagamentos SHALL ser descartadas, e os dados exibidos SHALL ser limpos.

#### Scenario: Logout com requisição pendente
- **WHEN** o usuário sai enquanto um pagamento aguarda resposta
- **THEN** a resposta é ignorada e nenhum dado da sessão anterior permanece na tela
