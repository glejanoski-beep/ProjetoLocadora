# Proposal

## Why

A devolução já identifica atraso (`returned_at > due_at`), mas não gera nenhuma consequência: não há multa, saldo, pagamento nem bloqueio por inadimplência. O frontend exibe "Multas" (navegação), "Multas pendentes" (dashboard) e as abas "Locações / Multas / Pagamentos" do cliente como "Em breve". O `docs/domain-model.md` deixa o cálculo, a tolerância e o cancelamento "a definir em especificação própria". Esta change define a política e implementa o ciclo multa → pagamento → quitação.

## What Changes

- **Política de multa por atraso** (valores em centavos, configuráveis no Xano):
  - diária de **R$ 3,00** por dia de atraso;
  - **tolerância de 2 horas** após o vencimento, sem multa;
  - ultrapassada a tolerância, os dias contam a partir do vencimento, em blocos de 24 h arredondados para cima;
  - **teto de 30 diárias (R$ 90,00)** por locação.
- **Geração automática** da multa na mesma transação da devolução atrasada, com retrato da política usada (diária, tolerância, teto, dias). Mudanças posteriores na política não alteram multas já geradas.
- **Pagamentos** totais ou parciais, registrados por `member` ou `admin`, sem ultrapassar o saldo, com meio informado (dinheiro, Pix, cartão de débito, cartão de crédito) e sem integração com meios de pagamento.
- **Ajustes administrativos rastreáveis** (somente `admin`, com motivo): estorno de pagamento e abono do saldo restante de uma multa. Nada é apagado.
- **Bloqueio financeiro**: cliente com multa em aberto não pode iniciar nova locação, de forma independente do bloqueio manual.
- **Interface**:
  - página `/multas` com lista, detalhe e registro de pagamento;
  - item "Multas" ativo na navegação;
  - card "Multas pendentes" com dados reais;
  - abas "Locações", "Multas" e "Pagamentos" do cliente com dados reais;
  - multa estimada na confirmação de devolução e multa gerada no detalhe da locação.
- Pagamentos, estornos e abonos usam a trava de escrita existente `XANO_RENTAL_WRITES_ENABLED` (app e Xano), a mesma da locação e da devolução. A Metadata API não gerencia variáveis do workspace, e uma trava única evita configuração manual adicional no painel.

**Não objetivos:**
- integração com gateway e emissão de recibo fiscal;
- multa por avaria ou perda, e cobrança de valor de locação;
- alteração manual do valor da multa (só abono);
- geração retroativa para devoluções feitas antes da publicação;
- juros e correção;
- relatórios ("Relatórios" continua "Em breve");
- notificação ao cliente.

## Capabilities

### New Capabilities

- `multas`: cálculo, geração atômica na devolução, consulta, abono administrativo e resumo.
- `pagamentos-multa`: registro idempotente de pagamento, quitação, estorno administrativo e consulta.
- `interface-multas`: página de multas, registro de pagamento, estorno e abono na interface.

### Modified Capabilities

- `devolucao-locacao`: a unidade atômica da devolução passa a incluir a multa, e a interface mostra a multa estimada e a gerada.
- `registro-locacao`: o cliente com multa em aberto passa a ser inelegível, e a listagem aceita filtro por cliente.
- `interface-dashboard`: "Multas" sai de "Em breve", e o card "Multas pendentes" passa a ter dados reais.
- `interface-clientes`: as abas de histórico passam a mostrar dados reais.

## Impact

- Xano (`v1`, publicação somente com autorização):
  - tabelas novas `fine` e `payment`;
  - função `locacoes/calculate_late_fine`;
  - endpoints novos `GET /multas`, `GET /multas/{id}`, `GET /multas/resumo`, `GET /multas/politica`, `POST /multas/{id}/pagamentos`, `POST /multas/{id}/abono`, `GET /pagamentos` e `POST /pagamentos/{id}/estorno`;
  - endpoints alterados: `POST /locacoes/{id}/devolucao` (gera a multa e devolve `fine`), `POST /locacoes` (bloqueio financeiro) e `GET /locacoes` (filtro `customer_id`);
  - variáveis opcionais `XANO_FINE_DAILY_CENTS`, `XANO_FINE_GRACE_MINUTES` e `XANO_FINE_CAP_CENTS` (ausentes = valores padrão).
- App:
  - novos `multas.py`, `multas_client.py`, `multas_state.py`, `multas_ui.py` e `assets/multas.css`;
  - ajustes em `locacoes_*`, `dashboard*`, no detalhe do cliente em `ProjetoLocadora.py`, em `config.py` e nos testes.
- Documentação: `docs/domain-model.md` (política, invariantes e matriz) e `docs/project-overview.md`.
