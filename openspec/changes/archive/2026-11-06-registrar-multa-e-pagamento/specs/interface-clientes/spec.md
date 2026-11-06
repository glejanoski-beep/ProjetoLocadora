# Spec Delta

## Purpose

Substituir as abas "Em breve" do detalhe do cliente pelo histórico real de locações, multas e pagamentos.

## RENAMED Requirements

- FROM: `### Requirement: Histórico e pendências permanecem sem dados até os domínios de origem`
- TO: `### Requirement: Histórico e pendências apresentam dados reais do cliente`

## MODIFIED Requirements

### Requirement: Histórico e pendências apresentam dados reais do cliente

O detalhe SHALL exibir a seção "Histórico e pendências" com as abas "Locações", "Multas" e "Pagamentos", todas habilitadas e carregadas sob demanda para o cliente exibido:
- "Locações" SHALL listar as locações do cliente (`GET /locacoes?customer_id`), com filme, exemplar, retirada, vencimento, situação e link para o detalhe;
- "Multas" SHALL listar as multas do cliente, com dias, valor, pago, saldo, situação e link para `/multas/{id}`;
- "Pagamentos" SHALL listar os pagamentos do cliente, com valor, meio, instante, responsável e situação, inclusive os estornados.

Acima das abas, SHALL ser exibido o saldo em aberto do cliente e, havendo multa `open`, o aviso "Novas locações bloqueadas até a quitação". Cada aba SHALL ter paginação, estado vazio, erro com "Tentar novamente" e tratamento de 429 sem novas tentativas automáticas. A seção SHALL NOT exibir valores, saldos, listas ou registros fictícios, e SHALL descartar os dados ao trocar de cliente ou de sessão.

#### Scenario: Cliente sem histórico
- **WHEN** o cliente não tem locações, multas nem pagamentos
- **THEN** cada aba informa a ausência de registros, e o saldo em aberto é "R$ 0,00"

#### Scenario: Cliente com multa em aberto
- **WHEN** o cliente possui uma multa `open` com saldo de 600 centavos
- **THEN** o detalhe mostra saldo de "R$ 6,00" e o aviso de bloqueio de novas locações
