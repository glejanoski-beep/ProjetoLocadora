# Proposal

## Why

"Relatórios" é o último item da navegação ainda marcado como "Em breve". O escopo inicial (`docs/project-overview.md`, funcionalidades 14 e 15) prevê relatórios de locações (locações, devoluções, atrasos e pagamentos) e de filmes mais alugados, para acompanhar a operação e apoiar decisões de aquisição. Hoje o dashboard mostra só indicadores do momento e os últimos dias, sem escolha de período nem consolidação financeira.

## What Changes

- Página `/relatorios`, somente para `admin`, com filtro de período em horário de Brasília: atalhos "Últimos 7 dias", "Últimos 30 dias", "Este mês" e "Mês anterior", ou datas de início e fim (até 366 dias).
- **Relatório de locações**, no período:
  - retiradas;
  - devoluções, quantas com atraso e o percentual;
  - multas geradas (quantidade e valor);
  - pagamentos recebidos, por meio de pagamento;
  - estornos e abonos.
- **Situação atual**, independente do período: locações ativas, ativas com vencimento ultrapassado e saldo de multas em aberto.
- **Filmes mais alugados**: os 10 filmes com mais retiradas no período, mostrando ao lado a quantidade de exemplares do filme, para não confundir filme com exemplar.
- Backend: um endpoint de leitura `GET /relatorios/operacional` no grupo `Locações`, restrito a `admin`, que agrega os registros persistidos sem gravar nada.
- Navegação: "Relatórios" passa a ser um link. Para `member`, a página informa que o conteúdo é restrito a administradores e não consulta o backend.

**Não objetivos:**
- exportação (CSV ou PDF) e impressão;
- gráficos de série temporal (a movimentação diária já está no dashboard);
- relatórios por cliente ou por funcionário;
- agendamento e envio de relatórios;
- comparação entre períodos.

## Capabilities

### New Capabilities

- `relatorios`: agregação protegida das locações, devoluções, multas, pagamentos e filmes mais alugados por período.
- `interface-relatorios`: página de relatórios com filtro de período e estados de carregamento, erro e vazio.

### Modified Capabilities

- `interface-dashboard`: "Relatórios" sai de "Em breve" e passa a ser um link para `/relatorios`.

## Impact

- Xano (`v1`, publicação somente com autorização): novo `GET /relatorios/operacional` no grupo `Locações`. Não há tabelas novas nem alteração de endpoints existentes.
- App:
  - novos `relatorios.py`, `relatorios_client.py`, `relatorios_state.py`, `relatorios_ui.py` e `assets/relatorios.css`;
  - navegação e rota em `ProjetoLocadora.py`;
  - testes.
- Documentação: `docs/domain-model.md` (matriz de permissões: relatórios para `admin`) e `docs/project-overview.md`.
