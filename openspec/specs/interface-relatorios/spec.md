# interface-relatorios Specification

## Purpose
Apresentar no backoffice Reflex os relatórios consolidados por período, usando somente dados retornados pelo backend.

## Requirements

### Requirement: Página de relatórios com filtro de período

A rota `/relatorios` SHALL exigir sessão válida. Para `admin`, SHALL oferecer os atalhos "Últimos 7 dias", "Últimos 30 dias" (padrão ao abrir), "Este mês" e "Mês anterior", além de datas de início e fim inclusivas e da ação "Gerar relatório". As datas SHALL ser interpretadas no horário de Brasília (`America/Sao_Paulo`) e convertidas pelo app no intervalo `[00:00 do início, 00:00 do dia seguinte ao fim)`. Período com início posterior ao fim, data inválida ou mais de 366 dias SHALL ser recusado na tela, sem consultar o backend. O cabeçalho SHALL exibir o período ativo e o horário de geração.

#### Scenario: Abertura padrão
- **WHEN** um administrador abre `/relatorios`
- **THEN** o relatório dos últimos 30 dias, incluindo hoje, é gerado automaticamente

#### Scenario: Período manual inválido
- **WHEN** o administrador informa início posterior ao fim
- **THEN** a tela informa o problema e não consulta o backend

### Requirement: Indicadores e ranking apresentam somente dados reais

A página SHALL agrupar os indicadores em "Locações no período" (retiradas, devoluções, devoluções com atraso e o percentual sobre as devoluções), "Financeiro no período" (multas geradas, pagamentos recebidos por meio, estornos e abonos) e "Situação atual" (locações ativas, vencidas e saldo de multas em aberto). Valores monetários SHALL ser formatados como `R$ 1.234,56` a partir de centavos. A página SHALL explicar que a devolução com atraso considera o vencimento, e não a tolerância da multa. "Filmes mais alugados" SHALL listar até 10 filmes, ordenados por retiradas (decrescente) e por título em empate, com "N locações · M exemplares" e barra proporcional ao primeiro colocado. Sem retiradas no período, SHALL exibir "Nenhuma locação no período.". A página SHALL NOT exibir valores de exemplo.

#### Scenario: Percentual de atraso sem devoluções
- **WHEN** não houve devoluções no período
- **THEN** o percentual de atraso é exibido como "—", sem divisão por zero

#### Scenario: Empate no ranking
- **WHEN** dois filmes têm o mesmo número de retiradas
- **THEN** aparecem em ordem alfabética de título

### Requirement: Acesso, estados e sessão

Para `member`, a página SHALL informar "Relatórios disponíveis apenas para administradores." e SHALL NOT consultar o backend. A página SHALL ter estados de carregamento, erro com "Tentar novamente" e limite de requisições (429), sem novas tentativas automáticas. Após logout, troca de conta ou mudança de papel, respostas pendentes SHALL ser descartadas, e os dados exibidos SHALL ser limpos.

#### Scenario: Membro abre a página
- **WHEN** um `member` abre `/relatorios`
- **THEN** vê a mensagem de restrição, e nenhuma requisição de relatório é enviada

#### Scenario: Logout durante o carregamento
- **WHEN** o usuário sai enquanto o relatório é carregado
- **THEN** a resposta é ignorada, e nenhum dado permanece na tela
