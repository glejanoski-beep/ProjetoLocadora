# Spec Delta

## Purpose

Impedir que a conferência operacional devolva à locação um exemplar baixado.

## MODIFIED Requirements

### Requirement: Confirmação operacional exige administrador e rastreabilidade

Somente conta ativa `admin` SHALL confirmar ou alterar a condição operacional de exemplar existente por operação protegida própria, com motivo não vazio e auditoria mínima de usuário, ação, resultado e exemplar, sem registrar texto livre do motivo no evento. Alteração SHALL NOT remover ocupação, encerrar locação, modificar identificação do exemplar ou promover permissões de `member`. Exemplar baixado SHALL ter a conferência recusada até ser reativado.

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

#### Scenario: Tentativa de liberar exemplar baixado
- **WHEN** o administrador tenta confirmar `available` para um exemplar baixado
- **THEN** o backend recusa com "Exemplar baixado: reative antes de conferir." sem alterar a condição
