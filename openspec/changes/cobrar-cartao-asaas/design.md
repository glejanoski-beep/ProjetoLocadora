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

### 2. Webhook como fonte de confirmação e estorno

O endpoint público de webhook validará o header secreto configurado no Asaas e processará os eventos de Checkout de forma idempotente usando o `event.id`. `CHECKOUT_PAID`, `CHECKOUT_CANCELED` e `CHECKOUT_EXPIRED` identificam a tentativa pelo `checkout.id`. A URL `successUrl` será apenas navegação; não confirmará o pagamento.

O Asaas envia estornos pelo evento `PAYMENT_REFUNDED`, que contém o pagamento e seu `externalReference`, em vez de um `checkout.id`. O sistema guardará esse `externalReference` no registro local e o usará para localizar o Checkout e reverter o pagamento original sem alterar seu valor. O payload completo do provedor não será persistido.

Eventos de criação, pagamento, cancelamento e expiração serão convertidos para estados locais monotônicos. Um evento atrasado não poderá regredir uma cobrança confirmada. A atualização do Checkout, criação do pagamento interno e atualização da multa ocorrerão numa unidade transacional do Xano quando o evento for confirmatório.

### 3. Cliente Asaas criado ou vinculado automaticamente

O backend localizará um vínculo Asaas persistido para o cliente da locadora e, se não existir, criará o cliente no Asaas com os dados mínimos permitidos e gravará somente o identificador externo. A criação deverá ser idempotente e não duplicar clientes quando houver repetição ou timeout.

### 4. Modelo local separado para tentativa e pagamento

Será criada uma entidade de tentativa de cobrança, relacionada à multa, cliente, usuário solicitante e operação idempotente, com valor em centavos, `checkout_id` opcional, estado local, timestamps, referência do último evento e metadados mínimos. O estado `unknown` representa uma chamada externa cujo resultado não pôde ser confirmado. O pagamento existente continuará representando somente valor confirmado.

Um índice único deverá impedir duas tentativas ativas para a mesma operação. Outro vínculo único deverá impedir mais de um pagamento confirmado para o mesmo Checkout. O modelo não armazenará payload bruto, segredo, dados do cartão ou resposta integral do Asaas.

### 5. Estados e reconciliação

O fluxo local usará estados `unknown`, `pending`, `confirmed`, `rejected`, `cancelled`, `expired` e `reversed`, com mapeamento documentado dos eventos Asaas. Apenas a transição para `confirmed` poderá criar um pagamento interno `credit_card` e atualizar `paid_cents`. A tentativa será gravada como `unknown` antes do POST ao Asaas. Se houver timeout ou falha ambígua, a repetição da mesma chave apenas devolverá a reserva local e nunca fará outro POST.

O Asaas não documenta consulta de Checkout por ID ou referência. Por isso, a reconciliação será administrativa: um endpoint restrito a `admin` lista tentativas desconhecidas com referência externa, cliente e valor. O administrador localizará o Checkout no painel Asaas pela `externalReference`, conferirá cliente e valor e enviará o ID, o valor conferido e uma justificativa ao endpoint protegido. O backend validará referência e valor contra a tentativa e registrará a auditoria. Essa associação só move `unknown` para `pending`; nunca confirma pagamento. O webhook autenticado continua sendo a única fonte de confirmação. Um evento de Checkout recebido antes da associação poderá ser reprocessado pelo Asaas após o endpoint registrar falha.

### 6. Segurança e permissões

O início da cobrança exigirá conta ativa `member` ou `admin`, multa aberta, saldo válido e trava de escrita habilitada. O webhook não dependerá de sessão de usuário, mas terá autenticação própria do Asaas e não aceitará identificadores financeiros fornecidos por um navegador como prova de pagamento. Auditorias registrarão somente ação, resultado, usuário quando conhecido, multa, tentativa e referência externa não secreta.

### 7. Configuração e rollback

O backend recebe `ASAAS_API_KEY`, `ASAAS_WEBHOOK_TOKEN`, `ASAAS_API_BASE_URL`, `ASAAS_CHECKOUT_ENABLED` e `ASAAS_CALLBACK_BASE_URL` como variáveis de ambiente. Durante desenvolvimento e homologação, a base deve apontar para o Sandbox; a feature permanece desabilitada quando `ASAAS_CHECKOUT_ENABLED` não estiver explicitamente habilitada. Os arquivos versionados contêm somente os nomes dessas variáveis, nunca os valores dos segredos.

Para rollback, desabilitar `ASAAS_CHECKOUT_ENABLED` e interromper novas tentativas. Manter registros de cobrança, pagamento, estorno e evento para reconciliação; corrigir fatos financeiros somente pelo fluxo administrativo de estorno, sem apagar histórico.

### 8. Implantação gradual

Primeiro serão publicadas as tabelas e funções de reconciliação compatíveis com o fluxo atual. Depois serão publicados endpoints e interface com a funcionalidade protegida por configuração de habilitação. A homologação usará Sandbox, eventos duplicados e falhas simuladas antes de qualquer chave de produção.

## Risks / Trade-offs

- **[Webhook atrasado ou duplicado]** → Persistir `event.id`, aplicar transições monotônicas e usar operações idempotentes.
- **[Timeout após criação do Checkout]** → A reserva persiste em `unknown`; a mesma chave não repete o POST. Administrador confere a `externalReference` e o valor no painel Asaas, associa o ID e registra justificativa; pagamento só é confirmado por webhook.
- **[Usuário abre a URL de retorno sem pagar]** → Nunca confirmar pela navegação; confirmar somente por webhook.
- **[Chave ou segredo exposto em logs]** → Sanitizar erros, não persistir payload bruto e testar respostas/logs sem credenciais.
- **[Saldo alterado enquanto o Checkout está aberto]** → Reservar a operação local, validar o saldo no início e reconciliar antes da confirmação; recusar confirmação incompatível sem alterar além do saldo disponível.
- **[Limitações de produção da tokenização]** → Não depender de tokenização nesta change; usar Checkout hospedado.
- **[Checkout expira enquanto o pagador está no fluxo]** → Mostrar estado expirado e permitir iniciar uma nova tentativa com nova chave, preservando a tentativa anterior.

## Migration Plan

1. Criar e validar o modelo de tentativa, índices e estados sem alterar pagamentos existentes.
2. Publicar funções de cliente Asaas, autenticação do webhook, reserva idempotente e reconciliação administrativa.
3. Criar e publicar um endpoint Xano público para webhook, configurar o segredo e registrar os eventos necessários no Asaas Sandbox.
4. Publicar endpoints e Reflex com a funcionalidade desabilitada por padrão.
5. Habilitar para usuários autorizados em homologação e executar testes financeiros/concorrência.
6. Habilitar em produção somente após revisão do segredo, permissões da chave e evidências do Sandbox.

Rollback: seguir a configuração de rollback descrita acima; manter tentativas e pagamentos confirmados para reconciliação.
