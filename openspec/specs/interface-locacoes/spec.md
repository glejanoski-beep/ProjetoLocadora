# interface-locacoes Specification

## Purpose
Interface Reflex para registrar e consultar locações com dados reais, na identidade visual do CineGestão, sem simular operações nem contornar as validações do backend.

## Requirements

### Requirement: Registro organizado em três etapas

A tela `/locacoes/nova` SHALL apresentar, em uma coluna, as etapas "Selecionar cliente", "Selecionar exemplar" e "Vencimento e confirmação", com indicador de progresso derivado das mesmas pendências que controlam a confirmação. Clientes e exemplares SHALL ser cartões acessíveis por teclado, com a seleção destacada; clientes inativos ou bloqueados SHALL aparecer desabilitados com o motivo e CPF mascarado. As listas SHALL usar páginas de 10 itens e exibir paginação somente quando houver mais de uma página. Atualizar ou paginar uma lista SHALL NOT apagar a seleção da outra. O resumo SHALL apresentar o vencimento como `dd/mm/aaaa às hh:mm` no horário de Brasília.

#### Scenario: Pendências visíveis antes da confirmação
- **WHEN** falta cliente, exemplar ou vencimento válido e futuro
- **THEN** a tela lista o que falta e "Confirmar locação" permanece desabilitado

#### Scenario: Gravações bloqueadas
- **WHEN** `XANO_RENTAL_WRITES_ENABLED` não é `true`
- **THEN** a tela exibe aviso neutro explicando o bloqueio, sem apresentá-lo como sucesso, e a confirmação permanece indisponível

#### Scenario: Conferência de condição separada
- **WHEN** um admin acessa a tela
- **THEN** a conferência de condição aparece em seção recolhida "Ação administrativa", fora das etapas, e a lista completa de exemplares só é consultada quando solicitada

### Requirement: Limite de requisições é informado sem novas tentativas automáticas

Quando o Xano responder 429, a interface SHALL informar o limite do plano e o tempo de espera indicado (20 s quando o cabeçalho `Retry-After` não estiver disponível), SHALL NOT encerrar a sessão e SHALL NOT enviar nova leitura antes desse prazo, inclusive pela ação manual "Tentar novamente".

#### Scenario: Nova tentativa antes do prazo
- **WHEN** o usuário aciona "Tentar novamente" antes de terminar a espera
- **THEN** nenhuma requisição é enviada e a tela informa quantos segundos faltam

### Requirement: Locação pode ser aberta pelo número

As telas de registro e de detalhe SHALL oferecer o campo "Abrir locação pelo número". Somente inteiros positivos SHALL ser aceitos; outro valor SHALL ser recusado na própria tela, sem navegação nem requisição. A existência da locação SHALL ser confirmada somente pela consulta protegida do backend.

#### Scenario: Número válido
- **WHEN** o usuário informa um inteiro positivo e confirma
- **THEN** a aplicação navega para `/locacoes/{número}`

#### Scenario: Número inválido
- **WHEN** o valor está vazio, não é numérico, é zero ou negativo
- **THEN** a tela informa o formato esperado e não navega

### Requirement: Detalhe apresenta somente dados persistidos

A rota `/locacoes/[rental_id]` SHALL consultar `GET /locacoes/{id}` e apresentar número, situação, cliente, exemplar, filme, retirada, vencimento no horário de Brasília e o número do funcionário responsável, com link para o cadastro do cliente. Quando a locação ativa tiver vencimento anterior ao momento da consulta, SHALL indicar "Vencimento ultrapassado", sem calcular multa ou valor. O detalhe SHALL ser somente de consulta e SHALL NOT oferecer devolução, cancelamento ou alteração.

#### Scenario: Locação existente
- **WHEN** um member ou admin abre o detalhe de uma locação existente
- **THEN** a tela apresenta os dados retornados pelo backend com datas formatadas

#### Scenario: Identificador inválido na rota
- **WHEN** o identificador da rota não é um inteiro positivo
- **THEN** a tela informa número inválido sem consultar o backend

#### Scenario: Locação inexistente
- **WHEN** o backend responde que a locação não existe
- **THEN** a tela informa que a locação daquele número não foi encontrada e não exibe dados anteriores

#### Scenario: Falha de conexão ou de autorização
- **WHEN** a consulta falha por rede, serviço, 401 ou 403
- **THEN** a tela informa a falha específica; 401 encerra a sessão, 403 não exibe dados, e falhas recuperáveis oferecem "Tentar novamente"

#### Scenario: Resposta tardia após troca de sessão
- **WHEN** a sessão muda enquanto a consulta está pendente
- **THEN** a resposta é descartada e não exibe dados na nova sessão

### Requirement: Locações registradas na tela de registro

A tela `/locacoes/nova` SHALL manter o formulário de registro e exibir a seção persistente "Locações registradas" em coluna à direita do formulário em telas largas e abaixo dele em telas estreitas, com as locações obtidas de `GET /locacoes`, mais recentes primeiro, em páginas de 10. Cada linha SHALL mostrar número, filme e exemplar, cliente, retirada no horário de Brasília, situação ("Ativa", "Devolvida" e indicação de vencimento ultrapassado para locação ativa) e uma ação que abre o detalhe em `/locacoes/{id}`. A seção SHALL ter estados distintos de carregamento, lista vazia e erro, e uma falha da lista SHALL NOT bloquear nem apagar o formulário. Após um registro confirmado, a seção SHALL recarregar a primeira página. A seção SHALL NOT exibir dados fictícios nem oferecer devolução.

#### Scenario: Locação recém-registrada aparece na lista
- **WHEN** o registro é confirmado pelo backend
- **THEN** a seção recarrega a primeira página e a nova locação aparece com link para o detalhe

#### Scenario: Locações antigas por página
- **WHEN** existem mais de 10 locações
- **THEN** a seção oferece "Anteriores" e "Próximas", sem requisição fora dos limites

#### Scenario: Listagem indisponível
- **WHEN** o endpoint de listagem não responde, retorna 404 ou dados inválidos
- **THEN** a seção exibe erro próprio, sem linhas, e o formulário continua utilizável

#### Scenario: Nenhuma locação
- **WHEN** o backend retorna página vazia
- **THEN** a seção informa "Nenhuma locação registrada", sem tratar como erro

#### Scenario: Limite de requisições
- **WHEN** a listagem recebe 429
- **THEN** a seção informa a espera e não envia nova consulta antes do `Retry-After`
