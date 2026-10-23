# Disponibilidade para locação

## Purpose

Controlar a elegibilidade operacional de cada exemplar sem confundir existência no cadastro, condição física e ocupação por uma locação ativa.

## ADDED Requirements

### Requirement: Exemplares sem confirmação não são presumidos disponíveis

O sistema SHALL representar condição operacional como `unverified`, `available` ou `unavailable`. Registros existentes ou novos sem confirmação explícita SHALL ser tratados como `unverified`. Disponibilidade para nova locação SHALL exigir condição `available`, filme ativo e ausência de ocupação ativa, calculadas no backend. Quantidade de estoque do filme SHALL NOT determinar disponibilidade.

#### Scenario: Exemplar legado
- **WHEN** a condição de um exemplar existente ainda não foi confirmada
- **THEN** ele não aparece entre as opções disponíveis para locação
- **AND** seu cadastro, identificador e associação ao filme permanecem preservados

#### Scenario: Exemplar ocupado
- **WHEN** um exemplar com condição `available` possui locação ativa
- **THEN** a consulta não o oferece para nova locação

### Requirement: Confirmação operacional exige administrador e rastreabilidade

Somente conta ativa `admin` SHALL confirmar ou alterar a condição operacional de exemplar existente por operação protegida própria, com motivo não vazio e auditoria mínima de usuário, ação, resultado e exemplar, sem registrar texto livre do motivo no evento. Alteração SHALL NOT remover ocupação, encerrar locação, modificar identificação do exemplar ou promover permissões de `member`.

#### Scenario: Administrador confirma exemplar
- **WHEN** um administrador verifica um exemplar e confirma condição `available` com motivo
- **THEN** a condição é persistida com responsável e instante de confirmação
- **AND** a disponibilidade continua dependendo de filme ativo e ausência de ocupação

#### Scenario: Member tenta liberar exemplar
- **WHEN** um `member` chama diretamente a operação administrativa de condição
- **THEN** o backend recusa antes de gravar

#### Scenario: Tentativa de liberar exemplar alugado
- **WHEN** a condição é alterada para `available` enquanto existe locação ativa
- **THEN** o exemplar continua indisponível para nova locação e a ocupação permanece intacta

### Requirement: Consulta de opções exige autorização e resultado real

Contas ativas `member` e `admin` SHALL poder consultar exemplares elegíveis e sua identificação e filme associado por consulta própria paginada. Falha de rede ou serviço SHALL NOT ser representada como lista vazia bem-sucedida. A seleção consultada SHALL NOT substituir a revalidação do backend no registro da locação.

#### Scenario: Nenhum exemplar elegível
- **WHEN** a consulta termina com sucesso sem exemplares elegíveis
- **THEN** a interface apresenta ausência de opções disponíveis sem sugerir dados fictícios

#### Scenario: Condição mudou depois da consulta
- **WHEN** o exemplar selecionado deixa de estar elegível antes da confirmação
- **THEN** o registro é recusado e a interface permite atualizar as opções
