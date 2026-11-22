# Spec Delta

## Purpose

Permitir que a locadora crie e acompanhe cobranças de cartão para multas por meio do Asaas, preservando segurança, idempotência, confirmação assíncrona e consistência entre a cobrança externa, o pagamento interno e o saldo da multa.

## ADDED Requirements

### Requirement: Cobrança de cartão usa credencial somente no backend

O sistema SHALL executar chamadas autenticadas ao Asaas somente no backend, usando a credencial configurada no ambiente seguro. A credencial SHALL NOT ser aceita do frontend, retornada em respostas, incluída em logs ou persistida em registros de negócio. O sistema SHALL usar credencial e conta Sandbox durante desenvolvimento e homologação.

#### Scenario: Frontend tenta fornecer credencial
- **WHEN** uma requisição de cobrança contém uma chave Asaas ou credencial adicional enviada pelo cliente
- **THEN** o backend recusa a entrada sem usar a credencial recebida
- **AND** nenhum segredo é gravado ou auditado

#### Scenario: Credencial ausente no backend
- **WHEN** uma cobrança é solicitada sem credencial Asaas configurada no ambiente
- **THEN** a operação é recusada com erro operacional neutro
- **AND** a multa permanece sem alteração

### Requirement: Cobrança é criada para multa aberta e valor válido

O backend SHALL permitir iniciar uma cobrança de cartão somente para uma multa existente em estado `open`, com valor inteiro positivo em centavos, não superior ao saldo atual, cliente identificável e conta interna autorizada. O valor e o cliente SHALL ser derivados da multa e da sessão, e não de dados financeiros confiados ao frontend.

#### Scenario: Cobrança válida
- **WHEN** um usuário autorizado solicita cartão para valor igual ou inferior ao saldo de uma multa aberta
- **THEN** o backend cria uma tentativa de cobrança no Asaas e retorna somente os dados necessários para acompanhar ou concluir o pagamento
- **AND** a multa ainda não é marcada como paga

#### Scenario: Multa quitada ou abonada
- **WHEN** uma cobrança é solicitada para uma multa `paid` ou `waived`
- **THEN** o backend recusa a operação sem chamada ao Asaas e sem alteração financeira

### Requirement: Criação de cobrança é idempotente e concorrente

Cada tentativa SHALL possuir uma chave de operação única por conta e multa. Repetições com a mesma chave SHALL devolver a tentativa já criada ou seu resultado atual, sem criar cobrança duplicada no Asaas. Tentativas concorrentes incompatíveis SHALL preservar no máximo uma cobrança ativa para a mesma operação e SHALL recusar valores que excedam o saldo vigente.

#### Scenario: Timeout após chamada externa
- **WHEN** a resposta do Asaas é ambígua ou não chega ao backend
- **THEN** a tentativa local permanece `unknown` e a repetição com a mesma chave devolve essa tentativa sem enviar novo POST
- **AND** nenhuma segunda cobrança é criada automaticamente

#### Scenario: Reconciliação administrativa de tentativa desconhecida
- **WHEN** um administrador consulta a lista protegida de tentativas desconhecidas, localiza o Checkout no painel Asaas e informa o ID, a referência externa correspondente, o valor conferido e uma justificativa
- **THEN** o backend associa o Checkout à tentativa `unknown`, registra a auditoria e muda a tentativa para `pending`
- **AND** a confirmação financeira continua dependendo de webhook autenticado do Asaas

#### Scenario: Duas tentativas simultâneas
- **WHEN** duas requisições tentam cobrar a mesma multa e operação ao mesmo tempo
- **THEN** somente uma tentativa é criada ou ambas observam a mesma tentativa idempotente
- **AND** o saldo não é baixado duas vezes

### Requirement: Estado externo não confirma pagamento prematuramente

O sistema SHALL distinguir tentativa desconhecida (`unknown`), cobrança pendente, cobrança confirmada, cobrança recusada, cancelada e estornada. A multa e o pagamento interno SHALL ser atualizados como quitados somente após confirmação válida do Asaas. Uma cobrança desconhecida, pendente, recusada ou cancelada SHALL NOT criar pagamento confirmado nem reduzir o saldo.

#### Scenario: Cartão pendente
- **WHEN** o Asaas retorna cobrança criada ou aguardando confirmação
- **THEN** a tentativa fica pendente
- **AND** a multa continua com o saldo original

#### Scenario: Resultado externo desconhecido
- **WHEN** o backend não consegue determinar se o Asaas criou o Checkout
- **THEN** registra `unknown` e informa que a tentativa precisa de reconciliação administrativa
- **AND** não oferece nova cobrança para aquela tentativa nem reduz o saldo

#### Scenario: Cartão confirmado
- **WHEN** o backend confirma um status de pagamento válido do Asaas para a tentativa
- **THEN** registra um pagamento interno `confirmed` com método `credit_card`
- **AND** atualiza o saldo da multa uma única vez

#### Scenario: Cartão recusado
- **WHEN** o Asaas informa recusa ou cancelamento antes da confirmação
- **THEN** a tentativa fica recusada ou cancelada
- **AND** nenhum pagamento interno confirmado é criado

### Requirement: Webhook do Asaas é autenticado, idempotente e auditável

O endpoint de webhook SHALL validar a autenticidade conforme o mecanismo oficial configurado para o Asaas, rejeitar eventos inválidos antes de alterar dados e processar cada evento externo de forma idempotente. Eventos recebidos fora de ordem SHALL respeitar a máquina de estados e não permitir regressão de um pagamento confirmado para pendente. O sistema SHALL registrar auditoria mínima sem chave, token, número completo de cartão ou payload sensível.

#### Scenario: Webhook inválido
- **WHEN** o endpoint recebe evento sem autenticação ou com assinatura inválida
- **THEN** responde rejeição sem atualizar cobrança, pagamento ou multa
- **AND** não grava credenciais ou dados sensíveis no log

#### Scenario: Webhook duplicado
- **WHEN** o mesmo evento confirmado é recebido novamente
- **THEN** o endpoint responde de forma idempotente
- **AND** não cria novo pagamento nem repete a atualização do saldo

#### Scenario: Evento atrasado
- **WHEN** chega um evento pendente depois de a cobrança já estar confirmada
- **THEN** o estado confirmado é preservado
- **AND** nenhum valor é revertido sem evento de estorno válido

### Requirement: Estorno externo preserva histórico

Quando um estorno válido do Asaas for recebido para um pagamento interno confirmado, o sistema SHALL marcar o pagamento como `reversed`, registrar instante, responsável sistêmico, referência externa e motivo disponível, e recalcular o saldo da multa conforme as regras existentes. O registro original SHALL permanecer preservado.

#### Scenario: Estorno confirmado pelo Asaas
- **WHEN** o webhook informa estorno de um pagamento confirmado
- **THEN** o pagamento original fica estornado e a multa volta ao saldo correspondente
- **AND** a operação é auditada sem expor credenciais

### Requirement: Cobrança expõe somente dados necessários

As respostas da cobrança SHALL omitir chave Asaas, dados completos de cartão, CVV, tokens secretos e payload bruto do provedor. O sistema SHALL retornar apenas identificadores externos não secretos, estado, valor, vencimento ou instrução pública necessária para o cliente acompanhar o fluxo.

#### Scenario: Consulta da tentativa
- **WHEN** um usuário autorizado consulta uma tentativa de cobrança
- **THEN** recebe estado, valor e identificadores operacionais permitidos
- **AND** não recebe segredo ou dado completo do cartão
