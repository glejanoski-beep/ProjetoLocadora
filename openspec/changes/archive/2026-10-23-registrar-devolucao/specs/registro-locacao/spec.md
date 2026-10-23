# Spec Delta

## Purpose

Ajustar o registro de locação para conviver com a devolução: status `returned` e respostas com os dados de devolução.

## MODIFIED Requirements

### Requirement: Datas e status são controlados

O sistema SHALL gerar a retirada no servidor e aceitar vencimento como instante ISO 8601 com offset explícito, convertido para UTC e estritamente posterior à retirada. Interface SHALL apresentar horário de Brasília (`America/Sao_Paulo`) e não preencher prazo comercial inventado. O status inicial SHALL ser `active`; responsável, retirada, status, valor financeiro e devolução SHALL NOT ser campos alteráveis pela entrada desta operação. O status SHALL passar a `returned` somente pela operação de devolução, e retirada e vencimento SHALL permanecer inalterados após a devolução.

#### Scenario: Prazo válido
- **WHEN** o usuário informa vencimento posterior à retirada
- **THEN** o backend persiste os instantes e status `active`, e a confirmação apresenta as datas no horário de Brasília

#### Scenario: Prazo inválido
- **WHEN** o vencimento está ausente, é inválido, não possui offset, ou é igual ou anterior à retirada
- **THEN** a operação é recusada sem gravação

#### Scenario: Status alterado somente pela devolução
- **WHEN** uma locação é devolvida
- **THEN** o status passa a `returned` e retirada e vencimento continuam iguais

### Requirement: Confirmação e auditoria preservam histórico e privacidade

O sistema SHALL oferecer consulta protegida da locação e reconciliação por chave da própria conta. Respostas SHALL conter somente identificação da locação, referências e rótulos necessários de cliente e exemplar, datas, status, responsável e, quando houver, instante e responsável da devolução (`returned_at` e `returned_by`, nulos enquanto `active`), sem CPF completo ou contatos. A criação SHALL registrar auditoria mínima com ação, resultado, usuário e identificador da locação. Falha de auditoria após commit SHALL distinguir gravação confirmada de auditoria pendente. A repetição da criação com a mesma chave SHALL retornar a locação em seu estado atual, inclusive `returned`. Nenhuma exclusão, cancelamento ou alteração de prazo SHALL ser oferecida.

#### Scenario: Registro confirmado
- **WHEN** a criação é confirmada
- **THEN** a consulta retorna dados persistidos e permite identificar cliente, exemplar, datas e status
- **AND** não apresenta saldos ou cobranças simulados

#### Scenario: Auditoria falha após commit
- **WHEN** a locação foi gravada mas o evento não foi confirmado
- **THEN** o resultado informa gravação confirmada com falha de auditoria e não orienta criar outra locação

#### Scenario: Consulta de locação devolvida
- **WHEN** a locação consultada já foi devolvida
- **THEN** a resposta inclui status `returned`, `returned_at` e `returned_by`, mantendo os demais campos originais
