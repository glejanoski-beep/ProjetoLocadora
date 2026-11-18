# Proposal

## Why

O projeto atualmente registra `credit_card` apenas como um meio de pagamento interno; ele não cria nem acompanha uma cobrança real no Asaas. A chave do Asaas já está disponível localmente, mas falta um fluxo de cobrança de cartão que preserve a integridade da multa, trate confirmações assíncronas e mantenha as credenciais fora do frontend.

## What Changes

- Criar um fluxo de cobrança de cartão via Asaas para multas abertas, com criação idempotente da cobrança e referência externa persistida.
- Separar o estado da tentativa de cobrança do estado do pagamento confirmado, evitando marcar a multa como paga antes da confirmação do Asaas.
- Processar confirmações, recusas, cancelamentos e estornos por webhook autenticado e idempotente.
- Exibir no backoffice Reflex a ação de cobrar por cartão, o estado da cobrança, erros recuperáveis e a orientação para consultar uma tentativa em andamento.
- Manter o registro manual de pagamentos existentes sem reprocessá-los no Asaas.
- Restringir credenciais, chamadas ao Asaas, transições financeiras e auditoria ao backend Xano; nenhuma chave ou dado sensível de cartão será enviado ao frontend ou gravado em logs.
- Adicionar testes de contrato, idempotência, concorrência, webhook duplicado, falha de rede e transições financeiras.

## Capabilities

### New Capabilities

- `cobranca-cartao-asaas`: criar e acompanhar cobranças de cartão de multas por meio do Asaas, incluindo confirmação por webhook, segurança e reconciliação.

### Modified Capabilities

- `pagamentos-multa`: distinguir pagamentos manuais de cobranças externas, preservar o saldo até a confirmação e registrar referências/status do provedor sem apagar histórico.
- `interface-multas`: oferecer o fluxo de cobrança via cartão e apresentar estados pendentes, confirmados, recusados e falhos sem prometer quitação prematura.

## Impact

- Backend Xano/XanoScript: novas tabelas ou campos de cobrança, funções de integração com Asaas, endpoints protegidos e endpoint de webhook.
- Frontend Reflex: cliente, estado e componentes do detalhe da multa para iniciar e acompanhar a cobrança.
- Dados financeiros: novas invariantes de idempotência, reconciliação, concorrência e preservação de histórico.
- Configuração: leitura da credencial Asaas somente no backend/ambiente seguro; a chave não deve ser exposta pelo `.mcp.json`, Reflex ou respostas da API.
- Integração externa: dependência da API e dos webhooks do Asaas, com Sandbox obrigatório durante homologação.

