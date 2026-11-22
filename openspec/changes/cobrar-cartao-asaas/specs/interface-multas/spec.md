# Spec Delta

## ADDED Requirements

### Requirement: Interface inicia cobrança de cartão sem prometer quitação

Para multa `open`, a interface SHALL oferecer a ação de cobrar por cartão somente quando o backend informar que a operação está disponível. Após o envio, SHALL apresentar o estado retornado (`unknown`, `pending`, `confirmed`, `rejected`, `cancelled` ou equivalente), bloquear duplicidade e deixar claro que estados desconhecidos e pendentes não representam quitação.

#### Scenario: Iniciar cobrança
- **WHEN** o usuário autorizado confirma uma cobrança de cartão válida
- **THEN** a interface apresenta a tentativa e seu estado atual
- **AND** não exibe a multa como quitada antes da confirmação do backend

#### Scenario: Cobrança pendente
- **WHEN** a cobrança aguarda confirmação do Asaas
- **THEN** a interface informa que o pagamento está pendente e permite consultar o estado
- **AND** mantém o saldo da multa visível

#### Scenario: Cobrança recusada
- **WHEN** o backend informa recusa ou cancelamento
- **THEN** a interface exibe erro compreensível e mantém a multa aberta
- **AND** não oferece uma confirmação financeira falsa

#### Scenario: Resultado desconhecido
- **WHEN** o backend informa `unknown`
- **THEN** a interface orienta o usuário a aguardar reconciliação administrativa
- **AND** não oferece repetir a chamada externa nem apresenta link inexistente

### Requirement: Interface não manipula dados sensíveis de cartão

A interface SHALL usar somente o fluxo seguro retornado pelo backend ou pelo Asaas e SHALL NOT armazenar, enviar ou exibir chave API, CVV, número completo de cartão ou tokens secretos. Erros exibidos SHALL ser sanitizados e não poderão conter payload bruto do provedor.

#### Scenario: Resposta com segredo ou payload sensível
- **WHEN** uma resposta externa contém credencial, token secreto ou dado completo de cartão
- **THEN** o backend não o repassa à interface
- **AND** a tela exibe apenas mensagem neutra de falha quando necessário
