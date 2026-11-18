# Design

## Context

O projeto possui pagamentos internos de multas e aceita `credit_card` como método manual, mas não possui entidade, endpoint ou integração Asaas. O backend Xano é a autoridade para saldo, autorização e auditoria; o Reflex não pode ser tratado como mecanismo de segurança. A motivação e o escopo funcional estão em `proposal.md`, e os contratos estão nos deltas de `specs/` desta change.

## Goals / Non-Goals

**Goals:**

- Permitir que um usuário interno autorizado gere um Checkout hospedado pelo Asaas para uma multa aberta.
- Persistir a tentativa, o identificador externo e a máquina de estados necessária para reconciliar webhooks.
- Confirmar o pagamento interno somente a partir de evento válido do Asaas.
- Garantir idempotência por operação local e por evento externo, preservando histórico.
- Manter a chave Asaas e o segredo do webhook somente no ambiente/backend.

**Non-Goals:**

- Capturar número, validade, CVV ou outros dados brutos de cartão no Reflex ou no Xano.
- Implementar recorrência, parcelamento, Pix, boleto ou assinatura.
- Alterar o fluxo já existente de pagamentos manuais.
- Usar a URL de retorno do navegador como confirmação financeira.

## Decisions

### 1. Usar Asaas Checkout hospedado

O Xano criará um Checkout do Asaas com valor, descrição e contexto da multa, armazenará o `checkout.id` e entregará ao Reflex apenas o link público de pagamento. O pagador informará o cartão na página hospedada pelo Asaas.

Essa opção reduz a exposição a dados de cartão e evita que o frontend precise manipular PAN/CVV. O processamento direto pela API foi considerado, mas exigiria transportar dados sensíveis, HTTPS estrito, tratamento de `remoteIp` e maior responsabilidade de conformidade. A tokenização também foi considerada, mas depende de habilitação em produção e não é necessária para uma cobrança avulsa.

### 2. Webhook como fonte de confirmação

O endpoint público de webhook validará o header secreto configurado no Asaas, localizará a tentativa pelo identificador externo e processará eventos de Checkout de forma idempotente usando o `event.id`. A URL `successUrl` será apenas navegação; não confirmará o pagamento.

Eventos de criação, pagamento, cancelamento e expiração serão convertidos para estados locais monotônicos. Um evento atrasado não poderá regredir uma cobrança confirmada. A atualização do Checkout, criação do pagamento interno e atualização da multa ocorrerão numa unidade transacional do Xano quando o evento for confirmatório.

### 3. Cliente Asaas criado ou vinculado automaticamente

O backend localizará um vínculo Asaas persistido para o cliente da locadora e, se não existir, criará o cliente no Asaas com os dados mínimos permitidos e gravará somente o identificador externo. A criação deverá ser idempotente e não duplicar clientes quando houver repetição ou timeout.

### 4. Modelo local separado para tentativa e pagamento

Será criada uma entidade de tentativa de cobrança, relacionada à multa, cliente, usuário solicitante e operação idempotente, com valor em centavos, `checkout_id`, estado local, timestamps, referência do último evento e metadados mínimos. O pagamento existente continuará representando somente valor confirmado.

Um índice único deverá impedir duas tentativas ativas para a mesma operação. Outro vínculo único deverá impedir mais de um pagamento confirmado para o mesmo Checkout. O modelo não armazenará payload bruto, segredo, dados do cartão ou resposta integral do Asaas.

### 5. Estados e reconciliação

O fluxo local usará estados equivalentes a `pending`, `confirmed`, `cancelled`, `expired` e `reversed`, com mapeamento documentado dos eventos Asaas. Apenas a transição para `confirmed` poderá criar um pagamento interno `credit_card` e atualizar `paid_cents`. Falhas de rede após criação serão resolvidas por repetição da mesma chave e consulta/reconciliação do Checkout, nunca por uma nova operação cega.

### 6. Segurança e permissões

O início da cobrança exigirá conta ativa `member` ou `admin`, multa aberta, saldo válido e trava de escrita habilitada. O webhook não dependerá de sessão de usuário, mas terá autenticação própria do Asaas e não aceitará identificadores financeiros fornecidos por um navegador como prova de pagamento. Auditorias registrarão somente ação, resultado, usuário quando conhecido, multa, tentativa e referência externa não secreta.

### 7. Implantação gradual

Primeiro serão publicadas as tabelas e funções de reconciliação compatíveis com o fluxo atual. Depois serão publicados endpoints e interface com a funcionalidade protegida por configuração de habilitação. A homologação usará Sandbox, eventos duplicados e falhas simuladas antes de qualquer chave de produção.

## Risks / Trade-offs

- **[Webhook atrasado ou duplicado]** → Persistir `event.id`, aplicar transições monotônicas e usar operações idempotentes.
- **[Timeout após criação do Checkout]** → Repetir a mesma chave e consultar/reconciliar o identificador externo antes de criar outra tentativa.
- **[Usuário abre a URL de retorno sem pagar]** → Nunca confirmar pela navegação; confirmar somente por webhook.
- **[Chave ou segredo exposto em logs]** → Sanitizar erros, não persistir payload bruto e testar respostas/logs sem credenciais.
- **[Saldo alterado enquanto o Checkout está aberto]** → Reservar a operação local, validar o saldo no início e reconciliar antes da confirmação; recusar confirmação incompatível sem alterar além do saldo disponível.
- **[Limitações de produção da tokenização]** → Não depender de tokenização nesta change; usar Checkout hospedado.
- **[Checkout expira enquanto o pagador está no fluxo]** → Mostrar estado expirado e permitir iniciar uma nova tentativa com nova chave, preservando a tentativa anterior.

## Migration Plan

1. Criar e validar o modelo de tentativa, índices e estados sem alterar pagamentos existentes.
2. Publicar funções de cliente Asaas, autenticação do webhook, criação idempotente e reconciliação.
3. Criar e publicar um endpoint Xano público para webhook, configurar o segredo e registrar os eventos necessários no Asaas Sandbox.
4. Publicar endpoints e Reflex com a funcionalidade desabilitada por padrão.
5. Habilitar para usuários autorizados em homologação e executar testes financeiros/concorrência.
6. Habilitar em produção somente após revisão do segredo, permissões da chave e evidências do Sandbox.

Rollback: desabilitar a feature flag e interromper novas cobranças; manter tentativas e pagamentos já confirmados para reconciliação. Não apagar registros nem reverter automaticamente valores financeiros. Se necessário, corrigir por fluxo administrativo de estorno já existente.
