# gestao-usuarios Specification

## Purpose
Consulta e alteração protegidas do papel e da situação das contas internas.

## Requirements

### Requirement: Listagem de contas restrita a administradores

O backend SHALL oferecer a lista das contas internas somente a contas ativas `admin`, verificando o papel antes de ler dados. Cada conta SHALL ser devolvida apenas com identificador, nome, e-mail, papel, situação e data de cadastro; senha e dados de recuperação de senha SHALL NOT ser devolvidos. Conta sem situação explícita SHALL ser apresentada como ativa.

#### Scenario: Admin consulta as contas
- **WHEN** uma conta ativa `admin` solicita a lista de usuários
- **THEN** o backend devolve as contas ordenadas por nome, com os campos permitidos

#### Scenario: Member tenta consultar
- **WHEN** uma conta `member` solicita a lista de usuários
- **THEN** o backend recusa a operação sem devolver dados

#### Scenario: Dados sensíveis
- **WHEN** a lista é devolvida
- **THEN** nenhum item contém senha ou dados de recuperação de senha

### Requirement: Admin altera papel e situação de outras contas

O backend SHALL permitir que uma conta ativa `admin` defina o papel (`admin` ou `member`) e a situação (ativa ou desativada) de outra conta, com motivo obrigatório de até 500 caracteres. A operação SHALL bloquear as contas envolvidas em ordem fixa, verificar de novo o papel e a situação do ator dentro da transação e recusar envio que não muda nada. Nenhuma conta SHALL ser excluída, e nome, e-mail e senha SHALL NOT ser alterados por esta operação.

#### Scenario: Promoção a administrador
- **WHEN** um admin define `admin` para uma conta `member`, com motivo
- **THEN** a conta passa a ter papel `admin`

#### Scenario: Desativação
- **WHEN** um admin desativa outra conta, com motivo
- **THEN** a conta passa a desativada
- **AND** o login e as operações protegidas dessa conta passam a ser recusados

#### Scenario: Reativação
- **WHEN** um admin reativa uma conta desativada, com motivo
- **THEN** a conta volta a poder entrar e operar conforme o seu papel

#### Scenario: Motivo ausente
- **WHEN** a alteração é enviada sem motivo
- **THEN** o backend recusa sem alterar a conta

#### Scenario: Nada a alterar
- **WHEN** o papel e a situação enviados são iguais aos atuais
- **THEN** o backend recusa com "Nenhuma alteração informada." sem gravar nada

#### Scenario: Member tenta alterar
- **WHEN** uma conta `member` chama a alteração
- **THEN** o backend recusa antes de ler ou alterar qualquer conta

### Requirement: Sempre resta ao menos um administrador ativo

O backend SHALL recusar que uma conta altere o próprio papel ou a própria situação. Assim, quem executa a alteração continua `admin` ativo, e a locadora nunca fica sem administrador ativo, mesmo com alterações simultâneas.

#### Scenario: Admin tenta alterar a própria conta
- **WHEN** um admin envia uma alteração para a própria conta
- **THEN** o backend recusa com "Você não pode alterar a própria conta."

#### Scenario: Dois admins rebaixam um ao outro ao mesmo tempo
- **WHEN** dois admins enviam ao mesmo tempo o rebaixamento um do outro
- **THEN** no máximo uma das operações é aplicada
- **AND** a outra é recusada porque o ator já não é `admin`

### Requirement: Alterações de conta são auditadas

Cada alteração aplicada SHALL gerar um evento `update_user` com o ator, a conta alterada, os valores anteriores e novos de papel e situação e o motivo. Falha ao registrar o evento SHALL NOT desfazer a alteração e SHALL ser informada na resposta.

#### Scenario: Alteração registrada
- **WHEN** um admin altera o papel ou a situação de uma conta
- **THEN** o log de eventos recebe `update_user` com o antes, o depois e o motivo
